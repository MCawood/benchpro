#!/bin/bash
#
# BenchPRO 2.0 Installation Script
#
# Usage: ./install.sh [INSTALL_PREFIX]
#
# If INSTALL_PREFIX is not provided, it defaults to $PWD/install
#

set -e

# Default prefix
PREFIX=${1:-$PWD/install}
VERSION=$(grep -m 1 version pyproject.toml | cut -d '"' -f 2)
INSTALL_DIR="$PREFIX/benchpro/$VERSION"

echo "Installing BenchPRO $VERSION to $INSTALL_DIR"

# Create directory structure
mkdir -p "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR/bin"
mkdir -p "$INSTALL_DIR/config"
mkdir -p "$INSTALL_DIR/modulefiles"

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv "$INSTALL_DIR/venv"

# Upgrade pip
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip

# Install BenchPRO
echo "Installing BenchPRO..."
"$INSTALL_DIR/venv/bin/pip" install .

# Create symlinks
echo "Creating symlinks..."
ln -sf "$INSTALL_DIR/venv/bin/bp" "$INSTALL_DIR/bin/bp"

# Copy default config
echo "Copying default configuration..."
# Assuming we have a default config in the repo, otherwise create a basic one
if [ -f "benchpro/core/config.py" ]; then
    # Extract defaults or copy a template
    # For now, we'll create a placeholder site config
    cat > "$INSTALL_DIR/config/benchpro.yaml" <<EOF
system:
  name: default
  scheduler: local
EOF
else
    echo "Warning: Could not find default config source."
fi

# Generate Module File
echo "Generating module file..."
./scripts/gen_module.sh "$INSTALL_DIR" "$VERSION" > "$INSTALL_DIR/modulefiles/$VERSION.lua"

echo "Installation complete!"
echo "To use BenchPRO, load the module:"
echo "  module use $INSTALL_DIR/modulefiles"
echo "  module load $VERSION"
