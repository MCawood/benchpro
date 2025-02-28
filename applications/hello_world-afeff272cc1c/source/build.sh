#!/bin/bash
#
# Build template for hello_world application

set -e  # Exit on error

echo "Building hello_world application..."

# Setup build environment
BUILD_DIR="/Users/mcawood/dev/benchpro/applications/hello_world-afeff272cc1c/build"
INSTALL_DIR="/Users/mcawood/dev/benchpro/applications/hello_world-afeff272cc1c/install"

cd "${BUILD_DIR}"

# Export build variables
export MESSAGE="Hello from BenchPro!"
export REPEAT_COUNT="1"

# Compile
echo "Compiling with gcc..."
gcc -o hello_world hello_world.c

# Install
echo "Installing to ${INSTALL_DIR}..."
mkdir -p ${INSTALL_DIR}//Users/mcawood/dev/benchpro/applications/hello_world-afeff272cc1c/build/bin
cp hello_world ${INSTALL_DIR}//Users/mcawood/dev/benchpro/applications/hello_world-afeff272cc1c/build/bin/

echo "Build completed successfully!"