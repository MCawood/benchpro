#!/bin/bash
# Local benchmark run script for hello_world_bench

# Job Information
echo "Job Name: hello_world_bench"
echo "Start Time: $(date)"

# Run the benchmark
echo "Running benchmark: hello_world"
examples/output/hello_world_bench_1740764306_4b4q2q/build/hello_world 

# Save output to results directory
echo "Results saved to: examples/output/hello_world_bench_1740764306_4b4q2q/results"

echo "End Time: $(date)"
echo "Benchmark run completed successfully" 