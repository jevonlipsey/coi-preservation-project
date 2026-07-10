import os
import multiprocessing
import papermill as pm

### init
# run one or both
TARGET_STATES = ["mo"]

STATE_CONFIG = {
    "mo": {"notebook": "mo/mo_scoring.ipynb", "state_name": "missouri"},
    "co": {"notebook": "co/co_scoring.ipynb", "state_name": "colorado"},
}

experiments = [
    {
        "accept": "neutral",
        "weights": "test_weights",
        "steps": 100_000,
        "desired_tcp": 0.56,
    },
    {
        "accept": "optimized",
        "weights": "test_weights",
        "steps": 100_000,
        "desired_tcp": 0.56,
    },
    {
        "accept": "unoptimized",
        "weights": "test_weights",
        "steps": 100_000,
        "desired_tcp": 0.56,
    },
]


### run
def run_experiment(job):
    state, exp = job
    config = STATE_CONFIG[state]
    results_dir = f"{state}/results"
    os.makedirs(results_dir, exist_ok=True)

    print(f"starting {config['state_name']} experiment: {exp['accept']}...")

    pm.execute_notebook(
        config["notebook"],  # template
        f"{results_dir}/{state}_{exp['accept']}.ipynb",  # output
        parameters=dict(
            STATE_NAME=config["state_name"],
            ACCEPT_STRATEGY_NAME=exp["accept"],
            WEIGHTS_FILE=exp["weights"],
            MARKOV_STEPS=exp["steps"],
            DESIRED_TCP=exp["desired_tcp"],
        ),
        cwd=state,
        autosave_cell_every=5,
    )
    print(f"finished {config['state_name']} {exp['accept']}.")


if __name__ == "__main__":
    # build all (state, experiment) jobs
    jobs = [(state, exp) for state in TARGET_STATES for exp in experiments]

    if len(jobs) > 1:
        with multiprocessing.Pool(len(jobs)) as pool:
            pool.map(run_experiment, jobs)
    else:
        run_experiment(jobs[0])
