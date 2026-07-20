import os
import time
import multiprocessing
import papermill as pm

### init
# run one or both
TARGET_STATES = ["co"]

STATE_CONFIG = {
    "mo": {"notebook": "mo/mo_scoring.ipynb", "state_name": "missouri"},
    "co": {"notebook": "co/co_scoring.ipynb", "state_name": "colorado"}, 
}

experiments = [
    {
        "accept": "proportional_cs_50",
        "run_id": 1,
        "weights": "test_weights",
        "steps": 100_000,
        "desired_tcp": 0.85,
        "objective": "tcp",
        "region_surcharge": {"county": 100, "coi": 0}
    },
    {
        "accept": "proportional_cs_100",
        "run_id": 1,
        "weights": "test_weights",
        "steps": 100_000,
        "desired_tcp": 0.85,
        "objective": "tcp",
        "region_surcharge": {"county": 100, "coi": 0}
    },
    {
        "accept": "proportional_cs_200",
        "run_id": 1,
        "weights": "test_weights",
        "steps": 100_000,
        "desired_tcp": 0.85,
        "objective": "tcp",
        "region_surcharge": {"county": 100, "coi": 0}
    },
    {
        "accept": "margin_cs_10_40",
        "run_id": 1,
        "weights": "test_weights",
        "steps": 100_000,
        "desired_tcp": 0.85,
        "objective": "tcp",
        "region_surcharge": {"county": 100, "coi": 0}
    },
    {
        "accept": "margin_cs_20_50",
        "run_id": 1,
        "weights": "test_weights",
        "steps": 100_000,
        "desired_tcp": 0.85,
        "objective": "tcp",
        "region_surcharge": {"county": 100, "coi": 0}
    },
    {
        "accept": "margin_cs_30_60",
        "run_id": 1,
        "weights": "test_weights",
        "steps": 100_000,
        "desired_tcp": 0.85,
        "objective": "tcp",
        "region_surcharge": {"county": 100, "coi": 0}
    },
    {
        "accept": "simple_cs_25",
        "run_id": 1,
        "weights": "test_weights",
        "steps": 100_000,
        "desired_tcp": 0.85,
        "objective": "tcp",
        "region_surcharge": {"county": 100, "coi": 0}
    },
    {
        "accept": "simple_cs_50",
        "run_id": 1,
        "weights": "test_weights",
        "steps": 100_000,
        "desired_tcp": 0.85,
        "objective": "tcp",
        "region_surcharge": {"county": 100, "coi": 0}
    },
    {
        "accept": "simple_cs_75",
        "run_id": 1,
        "weights": "test_weights",
        "steps": 100_000,
        "desired_tcp": 0.85,
        "objective": "tcp",
        "region_surcharge": {"county": 100, "coi": 0}
    },
    {
        "accept": "neutral",
        "run_id": 1,
        "weights": "test_weights",
        "steps": 100_000,
        "desired_tcp": 0.85,
        "objective": "tcp",
        "region_surcharge": {"county": 100, "coi": 0}
    }
]

# duplicate jobs for v2
experiments = experiments + [dict(e, run_id=2) for e in experiments]

### run
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
    surcharge = exp.get("region_surcharge", {"county": 100, "coi": 0})
    county_val = surcharge.get("county", 100)
    coi_val = surcharge.get("coi", 0)
    
    results_dir = f"analysis/results/{objective}/county_{county_val}_coi_{coi_val}"
    os.makedirs(results_dir, exist_ok=True)

    # stagger runs
    time.sleep(exp["run_id"] * 2)

    csv_name = f"{config['state_name']}_{exp['dist_lev']}_{exp['accept']}_{exp['weights']}_{exp['steps']}_v{exp['run_id']}"

    # Also save the notebook execution to the same place or a notebooks folder?
    # Let's just output it to the results_dir
    
    pm.execute_notebook(
        config["notebook"],  # template
        f"{results_dir}/{state}_{exp['accept']}_{exp['dist_lev']}_v{exp['run_id']}.ipynb",  # output
        parameters=dict(
            STATE_NAME=config["state_name"],
            ACCEPT_STRATEGY_NAME=exp["accept"],
            WEIGHTS_FILE=exp["weights"],
            MARKOV_STEPS=exp["steps"],
            DESIRED_TCP=exp["desired_tcp"],
            CSV_FILENAME=f"../{results_dir}/{csv_name}.csv", # relative to the cwd=state
            REGION_SURCHARGE=surcharge,
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
