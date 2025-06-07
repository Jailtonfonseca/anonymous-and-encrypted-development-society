import json
import os
import uuid # For a more robust project_id if needed, though sanitization is primary for now.
import re
import subprocess

# Assuming did_system.py and ipfs_storage.py are in the same directory or accessible in PYTHONPATH
import did_system
import ipfs_storage

from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.exceptions import ContractLogicError

PROJECTS_FILE = "projects.json"
PROJECT_DATA_BASE_DIR = "project_data" # Consistent with ipfs_storage
PROJECT_TOKEN_ABI_FILE = "ProjectToken.abi.json" # Assuming this is in the root
GANACHE_URL = "http://127.0.0.1:8545" # Default Ganache URL, should be consistent

def _sanitize_project_name_to_id(project_name: str) -> str:
    """
    Sanitizes a project name to create a filesystem-friendly and URL-friendly ID.
    """
    if not project_name:
        return f"project-{uuid.uuid4().hex[:8]}"
    name = project_name.lower()
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'[-\s]+', '-', name).strip('-_')
    if not name:
        return f"project-{uuid.uuid4().hex[:8]}"
    return name

def _load_projects() -> list:
    if not os.path.exists(PROJECTS_FILE):
        return []
    try:
        with open(PROJECTS_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Warning: {PROJECTS_FILE} contains invalid JSON. Starting with an empty project list.")
        return []
    except Exception as e:
        print(f"Error loading projects from {PROJECTS_FILE}: {e}")
        return []

def _save_projects(projects_data: list) -> bool:
    try:
        with open(PROJECTS_FILE, "w") as f:
            json.dump(projects_data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving projects to {PROJECTS_FILE}: {e}")
        return False

def _init_w3_for_pm() -> Web3 | None:
    """Initializes Web3 for project management tasks. Shared by token transfers."""
    try:
        w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        if not w3.is_connected():
             w3.eth.block_number # Test connection
        print(f"Web3 initialized and connected to {GANACHE_URL} for project management.")
        return w3
    except Exception as e:
        print(f"Error initializing Web3 for project management: {e}")
        return None

def _generate_token_symbol(project_id: str) -> str:
    """Generates a short token symbol from project_id."""
    parts = project_id.replace("project-", "").split('-')
    if len(parts) >= 1 and len(parts[0]) >=3:
        return parts[0][:3].upper()
    sanitized = re.sub(r'[^a-zA-Z]', '', project_id)
    return (sanitized[:3] if len(sanitized) >= 3 else sanitized + "TKN"[:3-len(sanitized)]).upper()


def create_project(project_name: str, owner_did: str, token_supply: int, owner_private_key: str) -> dict | None:
    """
    Creates a new project, deploys a ProjectToken for it, initializes IPFS repo.

    Args:
        project_name: The desired name for the project.
        owner_did: The DID string of the project owner.
        token_supply: The total supply for the project's token (in whole units).
        owner_private_key: The private key of the owner's Ethereum account for deploying the token.

    Returns:
        A dictionary containing the project's metadata if successful, otherwise None.
    """
    # 1. Validate owner_did and get owner's Ethereum address
    owner_did_bytes32 = did_system.generate_did_identifier(owner_did)
    if not did_system.is_did_registered(owner_did_bytes32):
        print(f"Error: Owner DID '{owner_did}' is not registered on the blockchain.")
        return None

    owner_did_info = did_system.get_did_info(owner_did_bytes32)
    if not owner_did_info or "owner" not in owner_did_info:
        print(f"Error: Could not retrieve Ethereum address for owner DID '{owner_did}'.")
        return None
    owner_eth_address = owner_did_info["owner"]
    print(f"Owner DID '{owner_did}' resolved to Ethereum address '{owner_eth_address}'.")

    # 2. Sanitize project_name to create project_id
    project_id = _sanitize_project_name_to_id(project_name)
    if not project_id:
        print(f"Error: Could not generate a valid project_id for '{project_name}'.")
        return None

    # 3. Check if project_id already exists
    projects = _load_projects()
    for p in projects:
        if p.get("project_id") == project_id:
            print(f"Error: Project with ID '{project_id}' (from name '{project_name}') already exists.")
            return None

    # 4. Deploy ProjectToken contract
    print(f"Attempting to deploy ProjectToken for '{project_name}'...")
    token_contract_name = f"{project_name} Token"
    token_contract_symbol = _generate_token_symbol(project_id)

    cmd = [
        "python", "deploy_project_token.py",
        "--name", token_contract_name,
        "--symbol", token_contract_symbol,
        "--supply", str(token_supply),
        "--owner-address", owner_eth_address,
        "--owner-pk", owner_private_key
    ]

    project_token_contract_address = None
    try:
        print(f"Executing deployment command: {' '.join(cmd)}")
        # Hide sensitive PK from direct print in production, but useful for debugging here
        result = subprocess.run(cmd, capture_output=True, text=True, check=False) # check=False for manual error handling

        if result.returncode == 0:
            print("Deployment script executed successfully.")
            print("Deployment script stdout:")
            print(result.stdout)

            # Parse contract address from stdout
            # Expected format: "Contract Address: <0xAddress>" or similar
            match = re.search(r"Contract Address: (0x[a-fA-F0-9]{40})", result.stdout)
            if match:
                project_token_contract_address = match.group(1)
                print(f"Successfully parsed ProjectToken contract address: {project_token_contract_address}")
            else:
                print("Error: Could not parse contract address from deployment script output.")
                print("Stdout was:\n", result.stdout)
                print("Stderr was:\n", result.stderr)
                return None
        else:
            print(f"Error: ProjectToken deployment script failed with return code {result.returncode}.")
            print("Deployment script stdout:")
            print(result.stdout)
            print("Deployment script stderr:")
            print(result.stderr)
            return None

    except FileNotFoundError:
        print("Error: 'python' or 'deploy_project_token.py' not found. Ensure Python is in PATH and script is present.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during token deployment: {e}")
        return None

    if not project_token_contract_address:
        print("Critical error: ProjectToken contract address not obtained after deployment attempt.")
        return None

    # 5. Initialize decentralized code repository
    print(f"Initializing IPFS repo for project ID: {project_id} (original name: {project_name})")
    repo_cid = ipfs_storage.initialize_project_repo(project_id)
    if not repo_cid:
        print(f"Error: Failed to initialize IPFS repository for project '{project_name}'.")
        # TODO: Consider cleanup for the deployed token if IPFS init fails (complex)
        return None
    
    project_main_dir = os.path.join(PROJECT_DATA_BASE_DIR, project_id)
    os.makedirs(project_main_dir, exist_ok=True)

    # 6. Prepare project metadata (no local token ledger anymore)
    new_project_data = {
        "project_id": project_id,
        "project_name": project_name,
        "owner_did": owner_did, # Storing the DID string
        "project_token_contract_address": project_token_contract_address,
        "token_name_on_creation": token_contract_name, # For reference
        "token_symbol_on_creation": token_contract_symbol, # For reference
        "initial_token_supply_whole": token_supply, # For reference
        "repo_cid": repo_cid,
    }

    # 7. Save the new project's metadata
    projects.append(new_project_data)
    if not _save_projects(projects):
        print(f"Error: Failed to save project '{project_name}' to {PROJECTS_FILE}.")
        return None

    print(f"Project '{project_name}' (ID: '{project_id}') created successfully with token contract: {project_token_contract_address}.")
    return new_project_data

def get_project(project_id: str) -> dict | None:
    projects = _load_projects()
    for p in projects:
        if p.get("project_id") == project_id:
            return p
    print(f"Project with ID '{project_id}' not found.")
    return None

def list_projects() -> list:
    return _load_projects()

def transfer_project_tokens(
    project_id: str,
    sender_did_string: str,
    receiver_did_string: str,
    amount_whole_tokens: int,
    sender_private_key: str
) -> bool:
    """
    Transfers project tokens from sender to receiver using the on-chain ProjectToken contract.
    """
    if amount_whole_tokens <= 0:
        print("Error: Transfer amount must be positive.")
        return False

    w3 = _init_w3_for_pm()
    if not w3:
        return False

    # 1. Get project data and token contract address
    project_data = get_project(project_id)
    if not project_data:
        print(f"Error: Project with ID '{project_id}' not found.")
        return False
    
    token_contract_address = project_data.get("project_token_contract_address")
    if not token_contract_address:
        print(f"Error: Project '{project_id}' does not have a token contract address.")
        return False

    # 2. Load ProjectToken ABI
    if not os.path.exists(PROJECT_TOKEN_ABI_FILE):
        print(f"Error: ProjectToken ABI file '{PROJECT_TOKEN_ABI_FILE}' not found.")
        return False
    try:
        with open(PROJECT_TOKEN_ABI_FILE, 'r') as f:
            token_abi = json.load(f)
    except Exception as e:
        print(f"Error loading ProjectToken ABI: {e}")
        return False

    # 3. Create contract instance
    try:
        token_contract = w3.eth.contract(address=Web3.to_checksum_address(token_contract_address), abi=token_abi)
    except Exception as e:
        print(f"Error creating contract instance for {token_contract_address}: {e}")
        return False

    # 4. Resolve DIDs to Ethereum addresses
    try:
        sender_did_bytes32 = did_system.generate_did_identifier(sender_did_string)
        sender_info = did_system.get_did_info(sender_did_bytes32)
        if not sender_info or "owner" not in sender_info:
            print(f"Error: Could not resolve sender DID '{sender_did_string}' to an Ethereum address.")
            return False
        sender_eth_address = Web3.to_checksum_address(sender_info["owner"])

        receiver_did_bytes32 = did_system.generate_did_identifier(receiver_did_string)
        receiver_info = did_system.get_did_info(receiver_did_bytes32)
        if not receiver_info or "owner" not in receiver_info:
            print(f"Error: Could not resolve receiver DID '{receiver_did_string}' to an Ethereum address.")
            return False
        receiver_eth_address = Web3.to_checksum_address(receiver_info["owner"])

        if sender_eth_address == receiver_eth_address:
            print("Error: Sender and receiver Ethereum addresses are the same.")
            return False

    except Exception as e:
        print(f"Error resolving DIDs: {e}")
        return False

    # 5. Perform ERC20 Transfer
    try:
        decimals = token_contract.functions.decimals().call()
        amount_in_smallest_units = amount_whole_tokens * (10**decimals)

        nonce = w3.eth.get_transaction_count(sender_eth_address)

        # Estimate gas for transfer
        try:
            gas_estimate = token_contract.functions.transfer(receiver_eth_address, amount_in_smallest_units).estimate_gas({
                'from': sender_eth_address,
                'nonce': nonce
            })
        except ContractLogicError as e:
             print(f"Contract logic error during gas estimation for transfer: {e}")
             print("This could mean insufficient balance or other contract constraints.")
             return False
        except Exception as e:
            print(f"Error estimating gas for transfer: {e}. Using default.")
            gas_estimate = 200000 # Fallback

        tx_params = {
            'from': sender_eth_address,
            'nonce': nonce,
            'gas': gas_estimate + 20000, # Buffer
            'gasPrice': w3.eth.gas_price or w3.to_wei('10', 'gwei')
        }
        if tx_params['gasPrice'] == 0: tx_params['gasPrice'] = w3.to_wei('1', 'gwei')


        transfer_tx = token_contract.functions.transfer(receiver_eth_address, amount_in_smallest_units).build_transaction(tx_params)

        signed_tx = w3.eth.account.sign_transaction(transfer_tx, private_key=sender_private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"Token transfer transaction sent. Hash: {w3.to_hex(tx_hash)}")

        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if tx_receipt.status == 1:
            print(f"Successfully transferred {amount_whole_tokens} tokens from {sender_did_string} ({sender_eth_address}) to {receiver_did_string} ({receiver_eth_address}) for project {project_id}.")
            return True
        else:
            print(f"Token transfer failed. Transaction status: {tx_receipt.status}.")
            print(f"Full receipt: {tx_receipt}")
            return False

    except ContractLogicError as e: # Catch specific contract logic errors like insufficient balance
        print(f"Contract logic error during token transfer: {e}")
        print("This often indicates insufficient funds or other contract conditions not met.")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during token transfer: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("--- Project Management Tests (Adapted for On-Chain Tokens) ---")

    # Simplified test setup due to complexity of mocking subprocess and Web3
    # These tests will require a running Ganache instance and deployed DIDRegistry.
    # Placeholder private keys - REPLACE WITH ACTUAL GANACHE KEYS FOR TESTING
    # Ensure these accounts have ETH for gas.
    # Ganache default account 0:
    TEST_OWNER_ETH_PK = "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d"
    TEST_OWNER_ETH_ADDR = "0x90F8bf6A479f320ead074411a4B0e7944Ea8c9C1" # Corresponds to PK above for default Ganache
    # Ganache default account 1:
    TEST_RECEIVER_ETH_PK = "0x6c002f5f36494661586ebb0882038bf8d598aafb88a5e2300971707fce91e997"
    TEST_RECEIVER_ETH_ADDR = "0x243540A32155412948a8963385C994A4e23f0750" # Corresponds to PK above for default Ganache

    # Test DIDs (these need to be registered on your DIDRegistry first, pointing to the above ETH addresses)
    # For testing, we assume these DIDs exist and are owned by the ETH addresses above.
    # You would need to run did_system.register_did() separately to set these up.
    # Example:
    # did_system.register_did(did_system.generate_did_identifier("did:aegis:testowner"), "pk1", "cid1", TEST_OWNER_ETH_ADDR, TEST_OWNER_ETH_PK)
    # did_system.register_did(did_system.generate_did_identifier("did:aegis:testreceiver"), "pk2", "cid2", TEST_RECEIVER_ETH_ADDR, TEST_RECEIVER_ETH_PK)

    TEST_OWNER_DID = f"did:aegis:owner-{uuid.uuid4().hex[:6]}" # Needs to be registered to TEST_OWNER_ETH_ADDR
    TEST_RECEIVER_DID = f"did:aegis:receiver-{uuid.uuid4().hex[:6]}" # Needs to be registered to TEST_RECEIVER_ETH_ADDR

    print(f"IMPORTANT: For tests to pass, ensure Ganache is running, DIDRegistry is deployed,")
    print(f"and the following DIDs are registered with their respective owners:")
    print(f"  {TEST_OWNER_DID} -> owned by {TEST_OWNER_ETH_ADDR}")
    print(f"  {TEST_RECEIVER_DID} -> owned by {TEST_RECEIVER_ETH_ADDR}")
    print(f"  ABI file '{PROJECT_TOKEN_ABI_FILE}' must be present.")
    print(f"  'deploy_project_token.py' script must be executable and in the same directory.")


    # Clean up previous test files
    if os.path.exists(PROJECTS_FILE):
        os.remove(PROJECTS_FILE)
        print(f"Removed existing {PROJECTS_FILE} for fresh test run.")
    
    # Base directory for project data
    import shutil
    if os.path.exists(PROJECT_DATA_BASE_DIR):
        # Let's clean specific project dirs at the end of tests instead of wiping base dir
        pass
    os.makedirs(PROJECT_DATA_BASE_DIR, exist_ok=True)

    project1_id_for_test = None
    created_project_data = None

    # --- Test create_project ---
    print("\n--- Testing create_project (on-chain token) ---")
    # This test now involves a subprocess call to deploy_project_token.py
    # Ensure deploy_project_token.py is runnable and ProjectToken.abi.json/bytecode.txt exist
    # Also, the owner_did (TEST_OWNER_DID) must be registered on the DIDRegistry contract
    # and its owner must be TEST_OWNER_ETH_ADDR.

    # Mocking registration for the purpose of this script's flow (actual registration is external)
    print(f"Reminder: Manually register '{TEST_OWNER_DID}' to '{TEST_OWNER_ETH_ADDR}' and '{TEST_RECEIVER_DID}' to '{TEST_RECEIVER_ETH_ADDR}' in DIDRegistry for full test success.")

    created_project_data = create_project(
        project_name="My OnChain Test Project",
        owner_did=TEST_OWNER_DID, # This DID must be registered to TEST_OWNER_ETH_ADDR
        token_supply=500000,
        owner_private_key=TEST_OWNER_ETH_PK # PK for TEST_OWNER_ETH_ADDR
    )

    if created_project_data:
        print(f"Project 'My OnChain Test Project' created successfully: {created_project_data}")
        project1_id_for_test = created_project_data.get("project_id")
        assert "project_token_contract_address" in created_project_data
        assert created_project_data["project_token_contract_address"].startswith("0x")
        print(f"Token contract address: {created_project_data['project_token_contract_address']}")
    else:
        print("Failed to create 'My OnChain Test Project'. Check Ganache, DIDRegistry setup, and deploy_project_token.py script.")

    # --- Test get_project ---
    print("\n--- Testing get_project ---")
    if project1_id_for_test:
        retrieved_project = get_project(project1_id_for_test)
        assert retrieved_project is not None
        assert retrieved_project.get("project_id") == project1_id_for_test
        print(f"Successfully retrieved project: {retrieved_project.get('project_name')}")
    else:
        print("Skipping get_project test as no project was successfully created.")

    # --- Test transfer_project_tokens (on-chain) ---
    print("\n--- Testing transfer_project_tokens (on-chain) ---")
    if project1_id_for_test and created_project_data:
        print(f"Attempting to transfer 100 tokens for project {project1_id_for_test}...")
        # Sender is TEST_OWNER_DID (owner of the project and token)
        # Receiver is TEST_RECEIVER_DID
        # PK is for TEST_OWNER_ETH_ADDR
        transfer_success = transfer_project_tokens(
            project_id=project1_id_for_test,
            sender_did_string=TEST_OWNER_DID,
            receiver_did_string=TEST_RECEIVER_DID,
            amount_whole_tokens=100,
            sender_private_key=TEST_OWNER_ETH_PK
        )
        if transfer_success:
            print("Token transfer reported successful by function.")
            # To verify, you'd check balances on-chain using web3, not via project_management.py
            print("Verification of on-chain balance changes would require separate Web3 calls here.")
        else:
            print("ERROR: On-chain token transfer failed. Check Ganache, DIDs, and token contract.")
        
        print("\nAttempting to transfer with insufficient funds (expected to fail)...")
        # Assuming owner has 500000 tokens, try to send 1,000,000
        insufficient_transfer_success = transfer_project_tokens(
            project_id=project1_id_for_test,
            sender_did_string=TEST_OWNER_DID,
            receiver_did_string=TEST_RECEIVER_DID,
            amount_whole_tokens=1000000, # More than initial supply for the owner
            sender_private_key=TEST_OWNER_ETH_PK
        )
        if not insufficient_transfer_success:
            print("Successfully prevented transfer of (likely) insufficient funds or caught other revert.")
        else:
            print("ERROR: Transfer of insufficient funds was reported as successful by the function (unexpected).")

    else:
        print("Skipping transfer_project_tokens tests due to prior setup failures.")

    # --- Test list_projects ---
    print("\n--- Testing list_projects ---")
    all_projects = list_projects()
    print(f"Found {len(all_projects)} projects:")
    for p_info in all_projects:
        print(f"  - {p_info.get('project_name')} (ID: {p_info.get('project_id')}, Token: {p_info.get('project_token_contract_address')})")

    if project1_id_for_test: # If the first project was created
        assert len(all_projects) >= 1
    else:
        assert len(all_projects) == 0


    print("\n--- Project Management Tests: Cleaning up ---")
    if project1_id_for_test:
        path_to_clean = os.path.join(PROJECT_DATA_BASE_DIR, project1_id_for_test)
        if os.path.exists(path_to_clean):
            shutil.rmtree(path_to_clean)
            print(f"Cleaned up test project directory: {path_to_clean}")

    if os.path.exists(PROJECTS_FILE):
        os.remove(PROJECTS_FILE)
        print(f"Cleaned up {PROJECTS_FILE}")

    print("\n--- End of Project Management Tests (On-Chain Adapted) ---")
    print("Reminder: These tests are simplified. Full verification requires on-chain checks and potentially mocking.")
    print("Ensure your Ganache, DIDRegistry, and ProjectToken contract/scripts are correctly set up.")
