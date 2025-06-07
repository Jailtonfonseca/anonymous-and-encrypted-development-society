# Aegis Forge - MVP Documentation

## 1. Overview

This document outlines the setup, usage, and core functionalities of the Minimum Viable Product (MVP) for Aegis Forge.

The Aegis Forge MVP provides a foundational platform for decentralized project management and collaboration, featuring:
*   **Decentralized Identifier (DID) Management:** Creation, registration, and management of DIDs on a local blockchain (e.g., Ganache) via the `DIDRegistry.sol` smart contract.
*   **Project Creation & Management:** Initialization of projects, each with its own dedicated ERC20 token contract (`ProjectToken.sol`) deployed on the blockchain for project-specific tokenomics. Project code/file storage uses the InterPlanetary File System (IPFS).
*   **Contribution Workflow:** A system for submitting contributions to projects, reviewing them, and rewarding contributors with on-chain project tokens.
*   **Platform Token ($AEGIS):** An ERC20 token (`AegisToken.sol`) for potential future platform-level utilities (basic interaction implemented).
*   **P2P Encrypted Messaging:** Basic end-to-end encrypted messaging between DIDs using their cryptographic keys.

## 2. Setup Instructions

### 2.1. Prerequisites
*   **Python:** Python 3.8 or newer is recommended.
*   **IPFS:** A running IPFS daemon is required for project and contribution data storage.
*   **Node.js & npm:** Required for `solc-select` if you need to manage `solc` versions (though `py-solc-x` can install `solc` directly).
*   **Solidity Compiler (`solc`):** The `compile_and_extract.py` script uses `py-solc-x` which can install `solc` versions. However, having `solc-select` or a system-installed `solc` (e.g., v0.8.20) can be beneficial.
*   **Ganache:** A local Ethereum blockchain for testing smart contract deployments and interactions. Download from [Truffle Suite](https://trufflesuite.com/ganache/).

### 2.2. Dependency Installation
Install the necessary Python libraries using pip:
```bash
pip install click ipfshttpclient web3 py-solc-x python-dotenv # Add other specific libraries if used, e.g., for p2p
```
*(Ensure `web3` and `py-solc-x` are included for blockchain interactions.)*

### 2.3. Blockchain Setup (Ganache)
1.  **Install and Run Ganache:** Start a Ganache instance. Note the RPC server URL (default: `http://127.0.0.1:8545`) and the available accounts with their private keys.
2.  **Compile Contracts:**
    ```bash
    python compile_and_extract.py
    ```
    This will compile `DIDRegistry.sol`, `AegisToken.sol`, and `ProjectToken.sol`, generating ABI and bytecode files.
3.  **Deploy Core Contracts:**
    *   **DIDRegistry:**
        ```bash
        python deploy_did_registry.py # Use an account from Ganache for deployment
        ```
        This will create `DIDRegistry.address.txt`.
    *   **AegisToken (Platform Token):**
        ```bash
        python deploy_aegis_token.py # Use an account from Ganache
        ```
        This will create `AegisToken.address.txt`.
    *(Note: `deploy_project_token.py` is used internally by `project_management.py` when a new project is created.)*

### 2.4. IPFS Setup
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
    *Ensure the IPFS daemon and Ganache are running for comprehensive test results. Some tests may require manual setup of DIDs or contract states.*

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

*   **Register a new DID on the blockchain:**
    ```bash
    # Replace placeholders with actual values from your Ganache instance
    python aegis_cli.py did register "did:aegis:alice" \
        --public-key "0xAlicePublicKey..." \
        --doc-cid "QmAliceDIDDocumentCID..." \
        --owner-address <alice_ganache_eth_address> \
        --owner-pk <alice_ganache_private_key>
    ```
    *(The `unique_identifier_string` like "did:aegis:alice" will be hashed to form the `bytes32` DID. WARNING: Private key usage is for local testing only.)*

*   **Show details for a specific DID:**
    ```bash
    python aegis_cli.py did show "did:aegis:alice"
    ```

*   **(Deprecated) List all DIDs from local file:**
    The `did list` command is deprecated as DIDs are now on-chain. For comprehensive tracking, event indexing would be needed.

### 3.2. Project Management (`project`)

*   **Create a new project (deploys an ERC20 token for the project):**
    ```bash
    python aegis_cli.py project create "MyCoolProject" --owner-did <did_string_of_owner> --owner-address <owner_eth_address> --owner-pk <owner_private_key_hex> --supply 1000000
    ```
    *(Replace placeholders. The `--owner-did` must be registered to the `--owner-address`. The `--owner-pk` is the private key for `--owner-address`, used to deploy the project's dedicated ERC20 token contract. WARNING: Directly using private keys on the command line is insecure and should only be done in local testing environments with test accounts.)*

*   **List all projects:**
    ```bash
    python aegis_cli.py project list
    ```

*   **Show details for a specific project:**
    ```bash
    python aegis_cli.py project show <project_id_from_list_or_create>
    ```
    *(Example: `python aegis_cli.py project show mycoolproject`)*

*   **Check token balance for a DID within a project (queries the on-chain token contract):**
    ```bash
    python aegis_cli.py project balance <project_id> <did_string_to_check>
    ```
    *(Example: `python aegis_cli.py project balance mycoolproject did:aegis:alice`)*

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

*   **Review a contribution proposal (may involve on-chain token transfer for rewards):**
    ```bash
    python aegis_cli.py contribution review <proposal_id> --reviewer-did <project_owner_did_string> --reviewer-pk <reviewer_private_key_hex> --status approved --reward 50
    ```
    *(Replace placeholders. The `--reviewer-pk` is the private key of the `--reviewer-did` (project owner), used to sign the on-chain transfer of project tokens if the contribution is approved with a reward. WARNING: Directly using private keys on the command line is insecure.)*

## 4. Project File Structure

The Aegis Forge MVP consists of the following key files and directories:

*   **Backend Modules (Python):**
    *   `did_system.py`: Manages DIDs via the `DIDRegistry.sol` smart contract.
    *   `ipfs_storage.py`: Handles interactions with IPFS.
    *   `project_management.py`: Manages project creation (including deploying `ProjectToken.sol` contracts) and on-chain token transfers for projects.
    *   `contribution_workflow.py`: Manages contribution lifecycle, including triggering on-chain token rewards.
    *   `platform_token.py`: Manages interactions with the `AegisToken.sol` (platform token).
    *   `p2p_messaging.py`: Handles P2P encrypted messaging logic.
*   **Solidity Smart Contracts (in root directory):**
    *   `DIDRegistry.sol`: For managing DIDs.
    *   `AegisToken.sol`: The platform's main ERC20 token.
    *   `ProjectToken.sol`: Template for project-specific ERC20 tokens.
    *   `openzeppelin/`: Contains OpenZeppelin contract dependencies.
*   **Command Line Interface:**
    *   `aegis_cli.py`: The main CLI application.
*   **Deployment & Compilation Scripts:**
    *   `compile_and_extract.py`: Compiles Solidity contracts.
    *   `deploy_did_registry.py`: Deploys `DIDRegistry.sol`.
    *   `deploy_aegis_token.py`: Deploys `AegisToken.sol`.
    *   `deploy_project_token.py`: Deploys `ProjectToken.sol` (used by `project_management.py`).
*   **Test Runner:**
    *   `run_tests.sh`: Shell script to execute backend module tests.
*   **Data Files (automatically created/updated):**
    *   `DIDRegistry.abi.json`, `DIDRegistry.bytecode.txt`, `DIDRegistry.address.txt`
    *   `AegisToken.abi.json`, `AegisToken.bytecode.txt`, `AegisToken.address.txt`
    *   `ProjectToken.abi.json`, `ProjectToken.bytecode.txt` (address is per-project)
    *   `projects.json`: Stores metadata for created projects, including their unique `project_token_contract_address` instead of a local `token_ledger`.
    *   `contributions.json`: Stores details of contribution proposals.
    *   `dids.json`: (Deprecated) No longer the source of truth for DIDs; `DIDRegistry.sol` is.
*   **Local Project Data Cache (automatically created):**
    *   `project_data/`: Caches project files for IPFS interaction.

## 5. Important Notes

*   **MVP Status:** This MVP demonstrates core functionalities with on-chain interactions on a local blockchain. Features like advanced governance, UI, and comprehensive security audits are beyond the current scope.
*   **IPFS Daemon:** Ensure your IPFS daemon is running (`ipfs daemon`) for creating projects or handling contribution content.
*   **Data Persistence:** Core DID and token data are on your local blockchain (Ganache). Project metadata and contribution details are in local JSON files (`projects.json`, `contributions.json`).
*   **Private Keys on CLI:** Several CLI commands (`did register`, `project create`, `contribution review`, `token transfer`) require private keys as options. **This is highly insecure and intended for local testing with Ganache accounts ONLY. Never use real private keys this way.**
*   **Token Transfers:** Project-specific token transfers (e.g., for contribution rewards) are now actual on-chain ERC20 transactions, interacting with each project's dedicated token contract. The $AEGIS platform token transfers are also on-chain.
*   **On-Chain Interactions:** Operations like project creation (which deploys a token contract), DID registration, and rewarding contributions now involve direct blockchain interactions. Ensure your local blockchain (e.g., Ganache) is running and correctly configured (core contracts deployed, accounts funded with ETH for gas).
```
