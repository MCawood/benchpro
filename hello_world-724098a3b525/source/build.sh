#!/bin/bash
#
# Build template for hello_world application

set -e  # Exit on error

echo "Building hello_world application..."

# Setup build environment
BUILD_DIR="/Users/mcawood/dev/benchpro/hello_world-724098a3b525/build"
INSTALL_DIR="/Users/mcawood/dev/benchpro/hello_world-724098a3b525/install"

cd "${BUILD_DIR}"

# Export build variables
export MESSAGE="Hello from BenchPro!"
export REPEAT_COUNT="1"

# Create bin directory
mkdir -p bin

# Compile
echo "Compiling with gcc..."
gcc -o bin/hello_world hello_world.c

# Install
echo "Installing to ${INSTALL_DIR}..."
mkdir -p ${INSTALL_DIR}/bin
cp bin/hello_world ${INSTALL_DIR}/bin/

echo "Build completed successfully!"