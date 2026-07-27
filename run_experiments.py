import os
import time
import multiprocessing
import subprocess
import json
from pathlib import Path

### init
# set target state and the single coi map to run on this machine
TARGET_STATES = ["co"]
COI_MAP = "community"  # 1 per pc (representable, community, people_based, superclean, economy, all_maps, government_based, mixed_fillers)

STEPS = 250_000
DIST_LEVELS = ["cog", "ss", "sh"]
SEEDS = (1, 2)

STATE_CONFIG = {
    "mo": {"state_name": "missouri", "coi_map": "aggregated"},
    "co": {"state_name": "colorado", "coi_map": COI_MAP},
}

# 6 experimental configurations per district level & seed (3 * 2 * 6 = 36 runs total)
CONFIGS = [
    # optimized tcp w/ 0.55 surcharge & 0 surcharge
    {
        "accept": "simple_37_5",
        "objective": "tcp",
        "region_surcharge": {"COUNTYFP20": 0.55},
    },
    {"accept": "simple_37_5", "objective": "tcp", "region_surcharge": {}},
    # optimized cs w/ 0.55 surcharge & 0 surcharge
    {
        "accept": "simple_cs_37_5",
        "objective": "cs",
        "region_surcharge": {"COUNTYFP20": 0.55},
    },
    {"accept": "simple_cs_37_5", "objective": "cs", "region_surcharge": {}},
    # neutral w/ 0.55 surcharge & 0 surcharge
    {
        "accept": "neutral",
        "objective": "neutral",
        "region_surcharge": {"COUNTYFP20": 0.55},
    },
    {"accept": "neutral", "objective": "neutral", "region_surcharge": {}},
]

experiments = []
for dist_level in DIST_LEVELS:
    for run_id in SEEDS:
        for cfg in CONFIGS:
            experiments.append(
                {
                    "accept": cfg["accept"],
                    "run_id": run_id,
                    "weights": "test_weights",
                    "steps": STEPS,
                    "desired_tcp": 0.85,
                    "objective": cfg["objective"],
                    "region_surcharge": cfg["region_surcharge"],
                    "dist_level": dist_level,
                    "coi_map": COI_MAP,
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
    dist_level = exp.get("dist_level", "cog")
    coi_map = (
        config["coi_map"] if state == "mo" else exp.get("coi_map", config["coi_map"])
    )
    county_val, coi_val = get_surcharge_vals(surcharge)

    results_dir = (
        Path.cwd()
        / "analysis"
        / "results"
        / objective
        / coi_map
        / dist_level
        / f"county_{county_val}_coi_{coi_val}"
    )
    gallery_dir = (
        Path.cwd()
        / "analysis"
        / "gallery"
        / objective
        / coi_map
        / dist_level
        / f"county_{county_val}_coi_{coi_val}"
    )

    results_dir.mkdir(parents=True, exist_ok=True)
    gallery_dir.mkdir(parents=True, exist_ok=True)

    # stagger runs
    time.sleep(exp["run_id"] * 2)

    csv_name = f"{config['state_name']}_{dist_level}_{coi_map}_{exp['accept']}_{exp['weights']}_{exp['steps']}_v{exp['run_id']}"
    csv_path = results_dir / f"{csv_name}.csv"
    gallery_base = gallery_dir / csv_name
    gallery_base.mkdir(parents=True, exist_ok=True)

    cmd = [
        "python",
        "run_chain.py",
        "--state",
        state,
        "--dist_level",
        dist_level,
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
        coi_map,
    ]

    subprocess.run(cmd)


if __name__ == "__main__":
    # build all (state, experiment) jobs
    raw_jobs = [
        (state, exp)
        for state in TARGET_STATES
        for exp in experiments
        if not (state == "mo" and exp["coi_map"] != COI_MAP)
    ]
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
