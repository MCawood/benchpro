#!/bin/bash
# Local application build script for hello_world_app

# Job Information
echo "Job Name: hello_world_app"
echo "Start Time: $(date)"

# Get the current directory
CURRENT_DIR=$(pwd)

# Change to source directory
cd examples/output/hello_world_app_1740763127_kc1rqc/source

# Build the application
echo "Building application: hello_world"
gcc -o hello_world hello_world.c

# Copy the binary to the build directory (using absolute path)
mkdir -p ${CURRENT_DIR}/examples/output/hello_world_app_1740763127_kc1rqc/build
cp hello_world ${CURRENT_DIR}/examples/output/hello_world_app_1740763127_kc1rqc/build/

echo "End Time: $(date)"
echo "Application build completed successfully" 