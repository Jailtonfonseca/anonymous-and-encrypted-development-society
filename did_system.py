import json
import uuid

DIDS_FILE = "dids.json"

def create_did(nickname: str = None) -> tuple[str, dict]:
    """
    Generates a new DID and stores it. Optionally accepts a nickname.

    Args:
        nickname: An optional nickname for the DID.

    Returns:
        A tuple containing the DID string and a dictionary with DID data (including nickname if provided).
    """
    did_uuid = uuid.uuid4()
    did_string = f"did:aegis:{did_uuid}"

    did_data = {"did": did_string}
    if nickname:
        did_data["nickname"] = nickname

    try:
        with open(DIDS_FILE, "r") as f:
            all_dids = json.load(f)
    except FileNotFoundError:
        all_dids = []

    all_dids.append(did_data)

    with open(DIDS_FILE, "w") as f:
        json.dump(all_dids, f, indent=4)

    return did_string, did_data

def get_did(did_string: str) -> dict | None:
    """
    Retrieves the information associated with a given DID string.

    Args:
        did_string: The DID string to retrieve.

    Returns:
        A dictionary with DID data if found, otherwise None.
    """
    try:
        with open(DIDS_FILE, "r") as f:
            all_dids = json.load(f)
    except FileNotFoundError:
        return None

    for did_data in all_dids:
        if did_data.get("did") == did_string:
            return did_data
    return None

def list_dids() -> list[dict]:
    """
    Lists all created DIDs.

    Returns:
        A list of dictionaries, where each dictionary contains DID data.
    """
    try:
        with open(DIDS_FILE, "r") as f:
            all_dids = json.load(f)
        return all_dids
    except FileNotFoundError:
        return []

if __name__ == "__main__":
    # Example Usage
    # Clean up dids.json before running examples for predictable output
    try:
        import os
        os.remove(DIDS_FILE)
    except FileNotFoundError:
        pass

    new_did, data = create_did(nickname="Alice_DID")
    print(f"Created DID: {new_did}")
    print(f"Associated Data: {data}")

    retrieved_data = get_did(new_did)
    print(f"Retrieved Data for {new_did}: {retrieved_data}")

    another_did, another_data = create_did()
    print(f"Created another DID: {another_did}")
    print(f"Associated Data: {another_data}")

    non_existent_did = "did:aegis:this-does-not-exist"
    retrieved_non_existent = get_did(non_existent_did)
    print(f"Retrieved Data for {non_existent_did}: {retrieved_non_existent}")

    print("\nListing all DIDs:")
    all_dids_list = list_dids()
    for did_entry in all_dids_list:
        print(did_entry)
    
    # Final cleanup for repeatable tests
    if os.path.exists(DIDS_FILE):
        os.remove(DIDS_FILE)
        # print(f"\nCleaned up {DIDS_FILE} at the end of tests.")

    print("\nAll did_system.py tests passed successfully!")
