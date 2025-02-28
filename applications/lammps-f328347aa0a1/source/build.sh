#!/bin/bash
#
# Build template for LAMMPS

set -e  # Exit on error

echo "Building LAMMPS 23Jun2022..."

# Setup build environment
BUILD_DIR="/Users/mcawood/dev/benchpro/applications/lammps-f328347aa0a1/build"
INSTALL_DIR="/Users/mcawood/dev/benchpro/applications/lammps-f328347aa0a1/install"
SOURCE_DIR="${BUILD_DIR}/lammps"

# Create build directory
cd "${BUILD_DIR}"

# Clone LAMMPS repository
echo "Cloning LAMMPS repository..."
git clone https://github.com/lammps/lammps.git "${SOURCE_DIR}"
cd "${SOURCE_DIR}"
git checkout stable_23Jun2022

# Create and enter build directory
mkdir -p build
cd build

# Configure with CMake
echo "Configuring with CMake..."
cmake ../cmake \
    -DCMAKE_INSTALL_PREFIX=${INSTALL_DIR} \

    -D CMAKE_BUILD_TYPE=Release \

    -D BUILD_MPI=yes \

    -D BUILD_OMP=yes \

    -D PKG_MOLECULE=yes \

    -D PKG_KSPACE=yes \

    -D PKG_MANYBODY=yes \

    -D PKG_RIGID=yes \



# Build
echo "Building with mpicxx..."
cmake --build . -j8

# Install
echo "Installing to ${INSTALL_DIR}..."
cmake --install .

# Create a module file if needed
if [ -d "${INSTALL_DIR}/modulefiles" ]; then
    mkdir -p "${INSTALL_DIR}/modulefiles"
    cat > "${INSTALL_DIR}/modulefiles/lammps" << 'EOF'
#%Module1.0
proc ModulesHelp { } {
    puts stderr "LAMMPS 23Jun2022 - Molecular Dynamics Simulator"
}

module-whatis "LAMMPS 23Jun2022"

set root /opt/lammps

prepend-path PATH $root/bin
prepend-path LD_LIBRARY_PATH $root/lib
prepend-path MANPATH $root/share/man
EOF
fi

echo "Build completed successfully!"