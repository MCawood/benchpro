#!/bin/bash
#SBATCH --job-name=test_app
echo "Building test_app"
gcc -o test_app test_app.c