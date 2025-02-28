#!/bin/bash
# Local application build script for hello_world_app

# Job Information
echo "Job Name: hello_world_app"
echo "Start Time: $(date)"

# Create output directory if it doesn't exist
mkdir -p /var/folders/r4/c2kvh3zs7230vndy5xy0rkg40000gp/T/tmp0oj4nbzq/output

# Change to source directory
cd examples/output/hello_world_app_1740763506_k9xuq8/source

# Build the application
echo "Building application: hello_world"
gcc -o hello_world hello_world.c

# Copy the binary to the output directory
cp hello_world /var/folders/r4/c2kvh3zs7230vndy5xy0rkg40000gp/T/tmp0oj4nbzq/output/

echo "End Time: $(date)"
echo "Application build completed successfully"