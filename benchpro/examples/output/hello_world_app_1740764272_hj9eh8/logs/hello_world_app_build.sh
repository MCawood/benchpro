#!/bin/bash
#SBATCH --job-name=hello_world_app
#SBATCH --output=/var/folders/r4/c2kvh3zs7230vndy5xy0rkg40000gp/T/tmpm2ne07hb/output/hello_world_app_%j.out
#SBATCH --error=/var/folders/r4/c2kvh3zs7230vndy5xy0rkg40000gp/T/tmpm2ne07hb/output/hello_world_app_%j.err
#SBATCH --time=00:05:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --partition=system_queue
#SBATCH --account=system_account

# Job Information
echo "Job ID: $SLURM_JOB_ID"
echo "Job Name: hello_world_app"
echo "Start Time: $(date)"

# Change to source directory
cd examples/output/hello_world_app_1740764272_hj9eh8/source

# Build the application
echo "Building application: hello_world"
gcc -o hello_world hello_world.c

# Copy the binary to the output directory
cp hello_world /var/folders/r4/c2kvh3zs7230vndy5xy0rkg40000gp/T/tmpm2ne07hb/output/

echo "End Time: $(date)"
echo "Application build completed successfully"