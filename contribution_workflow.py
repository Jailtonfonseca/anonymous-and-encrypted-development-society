import json
import os
import uuid
from datetime import datetime

# Assuming did_system.py, ipfs_storage.py, and project_management.py are accessible
import did_system
import ipfs_storage
import project_management

CONTRIBUTIONS_FILE = "contributions.json"

def _generate_proposal_id() -> str:
    """Generates a unique proposal ID."""
    return f"prop-{uuid.uuid4().hex}"

def _load_contributions() -> list:
    """Loads contribution data from CONTRIBUTIONS_FILE."""
    if not os.path.exists(CONTRIBUTIONS_FILE):
        return []
    try:
        with open(CONTRIBUTIONS_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Warning: {CONTRIBUTIONS_FILE} contains invalid JSON. Starting with an empty list.")
        return []
    except Exception as e:
        print(f"Error loading contributions from {CONTRIBUTIONS_FILE}: {e}")
        return []

def _save_contributions(contributions_data: list) -> bool:
    """Saves contribution data to CONTRIBUTIONS_FILE."""
    try:
        with open(CONTRIBUTIONS_FILE, "w") as f:
            json.dump(contributions_data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving contributions to {CONTRIBUTIONS_FILE}: {e}")
        return False

def submit_contribution(project_id: str, contributor_did: str, title: str, description: str, content_file_path: str) -> str | None:
    """
    Submits a new contribution proposal for a project.

    Args:
        project_id: The ID of the project.
        contributor_did: The DID of the contributor.
        title: The title of the contribution.
        description: A description of the contribution.
        content_file_path: The local path to the file containing the contribution content.

    Returns:
        The proposal_id if successful, otherwise None.
    """
    # 1. Validate project_id
    project_data = project_management.get_project(project_id)
    if not project_data:
        print(f"Error: Project with ID '{project_id}' not found. Cannot submit contribution.")
        return None

    # 2. Validate contributor_did
    contributor_did_bytes = did_system.generate_did_identifier(contributor_did)
    if not did_system.is_did_registered(contributor_did_bytes):
        print(f"Error: Contributor DID '{contributor_did}' (Bytes: {contributor_did_bytes.hex()}) is not registered on the blockchain.")
        return None

    # 3. Add content to IPFS
    if not os.path.exists(content_file_path):
        print(f"Error: Contribution content file '{content_file_path}' not found.")
        return None
    
    print(f"Adding contribution content '{content_file_path}' to IPFS...")
    content_cid = ipfs_storage.add_file_to_ipfs(content_file_path)
    if not content_cid:
        print(f"Error: Failed to add contribution content to IPFS for project '{project_id}'.")
        return None
    print(f"Content added to IPFS with CID: {content_cid}")

    # 4. Generate proposal_id
    proposal_id = _generate_proposal_id()

    # 5. Store the new proposal
    new_proposal = {
        "proposal_id": proposal_id,
        "project_id": project_id,
        "contributor_did": contributor_did,
        "title": title,
        "description": description,
        "content_cid": content_cid,
        "submission_timestamp": datetime.utcnow().isoformat(),
        "status": "pending", # Initial status
        "reviewer_did": None,
        "review_timestamp": None,
        "reward_amount": 0 # Default reward, can be set during review
    }

    contributions = _load_contributions()
    contributions.append(new_proposal)
    if not _save_contributions(contributions):
        print(f"Error: Failed to save new contribution proposal for project '{project_id}'.")
        # Potentially try to remove the content from IPFS if critical? For MVP, this is acceptable.
        return None

    print(f"Contribution '{title}' submitted successfully for project '{project_id}' with Proposal ID: {proposal_id}.")
    return proposal_id

def review_contribution(proposal_id: str, reviewer_did: str, new_status: str, reward_amount: int = 0) -> bool:
    """
    Reviews a contribution proposal, updating its status and potentially rewarding the contributor.

    Args:
        proposal_id: The ID of the contribution proposal to review.
        reviewer_did: The DID of the reviewer (must be project owner).
        new_status: The new status for the proposal (e.g., "approved", "rejected").
        reward_amount: The amount of project tokens to reward if approved.

    Returns:
        True if the review was successful, False otherwise.
    """
    contributions = _load_contributions()
    proposal_index = -1
    contribution_data = None

    for i, p in enumerate(contributions):
        if p.get("proposal_id") == proposal_id:
            proposal_index = i
            contribution_data = p
            break
    
    if not contribution_data:
        print(f"Error: Contribution proposal with ID '{proposal_id}' not found.")
        return False

    # 2. Retrieve project data
    project_id = contribution_data.get("project_id")
    project_data = project_management.get_project(project_id)
    if not project_data:
        print(f"Error: Project with ID '{project_id}' (associated with proposal) not found.")
        return False # Should not happen if submit_contribution worked

    # 3. Verify reviewer_did is project owner
    project_owner_did = project_data.get("owner_did")
    if reviewer_did != project_owner_did:
        print(f"Error: Reviewer DID '{reviewer_did}' is not the owner of project '{project_id}' ({project_owner_did}). Review unauthorized.")
        return False

    # 4. Update proposal details
    valid_statuses = ["approved", "rejected", "pending"] # Can add more like "needs_revision"
    if new_status not in valid_statuses:
        print(f"Error: Invalid new status '{new_status}'. Must be one of {valid_statuses}.")
        return False

    contribution_data["status"] = new_status
    contribution_data["reviewer_did"] = reviewer_did
    contribution_data["review_timestamp"] = datetime.utcnow().isoformat()
    contribution_data["reward_amount"] = reward_amount if new_status == "approved" else 0 # Only store reward if approved

    # 5. If approved and reward > 0, transfer tokens
    if new_status == "approved" and reward_amount > 0:
        contributor_did = contribution_data.get("contributor_did")
        print(f"Attempting to reward {reward_amount} tokens to contributor {contributor_did} for project {project_id}...")
        
        transfer_success = project_management.transfer_project_tokens(
            project_id=project_id,
            sender_did=project_owner_did, # Project owner's DID is the sender
            receiver_did=contributor_did,
            amount=reward_amount
        )
        if not transfer_success:
            print(f"Error: Token transfer of {reward_amount} to {contributor_did} failed for project {project_id}.")
            # Rollback status? For MVP, log and return False.
            # contribution_data["status"] = "pending" # Example rollback
            # contribution_data["reward_amount"] = 0
            # _save_contributions(contributions) # Save rollback
            print("Review status updated, but reward transfer failed. Manual intervention may be needed.")
            # Still save the review part, but indicate overall failure due to token transfer
            _save_contributions(contributions)
            return False 
    
    # Save changes to contributions.json
    contributions[proposal_index] = contribution_data
    if not _save_contributions(contributions):
        print(f"Error: Failed to save updated contribution proposal '{proposal_id}'.")
        return False

    print(f"Contribution proposal '{proposal_id}' reviewed successfully. New status: {new_status}, Reward: {reward_amount if new_status == 'approved' else 0}.")
    return True

def get_contribution(proposal_id: str) -> dict | None:
    """
    Retrieves a specific contribution proposal by its ID.

    Args:
        proposal_id: The ID of the proposal to retrieve.

    Returns:
        The contribution dictionary if found, otherwise None.
    """
    contributions = _load_contributions()
    for p in contributions:
        if p.get("proposal_id") == proposal_id:
            return p
    print(f"Contribution proposal with ID '{proposal_id}' not found.")
    return None

def list_contributions_for_project(project_id: str) -> list:
    """
    Lists all contribution proposals for a specific project.

    Args:
        project_id: The ID of the project.

    Returns:
        A list of contribution dictionaries for the project.
    """
    all_contributions = _load_contributions()
    project_contributions = [p for p in all_contributions if p.get("project_id") == project_id]
    return project_contributions

def list_all_contributions() -> list:
    """
    Lists all contribution proposals stored.

    Returns:
        A list of all contribution dictionaries.
    """
    return _load_contributions()

if __name__ == '__main__':
    # Test helper functions
    print("Testing _generate_proposal_id:")
    print(f"Generated ID 1: {_generate_proposal_id()}")
    print(f"Generated ID 2: {_generate_proposal_id()}")

    # --- Test submit_contribution ---
    print("\n--- Testing submit_contribution ---")

    # Setup: Requires did_system, ipfs_storage, project_management to be functional
    # and IPFS daemon running.
    # Clean up previous test files for a clean slate
    print("Cleaning up existing test files (if any)...")
    if os.path.exists(CONTRIBUTIONS_FILE):
        os.remove(CONTRIBUTIONS_FILE)
        print(f"Removed {CONTRIBUTIONS_FILE}")
    if os.path.exists(project_management.PROJECTS_FILE):
        os.remove(project_management.PROJECTS_FILE)
        print(f"Removed {project_management.PROJECTS_FILE}")
    # Note: did_system.DIDS_FILE is no longer used by did_system.py

    import shutil
    project_data_base_dir = project_management.PROJECT_DATA_BASE_DIR
    # Cautious about rmtree, only remove if it's genuinely from these tests or ensure it's empty
    # For now, just ensure it exists. Specific project test dirs will be cleaned later.
    os.makedirs(project_data_base_dir, exist_ok=True)

    # --- Test DID Setup on Blockchain ---
    print("\nAttempting to set up test DIDs on the blockchain for contribution workflow tests...")
    test_eth_address = None
    test_eth_pk = None
    can_run_did_tests = False
    DEFAULT_GANACHE_PK_0 = "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d" # Example PK

    if did_system.w3 and did_system.did_registry_contract:
        if did_system.w3.eth.accounts:
            test_eth_address = did_system.w3.eth.accounts[0]
            test_eth_pk = DEFAULT_GANACHE_PK_0
            print(f"Using Ganache account {test_eth_address} for test DID registrations.")
            can_run_did_tests = True
        else:
            print("WARNING: No Ganache accounts found. Cannot register test DIDs on-chain.")
    else:
        print("WARNING: did_system.w3 or did_system.did_registry_contract is None.")
        print("Ganache/contract connection issue. DID-dependent tests will be skipped.")

    owner_did_string = f"cw-test-owner-{uuid.uuid4().hex[:6]}"
    contributor_did_string = f"cw-test-contrib-{uuid.uuid4().hex[:6]}"
    non_owner_reviewer_did_string = f"cw-test-reviewer-{uuid.uuid4().hex[:6]}"

    owner_did_registered = False
    contributor_did_registered = False
    non_owner_reviewer_did_registered = False

    owner_did = None
    contributor_did = None
    non_owner_reviewer_did = None

    if can_run_did_tests:
        # Register Owner DID
        owner_did_bytes = did_system.generate_did_identifier(owner_did_string)
        if not did_system.is_did_registered(owner_did_bytes):
            print(f"Registering Owner DID: {owner_did_string}")
            owner_did_registered = did_system.register_did(
                owner_did_bytes, "test_pk_cw_owner", "QmCWTestOwner", test_eth_address, test_eth_pk
            )
            if owner_did_registered: print(f"Owner DID {owner_did_string} registered.")
            else: print(f"Failed to register Owner DID {owner_did_string}.")
        else:
            print(f"Owner DID {owner_did_string} already registered.")
            owner_did_registered = True
        if owner_did_registered: owner_did = owner_did_string

        # Register Contributor DID
        contributor_did_bytes = did_system.generate_did_identifier(contributor_did_string)
        if not did_system.is_did_registered(contributor_did_bytes):
            print(f"Registering Contributor DID: {contributor_did_string}")
            contributor_did_registered = did_system.register_did(
                contributor_did_bytes, "test_pk_cw_contrib", "QmCWTestContrib", test_eth_address, test_eth_pk
            )
            if contributor_did_registered: print(f"Contributor DID {contributor_did_string} registered.")
            else: print(f"Failed to register Contributor DID {contributor_did_string}.")
        else:
            print(f"Contributor DID {contributor_did_string} already registered.")
            contributor_did_registered = True
        if contributor_did_registered: contributor_did = contributor_did_string

        # Register Non-Owner Reviewer DID
        non_owner_did_bytes = did_system.generate_did_identifier(non_owner_reviewer_did_string)
        if not did_system.is_did_registered(non_owner_did_bytes):
            print(f"Registering Non-Owner Reviewer DID: {non_owner_reviewer_did_string}")
            non_owner_reviewer_did_registered = did_system.register_did(
                non_owner_did_bytes, "test_pk_cw_reviewer", "QmCWTestReviewer", test_eth_address, test_eth_pk
            )
            if non_owner_reviewer_did_registered: print(f"Non-Owner Reviewer DID {non_owner_reviewer_did_string} registered.")
            else: print(f"Failed to register Non-Owner Reviewer DID {non_owner_reviewer_did_string}.")
        else:
            print(f"Non-Owner Reviewer DID {non_owner_reviewer_did_string} already registered.")
            non_owner_reviewer_did_registered = True
        if non_owner_reviewer_did_registered: non_owner_reviewer_did = non_owner_reviewer_did_string
    else:
        print("Skipping DID registration due to Ganache/contract issues.")

    test_proposal_id = None
    test_project_id = None
    reject_proposal_id = None
    dummy_content_filename = f"dummy_contribution_{uuid.uuid4().hex[:6]}.txt"


    if owner_did and contributor_did and non_owner_reviewer_did:
        print(f"\nSuccessfully set up DIDs: Owner({owner_did}), Contributor({contributor_did}), Reviewer({non_owner_reviewer_did})")
        print("Setting up a test project...")
        project_data = project_management.create_project(
            "Test Project for Contributions", owner_did, token_supply=100000
        )
        if not project_data:
            print("Failed to create a test project. Aborting further tests that depend on it.")
        else:
            test_project_id = project_data.get("project_id")
            print(f"Test Project ID: {test_project_id}")

            with open(dummy_content_filename, "w") as f:
                f.write("This is a test contribution file.")
            print(f"Created dummy content file: {dummy_content_filename}")

            print("\nSubmitting a new contribution...")
            test_proposal_id = submit_contribution(
                project_id=test_project_id,
                contributor_did=contributor_did,
                title="My First Contribution",
                description="Added a new feature X.",
                content_file_path=dummy_content_filename
            )

            if test_proposal_id:
                print(f"Contribution submitted successfully. Proposal ID: {test_proposal_id}")
                contributions_list = _load_contributions()
                assert len(contributions_list) == 1
                assert contributions_list[0]["proposal_id"] == test_proposal_id
                print("Contribution found in contributions.json with correct details.")
            else:
                print("Failed to submit contribution. Further tests might fail.")

            # Test submitting to a non-existent project (should fail)
            # This test can run even if DIDs weren't fully set up, as it tests project existence primarily
            print("\nAttempting to submit to a non-existent project (should fail)...")
            # Need a valid-looking DID string for this test, even if not registered, to pass initial checks in some versions
            temp_contrib_did_for_neg_test = contributor_did if contributor_did else f"temp-did-{uuid.uuid4().hex[:4]}"

            # To test this properly, we need to ensure that the temp_contrib_did_for_neg_test *is* registered if submit_contribution checks it.
            # However, the primary check here is for project_id.
            # If contributor_did is None (because registration failed), this test might behave differently.
            # For now, let's assume submit_contribution's first check is project_id.
            # If it checks DID first and contributor_did is None, this test will also show that failure.
            if temp_contrib_did_for_neg_test and not did_system.is_did_registered(did_system.generate_did_identifier(temp_contrib_did_for_neg_test)) and can_run_did_tests:
                 print(f"Note: For negative test (non-existent project), a temporary contributor DID '{temp_contrib_did_for_neg_test}' is used. Registering it for robustness of this specific test path.")
                 did_system.register_did(did_system.generate_did_identifier(temp_contrib_did_for_neg_test), "pk", "cid", test_eth_address, test_eth_pk)

            if os.path.exists(dummy_content_filename): # Ensure file exists for this attempt
                fail_prop_id = submit_contribution("non-existent-project", temp_contrib_did_for_neg_test, "Fail", "Desc", dummy_content_filename)
                assert not fail_prop_id, "Should prevent submission to non-existent project."
                print("Successfully prevented submission to non-existent project.")
            else:
                print(f"Skipping non-existent project submission test as {dummy_content_filename} is missing.")

    else:
        print("Essential DIDs (owner, contributor, reviewer) failed to register. Skipping most functional tests.")

    # --- Test review_contribution ---
    # This block will only run if test_proposal_id, owner_did, test_project_id, contributor_did, non_owner_reviewer_did are set
    print("\n--- Testing review_contribution ---")
    if test_proposal_id and owner_did and test_project_id and contributor_did and non_owner_reviewer_did:
        print(f"\nAttempting to approve contribution {test_proposal_id} by project owner {owner_did} with 100 token reward...")
        review_success = review_contribution(test_proposal_id, owner_did, "approved", 100)
        if review_success:
            print(f"Review successful for proposal {test_proposal_id}.")
            updated_proposal = get_contribution(test_proposal_id)
            assert updated_proposal["status"] == "approved"
            assert updated_proposal["reviewer_did"] == owner_did
            assert updated_proposal["reward_amount"] == 100
            reviewed_project_state = project_management.get_project(test_project_id)
            contributor_balance = reviewed_project_state["token_ledger"].get(contributor_did)
            assert contributor_balance == 100, f"Contributor balance should be 100, got {contributor_balance}"
            print("Proposal status, reviewer, reward, and token ledger updated correctly.")
        else:
            print(f"ERROR: Review failed for proposal {test_proposal_id}.")

        print(f"\nAttempting to review by a non-owner DID {non_owner_reviewer_did} (should fail)...")
        unauth_review = review_contribution(test_proposal_id, non_owner_reviewer_did, "approved", 50)
        if not unauth_review:
            print("Successfully prevented unauthorized review.")
            updated_proposal_after_fail = get_contribution(test_proposal_id)
            assert updated_proposal_after_fail["status"] == "approved", "Status should not change on failed unauthorized review."
        else:
            print("ERROR: Allowed unauthorized review.")

        print(f"\nAttempting to reject another (new) contribution...")
        dummy_reject_content_filename = f"reject_me_{uuid.uuid4().hex[:6]}.txt"
        with open(dummy_reject_content_filename, "w") as f: f.write("content to reject")
        reject_proposal_id = submit_contribution(test_project_id, contributor_did, "Reject Test", "Desc", dummy_reject_content_filename)

        if reject_proposal_id:
            reject_success = review_contribution(reject_proposal_id, owner_did, "rejected", 0) 
            if reject_success:
                print(f"Rejection successful for proposal {reject_proposal_id}.")
                rejected_proposal = get_contribution(reject_proposal_id)
                assert rejected_proposal["status"] == "rejected"
                assert rejected_proposal["reward_amount"] == 0
                print("Rejection details updated correctly.")
            else:
                print(f"ERROR: Rejection failed for proposal {reject_proposal_id}.")
        else:
            print("Failed to submit a new contribution for rejection test.")
        if os.path.exists(dummy_reject_content_filename):
            os.remove(dummy_reject_content_filename)
    else:
        print("Skipping review_contribution tests due to prior setup failures (DIDs or initial project/proposal).")

    # --- Test get_contribution ---
    # This test can partially run if test_proposal_id was set, even if review tests were skipped.
    print("\n--- Testing get_contribution ---")
    if test_proposal_id:
        print(f"Attempting to retrieve existing proposal: {test_proposal_id}")
        retrieved = get_contribution(test_proposal_id)
        assert retrieved is not None and retrieved["proposal_id"] == test_proposal_id
        print(f"Successfully retrieved: {retrieved['title']}")
    
    print("Attempting to retrieve non-existent proposal:")
    non_existent = get_contribution("prop-does-not-exist")
    assert non_existent is None
    print("Successfully confirmed non-existent proposal returns None.")

    # --- Test list_contributions_for_project ---
    print("\n--- Testing list_contributions_for_project ---")
    if test_project_id: # Only if a project was successfully created
        print(f"Listing contributions for project: {test_project_id}")
        project_contribs = list_contributions_for_project(test_project_id)

        # Determine expected count based on successful submissions
        expected_count_proj = 0
        if test_proposal_id and get_contribution(test_proposal_id): expected_count_proj +=1
        if reject_proposal_id and get_contribution(reject_proposal_id): expected_count_proj +=1

        print(f"Found {len(project_contribs)} contributions for project {test_project_id}.")
        for pc in project_contribs:
            print(f"  - {pc['title']} (ID: {pc['proposal_id']})")
        assert len(project_contribs) == expected_count_proj, f"Expected {expected_count_proj} contributions for project, got {len(project_contribs)}"
        
        print("\nListing contributions for a non-existent project:")
        non_existent_proj_contribs = list_contributions_for_project("non-existent-project-id")
        assert len(non_existent_proj_contribs) == 0
        print("Successfully returned empty list for non-existent project.")
    else:
        print("Skipping list_contributions_for_project test as test_project_id was not set (project creation likely failed or skipped).")

    # --- Test list_all_contributions ---
    # This test is less dependent on specific project_id, more on whether any contributions were made.
    print("\n--- Testing list_all_contributions ---")
    all_contribs = list_all_contributions()
    expected_total_count = 0
    if test_proposal_id: expected_total_count +=1
    if reject_proposal_id: expected_total_count +=1
    print(f"Found {len(all_contribs)} total contributions.")
    assert len(all_contribs) == expected_total_count, f"Expected {expected_total_count} total contributions, got {len(all_contribs)}"
    for c in all_contribs:
        print(f"  - Project: {c['project_id']}, Title: {c['title']}")

    # Test with no contributions file (ensure this runs after other list tests)
    # To ensure this specific test is valid, we first save current, then remove, then test, then restore.
    current_contributions_if_any = list_all_contributions() # Get current state
    if os.path.exists(CONTRIBUTIONS_FILE):
        os.remove(CONTRIBUTIONS_FILE)
        print(f"\nTemporarily removed {CONTRIBUTIONS_FILE} to test listing with no file.")

    print("Listing all contributions after removing file (should be empty list):")
    empty_contribs = list_all_contributions()
    assert len(empty_contribs) == 0, f"Expected empty list with no contributions.json, got {len(empty_contribs)}"
    print("Successfully returned empty list when contributions.json is missing.")

    if current_contributions_if_any: # Restore if there were any
        _save_contributions(current_contributions_if_any)
        print(f"Restored {CONTRIBUTIONS_FILE} with {len(current_contributions_if_any)} items.")


    print("\n--- Contribution Workflow Tests: Cleaning up ---")
    if os.path.exists(dummy_content_filename): # Ensure main test dummy file is removed
        os.remove(dummy_content_filename)
        print(f"Cleaned up dummy content file: {dummy_content_filename}")

    # Clean up specific project directories created for these tests
    if test_project_id: # Only if a project was created
        path_to_clean = os.path.join(project_management.PROJECT_DATA_BASE_DIR, test_project_id)
        if os.path.exists(path_to_clean):
            shutil.rmtree(path_to_clean)
            print(f"Cleaned up test project directory: {path_to_clean}")

    # Clean up global JSON files created by these tests
    # Note: DIDS_FILE is not managed here as it's part of did_system's old behavior.
    # PROJECTS_FILE and CONTRIBUTIONS_FILE are managed at the start of the test block for a clean run.
    # This final cleanup is more for post-run state.
    if os.path.exists(CONTRIBUTIONS_FILE):
        os.remove(CONTRIBUTIONS_FILE)
        print(f"Cleaned up {CONTRIBUTIONS_FILE}")
    if os.path.exists(project_management.PROJECTS_FILE):
        os.remove(project_management.PROJECTS_FILE)
        print(f"Cleaned up {project_management.PROJECTS_FILE}")
            
    if not can_run_did_tests:
        print("\nNOTE: Some tests requiring DID registration and contract interaction may have been skipped or limited due to Ganache/contract connection issues.")
    if ipfs_storage.client is None:
        print("\n!!! Some contribution_workflow.py tests involving IPFS operations might have been affected or skipped due to no IPFS connection. !!!")
        print("!!! Ensure IPFS daemon is running for full test coverage. !!!")

    # Final success message depends on whether DID tests could run
    if can_run_did_tests or (not can_run_did_tests and not (owner_did or contributor_did or non_owner_reviewer_did)):
         # If DID tests were not runnable, and no DIDs were set (meaning test paths depending on DIDs were skipped)
         # then tests that could run, did.
        print("\nAll contribution_workflow.py tests that could be run completed based on environment setup.")
    else:
        # This case implies can_run_did_tests was true but some DIDs still failed to register.
        print("\nSome contribution_workflow.py tests completed, but there were issues with DID registrations despite available Ganache connection.")
