#!/bin/bash
# Local benchmark run script for hello_world_bench

# Job Information
echo "Job Name: hello_world_bench"
echo "Start Time: $(date)"

# Create output directory if it doesn't exist
mkdir -p examples/output

# Run the benchmark
echo "Running benchmark: hello_world"
examples/output/hello_world 

echo "End Time: $(date)"
echo "Benchmark run completed successfully"