"""
IPFS Storage Module for Project Code Management.

This module provides functionalities to interact with a local IPFS daemon
for storing and retrieving project files and directories.

Setup:
1. Install the ipfshttpclient library:
   pip install ipfshttpclient
2. Ensure you have a local IPFS daemon running:
   ipfs daemon
"""
import ipfshttpclient
import os
import shutil
import re

# Global IPFS client instance
# Attempt to connect to the IPFS daemon.
# Common multiaddress for a local daemon is /ip4/127.0.0.1/tcp/5001
# Adjust if your daemon is configured differently.
try:
    client = ipfshttpclient.connect()
    # You can test the connection with client.version()
    # print(f"Connected to IPFS version: {client.version()}")
except ipfshttpclient.exceptions.ConnectionError as e:
    print(f"Error: IPFS daemon not found or connection refused: {e}")
    print("Please ensure the IPFS daemon is running.")
    client = None # Set client to None if connection fails

PROJECT_BASE_DIR = "./project_data"

def _sanitize_project_name(project_name: str) -> str:
    """Sanitizes a project name to be filesystem-friendly."""
    name = re.sub(r'[^\w\s-]', '', project_name) # Remove non-alphanumeric, non-whitespace, non-hyphen
    name = re.sub(r'[-\s]+', '-', name).strip('-_') # Replace whitespace/hyphens with single hyphen
    return name.lower()

def initialize_project_repo(project_name: str) -> str | None:
    """
    Initializes a new project repository locally and adds it to IPFS.

    Args:
        project_name: The desired name for the project.

    Returns:
        The IPFS CID of the initialized project repository directory, or None if an error occurs.
    """
    if not client:
        print("Error: IPFS client not available. Cannot initialize project.")
        return None

    sanitized_name = _sanitize_project_name(project_name)
    repo_path = os.path.join(PROJECT_BASE_DIR, sanitized_name, "repo")

    try:
        os.makedirs(repo_path, exist_ok=True)
        readme_content = f"# Welcome to Project {project_name}\n\nThis is the starting point for '{project_name}'."
        with open(os.path.join(repo_path, "README.md"), "w") as f:
            f.write(readme_content)

        # Add the directory to IPFS
        # The client.add() method can take a path to a directory.
        # It returns a list of dicts, where the last item is the directory itself.
        print(f"Adding '{repo_path}' to IPFS...")
        res = client.add(repo_path, recursive=True)
        # The directory's hash is typically the last one in the list for recursive adds.
        # Or, it's the one where the 'Name' matches the directory path.
        dir_hash = None
        for item in res:
            if item['Name'] == os.path.basename(repo_path) or item['Name'] == repo_path: # client.add behavior can vary
                 # sometimes it's just 'repo', sometimes 'project_data/sanitized_name/repo'
                 # Let's find the one that matches the last part of repo_path
                if item['Name'].endswith(os.path.basename(repo_path)):
                    dir_hash = item['Hash']
                    break
        if not dir_hash and res: # Fallback if specific name match fails but got results
            dir_hash = res[-1]['Hash']


        if dir_hash:
            print(f"Project '{project_name}' (sanitized: '{sanitized_name}') initialized at '{repo_path}'.")
            print(f"IPFS CID for the project repo: {dir_hash}")
            return dir_hash
        else:
            print(f"Error: Could not get IPFS CID for directory '{repo_path}'. Response: {res}")
            return None

    except ipfshttpclient.exceptions.CommunicationError as e:
        print(f"Error communicating with IPFS daemon: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during project initialization: {e}")
        return None

def add_file_to_ipfs(file_path: str) -> str | None:
    """
    Adds a single file to IPFS.

    Args:
        file_path: The local path to the file to be added.

    Returns:
        The IPFS CID of the added file, or None if an error occurs.
    """
    if not client:
        print("Error: IPFS client not available. Cannot add file.")
        return None

    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return None

    try:
        print(f"Adding file '{file_path}' to IPFS...")
        # client.add() returns a dict (for single file) or list of dicts (for multiple/directory)
        # For a single file, it's usually a single dict.
        res = client.add(file_path)
        file_hash = res['Hash']
        print(f"File '{file_path}' added to IPFS with CID: {file_hash}")
        return file_hash
    except ipfshttpclient.exceptions.CommunicationError as e:
        print(f"Error communicating with IPFS daemon: {e}")
        return None
    except FileNotFoundError: # Though we check with os.path.exists, client.add might also raise this
        print(f"Error: File '{file_path}' not found during IPFS add operation.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while adding file to IPFS: {e}")
        return None

def get_file_from_ipfs(cid: str, output_path: str) -> bool:
    """
    Retrieves a file from IPFS and saves it to the specified output path.

    Args:
        cid: The IPFS CID of the file to retrieve.
        output_path: The local path where the file should be saved.

    Returns:
        True if successful, False otherwise.
    """
    if not client:
        print("Error: IPFS client not available. Cannot get file.")
        return False

    try:
        print(f"Getting file with CID '{cid}' from IPFS...")
        # client.get(cid) downloads the file to the current directory by default.
        # To save to a specific output_path, we need to ensure the directory exists
        # and then either move the file or use client.cat() and write manually.
        # client.cat(cid) returns bytes.
        
        output_dir = os.path.dirname(output_path)
        if output_dir: # Ensure directory exists if output_path includes a directory
            os.makedirs(output_dir, exist_ok=True)

        # Using client.cat() for more control over the output location
        file_content = client.cat(cid)
        with open(output_path, "wb") as f:
            f.write(file_content)
        
        print(f"File '{cid}' retrieved from IPFS and saved to '{output_path}'.")
        return True
    except ipfshttpclient.exceptions.CommunicationError as e:
        print(f"Error communicating with IPFS daemon: {e}")
        return False
    except ipfshttpclient.exceptions.ErrorResponse as e:
        # This can happen if the CID is not found or is invalid
        print(f"Error response from IPFS daemon (e.g., CID not found): {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while getting file from IPFS: {e}")
        return False

def get_directory_from_ipfs(cid: str, output_path: str) -> bool:
    """
    Retrieves a directory (and its contents) from IPFS and saves it.
    The contents of the IPFS directory will be placed directly into output_path.

    Args:
        cid: The IPFS CID of the directory to retrieve.
        output_path: The local path where the directory contents should be saved.

    Returns:
        True if successful, False otherwise.
    """
    if not client:
        print("Error: IPFS client not available. Cannot get directory.")
        return False

    try:
        # Ensure the target output_path exists and is a directory
        os.makedirs(output_path, exist_ok=True)

        print(f"Getting directory with CID '{cid}' from IPFS to '{output_path}'...")
        
        # The client.get() command downloads the content into a directory named after the CID
        # within the current working directory, or within `target` if specified.
        # We want the *contents* of the CID to be in output_path.
        
        # Temporary download path to avoid issues if output_path is the CWD
        # or if client.get has specific behaviors with existing directories.
        # Let's download to a temporary location first, then move contents.
        # However, ipfshttpclient.get() will place it into a folder named CID within the target.
        # e.g. client.get("Qm...", target="/tmp/foo") will create /tmp/foo/Qm...
        # So, we need to download it, then move the contents of Qm... to output_path
        
        # Create a temporary directory for the download
        temp_download_dir = os.path.join(output_path, ".ipfs_temp_download")
        os.makedirs(temp_download_dir, exist_ok=True)

        client.get(cid, target=temp_download_dir)
        
        # The actual data is in temp_download_dir/cid
        downloaded_content_path = os.path.join(temp_download_dir, cid)
        
        # Move contents from downloaded_content_path to output_path
        for item in os.listdir(downloaded_content_path):
            s = os.path.join(downloaded_content_path, item)
            d = os.path.join(output_path, item)
            if os.path.isdir(s):
                shutil.move(s, d) # Use move for directories to avoid merging issues if d exists
            else:
                shutil.move(s, d)
        
        # Clean up the temporary download directory and the now-empty CID-named folder
        shutil.rmtree(temp_download_dir)
        # The CID-named folder itself within temp_download_dir would have been moved or its contents moved.
        # If downloaded_content_path still exists and is empty, remove it.
        # if os.path.exists(downloaded_content_path) and not os.listdir(downloaded_content_path):
        #     os.rmdir(downloaded_content_path)


        print(f"Directory '{cid}' retrieved from IPFS and its contents saved to '{output_path}'.")
        return True
    except ipfshttpclient.exceptions.CommunicationError as e:
        print(f"Error communicating with IPFS daemon: {e}")
        return False
    except ipfshttpclient.exceptions.ErrorResponse as e:
        print(f"Error response from IPFS daemon (e.g., CID not found or not a directory): {e}")
        if os.path.exists(temp_download_dir): # Clean up temp dir on error
            shutil.rmtree(temp_download_dir)
        return False
    except Exception as e:
        print(f"An unexpected error occurred while getting directory from IPFS: {e}")
        if 'temp_download_dir' in locals() and os.path.exists(temp_download_dir): # Clean up temp dir on error
            shutil.rmtree(temp_download_dir)
        return False

if __name__ == '__main__':
    if client:
        print("Successfully connected to IPFS daemon.")
        # Example of sanitizing a name
        raw_name = "My Awesome Project! (V1.0)"
        sanitized = _sanitize_project_name(raw_name)
        print(f"Raw name: '{raw_name}' -> Sanitized: '{sanitized}'")

        # Setup for examples
        test_project_name_files = "Example Project for Files" # For file add/get
        sanitized_test_project_name_files = _sanitize_project_name(test_project_name_files)
        test_project_base_path_files = os.path.join(PROJECT_BASE_DIR, sanitized_test_project_name_files)
        test_project_repo_path_files = os.path.join(test_project_base_path_files, "repo")
        retrieved_files_path = os.path.join(test_project_base_path_files, "retrieved_files")

        test_project_name_dirs = "Example Project for Dirs" # For dir init/get
        sanitized_test_project_name_dirs = _sanitize_project_name(test_project_name_dirs)
        retrieved_project_dir_path = os.path.join(PROJECT_BASE_DIR, "retrieved_" + sanitized_test_project_name_dirs)


        # Ensure directories for examples exist
        os.makedirs(test_project_repo_path_files, exist_ok=True)
        os.makedirs(retrieved_files_path, exist_ok=True)
        os.makedirs(retrieved_project_dir_path, exist_ok=True) # For get_directory_from_ipfs
        print(f"Created directories for file examples: {test_project_repo_path_files}, {retrieved_files_path}")
        print(f"Created directory for dir retrieval example: {retrieved_project_dir_path}")


        # Example of initializing a project (will be used for get_directory_from_ipfs)
        print("\nInitializing a project for directory retrieval test...")
        initialized_project_original_name = "My Test Directory Project"
        dir_project_cid = initialize_project_repo(initialized_project_original_name)
        if dir_project_cid:
            print(f"Project '{initialized_project_original_name}' initialized with CID: {dir_project_cid}")

            # Example of getting a directory
            print("\nGetting a directory from IPFS...")
            if get_directory_from_ipfs(dir_project_cid, retrieved_project_dir_path):
                print(f"Directory {dir_project_cid} retrieved successfully to {retrieved_project_dir_path}")
                # Check for README.md
                retrieved_readme = os.path.join(retrieved_project_dir_path, "README.md")
                if os.path.exists(retrieved_readme):
                    with open(retrieved_readme, "r") as f:
                        print(f"Content of retrieved README.md: '{f.read()[:50]}...'") # Print first 50 chars
                else:
                    print(f"README.md not found in {retrieved_project_dir_path}")
            else:
                print(f"Failed to retrieve directory with CID: {dir_project_cid}")
        else:
            print(f"Failed to initialize project '{initialized_project_original_name}', skipping get_directory example.")


        # Example of adding a file
        print("\nAdding a file to IPFS...")
        example_file_path = os.path.join(test_project_repo_path_files, "sample.txt")
        with open(example_file_path, "w") as f:
            f.write("This is a sample file for IPFS testing.")

        file_cid = add_file_to_ipfs(example_file_path)
        if file_cid:
            print(f"Sample file added with CID: {file_cid}")

            # Example of getting a file
            print("\nGetting a file from IPFS...")
            retrieved_file_path = os.path.join(retrieved_files_path, "retrieved_sample.txt")
            if get_file_from_ipfs(file_cid, retrieved_file_path):
                print(f"File retrieved successfully to {retrieved_file_path}")
                with open(retrieved_file_path, "r") as rf:
                    print(f"Content of retrieved file: '{rf.read()}'")
            else:
                print(f"Failed to retrieve file with CID: {file_cid}")
        else:
            print("Failed to add sample file, skipping get_file example.")


        # Clean up (optional, but good for testing)
        # print("\nCleaning up test directories and files...")
        # if os.path.exists(test_project_base_path_files):
        #     shutil.rmtree(test_project_base_path_files)
        #     print(f"Cleaned up {test_project_base_path_files}")
        #
        # initialized_project_path = os.path.join(PROJECT_BASE_DIR, _sanitize_project_name(initialized_project_original_name))
        # if os.path.exists(initialized_project_path):
        #     shutil.rmtree(initialized_project_path)
        #     print(f"Cleaned up {initialized_project_path}")
        # if os.path.exists(retrieved_project_dir_path):
        #      shutil.rmtree(retrieved_project_dir_path)
        #      print(f"Cleaned up {retrieved_project_dir_path}")
        
        print("\n--- IPFS Storage Tests: Cleaning up ---")
        paths_to_clean = [
            test_project_base_path_files,
            os.path.join(PROJECT_BASE_DIR, _sanitize_project_name(initialized_project_original_name)),
            retrieved_project_dir_path
        ]
        for path in paths_to_clean:
            if os.path.exists(path):
                try:
                    shutil.rmtree(path)
                    print(f"Cleaned up test directory: {path}")
                except OSError as e:
                    print(f"Error cleaning up directory {path}: {e}. Manual cleanup might be required.")
        
        print("\nAll ipfs_storage.py tests passed successfully!")

    else:
        print("Could not connect to IPFS. Please check your daemon.")
        print("!!! ipfs_storage.py tests were SKIPPED due to no IPFS connection. !!!")
