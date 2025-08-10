#!/bin/bash

# Script to run all backend module tests and contract interaction tests

echo "Starting Aegis Forge Backend & Contract Tests..."
echo "================================================"

# Ensure Python can find the modules (assuming they are in the same directory as the script)
export PYTHONPATH=$(pwd):$PYTHONPATH

# Variable to track overall test status
OVERALL_STATUS=0 # 0 for success, 1 for failure

# Function to run a Python script and check its output for a success message
run_python_script_test() {
    SCRIPT_NAME=$1
    EXPECTED_SUCCESS_MESSAGE=$2
    CONTEXT=$3 # e.g., "module tests" or "contract interaction tests"

    echo ""
    echo "--- Running $CONTEXT for $SCRIPT_NAME ---"
    
    OUTPUT=$(python3 "$SCRIPT_NAME" 2>&1)
    EXIT_CODE=$? # Capture exit code of the script

    # Check if the output contains the success message AND exit code is 0
    if [ $EXIT_CODE -eq 0 ] && echo "$OUTPUT" | grep -qF "$EXPECTED_SUCCESS_MESSAGE"; then
        echo "$OUTPUT" 
        echo "--- $CONTEXT for $SCRIPT_NAME PASSED ---"
    else
        echo "--- $CONTEXT for $SCRIPT_NAME FAILED ---"
        echo "Exit Code: $EXIT_CODE"
        echo "Output:"
        echo "$OUTPUT"
        OVERALL_STATUS=1
    fi
}

# --- Setup: Compile and Deploy Contracts ---
echo ""
echo "--- Preparing for tests: Compiling and Deploying Contracts ---"

# 1. Compile DIDRegistry.sol
echo "Compiling DIDRegistry.sol..."
python3 compile_and_extract.py # This is for DIDRegistry.sol
COMPILE_DID_EXIT_CODE=$?
if [ $COMPILE_DID_EXIT_CODE -ne 0 ]; then
    echo "CRITICAL: DIDRegistry.sol compilation (compile_and_extract.py) failed. Aborting tests."
    exit 1
fi
echo "DIDRegistry.sol compilation successful."

# 2. Deploy DIDRegistry.sol (for did_system.py tests that use pre-deployed address)
echo "Deploying DIDRegistry.sol..."
python3 deploy_did_registry.py
DEPLOY_DID_EXIT_CODE=$?
if [ $DEPLOY_DID_EXIT_CODE -ne 0 ]; then
    echo "CRITICAL: DIDRegistry.sol deployment (deploy_did_registry.py) failed. Aborting tests that rely on this."
    OVERALL_STATUS=1 
fi
echo "DIDRegistry.sol deployment for did_system.py tests successful (or attempted)."

# 3. Compile AegisToken.sol
echo "Compiling AegisToken.sol (using a helper script, assuming it exists)..."
if [ -f "compile_aegis_token.py" ]; then
    python3 compile_aegis_token.py
    COMPILE_AEGIS_EXIT_CODE=$?
    if [ $COMPILE_AEGIS_EXIT_CODE -ne 0 ]; then
        echo "CRITICAL: AegisToken.sol compilation (compile_aegis_token.py) failed. Aborting token tests."
        OVERALL_STATUS=1
    else
        echo "AegisToken.sol compilation successful."
    fi
else
    echo "Warning: compile_aegis_token.py not found. Test test_aegis_token_interactions.py will attempt its own compilation."
    echo "However, deploy_aegis_token.py (and thus platform_token.py tests) might fail if ABI/bytecode are not present."
fi


# 4. Deploy AegisToken.sol (for platform_token.py tests)
echo "Deploying AegisToken.sol..."
python3 deploy_aegis_token.py
DEPLOY_AEGIS_EXIT_CODE=$?
if [ $DEPLOY_AEGIS_EXIT_CODE -ne 0 ]; then
    echo "CRITICAL: AegisToken.sol deployment (deploy_aegis_token.py) failed. Aborting tests for platform_token.py."
    OVERALL_STATUS=1
fi
echo "AegisToken.sol deployment for platform_token.py tests successful (or attempted)."


# --- Run Tests ---

# Run tests for each backend module (these might use the pre-deployed contracts)
run_python_script_test "did_system.py" "All did_system.py tests passed successfully!" "module tests (DID system)"
run_python_script_test "ipfs_storage.py" "All ipfs_storage.py tests passed successfully!" "module tests (IPFS storage)"
run_python_script_test "project_management.py" "All project_management.py tests passed successfully!" "module tests (Project management)"
run_python_script_test "contribution_workflow.py" "All contribution_workflow.py tests passed successfully!" "module tests (Contribution workflow)"
run_python_script_test "platform_token.py" "All platform_token.py tests passed successfully!" "module tests (Platform token)"
run_python_script_test "p2p_messaging.py" "All p2p_messaging.py tests passed successfully!" "module tests (P2P Messaging)"


# Run smart contract interaction tests (these deploy their own contract instances)
run_python_script_test "test_did_registry_interactions.py" "All test_did_registry_interactions.py tests passed successfully!" "contract interaction tests (DIDRegistry)"
run_python_script_test "test_aegis_token_interactions.py" "All test_aegis_token_interactions.py tests passed successfully!" "contract interaction tests (AegisToken)"


echo ""
echo "================================================"
if [ $OVERALL_STATUS -eq 0 ]; then
    echo "All backend and contract tests passed successfully!"
    exit 0
else
    echo "Some backend or contract tests FAILED. Please review the output above."
    exit 1
fi
