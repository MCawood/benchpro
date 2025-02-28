#!/bin/bash
# Local benchmark run script for hello_world_bench

# Job Information
echo "Job Name: hello_world_bench"
echo "Start Time: $(date)"

# Create output directory if it doesn't exist
mkdir -p /var/folders/r4/c2kvh3zs7230vndy5xy0rkg40000gp/T/tmp49zfdr1a/output

# Run the benchmark
echo "Running benchmark: hello_world"
/var/folders/r4/c2kvh3zs7230vndy5xy0rkg40000gp/T/tmp49zfdr1a/output/hello_world 

echo "End Time: $(date)"
echo "Benchmark run completed successfully"