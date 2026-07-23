import argparse
import json
import os
import random
import pandas as pd
from functools import partial
from tqdm import tqdm

from pathlib import Path
from gerrychain import Partition, Graph, MarkovChain
from gerrychain.accept import always_accept
from gerrychain.proposals import recom
from gerrychain.updaters import cut_edges, county_splits
from gerrychain.tree import recursive_tree_part

from common import scoring, acceptance

def run_chain(
    state,
    dist_level,
    accept_strategy,
    weights_file,
    steps,
    desired_tcp,
    csv_filename,
    gallery_dir,
    region_surcharge,
    position,
    coi_map
):
    # load graph
    graph_path = Path(state) / "data" / f"{state}_{dist_level}_{coi_map}.json"
    if not graph_path.exists() and state == 'co':
        graph_path = Path(state) / "data" / "coi_graphs" / f"{state}_{dist_level}_{coi_map}.json"
    if not graph_path.exists() and state == 'mo':
        # MO might not have dist_level in filename if we used mo_cog_graph
        graph_path = Path(state) / "data" / f"{state}_cog_{coi_map}.json"

    if not graph_path.exists():
        raise FileNotFoundError(
            f"Graph file not found for state={state}, dist_level={dist_level}, coi_map={coi_map}: tried {graph_path}"
        )

    g = Graph.from_json(graph_path.as_posix())

    # load weights
    weights_path = Path("weights") / f"{weights_file}.json"
    with open(weights_path, "r") as f:
        state_weights = json.load(f)
    
    g.graph['DESIRED_TCP'] = desired_tcp
    g.graph['WEIGHT_MAP'] = state_weights

    # determine parts
    if state == "mo":
        dist_parts = 8
    else:
        if dist_level == "cog":
            dist_parts = 8
        elif dist_level == "ss":
            dist_parts = 35
        elif dist_level == "sh":
            dist_parts = 65

    total_population = sum(node.get('TOTPOP', 1) for node in g.nodes.values())
    target_pop = total_population / dist_parts

    starting_assignment = recursive_tree_part(
        g, 
        parts=range(dist_parts), 
        pop_target=target_pop, 
        pop_col="TOTPOP", 
        epsilon=0.05
    )

    updaters_dict = { 
        '_coi_state': scoring.coi_district_pops,
        '_partisan': scoring.partisan_data, 
        'unweighted_tcp_score': scoring.calculate_unweighted_tcp,
        'weighted_tcp_score': scoring.calculate_weighted_tcp,
        'communities_split': scoring.communities_split,
        'effective_splits': scoring.effective_splits,
        'sr_entropy': scoring.square_root_entropy,
        'shannon_entropy': scoring.shannon_entropy,
        'even_splits': scoring.even_splits,
        'cut_edges': cut_edges,
        'dem_wins': scoring.count_dem_wins,
        'dem_share': scoring.dem_share,
        'dem_box': scoring.dem_boxes,
        'county_splits': county_splits('county_splits', 'COUNTYFP20'),
        'county_split_count': scoring.count_county_splits,
        'county_fragments': scoring.count_county_fragments,
        'community_fragments': scoring.community_fragments
    }

    initial_partition = Partition(
        g, 
        assignment=starting_assignment, 
        updaters=updaters_dict
    )

    proposal = partial(
        recom, 
        pop_col="TOTPOP", 
        pop_target=target_pop, 
        epsilon=0.05, 
        node_repeats=2, 
        region_surcharge=region_surcharge
    )

    accept_function = acceptance.STRATEGIES.get(accept_strategy, always_accept)

    chain = MarkovChain(
        proposal=proposal,
        constraints=[],
        accept=accept_function,
        initial_state=initial_partition,
        total_steps=steps
    )

    csv_path = Path(csv_filename)
    gallery_path = Path(gallery_dir)

    gallery_path.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    base_path = gallery_path / "base_assignment.json"
    diffs_path = gallery_path / "diffs.jsonl"

    # remove old files if exist
    for p in [base_path, diffs_path, csv_path]:
        if p.exists():
            p.unlink()

    prev_assignment = None
    diffs_file = open(diffs_path, 'w')

    chain_results = []
    chunk_size = 1000
    num_districts = len(initial_partition.parts)

    pbar = tqdm(total=steps, position=position, desc=f"{state} {accept_strategy}", leave=True)

    for step, partition in enumerate(chain):
        is_accepted = 1 if (partition.parent is not None and partition is not partition.parent) else 0

        # Collect metrics
        metrics = scoring.collect_metrics(partition, [
            'weighted_tcp_score', 'unweighted_tcp_score', 'communities_split',
            'effective_splits', 'sr_entropy', 'shannon_entropy', 'even_splits',
            'dem_wins', 'dem_share', 'cut_edges', 'county_split_count', 'county_fragments', 'community_fragments'
        ])

        row = {
            'step': step,
            'weighted_tcp_score': metrics['weighted_tcp_score'],
            'unweighted_tcp_score': metrics['unweighted_tcp_score'],
            'communities_split': metrics['communities_split'],
            'effective_splits': metrics['effective_splits'],
            'sr_entropy': metrics['sr_entropy'],
            'shannon_entropy': metrics['shannon_entropy'],
            'even_splits': metrics['even_splits'],
            'cut_edges': len(metrics['cut_edges']),
            'dem_wins': metrics['dem_wins'],
            'accepted': is_accepted,
            'county_split_count': metrics['county_split_count'],
            'county_fragments': metrics['county_fragments'],
            'community_fragments': metrics['community_fragments']
        }
        for i in range(num_districts):
            row[f'dist_{i+1}_dem_share'] = metrics['dem_share'][i]
            
        chain_results.append(row)

        # Handle diff storage
        current_assignment = partition.assignment.to_dict()
        if step == 0:
            with open(base_path, 'w') as f:
                json.dump(current_assignment, f)
        else:
            if is_accepted:
                diff = {node: val for node, val in current_assignment.items() if val != prev_assignment[node]}
                diffs_file.write(json.dumps(diff) + '\n')
            else:
                diffs_file.write('{}\n') # empty diff for rejected steps

        prev_assignment = current_assignment.copy()

        pbar.update(1)

        # flush CSV
        if (step + 1) % chunk_size == 0 or (step + 1) == steps:
            df = pd.DataFrame(chain_results)
            df.to_csv(csv_path, mode='a', header=not csv_path.exists(), index=False)
            chain_results = []

    diffs_file.close()
    pbar.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=str, required=True)
    parser.add_argument("--dist_level", type=str, default="cog")
    parser.add_argument("--accept_strategy", type=str, required=True)
    parser.add_argument("--weights_file", type=str, required=True)
    parser.add_argument("--steps", type=int, required=True)
    parser.add_argument("--desired_tcp", type=float, required=True)
    parser.add_argument("--csv_filename", type=str, required=True)
    parser.add_argument("--gallery_dir", type=str, required=True)
    parser.add_argument("--region_surcharge", type=str, default="{}")
    parser.add_argument("--position", type=int, default=0)
    parser.add_argument("--coi_map", type=str, default="graph")

    args = parser.parse_args()
    
    surcharge_dict = json.loads(args.region_surcharge)

    run_chain(
        state=args.state,
        dist_level=args.dist_level,
        accept_strategy=args.accept_strategy,
        weights_file=args.weights_file,
        steps=args.steps,
        desired_tcp=args.desired_tcp,
        csv_filename=args.csv_filename,
        gallery_dir=args.gallery_dir,
        region_surcharge=surcharge_dict,
        position=args.position,
        coi_map=args.coi_map
    )
