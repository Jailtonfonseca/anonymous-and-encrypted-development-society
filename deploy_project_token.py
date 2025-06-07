import json
import os
import argparse
from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.exceptions import ContractLogicError

# --- Configuration ---
GANACHE_URL = "http://127.0.0.1:8545" # Default Ganache URL
ABI_FILE_PATH_TEMPLATE = "{}.abi.json"
BYTECODE_FILE_PATH_TEMPLATE = "{}.bytecode.txt"
PROJECT_TOKEN_CONTRACT_NAME = "ProjectToken" # Should match the contract name in .sol and compilation output

def _init_web3() -> Web3 | None:
    """
    Initializes and returns a Web3 instance connected to GANACHE_URL.
    Injects geth_poa_middleware for Ganache compatibility.
    """
    try:
        w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)

        if not w3.is_connected(): # For web3.py v6+, use w3.is_listening() or test with a request
            try: # Attempt a simple request to confirm connection for newer web3.py versions
                w3.eth.block_number
                print(f"Successfully connected to Ganache at {GANACHE_URL} (via request).")
            except Exception as e_inner:
                print(f"Failed to connect to Ganache at {GANACHE_URL} after initial check. Error: {e_inner}")
                raise ConnectionError(f"Failed to connect to Ganache: {GANACHE_URL}")
        else: # For older web3.py versions or if is_connected() works
             print(f"Successfully connected to Ganache at {GANACHE_URL} (via is_connected()).")
        return w3
    except Exception as e:
        print(f"Error initializing Web3 or connecting to Ganache: {e}")
        return None

def deploy_project_token(
    w3: Web3,
    token_name: str,
    token_symbol: str,
    initial_supply_whole_tokens: int,
    deployer_address: str,
    deployer_private_key: str
) -> str | None:
    """
    Deploys the ProjectToken contract to the blockchain.

    Args:
        w3: Initialized Web3 instance.
        token_name: Name of the token (e.g., "My Project Token").
        token_symbol: Symbol of the token (e.g., "MPT").
        initial_supply_whole_tokens: Total supply of tokens (in whole units, e.g., 1000000).
                                     The contract handles multiplication by 10**decimals().
        deployer_address: The Ethereum address from which the contract will be deployed.
                          This address will also be the initial owner.
        deployer_private_key: The private key of the deployer_address for signing the transaction.

    Returns:
        The contract address if deployment is successful, None otherwise.
    """
    print(f"\nStarting deployment of '{PROJECT_TOKEN_CONTRACT_NAME}'...")
    print(f"  Token Name: {token_name}")
    print(f"  Token Symbol: {token_symbol}")
    print(f"  Initial Supply (whole tokens): {initial_supply_whole_tokens}")
    print(f"  Deployer Address: {deployer_address}")

    abi_file = ABI_FILE_PATH_TEMPLATE.format(PROJECT_TOKEN_CONTRACT_NAME)
    bytecode_file = BYTECODE_FILE_PATH_TEMPLATE.format(PROJECT_TOKEN_CONTRACT_NAME)

    # 1. Load ABI and Bytecode
    if not os.path.exists(abi_file):
        print(f"Error: ABI file '{abi_file}' not found. Please compile the contracts first.")
        return None
    if not os.path.exists(bytecode_file):
        print(f"Error: Bytecode file '{bytecode_file}' not found. Please compile the contracts first.")
        return None

    try:
        with open(abi_file, 'r') as f:
            abi = json.load(f)
        with open(bytecode_file, 'r') as f:
            bytecode = f.read().strip()
        print("ABI and Bytecode loaded successfully.")
    except Exception as e:
        print(f"Error loading ABI/Bytecode: {e}")
        return None

    # Ensure deployer address is checksummed
    try:
        checksum_deployer_address = Web3.to_checksum_address(deployer_address)
    except ValueError:
        print(f"Error: Invalid deployer_address format: '{deployer_address}'.")
        return None

    # 2. Create Contract Instance
    ProjectTokenContract = w3.eth.contract(abi=abi, bytecode=bytecode)

    # 3. Build Deployment Transaction
    try:
        nonce = w3.eth.get_transaction_count(checksum_deployer_address)

        constructor_args = (
            token_name,
            token_symbol,
            initial_supply_whole_tokens,
            checksum_deployer_address # initialOwner for Ownable and recipient of initialSupply
        )

        # Estimate gas
        try:
            gas_estimate = ProjectTokenContract.constructor(*constructor_args).estimate_gas({'from': checksum_deployer_address})
            print(f"Estimated gas for deployment: {gas_estimate}")
        except ContractLogicError as e:
            print(f"Error estimating gas (ContractLogicError): {e}. This might indicate an issue with constructor arguments or contract logic.")
            return None
        except Exception as e:
            print(f"Error estimating gas: {e}. Using a default gas limit.")
            gas_estimate = 1500000 # Fallback gas limit

        tx_params = {
            'from': checksum_deployer_address,
            'nonce': nonce,
            'gas': gas_estimate + 50000, # Add a buffer to gas estimate
            'gasPrice': w3.eth.gas_price or w3.to_wei('20', 'gwei') # Use network gas price or a default for Ganache
        }

        # Some Ganache versions might not have a gas price, set a default if zero
        if tx_params['gasPrice'] == 0:
            tx_params['gasPrice'] = w3.to_wei('1', 'gwei')


        deploy_transaction = ProjectTokenContract.constructor(*constructor_args).build_transaction(tx_params)
        print("Deployment transaction built.")

    except Exception as e:
        print(f"Error building transaction: {e}")
        return None

    # 4. Sign Transaction
    try:
        signed_tx = w3.eth.account.sign_transaction(deploy_transaction, private_key=deployer_private_key)
        print("Transaction signed.")
    except Exception as e:
        print(f"Error signing transaction: {e}")
        return None

    # 5. Send Transaction
    try:
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"Transaction sent. Hash: {w3.to_hex(tx_hash)}")
    except Exception as e:
        print(f"Error sending transaction: {e}")
        return None

    # 6. Wait for Receipt
    try:
        print("Waiting for transaction receipt...")
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120) # 120s timeout

        if tx_receipt.status == 1:
            contract_address = tx_receipt.contractAddress
            print(f"'{PROJECT_TOKEN_CONTRACT_NAME}' deployed successfully!")
            print(f"Contract Address: {contract_address}")
            return contract_address
        else:
            print(f"Error: Contract deployment failed. Transaction status: {tx_receipt.status}")
            print(f"Full receipt: {tx_receipt}")
            return None
    except Exception as e:
        print(f"Error waiting for transaction receipt: {e}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Deploy the {PROJECT_TOKEN_CONTRACT_NAME} contract.")
    parser.add_argument("--name", required=True, help="Name of the token (e.g., 'My Project Token')")
    parser.add_argument("--symbol", required=True, help="Symbol of the token (e.g., 'MPT')")
    parser.add_argument("--supply", required=True, type=int, help="Initial supply of tokens in whole units (e.g., 1000000)")
    parser.add_argument("--owner-address", required=True, help="Ethereum address of the deployer and initial owner")
    parser.add_argument("--owner-pk", required=True, help="Private key of the owner-address (deployer). "
                                                       "WARNING: Be careful with private keys on the command line.")
    parser.add_argument("--ganache-url", default=GANACHE_URL, help=f"URL of the Ganache instance (default: {GANACHE_URL})")

    args = parser.parse_args()

    # Update GANACHE_URL if provided via CLI
    GANACHE_URL = args.ganache_url

    print("--- ProjectToken Deployment Script ---")
    print(f"Using Ganache URL: {GANACHE_URL}")
    print("WARNING: You are providing a private key on the command line. This is insecure for production environments.")

    w3_instance = _init_web3()

    if w3_instance:
        deployed_address = deploy_project_token(
            w3=w3_instance,
            token_name=args.name,
            token_symbol=args.symbol,
            initial_supply_whole_tokens=args.supply,
            deployer_address=args.owner_address,
            deployer_private_key=args.owner_pk
        )

        if deployed_address:
            print(f"\nDeployment Summary: '{args.name}' ({args.symbol}) token successfully deployed at {deployed_address}")
            print("You can now interact with this contract using its address and ABI.")
        else:
            print("\nDeployment failed. Check the error messages above.")
    else:
        print("Failed to initialize Web3. Cannot proceed with deployment.")

    print("\n--- End of Deployment Script ---")
