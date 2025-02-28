#!/bin/bash
# Local application build script for hello_world_app

# Job Information
echo "Job Name: hello_world_app"
echo "Start Time: $(date)"

# Change to source directory
cd examples/output/hello_world_app_1740762137_60u39i/source

# Build the application
echo "Building application: hello_world"
gcc -o hello_world hello_world.c

# Copy the binary to the build directory
cp examples/output/hello_world_app_1740762137_60u39i/build/hello_world examples/output/hello_world_app_1740762137_60u39i/build/

echo "End Time: $(date)"
echo "Application build completed successfully" 