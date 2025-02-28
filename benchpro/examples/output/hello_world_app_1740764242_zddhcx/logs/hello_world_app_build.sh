#!/bin/bash
# Local application build script for hello_world_app

# Job Information
echo "Job Name: hello_world_app"
echo "Start Time: $(date)"

# Create output directory if it doesn't exist
mkdir -p examples/output

# Change to source directory
cd examples/output/hello_world_app_1740764242_zddhcx/source

# Build the application
echo "Building application: hello_world"
gcc -o hello_world hello_world.c

# Copy the binary to the output directory
cp hello_world examples/output/

echo "End Time: $(date)"
echo "Application build completed successfully"