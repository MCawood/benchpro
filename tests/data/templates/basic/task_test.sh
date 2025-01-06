#!/bin/bash
#
# Basic Task Test Template
# This template is used for testing basic task execution functionality
#
# Expected Environment Variables:
# - BENCHPRO_TEST_VAR: Test variable to verify environment passing
# - BENCHPRO_WORKING_DIR: Working directory for the task

# Echo start for test verification
echo "TASK_START"

# Verify environment variables
if [ -n "${BENCHPRO_TEST_VAR}" ]; then
    echo "TEST_VAR=${BENCHPRO_TEST_VAR}"
fi

# Verify working directory
if [ -n "${BENCHPRO_WORKING_DIR}" ]; then
    echo "WORKING_DIR=${BENCHPRO_WORKING_DIR}"
fi

# Create a test output file
echo "Test output" > test_output.txt

# Simulate work
sleep 1

# Echo completion for test verification
echo "TASK_COMPLETE" 