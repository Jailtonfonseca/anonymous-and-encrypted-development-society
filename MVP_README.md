# Aegis Forge - MVP Documentation

## 1. Overview

This document outlines the setup, usage, and core functionalities of the Minimum Viable Product (MVP) for Aegis Forge.

The Aegis Forge MVP provides a foundational platform for decentralized project management and collaboration, featuring:
*   **Decentralized Identifier (DID) Management:** Creation and tracking of DIDs for users and projects.
*   **Project Creation & Management:** Initialization of projects with basic tokenomics (project-specific tokens) and decentralized code/file storage using the InterPlanetary File System (IPFS).
*   **Contribution Workflow:** A system for submitting contributions to projects, reviewing them, and rewarding contributors with project tokens.

## 2. Setup Instructions

### 2.1. Prerequisites
*   **Python:** Python 3.8 or newer is recommended.
*   **IPFS:** A running IPFS daemon is required for most operations involving project and contribution data.

### 2.2. Dependency Installation
Install the necessary Python libraries using pip:
```bash
pip install click ipfshttpclient
```

### 2.3. IPFS Setup
1.  **Install IPFS:** Follow the official instructions at [https://docs.ipfs.tech/install/command-line/](https://docs.ipfs.tech/install/command-line/).
2.  **Initialize your IPFS repository** (if you haven't already):
    ```bash
    ipfs init
    ```
3.  **Start the IPFS daemon:** This daemon must be running in a separate terminal window for Aegis Forge to interact with IPFS.
    ```bash
    ipfs daemon
    ```
    *Note: Keep the IPFS daemon running while using Aegis Forge functionalities that involve file storage (project creation, contribution submission).*

### 2.4. Running Tests
To verify the backend modules are functioning correctly:
1.  Make the test script executable:
    ```bash
    chmod +x run_tests.sh
    ```
2.  Run the tests:
    ```bash
    ./run_tests.sh
    ```
    *Ensure the IPFS daemon is running for comprehensive test results.*

## 3. Using the CLI (`aegis_cli.py`)

The primary way to interact with Aegis Forge is through its Command Line Interface (CLI).

**Basic Command Structure:**
```bash
python aegis_cli.py <command_group> <subcommand> [ARGUMENTS_AND_OPTIONS]
```
Alternatively, if you make `aegis_cli.py` executable (`chmod +x aegis_cli.py`), you can run it as:
```bash
./aegis_cli.py <command_group> <subcommand> [ARGUMENTS_AND_OPTIONS]
```

### 3.1. DID Management (`did`)

*   **Create a new DID:**
    ```bash
    python aegis_cli.py did create --nickname "Alice"
    ```
    *(Replace "Alice" with any desired nickname, or omit `--nickname` for no nickname).*

*   **List all DIDs:**
    ```bash
    python aegis_cli.py did list
    ```

*   **Show details for a specific DID:**
    ```bash
    python aegis_cli.py did show <did_string_output_from_create_or_list>
    ```
    *(Example: `python aegis_cli.py did show did:aegis:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)*

### 3.2. Project Management (`project`)

*   **Create a new project:**
    ```bash
    python aegis_cli.py project create "MyCoolProject" --owner-did <did_string_of_owner> --supply 1000000
    ```
    *(Replace `"MyCoolProject"` with your project name, `<did_string_of_owner>` with the owner's actual DID, and `1000000` with the desired initial token supply).*

*   **List all projects:**
    ```bash
    python aegis_cli.py project list
    ```

*   **Show details for a specific project:**
    ```bash
    python aegis_cli.py project show <project_id_from_list_or_create>
    ```
    *(Example: `python aegis_cli.py project show mycoolproject`)*

*   **Check token balance for a DID within a project:**
    ```bash
    python aegis_cli.py project balance <project_id> <did_string_to_check>
    ```
    *(Example: `python aegis_cli.py project balance mycoolproject did:aegis:yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy`)*

### 3.3. Contribution Workflow (`contribution`)

*   **Submit a new contribution proposal:**
    ```bash
    python aegis_cli.py contribution submit <project_id> --contributor-did <contributor_did_string> --title "Add new login feature" --description "Implemented OAuth2 login using Python." --file ./path/to/your/contribution_archive.zip
    ```
    *(Replace placeholders with actual values. The `--file` argument should point to a local file representing the contribution, e.g., a code archive, document, etc.)*

*   **List contributions:**
    *   For a specific project:
        ```bash
        python aegis_cli.py contribution list --project-id <project_id>
        ```
    *   List all contributions in the system:
        ```bash
        python aegis_cli.py contribution list
        ```

*   **Show details for a specific contribution proposal:**
    ```bash
    python aegis_cli.py contribution show <proposal_id_from_list>
    ```
    *(Example: `python aegis_cli.py contribution show prop-zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz`)*

*   **Review a contribution proposal:**
    ```bash
    python aegis_cli.py contribution review <proposal_id> --reviewer-did <project_owner_did_string> --status approved --reward 50
    ```
    *(Replace placeholders. `<project_owner_did_string>` must be the DID of the project owner. `--status` can be `approved` or `rejected`. `--reward` is the number of project tokens to give if approved.)*

## 4. Project File Structure

The Aegis Forge MVP consists of the following key files and directories:

*   **Backend Modules (Python):**
    *   `did_system.py`: Manages Decentralized Identifiers.
    *   `ipfs_storage.py`: Handles interactions with the IPFS network for file storage.
    *   `project_management.py`: Manages project creation, metadata, and token ledgers.
    *   `contribution_workflow.py`: Manages the lifecycle of contribution proposals.
*   **Command Line Interface:**
    *   `aegis_cli.py`: The main CLI application built with `click`.
*   **Test Runner:**
    *   `run_tests.sh`: Shell script to execute tests within the backend modules.
*   **Data Files (automatically created in the root directory):**
    *   `dids.json`: Stores information about created DIDs.
    *   `projects.json`: Stores metadata for all created projects, including their token ledgers.
    *   `contributions.json`: Stores details of all contribution proposals.
*   **Local Project Data Cache (automatically created):**
    *   `project_data/`: This directory is used by `ipfs_storage.py` to temporarily store project files before adding them to IPFS and to cache retrieved content. Each project will have a subdirectory named after its sanitized `project_id`.

## 5. Important Notes

*   **MVP Status:** This is a Minimum Viable Product. Many features that would be part of a full-fledged decentralized collaboration platform (e.g., advanced governance models, on-chain smart contracts for token management, sophisticated UI, comprehensive security audits) are currently simplified, simulated, or handled manually.
*   **IPFS Daemon:** Ensure your IPFS daemon is running (`ipfs daemon`) for any operations that involve creating projects or submitting/retrieving contribution content. Without it, these operations will fail.
*   **Data Persistence:** Project and DID data are stored in local JSON files (`dids.json`, `projects.json`, `contributions.json`). For a production system, a more robust decentralized storage solution or database would be necessary.
*   **Token Transfers:** Token transfers are currently managed by updating balances within the `projects.json` file. They are not on-chain cryptocurrency transactions in this MVP.
```
