#!/bin/bash
#SBATCH --job-name=hello_suite_bench_0
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:05:00
#SBATCH --output=hello_suite_bench_0.out
#SBATCH --error=hello_suite_bench_0.err


#SBATCH --partition=gg



#SBATCH --account=A-ccsc


echo "Running benchmark hello_suite_bench_0"
echo "Date: $(date)"
echo "Host: $(hostname)"

# Run tasks

echo "Starting task hello_suite_task_0"
module use /home1/06280/mcawood/benchpro/workspaces/build_hello_1.0_1764795492 && module load hello && hello


echo "Done"