import pandas as pd
import numpy as np
from math import log2, sqrt


### Static helpers

def _get_coi_meta(partition):
    """
    lazy accessor for static coi metadata. computed once, cached on graph.

    outputs:
        meta: {coi_id: {'category': str, 'total_pop': float}}
    """
    graph_attrs = partition.graph.graph.graph
    meta = graph_attrs.get('_coi_meta', None)
    if meta is not None:
        return meta

    # scan all nodes once to build category + total pop per community
    coi_pops = {}
    coi_cats = {}

    for node_id in partition.graph.nodes:
        node_cois = partition.graph.nodes[node_id].get('COI_POPS', {})
        for coi_id, coi_data in node_cois.items():
            pop = float(coi_data.get('pop', 0))
            coi_pops[coi_id] = coi_pops.get(coi_id, 0) + pop

            if coi_id not in coi_cats:
                cat_val = coi_data.get('category', 'coi')
                if isinstance(cat_val, pd.Series):
                    cat_val = cat_val.iloc[0]
                elif isinstance(cat_val, list):
                    cat_val = cat_val[0]
                coi_cats[coi_id] = str(cat_val)

    meta = {
        coi_id: {
            'category': coi_cats.get(coi_id, 'coi'),
            'total_pop': coi_pops.get(coi_id, 0),
        }
        for coi_id in coi_pops
    }

    graph_attrs['_coi_meta'] = meta
    return meta


def _compute_sss(cdp, meta):
    """sum of squared shares per community from district pops"""
    sss = {}
    for coi_id, dist_pops in cdp.items():
        tp = meta[coi_id]['total_pop']
        if tp <= 0:
            sss[coi_id] = 1.0
            continue
        sss[coi_id] = sum((p / tp) ** 2 for p in dist_pops.values() if p > 0)
    return sss


def _compute_tcp(sss, meta, weights):
    """tcp from sss scores — pop-weighted avg per category, then category-weighted sum"""
    cat_weighted_sum = {}
    cat_total_pop = {}
    for coi_id, score in sss.items():
        cat = meta[coi_id]['category']
        tp = meta[coi_id]['total_pop']
        cat_weighted_sum[cat] = cat_weighted_sum.get(cat, 0) + score * tp
        cat_total_pop[cat] = cat_total_pop.get(cat, 0) + tp

    tcp = 0
    for cat, w in weights.items():
        cp = cat_total_pop.get(cat, 0)
        if cp > 0:
            tcp += w * (cat_weighted_sum[cat] / cp)
    return tcp


### Core incremental updaters

def coi_district_pops(partition):
    """
    incrementally maintains {coi_id: {district_id: pop}}.
    register as '_coi_state' in updaters_dict.

    on initial partition, scans all nodes.
    on subsequent steps, only processes nodes that actually moved (via partition.flows).
    """
    if partition.parent is None:
        # full build from scratch
        cdp = {}
        for node_id in partition.graph.nodes:
            dist = partition.assignment[node_id]
            node_cois = partition.graph.nodes[node_id].get('COI_POPS', {})
            for coi_id, coi_data in node_cois.items():
                if coi_id not in cdp:
                    cdp[coi_id] = {}
                pop = float(coi_data.get('pop', 0))
                cdp[coi_id][dist] = cdp[coi_id].get(dist, 0) + pop
        return cdp

    # incremental update — only touch cois affected by the 2 changed districts
    parent_cdp = partition.parent['_coi_state']
    cdp = dict(parent_cdp)  # shallow copy outer dict (inner dicts shared w/ parent)
    copied = set()  # track which inner dicts we've already copied

    for dist, flow in partition.flows.items():
        # nodes that left this district
        for node_id in flow['out']:
            node_cois = partition.graph.nodes[node_id].get('COI_POPS', {})
            for coi_id, coi_data in node_cois.items():
                if coi_id not in copied:
                    cdp[coi_id] = dict(parent_cdp.get(coi_id, {}))
                    copied.add(coi_id)
                pop = float(coi_data.get('pop', 0))
                cdp[coi_id][dist] = cdp[coi_id].get(dist, 0) - pop

        # nodes that entered this district
        for node_id in flow['in']:
            node_cois = partition.graph.nodes[node_id].get('COI_POPS', {})
            for coi_id, coi_data in node_cois.items():
                if coi_id not in copied:
                    cdp[coi_id] = dict(parent_cdp.get(coi_id, {}))
                    copied.add(coi_id)
                pop = float(coi_data.get('pop', 0))
                cdp[coi_id][dist] = cdp[coi_id].get(dist, 0) + pop

    # clean near-zero entries from floating point drift
    for coi_id in copied:
        cdp[coi_id] = {d: p for d, p in cdp[coi_id].items() if p > 1e-10}

    return cdp


def partisan_data(partition):
    """
    incrementally maintains per-district partisan vote totals.
    register as '_partisan' in updaters_dict.

    outputs:
        (dem_by_dist, tot_by_dist): two dicts {district_id: vote_count}
    """
    if partition.parent is None:
        dem = {}
        tot = {}
        for dist, nodes in partition.parts.items():
            dem[dist] = sum(partition.graph.nodes[n].get('PRE20D', 0) for n in nodes)
            tot[dist] = sum(partition.graph.nodes[n].get('TOTVOTES20', 0) for n in nodes)
        return dem, tot

    parent_dem, parent_tot = partition.parent['_partisan']
    dem = dict(parent_dem)
    tot = dict(parent_tot)

    for dist, flow in partition.flows.items():
        for node_id in flow['out']:
            dem[dist] -= partition.graph.nodes[node_id].get('PRE20D', 0)
            tot[dist] -= partition.graph.nodes[node_id].get('TOTVOTES20', 0)
        for node_id in flow['in']:
            dem[dist] += partition.graph.nodes[node_id].get('PRE20D', 0)
            tot[dist] += partition.graph.nodes[node_id].get('TOTVOTES20', 0)

    return dem, tot


### TCP metrics

def calculate_unweighted_tcp(partition):
    """tcp with equal weight per category. requires '_coi_state' updater."""
    cdp = partition['_coi_state']
    meta = _get_coi_meta(partition)
    sss = _compute_sss(cdp, meta)

    categories = set(m['category'] for m in meta.values())
    n = len(categories)
    weights = {cat: 1.0 / n for cat in categories} if n > 0 else {}

    return _compute_tcp(sss, meta, weights)


def calculate_weighted_tcp(partition):
    """tcp with weights from WEIGHT_MAP on graph. requires '_coi_state' updater."""
    cdp = partition['_coi_state']
    meta = _get_coi_meta(partition)
    sss = _compute_sss(cdp, meta)

    categories = set(m['category'] for m in meta.values())
    weight_map = partition.graph.graph.graph.get('WEIGHT_MAP', {})
    raw_weights = {cat: weight_map.get(cat, 1.0) for cat in categories}
    total_w = sum(raw_weights.values())
    weights = {cat: v / total_w for cat, v in raw_weights.items()} if total_w > 0 else {}

    return _compute_tcp(sss, meta, weights)


### Partisan metrics

def count_dem_wins(partition):
    """requires '_partisan' updater"""
    dem, tot = partition['_partisan']
    return sum(1 for d in dem if tot[d] > 0 and (dem[d] / tot[d]) > 0.5)


def dem_share(partition):
    """requires '_partisan' updater"""
    dem, tot = partition['_partisan']
    return sorted(dem[d] / tot[d] if tot[d] > 0 else 0 for d in dem)


def dem_boxes(partition):
    """requires '_partisan' updater"""
    dem, tot = partition['_partisan']
    return sorted(dem[d] / tot[d] if tot[d] > 0 else 0 for d in dem)


### Other COI metrics

def communities_split(partition):
    """count of communities appearing in more than 1 district. requires '_coi_state'."""
    cdp = partition['_coi_state']
    return sum(1 for dist_pops in cdp.values() if len(dist_pops) > 1)


def community_fragments(partition):
    """total number of community pieces (district intersections). requires '_coi_state'."""
    cdp = partition['_coi_state']
    return sum(len(dist_pops) for dist_pops in cdp.values())


def count_county_splits(partition):
    """requires 'county_splits' updater from gerrychain"""
    splits_dict = partition['county_splits']
    return sum(1 for info in splits_dict.values() if len(info.contains) > 1)


def count_county_fragments(partition):
    """requires 'county_splits' updater from gerrychain"""
    splits_dict = partition['county_splits']
    return sum(len(info.contains) for info in splits_dict.values())


def effective_splits(partition):
    """pop-weighted avg of (1/sss - 1). requires '_coi_state'."""
    cdp = partition['_coi_state']
    meta = _get_coi_meta(partition)
    sss = _compute_sss(cdp, meta)

    weighted_sum = 0
    total_pop = 0
    for coi_id, score in sss.items():
        tp = meta[coi_id]['total_pop']
        eff = (1.0 / score) - 1 if score > 0 else 0
        weighted_sum += eff * tp
        total_pop += tp

    return weighted_sum / total_pop if total_pop > 0 else 0


def square_root_entropy(partition):
    """sum of sqrt(share) across all community-district pairs. requires '_coi_state'."""
    cdp = partition['_coi_state']
    meta = _get_coi_meta(partition)

    total = 0
    for coi_id, dist_pops in cdp.items():
        tp = meta[coi_id]['total_pop']
        if tp <= 0:
            continue
        for p in dist_pops.values():
            if p > 0:
                total += sqrt(p / tp)
    return total


def shannon_entropy(partition):
    """sum of share * log2(total/pop) across all community-district pairs. requires '_coi_state'."""
    cdp = partition['_coi_state']
    meta = _get_coi_meta(partition)

    total = 0
    for coi_id, dist_pops in cdp.items():
        tp = meta[coi_id]['total_pop']
        if tp <= 0:
            continue
        for p in dist_pops.values():
            if p > 0:
                share = p / tp
                total += share * log2(tp / p)
    return total


def even_splits(partition):
    """sum of splits * (1 - min_share) across communities. requires '_coi_state'."""
    cdp = partition['_coi_state']
    meta = _get_coi_meta(partition)

    total = 0
    for coi_id, dist_pops in cdp.items():
        pops = list(dist_pops.values())
        tp = meta[coi_id]['total_pop']
        if tp <= 0:
            continue
        min_share = min(pops) / tp
        total += len(pops) * (1 - min_share)
    return total


### Chain helpers

def collect_metrics(partition, keys):
    """
    collects metrics from a partition into a dict for dataframe construction.

    inputs:
        partition: gerrychain partition with updaters
        keys: list of updater keys to collect
    outputs:
        dict of {key: value} for each requested metric
    """
    return {k: partition[k] for k in keys}


### Legacy compatibility
# these are slow (full graph scan + pandas groupby) but preserved for
# plotting.py and old notebooks that have local copies.

def extract_data(partition):
    """extracts coi data from a gerrychain partition into a dataframe."""
    data_rows = []

    for node_id in partition.graph.nodes:
        assigned_dist = partition.assignment[node_id]
        node_cois = partition.graph.nodes[node_id].get('COI_POPS', {})

        for coi_id, coi_data in node_cois.items():
            cat_val = coi_data.get('category', 'coi')
            if isinstance(cat_val, pd.Series):
                cat_val = cat_val.iloc[0]
            elif isinstance(cat_val, list):
                cat_val = cat_val[0]

            data_rows.append(
                {
                    'category': str(cat_val),
                    'community_id': str(coi_id),
                    'district': assigned_dist,
                    'pop': float(coi_data.get('pop', 0)),
                }
            )

    return pd.DataFrame(data_rows)


def score_communities(unscored_df):
    """
    calculates the sum of squared shares for each community

    inputs:
        unscored_df: df with cols: category, community_id, district, pop
    outputs:
        communities_scores: df with cols: category, community_id, total_pop, sss_score
    """
    total_pops = (
        unscored_df.groupby(['category', 'community_id'])['pop'].sum().reset_index()
    )
    total_pops.rename(columns={'pop': 'total_pop'}, inplace=True)

    district_splits = (
        unscored_df.groupby(['category', 'community_id', 'district'])['pop']
        .sum()
        .reset_index()
    )

    merged = pd.merge(district_splits, total_pops, on=['category', 'community_id'])
    merged['share'] = merged['pop'] / merged['total_pop']
    merged['squared_share'] = merged['share'] ** 2

    final_sss_df = (
        merged.groupby(['category', 'community_id', 'total_pop'])['squared_share']
        .sum()
        .reset_index()
    )
    final_sss_df.rename(columns={'squared_share': 'sss_score'}, inplace=True)
    return final_sss_df


def score_overall(dataframe, weights):
    """
    calculates total coi preservation as a single metric between 0 and 1

    inputs:
        dataframe: output from score_communities()
        weights: dict with keys: category, values: weight
    outputs:
        final_score: tcp between 0 and 1
    """
    dataframe['weighted_score'] = dataframe['sss_score'] * dataframe['total_pop']
    category_score_sums = dataframe.groupby('category')['weighted_score'].sum()
    category_pop_sums = dataframe.groupby('category')['total_pop'].sum()

    pop_weighted_avg = category_score_sums / category_pop_sums
    final_score = (pop_weighted_avg * pd.Series(weights)).sum()
    return final_score
