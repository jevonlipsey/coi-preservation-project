import os
import time
import multiprocessing
from pathlib import Path
import papermill as pm

### init
# run one or both
TARGET_STATES = ["co"]
STEPS = 100_000

STATE_CONFIG = {
    "mo": {"notebook": "mo/mo_scoring.ipynb", "state_name": "missouri"},
    "co": {"notebook": "co/co_scoring.ipynb", "state_name": "colorado"},
}

OBJECTIVES = ["tcp"]

STRATEGIES = [
    "simple_12_5",
    "simple_25",
    "simple_37_5",
    "simple_50",
    "neutral",
]

# For CO: 'COUNTYFP20', 'entry_ID'. For MO: 'COUNTYFP20', 'cluster_id'
SURCHARGES = [
    {"COUNTYFP20": 1.0},
    {"COUNTYFP20": .75},
    {"COUNTYFP20": .60},
    {"COUNTYFP20": .50},
    {"COUNTYFP20": .25},
    {"COUNTYFP20": 0},
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
        if "COUNTY" in k.upper():
            county_val = v
        else:
            coi_val = v
    return county_val, coi_val


def run_experiment(job):
    # quiet warnings
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull_fd, 1)  # mute stdout
    os.dup2(devnull_fd, 2)  # mute stderr

    # bypass plotly maps
    os.environ["PAPERMILL_RUN"] = "True"

    state, exp = job
    config = STATE_CONFIG[state]

    objective = exp.get("objective", "tcp")
    surcharge = exp.get("region_surcharge", {})
    county_val, coi_val = get_surcharge_vals(surcharge)

    results_dir = Path.cwd() / "analysis" / "results" / objective / f"county_{county_val}_coi_{coi_val}"
    gallery_dir = Path.cwd() / "analysis" / "gallery" / objective / f"county_{county_val}_coi_{coi_val}"

    results_dir.mkdir(parents=True, exist_ok=True)
    gallery_dir.mkdir(parents=True, exist_ok=True)

    # stagger runs
    time.sleep(exp["run_id"] * 2)

    csv_name = f"{config['state_name']}_{exp['accept']}_{exp['weights']}_{exp['steps']}_v{exp['run_id']}"
    csv_path = results_dir / f"{csv_name}.csv"
    notebook_output = results_dir / f"{state}_{exp['accept']}_v{exp['run_id']}.ipynb"
    gallery_base = gallery_dir / csv_name
    os.makedirs(gallery_base, exist_ok=True)

    pm.execute_notebook(
        config["notebook"],  # template
        notebook_output.as_posix(),  # output
        parameters=dict(
            STATE_NAME=config["state_name"],
            ACCEPT_STRATEGY_NAME=exp["accept"],
            WEIGHTS_FILE=exp["weights"],
            MARKOV_STEPS=exp["steps"],
            DESIRED_TCP=exp["desired_tcp"],
            CSV_FILENAME=csv_path.as_posix(),
            GALLERY_DIR=f"{gallery_base.as_posix()}/",
            REGION_SURCHARGE=surcharge,
            DIST_LEVEL="cog",
        ),
        cwd=state,
        autosave_cell_every=0,  # save at end
        progress_bar=False,
    )


if __name__ == "__main__":
    # build all (state, experiment) jobs
    jobs = [(state, exp) for state in TARGET_STATES for exp in experiments]
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
