import os
import time
import multiprocessing
import subprocess
import json
from pathlib import Path

### init
# run one or both
TARGET_STATES = ["co"]
STEPS = 250_000

STATE_CONFIG = {
    "mo": {"state_name": "missouri", "coi_map": "aggregated"},
    "co": {"state_name": "colorado", "coi_map": "representable"},
}

OBJECTIVES = ["tcp", "cs"]

STRATEGIES = [
    "simple_12_5",
    "simple_25",
    "simple_37_5",
    "simple_50",
    "neutral",
]

# For CO: 'COUNTYFP20', 'entry_ID'. For MO: 'COUNTYFP20', 'cluster_id'
SURCHARGES = [
    {"COUNTYFP20": 0},
    {"COUNTYFP20": 0.55},
    {"COUNTYFP20": 0.6},
    {"COUNTYFP20": 0.65},
    {"COUNTYFP20": 0.7},
]

experiments = []
for objective in OBJECTIVES:
    for surcharge_dict in SURCHARGES:
        for strategy in STRATEGIES:
            for run_id in (1, 2):
                experiments.append(
                    {
                        "accept": strategy,
                        "run_id": run_id,
                        "weights": "test_weights",
                        "steps": STEPS,
                        "desired_tcp": 0.85,
                        "objective": objective,
                        "region_surcharge": surcharge_dict,
                    }
                )


### run
def get_surcharge_vals(surcharge_dict):
    """Extract numeric values for folder naming, regardless of state-specific keys"""
    county_val = 0
    coi_val = 0
    for k, v in surcharge_dict.items():
        # normalize numeric types and convert fractional surcharges to percentages
        try:
            num = float(v)
        except Exception:
            continue
        if 0 < num <= 1:
            num = int(round(num * 100))
        else:
            num = int(round(num))

        if "COUNTY" in k.upper():
            county_val = num
        else:
            coi_val = num
    return county_val, coi_val


def run_experiment(job):
    position, state, exp = job
    config = STATE_CONFIG[state]

    objective = exp.get("objective", "tcp")
    surcharge = exp.get("region_surcharge", {})
    county_val, coi_val = get_surcharge_vals(surcharge)

    results_dir = (
        Path.cwd()
        / "analysis"
        / "results"
        / objective
        / f"county_{county_val}_coi_{coi_val}"
    )
    gallery_dir = (
        Path.cwd()
        / "analysis"
        / "gallery"
        / objective
        / f"county_{county_val}_coi_{coi_val}"
    )

    results_dir.mkdir(parents=True, exist_ok=True)
    gallery_dir.mkdir(parents=True, exist_ok=True)

    # stagger runs
    time.sleep(exp["run_id"] * 2)

    csv_name = f"{config['state_name']}_{exp['accept']}_{exp['weights']}_{exp['steps']}_v{exp['run_id']}"
    csv_path = results_dir / f"{csv_name}.csv"
    gallery_base = gallery_dir / csv_name
    gallery_base.mkdir(parents=True, exist_ok=True)

    cmd = [
        "python",
        "run_chain.py",
        "--state",
        state,
        "--dist_level",
        "cog",
        "--accept_strategy",
        exp["accept"],
        "--weights_file",
        exp["weights"],
        "--steps",
        str(exp["steps"]),
        "--desired_tcp",
        str(exp["desired_tcp"]),
        "--csv_filename",
        csv_path.as_posix(),
        "--gallery_dir",
        gallery_base.as_posix(),
        "--region_surcharge",
        json.dumps(surcharge),
        "--position",
        str(position),
        "--coi_map",
        config["coi_map"],
    ]

    subprocess.run(cmd)


if __name__ == "__main__":
    # build all (state, experiment) jobs
    raw_jobs = [(state, exp) for state in TARGET_STATES for exp in experiments]
    jobs = [(i, state, exp) for i, (state, exp) in enumerate(raw_jobs)]
    print(f"running {len(jobs)} experiments across {len(TARGET_STATES)} state(s)...")

    t_start = time.time()

    if len(jobs) > 1:
        with multiprocessing.Pool(max(1, multiprocessing.cpu_count() - 1)) as pool:
            pool.map(run_experiment, jobs)
    else:
        run_experiment(jobs[0])

    total = time.time() - t_start
    mins, secs = divmod(int(total), 60)
    print(f"\nall done in {mins}m {secs}s")
