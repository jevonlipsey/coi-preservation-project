import pandas as pd
import numpy as np


### Util
def extract_data(partition):
    """
    extracts coi data from a gerrychain partition.
    """
    data_rows = []

    for node_id in partition.graph.nodes:
        assigned_dist = partition.assignment[node_id]
        node_cois = partition.graph.nodes[node_id].get("COI_POPS", {})

        for coi_id, coi_data in node_cois.items():
            cat_val = coi_data.get("category", "coi")
            if isinstance(cat_val, pd.Series):
                cat_val = cat_val.iloc[0]
            elif isinstance(cat_val, list):
                cat_val = cat_val[0]

            data_rows.append(
                {
                    "category": str(cat_val),
                    "community_id": str(coi_id),
                    "district": assigned_dist,
                    "pop": float(coi_data.get("pop", 0)),
                }
            )

    return pd.DataFrame(data_rows)


### TCP Functions
def score_communities(unscored_df):
    """
    calculates the sum of squared shares for each community

    inputs:
        unscored_df: df with cols: category, community_id, district, pop
    outputs:
        communities_scores: df with cols: category, community_id, total_pop, sss_score
    """
    # get total pop per community (water1, water2..)
    total_pops = (
        unscored_df.groupby(["category", "community_id"])["pop"].sum().reset_index()
    )
    total_pops.rename(columns={"pop": "total_pop"}, inplace=True)

    # get pop per community and district
    district_splits = (
        unscored_df.groupby(["category", "community_id", "district"])["pop"]
        .sum()
        .reset_index()
    )

    # merge to get pop / total pop
    merged = pd.merge(district_splits, total_pops, on=["category", "community_id"])

    # get squared shares
    merged["share"] = merged["pop"] / merged["total_pop"]
    merged["squared_share"] = merged["share"] ** 2

    # sum squared shares across all communities in each category
    # this is the 'final' score for each community (not grouped yet)
    final_sss_df = (
        merged.groupby(["category", "community_id", "total_pop"])["squared_share"]
        .sum()
        .reset_index()
    )
    final_sss_df.rename(columns={"squared_share": "sss_score"}, inplace=True)
    return final_sss_df


def score_overall(dataframe, weights):
    """
    calculates the total coi preservation as a single metric between 0 and 1

    inputs:
        dataframe: output from score_communities()
        weights: dict with keys: category, values: weight
    outputs:
        final_score: total coi preservation (tcp) between 0 and 1
    """
    # after getting sss score for each community, we want 1 final metric
    # bigger populations need more weight in category averages
    # get pop weighted avg for each community - sum(pop[i] * coi score / category pop
    dataframe["weighted_score"] = dataframe["sss_score"] * dataframe["total_pop"]
    category_score_sums = dataframe.groupby("category")["weighted_score"].sum()
    category_pop_sums = dataframe.groupby("category")["total_pop"].sum()

    # gets our category averages
    pop_weighted_avg = category_score_sums / category_pop_sums
    # multiply each category score by weight and sum for final metric
    final_score = (pop_weighted_avg * pd.Series(weights)).sum()
    return final_score


def calculate_unweighted_tcp(partition):
    """
    calculates tcp with equal weight for each category

    inputs:
        gerrychain partition (expected keys: raw_df)
    outputs:
        final_score: tcp between 0 and 1
    """
    # pull data and score communities
    raw_df = partition["raw_df"]
    community_scores = score_communities(raw_df)
    categories = community_scores["category"].unique()
    # flat weights for categories
    weights = {cat: 1.0 for cat in categories}
    # normalize so they sum to 1
    total_raw_weight = sum(weights.values())
    normalized_weights = {cat: val / total_raw_weight for cat, val in weights.items()}
    # compute final unweighted score
    final_score = score_overall(community_scores, normalized_weights)
    return final_score


def calculate_weighted_tcp(partition):
    """
    calculates tcp with weights for each category based on importance values

    inputs:
        gerrychain partition (expected keys: raw_df)
    outputs:
        final_score: tcp between 0 and 1
    """
    # pull data and score communities
    raw_df = partition["raw_df"]
    community_scores = score_communities(raw_df)
    categories = community_scores["category"].unique()
    # get importance values for categories
    weight_map = partition.graph.graph.get('WEIGHT_MAP', {})
    raw_weights = {cat: weight_map.get(cat, 1.0) for cat in categories}
    # normalize so they sum to 1
    total_raw_weight = sum(raw_weights.values())
    normalized_weights = {
        cat: val / total_raw_weight for cat, val in raw_weights.items()
    }
    # compute final weighted score
    final_score = score_overall(community_scores, normalized_weights)
    return final_score


### Partisan Metrics
def count_dem_wins(partition):
    dem_wins = 0
    for district_id, node_ids in partition.parts.items():
        dem_pop = sum(partition.graph.nodes[n]["PRE20D"] for n in node_ids)
        tot_pop = sum(partition.graph.nodes[n]["TOTVOTES20"] for n in node_ids)
        if tot_pop > 0 and (dem_pop / tot_pop) > 0.5:
            dem_wins += 1
    return dem_wins


def dem_share(partition):
    dem_shares = []
    for district_id, node_ids in partition.parts.items():
        dem_pop = sum(partition.graph.nodes[n]["PRE20D"] for n in node_ids)
        tot_pop = sum(partition.graph.nodes[n]["TOTVOTES20"] for n in node_ids)
        dem_shares.append(dem_pop / tot_pop if tot_pop > 0 else 0)
    return sorted(dem_shares)


def dem_boxes(partition):
    dem_shares = []
    for district_id, node_ids in partition.parts.items():
        dem_pop = sum(partition.graph.nodes[n]["PRE20D"] for n in node_ids)
        tot_pop = sum(partition.graph.nodes[n]["TOTVOTES20"] for n in node_ids)
        dem_shares.append(dem_pop / tot_pop if tot_pop > 0 else 0)
    return sorted(dem_shares)


### Other COI Metrics
def communities_split(partition):
    df = partition["raw_df"]
    ss_scores = score_communities(df)
    return (ss_scores["sss_score"] != 1).sum()


def square_root_entropy(partition):
    raw_df = partition["raw_df"]
    total_pops = raw_df.groupby(["category", "community_id"])["pop"].sum().reset_index()
    total_pops.rename(columns={"pop": "total_pop"}, inplace=True)
    district_splits = (
        raw_df.groupby(["category", "community_id", "district"])["pop"]
        .sum()
        .reset_index()
    )
    merged = pd.merge(district_splits, total_pops, on=["category", "community_id"])
    merged["share"] = merged["pop"] / merged["total_pop"]
    merged["sre_score"] = np.sqrt(merged["share"])
    final_sre_df = (
        merged.groupby(["category", "community_id", "total_pop"])["sre_score"]
        .sum()
        .reset_index()
    )
    return final_sre_df["sre_score"].sum()


def shannon_entropy(partition):
    raw_df = partition["raw_df"]
    total_pops = raw_df.groupby(["category", "community_id"])["pop"].sum().reset_index()
    total_pops.rename(columns={"pop": "total_pop"}, inplace=True)
    district_splits = (
        raw_df.groupby(["category", "community_id", "district"])["pop"]
        .sum()
        .reset_index()
    )
    merged = pd.merge(district_splits, total_pops, on=["category", "community_id"])
    merged["share"] = merged["pop"] / merged["total_pop"]
    merged["share_inv"] = merged["total_pop"] / merged["pop"]
    merged["se_score"] = merged["share"] * np.log2(merged["share_inv"])
    final_se_df = (
        merged.groupby(["category", "community_id", "total_pop"])["se_score"]
        .sum()
        .reset_index()
    )
    return final_se_df["se_score"].sum()


def even_splits(partition):
    raw_df = partition["raw_df"]
    total_pops = raw_df.groupby(["category", "community_id"])["pop"].sum().reset_index()
    total_pops.rename(columns={"pop": "total_pop"}, inplace=True)
    district_splits = (
        raw_df.groupby(["category", "community_id", "district"])["pop"]
        .sum()
        .reset_index()
    )
    merged = pd.merge(district_splits, total_pops, on=["category", "community_id"])
    es_score = 0
    for c_id in merged["community_id"].unique():
        muni_simp = merged[merged["community_id"] == c_id]
        splits = len(muni_simp)
        min_pop = muni_simp["pop"].min()
        total_pop = muni_simp["pop"].sum()
        min_share = min_pop / total_pop
        es_score += splits * (1 - min_share)
    return es_score
