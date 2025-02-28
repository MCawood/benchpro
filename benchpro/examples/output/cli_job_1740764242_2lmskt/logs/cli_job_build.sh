#!/bin/bash
#SBATCH --job-name=cli_job
#SBATCH --output=examples/output/cli_job_%j.out
#SBATCH --error=examples/output/cli_job_%j.err
#SBATCH --time=00:10:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --partition=cli_queue
#SBATCH --account=system_account

# Job Information
echo "Job ID: $SLURM_JOB_ID"
echo "Job Name: cli_job"
echo "Start Time: $(date)"

# Change to source directory
cd examples/output/cli_job_1740764242_2lmskt/source

# Build the application
echo "Building application: hello_world"
gcc -o hello_world hello_world.c

# Copy the binary to the output directory
cp hello_world examples/output/

echo "End Time: $(date)"
echo "Application build completed successfully"