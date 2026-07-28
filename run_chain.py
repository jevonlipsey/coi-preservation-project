import argparse
import gzip
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
        graph_path = Path(state) / "data" / "coi-graphs" / f"{state}_{dist_level}_{coi_map}.json"
        if not graph_path.exists():
            graph_path = Path(state) / "data" / "coi_graphs" / f"{state}_{dist_level}_{coi_map}.json"
    if not graph_path.exists() and state == 'mo':
        # mo might not have dist_level in filename if we used mo_cog_graph
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

    csv_path = Path(csv_filename)
    gallery_path = Path(gallery_dir)

    gallery_path.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    surcharge_label = gallery_path.parent.name if "county_" in gallery_path.parent.name else "no_surcharge"
    short_surcharge = surcharge_label.replace("county_", "").replace("_coi_", "/")
    parts = csv_path.stem.split("_")
    seed_label = parts[-1] if parts and parts[-1].startswith("v") and parts[-1][1:].isdigit() else "v1"

    desc_str = f"{dist_level:<3} {accept_strategy:<15} {short_surcharge:<4} {seed_label:<2}"
    log_prefix = f"[{coi_map} | {dist_level} | {accept_strategy} | {surcharge_label} | {seed_label}]"

    base_path = gallery_path / "base_assignment.json"
    diffs_path = gallery_path / "diffs.jsonl.gz"
    legacy_diffs_path = gallery_path / "diffs.jsonl"

    start_step = 0
    clean_diff_lines = []
    reconstructed_assignment = None

    if csv_path.exists() and base_path.exists():
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                num_lines = sum(1 for line in f if line.strip())
            completed_steps = max(0, num_lines - 1)

            if completed_steps >= steps:
                print(f"{log_prefix} Run already completed ({completed_steps:,}/{steps:,} steps). Skipping.")
                return

            if completed_steps > 0:
                with open(base_path, "r", encoding="utf-8") as f:
                    loaded_base = json.load(f)

                node_key_type = type(next(iter(g.nodes())))
                reconstructed_assignment = {node_key_type(k): v for k, v in loaded_base.items()}

                diffs_target_count = completed_steps - 1

                if diffs_target_count > 0:
                    target_diffs = diffs_path if diffs_path.exists() else (legacy_diffs_path if legacy_diffs_path.exists() else None)
                    if target_diffs is None:
                        print(f"{log_prefix} Warning: Diffs missing for resuming {completed_steps:,} steps. Starting fresh.")
                        start_step = 0
                    else:
                        opener = gzip.open if target_diffs.suffix == '.gz' else open
                        mode = 'rt' if target_diffs.suffix == '.gz' else 'r'
                        try:
                            with opener(target_diffs, mode, encoding='utf-8') as f:
                                for idx, line in enumerate(f):
                                    if idx < diffs_target_count:
                                        clean_diff_lines.append(line.rstrip('\r\n') + '\n')
                                        diff_dict = json.loads(line.strip())
                                        for k, v in diff_dict.items():
                                            if isinstance(v, list):
                                                try:
                                                    dist_val = int(k)
                                                except ValueError:
                                                    dist_val = k
                                                for node in v:
                                                    reconstructed_assignment[node_key_type(node)] = dist_val
                                            else:
                                                reconstructed_assignment[node_key_type(k)] = v
                                    else:
                                        break
                        except Exception as stream_err:
                            # catch EOFError, zlib.error, JSONDecodeError from abrupt system crash mid-write
                            pass

                        if len(clean_diff_lines) < diffs_target_count:
                            if len(clean_diff_lines) > 0:
                                recovered_steps = len(clean_diff_lines) + 1
                                print(f"{log_prefix} Recovered {recovered_steps:,} steps before truncated gzip stream cut-off. Resynchronizing CSV...")
                                try:
                                    with open(csv_path, "r", encoding="utf-8") as f:
                                        valid_rows = [next(f)]  # header
                                        for _ in range(recovered_steps):
                                            valid_rows.append(next(f))
                                    with open(csv_path, "w", encoding="utf-8") as f:
                                        f.writelines(valid_rows)
                                    start_step = recovered_steps
                                except Exception as sync_err:
                                    print(f"{log_prefix} Warning: Could not resync CSV ({sync_err}). Starting fresh.")
                                    start_step = 0
                                    reconstructed_assignment = None
                                    clean_diff_lines = []
                            else:
                                print(f"{log_prefix} Warning: Found 0 diffs (expected {diffs_target_count:,}). Starting fresh.")
                                start_step = 0
                                reconstructed_assignment = None
                                clean_diff_lines = []
                        else:
                            start_step = completed_steps
                else:
                    start_step = completed_steps

                if start_step > 0:
                    pct = (start_step / steps) * 100 if steps > 0 else 0
                    print(f"{log_prefix} Resuming from checkpoint at step {start_step:,}/{steps:,} ({pct:.1f}%)...")
        except Exception as e:
            print(f"{log_prefix} Warning: Could not resume from checkpoint ({e}). Starting fresh.")
            start_step = 0
            reconstructed_assignment = None
            clean_diff_lines = []

    if start_step == 0:
        for p in [base_path, diffs_path, legacy_diffs_path, csv_path]:
            if p.exists():
                p.unlink()
        starting_assignment = recursive_tree_part(
            g, 
            parts=range(dist_parts), 
            pop_target=target_pop, 
            pop_col="TOTPOP", 
            epsilon=0.05
        )
    else:
        starting_assignment = reconstructed_assignment

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

    if start_step > 0:
        total_chain_steps = steps - start_step + 1
        current_step_num = start_step - 1
    else:
        total_chain_steps = steps
        current_step_num = 0

    chain = MarkovChain(
        proposal=proposal,
        constraints=[],
        accept=accept_function,
        initial_state=initial_partition,
        total_steps=total_chain_steps
    )

    prev_assignment = None
    diffs_file = gzip.open(diffs_path, 'wt', encoding='utf-8')
    if start_step > 0:
        if clean_diff_lines:
            for line in clean_diff_lines:
                diffs_file.write(line)
        del clean_diff_lines

    chain_results = []
    chunk_size = 1000
    num_districts = len(initial_partition.parts)

    pbar = tqdm(total=steps, initial=start_step, position=position, desc=desc_str, leave=True)

    for partition in chain:
        if start_step > 0 and current_step_num < start_step:
            prev_assignment = partition.assignment.to_dict()
            current_step_num += 1
            continue

        step = current_step_num
        is_accepted = 1 if (partition.parent is not None and partition is not partition.parent) else 0

        # collect metrics
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

        # handle diff storage using compressed inverted lists {district: [node_ids]}
        if step == 0:
            current_assignment = partition.assignment.to_dict()
            with open(base_path, 'w') as f:
                json.dump(current_assignment, f)
            prev_assignment = current_assignment.copy()
        elif is_accepted:
            current_assignment = partition.assignment.to_dict()
            inv_diff = {}
            for node, val in current_assignment.items():
                if val != prev_assignment[node]:
                    str_val = str(val)
                    if str_val not in inv_diff:
                        inv_diff[str_val] = []
                    inv_diff[str_val].append(int(node))
            for k in inv_diff:
                inv_diff[k].sort()
            diffs_file.write(json.dumps(inv_diff) + '\n')
            prev_assignment = current_assignment.copy()
        else:
            diffs_file.write('{}\n')  # empty diff for rejected steps

        pbar.update(1)

        # flush csv
        if (step + 1) % chunk_size == 0 or (step + 1) == steps:
            df = pd.DataFrame(chain_results)
            df.to_csv(csv_path, mode='a', header=not csv_path.exists(), index=False)
            chain_results = []

        # break linked-list memory retention to prevent memory accumulation & gc thrashing over long runs
        if partition.parent is not None and partition.parent is not partition:
            if partition.parent.parent is not None and partition.parent.parent is not partition.parent:
                partition.parent.parent = None

        current_step_num += 1

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
