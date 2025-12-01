#!/bin/bash
#
# Generate Lmod module file for BenchPRO
#
# Usage: ./gen_module.sh <INSTALL_DIR> <VERSION>
#

INSTALL_DIR=$1
VERSION=$2

if [ -z "$INSTALL_DIR" ] || [ -z "$VERSION" ]; then
    echo "Usage: $0 <INSTALL_DIR> <VERSION>"
    exit 1
fi

cat <<EOF
help([[
BenchPRO: A deterministic benchmark orchestrator for HPC.
Version: $VERSION
]])

whatis("Name: benchpro")
whatis("Version: $VERSION")
whatis("Description: BenchPRO Benchmark Orchestrator")

local root = "$INSTALL_DIR"
local bin = pathJoin(root, "bin")
local config = pathJoin(root, "config", "benchpro.yaml")
local profiles = pathJoin(root, "config", "profiles")

prepend_path("PATH", bin)
setenv("BENCHPRO_SITE_CONFIG", config)
setenv("BENCHPRO_SITE_PROFILES", profiles)
EOF
