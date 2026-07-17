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
        "accept": "proportional_50",
        "run_id": 1,
        "weights": "test_weights",
        "steps": 100_000,
        "desired_tcp": 0.85,
    },
    {
        "accept": "proportional_100",
        "run_id": 2,
        "weights": "test_weights",
        "steps": 100_000,
        "desired_tcp": 0.85,
    },
    {
        "accept": "proportional_200",
        "run_id": 1,
        "weights": "test_weights",
        "steps": 100_000,
        "desired_tcp": 0.85,
    },
    {
        "accept": "margin_10_40",
        "run_id": 2,
        "weights": "test_weights",
        "steps": 100_000,
        "desired_tcp": 0.85,
    },
    {
        "accept": "margin_20_50",
        "run_id": 1,
        "weights": "test_weights",
        "steps": 100_000,
        "desired_tcp": 0.85,
    },
    {
        "accept": "margin_30_60",
        "run_id": 2,
        "weights": "test_weights",
        "steps": 100_000,
        "desired_tcp": 0.85,
    },
    {
        "accept": "simple_25",
        "run_id": 1,
        "weights": "test_weights",
        "steps": 100_000,
        "desired_tcp": 0.85,
    },
    {
        "accept": "simple_50",
        "run_id": 2,
        "weights": "test_weights",
        "steps": 100_000,
        "desired_tcp": 0.85,
    },
    {
        "accept": "simple_75",
        "run_id": 1,
        "weights": "test_weights",
        "steps": 100_000,
        "desired_tcp": 0.85,
    },
]


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
    results_dir = f"{state}/results"
    os.makedirs(results_dir, exist_ok=True)

    # stagger runs
    time.sleep(exp["run_id"] * 2)

    csv_name = f"{config['state_name']}_{exp['accept']}_{exp['weights']}_{exp['steps']}_v{exp['run_id']}"

    pm.execute_notebook(
        config["notebook"],  # template
        f"{results_dir}/{state}_{exp['accept']}_v{exp['run_id']}.ipynb",  # output
        parameters=dict(
            STATE_NAME=config["state_name"],
            ACCEPT_STRATEGY_NAME=exp["accept"],
            WEIGHTS_FILE=exp["weights"],
            MARKOV_STEPS=exp["steps"],
            DESIRED_TCP=exp["desired_tcp"],
            CSV_FILENAME=csv_name,
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
        with multiprocessing.Pool(len(jobs)) as pool:
            pool.map(run_experiment, jobs)
    else:
        run_experiment(jobs[0])

    total = time.time() - t_start
    mins, secs = divmod(int(total), 60)
    print(f"\nall done in {mins}m {secs}s")
