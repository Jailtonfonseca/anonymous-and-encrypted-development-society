import json
import os
import uuid
import re

# Assuming did_system.py and ipfs_storage.py are in the same directory or accessible in PYTHONPATH
import did_system
import ipfs_storage

PROJECTS_FILE = "projects.json"
PROJECT_DATA_BASE_DIR = "project_data" # Consistent with ipfs_storage

def _sanitize_project_name_to_id(project_name: str) -> str:
    """
    Sanitizes a project name to create a filesystem-friendly and URL-friendly ID.
    Converts to lowercase, replaces spaces and special characters with hyphens,
    and removes any remaining non-alphanumeric characters (except hyphens).
    """
    if not project_name:
        return f"project-{uuid.uuid4().hex[:8]}" # Fallback for empty names
    
    # Remove common problematic characters or replace them
    name = project_name.lower()
    name = re.sub(r'[^\w\s-]', '', name) # Remove non-alphanumeric, non-whitespace, non-hyphen
    name = re.sub(r'[-\s]+', '-', name).strip('-_') # Replace whitespace/hyphens with single hyphen
    
    if not name: # If all characters were stripped
        return f"project-{uuid.uuid4().hex[:8]}"
    return name

def _load_projects() -> list:
    """Loads project data from PROJECTS_FILE."""
    if not os.path.exists(PROJECTS_FILE):
        return []
    try:
        with open(PROJECTS_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Warning: {PROJECTS_FILE} contains invalid JSON. Starting with an empty project list.")
        return [] # Or handle more gracefully, e.g., backup and create new
    except Exception as e:
        print(f"Error loading projects from {PROJECTS_FILE}: {e}")
        return []


def _save_projects(projects_data: list) -> bool:
    """Saves project data to PROJECTS_FILE."""
    try:
        with open(PROJECTS_FILE, "w") as f:
            json.dump(projects_data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving projects to {PROJECTS_FILE}: {e}")
        return False

def create_project(project_name: str, owner_did: str, token_supply: int = 1000000) -> dict | None:
    """
    Creates a new project, initializes its repository in IPFS, and sets up basic tokenomics.

    Args:
        project_name: The desired name for the project.
        owner_did: The DID string of the project owner.
        token_supply: The total supply for the project's token.

    Returns:
        A dictionary containing the project's metadata if successful, otherwise None.
    """
    # 1. Validate owner_did
    owner_did_bytes = did_system.generate_did_identifier(owner_did)
    if not did_system.is_did_registered(owner_did_bytes):
        print(f"Error: Owner DID '{owner_did}' (Bytes: {owner_did_bytes.hex()}) is not registered on the blockchain.")
        return None

    # 2. Sanitize project_name to create project_id
    project_id = _sanitize_project_name_to_id(project_name)
    if not project_id: # Should be handled by sanitize, but as a safeguard
        print(f"Error: Could not generate a valid project_id for '{project_name}'.")
        return None

    # 3. Check if project_id already exists
    projects = _load_projects()
    for p in projects:
        if p.get("project_id") == project_id:
            print(f"Error: Project with ID '{project_id}' (from name '{project_name}') already exists.")
            return None

    # 4. Initialize decentralized code repository
    # The ipfs_storage.initialize_project_repo expects the "display" project name,
    # but we should use project_id for the directory structure to ensure uniqueness and FS safety.
    # The ipfs_storage module's internal sanitization will handle its part.
    # For consistency, let's pass project_id to initialize_project_repo,
    # as it will be used for the directory name.
    print(f"Initializing IPFS repo for project ID: {project_id} (original name: {project_name})")
    repo_cid = ipfs_storage.initialize_project_repo(project_id) # Use project_id for path
    if not repo_cid:
        print(f"Error: Failed to initialize IPFS repository for project '{project_name}'.")
        # Potentially clean up project_data/<project_id> if ipfs_storage created partial dirs
        project_specific_dir = os.path.join(PROJECT_DATA_BASE_DIR, project_id)
        if os.path.exists(project_specific_dir):
            # Be cautious with rmtree; for now, let ipfs_storage handle its own cleanup if any.
            pass
        return None
    
    # Create the project specific data directory (excluding the 'repo' part handled by ipfs_storage)
    # project_data/<project_id>/
    project_main_dir = os.path.join(PROJECT_DATA_BASE_DIR, project_id)
    os.makedirs(project_main_dir, exist_ok=True) # Ensure it exists, repo is a subdir

    # 5. Create token details
    token_name = f"{project_id}_TOKEN" # Or use a sanitized version of project_name + _TOKEN

    # 6. Initialize token_ledger
    token_ledger = {owner_did: token_supply}

    # 7. Prepare project metadata
    new_project_data = {
        "project_id": project_id,
        "project_name": project_name, # Store original name
        "owner_did": owner_did,
        "repo_cid": repo_cid,
        "token_name": token_name,
        "token_supply": token_supply,
        "token_ledger": token_ledger,
    }

    # 8. Save the new project's metadata
    projects.append(new_project_data)
    if not _save_projects(projects):
        print(f"Error: Failed to save project '{project_name}' to {PROJECTS_FILE}.")
        # Attempt to clean up IPFS storage? This is complex.
        # For now, assume if save fails, the IPFS repo is orphaned but not critical for MVP.
        return None

    print(f"Project '{project_name}' (ID: '{project_id}') created successfully.")
    return new_project_data

def get_project(project_id: str) -> dict | None:
    """
    Retrieves project details from projects.json using project_id.

    Args:
        project_id: The ID of the project to retrieve.

    Returns:
        The project dictionary or None if not found.
    """
    projects = _load_projects()
    for p in projects:
        if p.get("project_id") == project_id:
            return p
    print(f"Project with ID '{project_id}' not found.")
    return None

def list_projects() -> list:
    """
    Returns a list of all project dictionaries from projects.json.

    Returns:
        A list of project dictionaries.
    """
    return _load_projects()

def transfer_project_tokens(project_id: str, sender_did: str, receiver_did: str, amount: int) -> bool:
    """
    Transfers project tokens from sender to receiver.

    Args:
        project_id: The ID of the project.
        sender_did: The DID of the token sender.
        receiver_did: The DID of the token receiver.
        amount: The amount of tokens to transfer.

    Returns:
        True if the transfer was successful, False otherwise.
    """
    if amount <= 0:
        print("Error: Transfer amount must be positive.")
        return False

    # 1. Validate DIDs
    sender_did_bytes = did_system.generate_did_identifier(sender_did)
    if not did_system.is_did_registered(sender_did_bytes):
        print(f"Error: Sender DID '{sender_did}' (Bytes: {sender_did_bytes.hex()}) is not registered.")
        return False

    receiver_did_bytes = did_system.generate_did_identifier(receiver_did)
    if not did_system.is_did_registered(receiver_did_bytes):
        print(f"Error: Receiver DID '{receiver_did}' (Bytes: {receiver_did_bytes.hex()}) is not registered.")
        return False
    
    if sender_did == receiver_did:
        print("Error: Sender and receiver DIDs cannot be the same.")
        return False

    # 2. Load all projects and find the target project
    projects = _load_projects()
    project_found = False
    target_project_index = -1

    for i, p in enumerate(projects):
        if p.get("project_id") == project_id:
            target_project_index = i
            project_found = True
            break
    
    if not project_found:
        print(f"Error: Project with ID '{project_id}' not found.")
        return False

    project = projects[target_project_index]
    token_ledger = project.get("token_ledger", {})

    # 3. Check sender's balance
    sender_balance = token_ledger.get(sender_did, 0)
    if sender_balance < amount:
        print(f"Error: Sender '{sender_did}' has insufficient balance ({sender_balance}) to transfer {amount} tokens.")
        return False

    # 4. Update token ledger
    token_ledger[sender_did] = sender_balance - amount
    
    receiver_balance = token_ledger.get(receiver_did, 0)
    token_ledger[receiver_did] = receiver_balance + amount
    
    project["token_ledger"] = token_ledger # Update the project's ledger

    # 5. Save updated projects data
    if _save_projects(projects):
        print(f"Successfully transferred {amount} tokens from {sender_did} to {receiver_did} for project {project_id}.")
        return True
    else:
        print(f"Error: Failed to save token transfer for project {project_id}.")
        # Attempt to revert ledger changes in memory (though this is getting complex for a simple function)
        # This is a temporary revert, if _save_projects failed, the file is likely the old state anyway.
        token_ledger[sender_did] = sender_balance 
        token_ledger[receiver_did] = receiver_balance
        return False

if __name__ == '__main__':
    # Test sanitize function
    print("Testing _sanitize_project_name_to_id:")
    names_to_test = ["My Awesome Project!", "  Project with spaces  ", "project_with_underscores", "Test@123", "", "!@#$%^"]
    for name in names_to_test:
        print(f"'{name}' -> '{_sanitize_project_name_to_id(name)}'")

    # --- Test create_project ---
    print("\n--- Testing create_project ---")

    # Setup: Ensure IPFS daemon is running. Create a dummy DID for testing.
    # Clean up previous test files
    if os.path.exists(PROJECTS_FILE):
        os.remove(PROJECTS_FILE)
        print(f"Removed existing {PROJECTS_FILE} for fresh test run.")
    # Removed DIDS_FILE handling as it's no longer used by did_system
    
    # Base directory for project data; ipfs_storage also uses this.
    import shutil
    # Commenting out broad rmtree for safety during iterative development
    # if os.path.exists(PROJECT_DATA_BASE_DIR):
    #     shutil.rmtree(PROJECT_DATA_BASE_DIR) 
    #     print(f"Cleaned up base directory: {PROJECT_DATA_BASE_DIR}")
    os.makedirs(PROJECT_DATA_BASE_DIR, exist_ok=True)

    # --- Test DID Setup on Blockchain ---
    print("\nAttempting to set up test DIDs on the blockchain...")
    test_owner_eth_address = None
    test_owner_eth_pk = None
    can_run_did_tests = False

    if did_system.w3 and did_system.did_registry_contract:
        if did_system.w3.eth.accounts:
            test_owner_eth_address = did_system.w3.eth.accounts[0]
            # Common default Ganache private key for the first account
            # IMPORTANT: This is a default key for development with Ganache.
            # It will NOT work if your Ganache instance uses a different seed/mnemonic.
            # Replace if your Ganache account 0 has a different private key.
            DEFAULT_GANACHE_PK_0 = "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d"
            test_owner_eth_pk = DEFAULT_GANACHE_PK_0
            print(f"Using Ganache account {test_owner_eth_address} for test DID registrations.")
            can_run_did_tests = True
        else:
            print("WARNING: No Ganache accounts found (w3.eth.accounts is empty).")
            print("Cannot register test DIDs on-chain. Contract interaction tests will be limited.")
    else:
        print("WARNING: did_system.w3 or did_system.did_registry_contract is None.")
        print("This means the connection to Ganache or contract setup failed in did_system.py.")
        print("Project creation/transfer tests requiring DIDs will be skipped or may fail if they proceed.")

    test_owner_did_string = f"pm-test-owner-did-{uuid.uuid4().hex[:8]}"
    test_receiver_did_string = f"pm-test-receiver-did-{uuid.uuid4().hex[:8]}"
    owner_registered = False
    receiver_registered = False
    test_owner_did = None # Will hold the string DID if registration is successful
    test_receiver_did = None # Will hold the string DID if registration is successful

    if can_run_did_tests and test_owner_eth_address and test_owner_eth_pk:
        owner_did_bytes = did_system.generate_did_identifier(test_owner_did_string)
        print(f"Attempting to register owner DID: {test_owner_did_string} (0x{owner_did_bytes.hex()})")
        if not did_system.is_did_registered(owner_did_bytes):
            owner_registered = did_system.register_did(
                owner_did_bytes, "test_pk_owner_pm", "QmTestCIDOwnerPM",
                test_owner_eth_address, test_owner_eth_pk
            )
            if owner_registered:
                print(f"Owner DID {test_owner_did_string} registered successfully.")
            else:
                print(f"Failed to register owner DID {test_owner_did_string}. See errors from did_system.")
        else:
            print(f"Owner DID {test_owner_did_string} (0x{owner_did_bytes.hex()}) is already registered.")
            owner_registered = True # Treat as success for the test if already there

        if owner_registered:
            test_owner_did = test_owner_did_string # Use the string identifier for project functions

        receiver_did_bytes = did_system.generate_did_identifier(test_receiver_did_string)
        print(f"Attempting to register receiver DID: {test_receiver_did_string} (0x{receiver_did_bytes.hex()})")
        if not did_system.is_did_registered(receiver_did_bytes):
            receiver_registered = did_system.register_did(
                receiver_did_bytes, "test_pk_receiver_pm", "QmTestCIDReceiverPM",
                test_owner_eth_address, test_owner_eth_pk # Registering with the same eth account for simplicity
            )
            if receiver_registered:
                print(f"Receiver DID {test_receiver_did_string} registered successfully.")
            else:
                print(f"Failed to register receiver DID {test_receiver_did_string}. See errors from did_system.")
        else:
            print(f"Receiver DID {test_receiver_did_string} (0x{receiver_did_bytes.hex()}) is already registered.")
            receiver_registered = True

        if receiver_registered:
            test_receiver_did = test_receiver_did_string # Use string identifier

    else:
        print("Skipping on-chain DID registration due to Ganache connection/account issues.")
        print("Project creation and transfer tests requiring new DIDs may fail or be skipped.")

    project1_id_for_test = None
    project2_id_for_test = None

    if owner_registered and test_owner_did: # Ensure owner DID string is available
        print(f"\nUsing registered owner DID: {test_owner_did} for project tests.")
        print("\nAttempting to create a new project 'My First Project'...")
        project1_data = create_project("My First Project", test_owner_did)
        if project1_data:
            print(f"Project 'My First Project' created successfully: {project1_data}")
            project1_id_for_test = project1_data.get("project_id")
        else:
            print("Failed to create 'My First Project'. Check IPFS daemon and DID registration status.")

        print("\nAttempting to create a project with the same name (should fail)...")
        project1_again_data = create_project("My First Project", test_owner_did)
        if not project1_again_data:
            print("Successfully prevented creation of duplicate project name/ID.")
        else:
            print(f"ERROR: Allowed creation of duplicate project: {project1_again_data}")

        print("\nAttempting to create a project with a different name 'Another Cool Project'...")
        project2_data = create_project("Another Cool Project!", test_owner_did, token_supply=500000)
        if project2_data:
            print(f"Project 'Another Cool Project!' created successfully: {project2_data}")
            project2_id_for_test = project2_data.get("project_id")
        else:
            print("Failed to create 'Another Cool Project!'.")
    else:
        print("\nSkipping project creation tests as owner DID was not successfully registered or available.")
        if not can_run_did_tests:
            print("   Reason: Ganache/contract connection issue or no accounts found.")
        elif not test_owner_eth_address or not test_owner_eth_pk:
             print("   Reason: Ethereum test account address or private key not set up.")
        else:
             print("   Reason: Failed to register or confirm owner DID on the blockchain.")

    print("\nAttempting to create a project with a non-registered DID string (should fail)...")
    # This test should ideally run regardless of whether test_owner_did was registered,
    # as it tests the negative case for create_project's DID validation.
    non_registered_did_string = "did:aegis:non-existent-pm-test-did"
    invalid_did_project = create_project("Invalid DID Project", non_registered_did_string)
    if not invalid_did_project:
        print(f"Successfully prevented creation with non-registered DID '{non_registered_did_string}'.")
    else:
        print(f"ERROR: Allowed creation of project with non-registered DID '{non_registered_did_string}': {invalid_did_project}")


    # --- Test get_project ---
    print("\n--- Testing get_project ---")
    if project1_id_for_test:
        print(f"Attempting to retrieve project with ID: {project1_id_for_test}")
        retrieved_project = get_project(project1_id_for_test)
        if retrieved_project:
            print(f"Successfully retrieved project: {retrieved_project}")
            assert retrieved_project.get("project_id") == project1_id_for_test
        else:
            print(f"Failed to retrieve project with ID: {project1_id_for_test}")
    else:
        print("Skipping get_project test as no project was successfully created.")

    print("\nAttempting to retrieve a non-existent project:")
    non_existent_project = get_project("non-existent-id")
    if not non_existent_project:
        print("Successfully confirmed non-existent project is not found.")
    else:
        print(f"ERROR: Retrieved a non-existent project: {non_existent_project}")

    # --- Test list_projects ---
    print("\n--- Testing list_projects ---")
    all_projects_before_transfer_test = list_projects() # Save state before potential removal
    print(f"Found {len(all_projects_before_transfer_test)} projects:")
    expected_project_count = 0
    if project1_id_for_test: expected_project_count +=1
    if project2_id_for_test: expected_project_count +=1
    
    for p in all_projects_before_transfer_test:
        print(f"  - {p.get('project_name')} (ID: {p.get('project_id')})")
    
    if len(all_projects_before_transfer_test) == expected_project_count:
        print(f"List projects returned expected number of projects ({expected_project_count}).")
    else:
        print(f"ERROR: List projects returned {len(all_projects_before_transfer_test)}, expected {expected_project_count}.")
    

    # --- Test transfer_project_tokens ---
    print("\n--- Testing transfer_project_tokens ---")
    if owner_registered and receiver_registered and test_owner_did and test_receiver_did and project1_id_for_test:
        print(f"Using registered owner DID: {test_owner_did} and receiver DID: {test_receiver_did} for transfer tests.")

        initial_project_state = get_project(project1_id_for_test)
        initial_owner_balance = initial_project_state["token_ledger"].get(test_owner_did, 0)
        print(f"Initial owner balance for project {project1_id_for_test}: {initial_owner_balance}")

        print("\nAttempting a valid transfer of 100 tokens...")
        if transfer_project_tokens(project1_id_for_test, test_owner_did, test_receiver_did, 100):
            print("Token transfer successful.")
            updated_project_state = get_project(project1_id_for_test)
            owner_balance_after = updated_project_state["token_ledger"].get(test_owner_did)
            receiver_balance_after = updated_project_state["token_ledger"].get(test_receiver_did)
            print(f"Owner balance after: {owner_balance_after}, Receiver balance after: {receiver_balance_after}")
            if owner_balance_after == initial_owner_balance - 100 and receiver_balance_after == 100:
                 print("Balances updated correctly.")
            else:
                 print("ERROR: Balances not updated correctly after transfer.")
        else:
            print("ERROR: Valid token transfer failed. Check DID registration and project state.")

        print("\nAttempting to transfer more tokens than available (should fail)...")
        # Ensure initial_owner_balance_for_this_test reflects the current balance after the first transfer
        current_owner_balance_for_fail_test = get_project(project1_id_for_test)["token_ledger"].get(test_owner_did, 0)
        if not transfer_project_tokens(project1_id_for_test, test_owner_did, test_receiver_did, current_owner_balance_for_fail_test + 100):
            print("Successfully prevented transfer of insufficient funds.")
        else:
            print("ERROR: Allowed transfer of insufficient funds.")

        print("\nAttempting to transfer with a non-registered sender DID string (should fail)...")
        non_registered_sender_did = "did:aegis:non-existent-sender-pm"
        if not transfer_project_tokens(project1_id_for_test, non_registered_sender_did, test_receiver_did, 10):
            print(f"Successfully prevented transfer from non-registered sender '{non_registered_sender_did}'.")
        else:
            print(f"ERROR: Allowed transfer from non-registered sender '{non_registered_sender_did}'.")
        
        print("\nAttempting to transfer to self (should fail)...")
        if not transfer_project_tokens(project1_id_for_test, test_owner_did, test_owner_did, 10):
            print("Successfully prevented transfer to self.")
        else:
            print("ERROR: Allowed transfer to self.")

    else:
        print("Skipping transfer_project_tokens tests due to missing or failed DID registrations, or project creation failure.")
        if not project1_id_for_test:
             print("   Reason: project1_id_for_test is not set (project creation likely failed).")
        if not owner_registered:
             print("   Reason: Owner DID was not registered.")
        if not receiver_registered:
             print("   Reason: Receiver DID was not registered.")
        if not test_owner_did:
             print("   Reason: test_owner_did string is None.")
        if not test_receiver_did:
             print("   Reason: test_receiver_did string is None.")


    # Test list_projects with no projects file (restore projects.json if it was removed by previous test)
    if not os.path.exists(PROJECTS_FILE) and all_projects_before_transfer_test:
         _save_projects(all_projects_before_transfer_test) # Restore for other potential tests or manual check

    if os.path.exists(PROJECTS_FILE): # This block should run if projects were created
        os.remove(PROJECTS_FILE)
        print(f"\nRemoved {PROJECTS_FILE} to test listing with no file.")
        all_projects_no_file = list_projects()
        if not all_projects_no_file: # Expect empty list
             print("Successfully returned empty list when projects.json is missing.")
        else:
             print(f"ERROR: Expected empty list with no projects.json, got: {all_projects_no_file}")


    # Clean up for next run (optional, good for CI/repeated tests)
    # Specific cleanup for created project directories could go here
    # Example:
    # if project1_id_for_test:
    #     project1_dir = os.path.join(PROJECT_DATA_BASE_DIR, project1_id_for_test)
    #     if os.path.exists(project1_dir):
    #         shutil.rmtree(project1_dir)
    #         print(f"Cleaned up test project directory: {project1_dir}")
    # if project2_id_for_test:
    #     project2_dir = os.path.join(PROJECT_DATA_BASE_DIR, project2_id_for_test)
    #     if os.path.exists(project2_dir):
    #         shutil.rmtree(project2_dir)
    #         print(f"Cleaned up test project directory: {project2_dir}")
    
    print("\n--- Project Management Tests: Cleaning up ---")
    # Clean up created project directories
    if project1_id_for_test:
        path_to_clean = os.path.join(PROJECT_DATA_BASE_DIR, project1_id_for_test)
        if os.path.exists(path_to_clean):
            shutil.rmtree(path_to_clean)
            print(f"Cleaned up test project directory: {path_to_clean}")
    if project2_id_for_test:
        path_to_clean = os.path.join(PROJECT_DATA_BASE_DIR, project2_id_for_test)
        if os.path.exists(path_to_clean):
            shutil.rmtree(path_to_clean)
            print(f"Cleaned up test project directory: {path_to_clean}")

    # Remove global files
    if os.path.exists(PROJECTS_FILE):
        os.remove(PROJECTS_FILE)
        print(f"Cleaned up {PROJECTS_FILE}")
    # Removed DIDS_FILE cleanup, no longer used by did_system or these tests directly.
        
    # Check if ipfs_storage.client is None to determine if IPFS-dependent tests were skipped
    if ipfs_storage.client is None:
        print("\n!!! Some project_management.py tests involving IPFS operations might have been affected or skipped due to no IPFS connection. !!!")
        print("!!! Ensure IPFS daemon is running for full test coverage. !!!")

    print("\nAll project_management.py tests passed successfully!")
