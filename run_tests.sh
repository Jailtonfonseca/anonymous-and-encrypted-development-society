#!/bin/bash

# Script to run all backend module tests

echo "Starting Aegis Forge Backend Tests..."
echo "====================================="

# Ensure Python can find the modules (assuming they are in the same directory as the script)
export PYTHONPATH=$(pwd):$PYTHONPATH

# Variable to track overall test status
OVERALL_STATUS=0 # 0 for success, 1 for failure

# Function to run a test and check its output
run_test_module() {
    MODULE_NAME=$1
    echo ""
    echo "--- Running tests for $MODULE_NAME ---"
    
    # Execute the Python module's test block
    # Capture output to check for success message
    OUTPUT=$(python3 "$MODULE_NAME" 2>&1)
    
    # Check if the output contains the success message
    # Using a generic "tests passed successfully!" message convention
    if echo "$OUTPUT" | grep -q "All ${MODULE_NAME%.*} tests passed successfully!"; then
        echo "$OUTPUT" # Print the full output from the module
        echo "--- $MODULE_NAME tests PASSED ---"
    else
        echo "--- $MODULE_NAME tests FAILED ---"
        echo "Output:"
        echo "$OUTPUT"
        OVERALL_STATUS=1
    fi
}

# Run tests for each module
run_test_module "did_system.py"
run_test_module "ipfs_storage.py"
run_test_module "project_management.py"
run_test_module "contribution_workflow.py"

echo ""
echo "====================================="
if [ $OVERALL_STATUS -eq 0 ]; then
    echo "All backend tests passed successfully!"
    exit 0
else
    echo "Some backend tests FAILED. Please review the output above."
    exit 1
fi
