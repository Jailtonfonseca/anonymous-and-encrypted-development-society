# Local Ethereum Development Environment Setup: Ganache and Web3.py

This document outlines the steps to set up a local Ethereum development environment using Ganache as a personal blockchain and `web3.py` as the Python interface.

## 1. Ganache Installation

Ganache is a personal Ethereum blockchain you can use to run tests, execute commands, and inspect state while controlling how the chain operates.

### Prerequisites:
*   **Node.js and npm:** Ganache CLI is installed via npm, which comes with Node.js. If you don't have Node.js and npm installed, download them from [https://nodejs.org/](https://nodejs.org/). (Node.js >= v16.0.0 and npm >= 7.10.0 are recommended for the latest Ganache versions).

### Installation Steps:
The `ganache` CLI (formerly `ganache-cli`) can be installed globally using npm:

```bash
npm install ganache --global
```

For more detailed instructions or information on the Ganache GUI, refer to the official documentation:
*   Ganache Quickstart (GUI focus): [https://trufflesuite.com/docs/ganache/quickstart/](https://trufflesuite.com/docs/ganache/quickstart/)
*   Ganache CLI (more detailed): [https://github.com/trufflesuite/ganache#readme](https://github.com/trufflesuite/ganache#readme) (Note: Truffle Suite, including Ganache, is being sunset. The GitHub repository is archived, but the tool is still functional for local development).

## 2. Running Ganache

Once Ganache is installed, you can start a local blockchain instance from your terminal:

```bash
ganache
```

If you have an older version or a specific installation path, you might use `ganache-cli`.

### Default RPC Endpoint:
When Ganache starts, it will display a list of available accounts and private keys. It will also indicate where it's listening. The typical default RPC endpoints are:
*   **`http://127.0.0.1:8545`** (Common for current `ganache` CLI and newer versions)
*   `http://127.0.0.1:7545` (Sometimes used by older `ganache-cli` or the Ganache GUI)

Pay attention to the output of the `ganache` command to confirm the correct port.

## 3. Python Ethereum Library: `web3.py`

`web3.py` is the standard Python library for interacting with Ethereum.

### Installation:
Install `web3.py` using pip (preferably in a Python virtual environment):

```bash
pip install web3
```

## 4. Connection Test Script (`test_ganache_connection.py`)

The following Python script can be used to test the connection to your local Ganache instance and list the available accounts.

```python
from web3 import Web3

# Ganache default RPC endpoint
GANACHE_URL = "http://127.0.0.1:8545" # Default for ganache (formerly ganache-cli)
# For older ganache-cli or GUI, it might be http://127.0.0.1:7545

def test_connection():
    """
    Tests the connection to a local Ganache instance and lists accounts.
    """
    print(f"Attempting to connect to Ganache at {GANACHE_URL}...")
    w3 = Web3(Web3.HTTPProvider(GANACHE_URL))

    try:
        # For web3.py v6+, is_connected() is deprecated, use is_listening()
        # However, to maintain broader compatibility for now, let's try is_connected()
        # and mention is_listening() in comments or documentation.
        # As of Jan 2024, is_connected() still works but might show a warning.
        if hasattr(w3, 'is_connected') and callable(w3.is_connected):
            is_conn = w3.is_connected()
        elif hasattr(w3.provider, 'is_connected') and callable(w3.provider.is_connected): # For some provider setups
             is_conn = w3.provider.is_connected()
        else:
            # Fallback or error if no known connection check method is found
            # For modern web3.py, direct check or a simple request is better.
            # Let's try fetching accounts as a connection test.
            w3.eth.accounts 
            is_conn = True # If the above line doesn't raise an exception, we assume connection.
            print("Connection check method 'is_connected' not found, attempting direct operation.")


        if is_conn:
            print("Successfully connected to Ganache!")
            
            accounts = w3.eth.accounts
            if accounts:
                print("Available accounts:")
                for i, account in enumerate(accounts):
                    print(f"  {i}: {account}")
            else:
                print("No accounts found. Ganache might be running with no default accounts or a custom setup.")
        else:
            print("Failed to connect to Ganache. Please ensure Ganache is running.")

    except Exception as e:
        print(f"An error occurred: {e}")
        print("Please ensure Ganache is running and accessible at the specified URL.")
        print("You might need to install web3.py: pip install web3")

if __name__ == "__main__":
    test_connection()
```

### Running the Test Script:
1.  Save the code above as `test_ganache_connection.py`.
2.  Ensure your Ganache instance is running in a separate terminal.
3.  Run the script from your terminal:
    ```bash
    python test_ganache_connection.py
    ```

This setup provides a basic but powerful environment for local Ethereum smart contract development and testing.
