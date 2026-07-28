import sys
from pathlib import Path

# import configuration from run_experiments
try:
    from run_experiments import (
        TARGET_STATES,
        COI_MAP,
        STEPS,
        DIST_LEVELS,
        SEEDS,
        CONFIGS,
        STATE_CONFIG,
        get_surcharge_vals,
    )
except ImportError as e:
    print(f"Error importing configuration from run_experiments.py: {e}")
    sys.exit(1)


### status report
def generate_status_report():
    print("=" * 130)
    print(f"STATUS REPORT FOR COI MAP: {COI_MAP} (Target Steps: {STEPS:,})")
    print("=" * 130)

    header = f"{'LEVEL':<6} {'STRATEGY':<16} {'SURCHARGE':<16} {'SEED':<6} {'STATUS':<14} {'PROGRESS':<25} {'CSV LOCATION'}"
    print(header)
    print("-" * 130)

    total_complete = 0
    total_in_progress = 0
    total_pending = 0

    configured_csvs = set()

    for state in TARGET_STATES:
        config = STATE_CONFIG[state]
        coi_map = config["coi_map"] if state == "mo" else COI_MAP

        for dist_level in DIST_LEVELS:
            for run_id in SEEDS:
                for cfg in CONFIGS:
                    objective = cfg.get("objective", "tcp")
                    surcharge = cfg.get("region_surcharge", {})
                    county_val, coi_val = get_surcharge_vals(surcharge)
                    surcharge_label = f"county_{county_val}_coi_{coi_val}"

                    results_dir = (
                        Path.cwd()
                        / "analysis"
                        / "results"
                        / objective
                        / coi_map
                        / dist_level
                        / surcharge_label
                    )
                    csv_name = f"{config['state_name']}_{dist_level}_{coi_map}_{cfg['accept']}_test_weights_{STEPS}_v{run_id}.csv"
                    csv_path = results_dir / csv_name

                    configured_csvs.add(csv_path.resolve())

                    rel_path = (
                        f"analysis/results/{objective}/{coi_map}/{dist_level}/{surcharge_label}/{csv_name}"
                    )
                    if len(rel_path) > 42:
                        # compact display if path is very long
                        rel_path = f".../{dist_level}/{surcharge_label}/{csv_name}"

                    if csv_path.exists():
                        try:
                            with open(csv_path, "r", encoding="utf-8") as f:
                                # count non-empty lines and subtract 1 for header
                                num_lines = sum(1 for line in f if line.strip())
                            completed = max(0, num_lines - 1)
                        except Exception:
                            completed = 0
                    else:
                        completed = 0

                    if completed >= STEPS:
                        status = "COMPLETE"
                        total_complete += 1
                    elif completed > 0:
                        status = "IN PROGRESS"
                        total_in_progress += 1
                    else:
                        status = "PENDING"
                        total_pending += 1

                    pct = (completed / STEPS) * 100 if STEPS > 0 else 0
                    progress_str = f"{completed:,} / {STEPS:,} ({pct:.1f}%)"
                    seed_str = f"v{run_id}"

                    print(
                        f"{dist_level:<6} {cfg['accept']:<16} {surcharge_label:<16} {seed_str:<6} {status:<14} {progress_str:<25} {rel_path}"
                    )

    print("-" * 130)
    print(
        f"SUMMARY: {total_complete} Complete | {total_in_progress} In Progress | {total_pending} Pending (Total Configured: {total_complete + total_in_progress + total_pending})"
    )
    print("=" * 130)

    # check for any additional csv files on disk that are not in the current configuration
    all_csvs = set(
        p.resolve() for p in Path("analysis/results").rglob("*.csv") if p.is_file()
    )
    other_csvs = sorted(all_csvs - configured_csvs)

    if other_csvs:
        print(f"\nOther existing experiment CSVs found on this computer ({len(other_csvs)} file(s)):")
        print("-" * 130)
        for p in other_csvs:
            try:
                with open(p, "r", encoding="utf-8") as f:
                    lines = max(0, sum(1 for line in f if line.strip()) - 1)
            except Exception:
                lines = 0
            try:
                rel = p.relative_to(Path.cwd())
            except ValueError:
                rel = p
            print(f"  {str(rel):<85} | {lines:,} steps recorded")
        print("-" * 130)


if __name__ == "__main__":
    generate_status_report()
