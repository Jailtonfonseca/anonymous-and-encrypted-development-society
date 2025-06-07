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
    contributor_did_bytes32 = did_system.generate_did_identifier(contributor_did)
    if not did_system.is_did_registered(contributor_did_bytes32):
        print(f"Error: Contributor DID '{contributor_did}' is not registered on the blockchain. Cannot submit contribution.")
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

def review_contribution(proposal_id: str, reviewer_did: str, reviewer_private_key: str, new_status: str, reward_amount: int = 0) -> bool:
    """
    Reviews a contribution proposal, updating its status and potentially rewarding the contributor.

    Args:
        proposal_id: The ID of the contribution proposal to review.
        reviewer_did: The DID of the reviewer (must be project owner).
        reviewer_private_key: The private key of the reviewer (project owner) for signing token transfer.
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
            sender_did_string=project_owner_did, # This is reviewer_did, who must be the project owner
            receiver_did_string=contributor_did,
            amount_whole_tokens=reward_amount,
            sender_private_key=reviewer_private_key # Pass the new private key argument
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
    # Clean up previous test files
    # Note: did_system.DIDS_FILE is from the old local DID system, less relevant for blockchain tests.
    files_to_clean_for_test = [CONTRIBUTIONS_FILE, project_management.PROJECTS_FILE]
    # if os.path.exists(did_system.DIDS_FILE): # Keep this commented or remove if not testing old system fallback
    #     files_to_clean_for_test.append(did_system.DIDS_FILE)

    for f in files_to_clean_for_test:
        if os.path.exists(f):
            os.remove(f)
            print(f"Removed existing {f} for fresh test run.")

    import shutil
    # Clean up project_data directory if it exists from previous runs
    project_data_base_dir = project_management.PROJECT_DATA_BASE_DIR
    if os.path.exists(project_data_base_dir):
        # shutil.rmtree(project_data_base_dir)
        # print(f"Cleaned up base directory: {project_data_base_dir}")
        pass 

    os.makedirs(project_data_base_dir, exist_ok=True)
    
    # 1. Create a dummy owner DID and a contributor DID
    # These DIDs and their corresponding Ethereum accounts/private keys need to be managed carefully for on-chain tests.
    # For this test suite, we'll use placeholders.
    # Actual end-to-end testing requires these DIDs to be registered on the DIDRegistry
    # and linked to Ethereum accounts that hold tokens/ETH on Ganache.

    # Placeholder ETH addresses and private keys (replace with actual Ganache ones for real testing)
    # These should align with what project_management.py tests might use or expect for consistency.
    TEST_OWNER_ETH_PK = "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d" # Ganache default account 0 PK
    TEST_OWNER_ETH_ADDR = "0x90F8bf6A479f320ead074411a4B0e7944Ea8c9C1" # Ganache default account 0 Addr

    TEST_CONTRIBUTOR_ETH_PK = "0x6c002f5f36494661586ebb0882038bf8d598aafb88a5e2300971707fce91e997" # Ganache default account 1 PK
    TEST_CONTRIBUTOR_ETH_ADDR = "0x243540A32155412948a8963385C994A4e23f0750" # Ganache default account 1 Addr

    TEST_NON_OWNER_ETH_PK = "0x7e0d6f92f98915a1dedc605245bdd07e1f7f08a500440234ac93c629624f808a" # Ganache default account 2 PK
    TEST_NON_OWNER_ETH_ADDR = "0xACa94ef8bD5ffEE41947b4585a84BdA5a3d3DA6E" # Ganache default account 2 Addr


    # For the purpose of this test, we'll use DID strings.
    # In a real test, ensure these DIDs are registered via did_system.py to the ETH addresses above.
    owner_did = f"did:aegis:owner-contrib-test-{uuid.uuid4().hex[:4]}"
    contributor_did = f"did:aegis:contrib-contrib-test-{uuid.uuid4().hex[:4]}"
    non_owner_reviewer_did = f"did:aegis:nonowner-contrib-test-{uuid.uuid4().hex[:4]}"

    print(f"Test DIDs: Owner='{owner_did}', Contributor='{contributor_did}', NonOwnerReviewer='{non_owner_reviewer_did}'")
    print(f"Reminder: For full end-to-end tests, these DIDs must be registered on DIDRegistry,")
    print(f"  '{owner_did}' must be linked to an ETH account like '{TEST_OWNER_ETH_ADDR}',")
    print(f"  '{contributor_did}' to an ETH account like '{TEST_CONTRIBUTOR_ETH_ADDR}'.")
    print(f"  The project created by '{owner_did}' will have its tokens owned by '{TEST_OWNER_ETH_ADDR}'.")


    test_proposal_id = None
    test_project_id = None
    reject_proposal_id = None

    # 2. Create a dummy project using project_management.py
    # This now requires owner_private_key for token deployment.
    print("Setting up a test project using project_management.create_project...")
    project_data = project_management.create_project(
        project_name="Contributions Test Project",
        owner_did=owner_did, # This DID must be registered to TEST_OWNER_ETH_ADDR for the call to succeed
        token_supply=1000000, # Whole tokens
        owner_private_key=TEST_OWNER_ETH_PK # PK for TEST_OWNER_ETH_ADDR
    )
    if not project_data:
        print("Failed to create a test project via project_management. Aborting further contribution tests.")
        # Clean up and exit or skip tests
        if os.path.exists(CONTRIBUTIONS_FILE): os.remove(CONTRIBUTIONS_FILE)
        if os.path.exists(project_management.PROJECTS_FILE): os.remove(project_management.PROJECTS_FILE)
        # Add more cleanup if needed
    else:
        test_project_id = project_data.get("project_id")
        print(f"Test Project ID: {test_project_id} created with Token Contract: {project_data.get('project_token_contract_address')}")

            # 3. Create a dummy content file
            dummy_content_filename = "dummy_contribution.txt"
            with open(dummy_content_filename, "w") as f:
                f.write("This is a test contribution file.")
            print(f"Created dummy content file: {dummy_content_filename}")

            # 4. Test submit_contribution
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

            print("\nAttempting to submit to a non-existent project (should fail)...")
            fail_prop_id = submit_contribution("non-existent-project", contributor_did, "Fail", "Desc", dummy_content_filename)
            assert not fail_prop_id, "Should prevent submission to non-existent project."
            print("Successfully prevented submission to non-existent project.")

            if os.path.exists(dummy_content_filename):
                os.remove(dummy_content_filename)

    # --- Test review_contribution ---
    # This now involves an on-chain token transfer.
    print("\n--- Testing review_contribution (on-chain token transfer) ---")
    if test_proposal_id and owner_did and test_project_id and contributor_did:
        print(f"\nAttempting to approve contribution {test_proposal_id} by project owner {owner_did} with 100 token reward...")
        # The `owner_did` is the reviewer, and their private key `TEST_OWNER_ETH_PK` is needed for the transfer.
        review_success = review_contribution(
            proposal_id=test_proposal_id,
            reviewer_did=owner_did,
            reviewer_private_key=TEST_OWNER_ETH_PK, # PK for project owner (sender of tokens)
            new_status="approved",
            reward_amount=100
        )
        if review_success:
            print(f"Review successful for proposal {test_proposal_id}.")
            updated_proposal = get_contribution(test_proposal_id)
            assert updated_proposal["status"] == "approved"
            assert updated_proposal["reviewer_did"] == owner_did
            assert updated_proposal["reward_amount"] == 100
            # Balance check would require Web3 interaction with the ProjectToken contract here
            # For this test, we assume project_management.transfer_project_tokens handles it.
            print("Proposal status, reviewer, and reward amount updated correctly in contributions.json.")
            print("On-chain token transfer assumed successful if review_contribution returned True.")
        else:
            print(f"ERROR: Review failed for proposal {test_proposal_id}. Check Ganache logs and token transfer logic.")

        print(f"\nAttempting to review by a non-owner DID {non_owner_reviewer_did} (should fail)...")
        # Non-owner tries to approve, providing their PK. The function should reject based on DID.
        unauth_review = review_contribution(
            proposal_id=test_proposal_id,
            reviewer_did=non_owner_reviewer_did,
            reviewer_private_key=TEST_NON_OWNER_ETH_PK, # PK of the non-owner
            new_status="approved",
            reward_amount=50
        )
        if not unauth_review:
            print("Successfully prevented unauthorized review.")
            updated_proposal_after_fail = get_contribution(test_proposal_id)
            # Status should remain 'approved' from the legitimate review, not changed by unauthorized attempt.
            assert updated_proposal_after_fail["status"] == "approved"
        else:
            print("ERROR: Allowed unauthorized review.")

        print(f"\nAttempting to reject another (new) contribution...")
        dummy_reject_content = "reject_me.txt"
        with open(dummy_reject_content, "w") as f: f.write("content to reject")
        reject_proposal_id = submit_contribution(test_project_id, contributor_did, "Reject Test", "Desc", dummy_reject_content)
        os.remove(dummy_reject_content)

        if reject_proposal_id:
            # Project owner (owner_did) rejects, their PK is technically not needed for 'rejected' status if reward is 0.
            # However, the function signature requires it.
            reject_success = review_contribution(
                proposal_id=reject_proposal_id,
                reviewer_did=owner_did,
                reviewer_private_key=TEST_OWNER_ETH_PK,
                new_status="rejected",
                reward_amount=0
            )
            if reject_success:
                print(f"Rejection successful for proposal {reject_proposal_id}.")
                rejected_proposal = get_contribution(reject_proposal_id)
                assert rejected_proposal["status"] == "rejected"
                assert rejected_proposal["reward_amount"] == 0
                print("Rejection details updated correctly.")
            else:
                print(f"ERROR: Rejection failed for proposal {reject_proposal_id}.")
    else:
        print("Skipping review_contribution tests due to prior setup failures.")

    # --- Test get_contribution ---
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
    if test_project_id:
        print(f"Listing contributions for project: {test_project_id}")
        project_contribs = list_contributions_for_project(test_project_id)
        expected_count = 0
        if test_proposal_id: expected_count +=1
        if reject_proposal_id: expected_count +=1 # The one created for rejection test

        print(f"Found {len(project_contribs)} contributions for project {test_project_id}.")
        for pc in project_contribs:
            print(f"  - {pc['title']} (ID: {pc['proposal_id']})")
        assert len(project_contribs) == expected_count, f"Expected {expected_count} contributions, got {len(project_contribs)}"
        
        print("\nListing contributions for a non-existent project:")
        non_existent_proj_contribs = list_contributions_for_project("non-existent-project-id")
        assert len(non_existent_proj_contribs) == 0
        print("Successfully returned empty list for non-existent project.")
    else:
        print("Skipping list_contributions_for_project test as test_project_id is not set.")

    # --- Test list_all_contributions ---
    print("\n--- Testing list_all_contributions ---")
    all_contribs = list_all_contributions()
    expected_total_count = 0
    if test_proposal_id: expected_total_count +=1
    if reject_proposal_id: expected_total_count +=1
    print(f"Found {len(all_contribs)} total contributions.")
    assert len(all_contribs) == expected_total_count, f"Expected {expected_total_count} total contributions, got {len(all_contribs)}"
    for c in all_contribs:
        print(f"  - Project: {c['project_id']}, Title: {c['title']}")

    # Test with no contributions file
    if os.path.exists(CONTRIBUTIONS_FILE):
        os.remove(CONTRIBUTIONS_FILE)
    print("\nListing all contributions after removing file (should be empty list):")
    empty_contribs = list_all_contributions()
    assert len(empty_contribs) == 0
    print("Successfully returned empty list when contributions.json is missing.")


    # Clean up test files at the end (optional)
    # for f in [CONTRIBUTIONS_FILE, did_system.DIDS_FILE, project_management.PROJECTS_FILE]:
    #     if os.path.exists(f): os.remove(f)
    # if os.path.exists(project_data_base_dir): shutil.rmtree(project_data_base_dir)

    print("\n--- Contribution Workflow Tests: Cleaning up ---")
    # Clean up specific project directories created for these tests
    if test_project_id:
        path_to_clean = os.path.join(project_management.PROJECT_DATA_BASE_DIR, test_project_id)
        if os.path.exists(path_to_clean):
            shutil.rmtree(path_to_clean)
            print(f"Cleaned up test project directory: {path_to_clean}")

    # Clean up global JSON files
    files_to_remove_after_test = [CONTRIBUTIONS_FILE, project_management.PROJECTS_FILE]
    # did_system.DIDS_FILE is managed by did_system tests, not directly by these.

    for f_path in files_to_remove_after_test:
        if os.path.exists(f_path):
            os.remove(f_path)
            print(f"Cleaned up {f_path}")
            
    # Check if ipfs_storage.client is None to determine if IPFS-dependent tests were skipped
    # Also, check project_management.py's web3 instance for on-chain dependent tests
    if ipfs_storage.client is None :
        print("\n!!! IPFS-dependent tests might have been affected or skipped due to no IPFS connection. Ensure IPFS daemon is running. !!!")

    # Check if project_management could connect to web3, which is needed for create_project's token deployment
    # This is an indirect check. A more direct check within project_management tests would be better.
    if project_data is None and test_project_id is None: # If project creation failed early
         print("\n!!! On-chain dependent tests in contribution_workflow.py were likely skipped or failed due to project creation failure. !!!")
         print("!!! This often means issues connecting to Ganache, or problems with `deploy_project_token.py` or DID setup. !!!")


    print("\nAll contribution_workflow.py tests (adapted for on-chain interaction) completed!")
    print("Note: Full success of these tests depends on a correctly configured local blockchain environment (Ganache),")
    print("deployed DIDRegistry, registered DIDs, and functional dependent scripts (deploy_project_token.py).")
