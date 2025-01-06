#!/bin/bash
#
# Hello World Example Template
# This template demonstrates basic task execution in BenchPRO
#
# Available variables:
# - BENCHPRO_CORES: Number of cores allocated
# - BENCHPRO_MEMORY: Memory allocated
# - BENCHPRO_WALLTIME: Wall time limit in seconds

echo "Hello from BenchPRO!"
echo "Running with ${BENCHPRO_CORES} cores and ${BENCHPRO_MEMORY} memory"
echo "Wall time limit: ${BENCHPRO_WALLTIME} seconds"

# Simulate some work
sleep 2

echo "Task completed successfully!" 