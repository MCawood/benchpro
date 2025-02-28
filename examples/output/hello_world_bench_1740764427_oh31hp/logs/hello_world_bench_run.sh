#!/bin/bash
# Local benchmark run script for hello_world_bench

# Job Information
echo "Job Name: hello_world_bench"
echo "Start Time: $(date)"

# Get current directory
CURRENT_DIR=$(pwd)

# Run the benchmark
echo "Running benchmark: hello_world"
${CURRENT_DIR}/examples/output/hello_world_bench_1740764427_oh31hp/build/hello_world 

# Save output to results directory
echo "Results saved to: examples/output/hello_world_bench_1740764427_oh31hp/results"

echo "End Time: $(date)"
echo "Benchmark run completed successfully" 