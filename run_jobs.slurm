#!/bin/bash
#SBATCH --job-name=coi_experiments
#SBATCH --output=coi_run_%j.log          # Standard output and error log (%j becomes the job ID)
#SBATCH --nodes=1                        # Run all processes on a single node
#SBATCH --ntasks=1                       # Run a single task...
#SBATCH --cpus-per-task=100              # ...but allocate 100 CPUs to that task!
#SBATCH --mem=32G                        # Request 32GB of RAM (plenty for 100 jobs on our optimized pipeline)
#SBATCH --time=24:00:00                  # Max time limit

# NOTE: If you need to run 300 jobs at once, simply change `--cpus-per-task=100` to 300!
# SLURM will grab up to 300 cores on one of those fat nodes (like cpu0/gpu0).
# The Python script will automatically detect this number and spin up exactly that many workers.

# 1. Activate your virtual environment
source venv/bin/activate

# 2. Run the experiments
python run_experiments.py
