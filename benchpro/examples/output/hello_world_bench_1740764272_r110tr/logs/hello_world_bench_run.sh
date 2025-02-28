#!/bin/bash
#SBATCH --job-name=hello_world_bench
#SBATCH --output=/var/folders/r4/c2kvh3zs7230vndy5xy0rkg40000gp/T/tmpdo3hquvb/output/hello_world_bench_%j.out
#SBATCH --error=/var/folders/r4/c2kvh3zs7230vndy5xy0rkg40000gp/T/tmpdo3hquvb/output/hello_world_bench_%j.err
#SBATCH --time=00:05:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --partition=system_queue
#SBATCH --account=system_account

# Job Information
echo "Job ID: $SLURM_JOB_ID"
echo "Job Name: hello_world_bench"
echo "Start Time: $(date)"

# Run the benchmark
echo "Running benchmark: hello_world"
/var/folders/r4/c2kvh3zs7230vndy5xy0rkg40000gp/T/tmpdo3hquvb/output/hello_world 

echo "End Time: $(date)"
echo "Benchmark run completed successfully"