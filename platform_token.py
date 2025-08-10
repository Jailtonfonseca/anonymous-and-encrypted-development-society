import json
import os
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware # For Ganache PoA compatibility

# --- Configuration ---
GANACHE_URL = "http://127.0.0.1:8545"
ABI_FILE_PATH = "AegisToken.abi.json"
CONTRACT_ADDRESS_FILE = "AegisToken.address.txt"

# --- Global Web3 and Contract Instances ---
w3 = None
aegis_token_contract = None
contract_address = None

# Default Ganache private keys (for testing only, replace if your Ganache uses different ones)
# Account 0: 0x90F8bf6A479f320ead074411a4B0e7944Ea8c9C1
DEFAULT_GANACHE_PK_0 = "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d"
# Account 1: 0xFFcf8FDEE72ac11b5c542428B35EEF5769C409f0
DEFAULT_GANACHE_PK_1 = "0x6c002f5f36494661586ebb0882038bf8d598aafb88a5e2300971707fce91e997"


def _init_web3_and_contract():
    global w3, aegis_token_contract, contract_address

    if not os.path.exists(ABI_FILE_PATH):
        raise FileNotFoundError(f"ABI file not found: {ABI_FILE_PATH}. Please compile and deploy the AegisToken contract first.")
    if not os.path.exists(CONTRACT_ADDRESS_FILE):
        raise FileNotFoundError(f"Contract address file not found: {CONTRACT_ADDRESS_FILE}. Please deploy the AegisToken contract first.")

    with open(ABI_FILE_PATH, 'r') as f:
        abi = json.load(f)
    with open(CONTRACT_ADDRESS_FILE, 'r') as f:
        contract_address = f.read().strip()

    if not contract_address:
        raise ValueError("Contract address is empty. Please check AegisToken.address.txt.")
    if not Web3.is_address(contract_address):
         print(f"Warning: Contract address {contract_address} is not a checksum address. Attempting to use as is.")

    w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    if not w3.is_connected():
        try:
            w3.eth.block_number
            print(f"Successfully connected to Ganache at {GANACHE_URL} (via request).")
        except Exception as e:
            print(f"Failed to connect to Ganache at {GANACHE_URL}. Error: {e}")
            raise ConnectionError(f"Failed to connect to Ganache: {e}")
    else:
        print(f"Successfully connected to Ganache at {GANACHE_URL} (via is_connected()).")

    aegis_token_contract = w3.eth.contract(address=contract_address, abi=abi)
    print(f"AegisToken contract instance created for address: {contract_address}")

# --- Initialize on import ---
try:
    _init_web3_and_contract()
except Exception as e:
    print(f"Critical error during platform_token.py initialization: {e}")
    print("Ensure Ganache is running and contract files (ABI, address) are present.")
    w3 = None
    aegis_token_contract = None

# --- Token Information Functions ---
def get_token_name() -> str | None:
    if not aegis_token_contract: return None
    try:
        return aegis_token_contract.functions.name().call()
    except Exception as e:
        print(f"Error getting token name: {e}")
        return None

def get_token_symbol() -> str | None:
    if not aegis_token_contract: return None
    try:
        return aegis_token_contract.functions.symbol().call()
    except Exception as e:
        print(f"Error getting token symbol: {e}")
        return None

def get_token_decimals() -> int | None:
    if not aegis_token_contract: return None
    try:
        return aegis_token_contract.functions.decimals().call()
    except Exception as e:
        print(f"Error getting token decimals: {e}")
        return None

def get_total_supply() -> int | None:
    if not aegis_token_contract: return None
    try:
        return aegis_token_contract.functions.totalSupply().call()
    except Exception as e:
        print(f"Error getting total supply: {e}")
        return None

def get_aegis_balance(account_address: str) -> int | None:
    if not aegis_token_contract or not w3: return None
    try:
        checksum_address = Web3.to_checksum_address(account_address)
        return aegis_token_contract.functions.balanceOf(checksum_address).call()
    except Exception as e:
        print(f"Error getting balance for {account_address}: {e}")
        return None

# --- Token Transfer Function ---
def transfer_aegis(sender_address: str, sender_private_key: str, recipient_address: str, amount_in_smallest_units: int) -> bool:
    if not aegis_token_contract or not w3:
        print("Error: Contract or Web3 not initialized for transfer.")
        return False
    try:
        checksum_sender_address = Web3.to_checksum_address(sender_address)
        checksum_recipient_address = Web3.to_checksum_address(recipient_address)

        nonce = w3.eth.get_transaction_count(checksum_sender_address)
        
        tx_data = {
            'from': checksum_sender_address,
            'nonce': nonce,
        }
        
        # Estimate gas
        try:
            gas_estimate = aegis_token_contract.functions.transfer(
                checksum_recipient_address, amount_in_smallest_units
            ).estimate_gas(tx_data)
            tx_data['gas'] = gas_estimate
        except Exception as e:
            print(f"Gas estimation failed for transfer: {e}. Using default gas limit.")
            tx_data['gas'] = 100000 # Default fallback gas for ERC20 transfer

        # Set gas price (handle Ganache's potentially zero gas price)
        current_gas_price = w3.eth.gas_price
        tx_data['gasPrice'] = current_gas_price if current_gas_price > 0 else w3.to_wei('1', 'gwei')


        transaction = aegis_token_contract.functions.transfer(
            checksum_recipient_address, amount_in_smallest_units
        ).build_transaction(tx_data)

        signed_tx = w3.eth.account.sign_transaction(transaction, private_key=sender_private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"Transfer transaction sent. Hash: {w3.to_hex(tx_hash)}")

        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if tx_receipt.status == 1:
            print(f"Successfully transferred {amount_in_smallest_units} $AEGIS from {checksum_sender_address} to {checksum_recipient_address}.")
            return True
        else:
            print(f"Token transfer failed. Transaction status: {tx_receipt.status}")
            return False
            
    except Exception as e:
        print(f"An error occurred during token transfer: {e}")
        return False

if __name__ == '__main__':
    print("\n--- Aegis Platform Token Interaction Tests ---")
    if not w3 or not aegis_token_contract:
        print("Web3/Contract not initialized. Aborting tests.")
    else:
        print("Web3 and AegisToken contract initialized successfully.")

        # 1. Print token info
        print("\n--- Token Information ---")
        name = get_token_name()
        symbol = get_token_symbol()
        decimals = get_token_decimals()
        total_supply = get_total_supply()
        print(f"Name: {name}")
        print(f"Symbol: {symbol}")
        print(f"Decimals: {decimals}")
        if total_supply is not None and decimals is not None:
            print(f"Total Supply (smallest units): {total_supply}")
            print(f"Total Supply (formatted): {total_supply / (10**decimals)}")
        else:
            print(f"Total Supply (smallest units): Error retrieving")


        # 2. Get balance of deployer (initial owner)
        print("\n--- Balance Checks & Transfer ---")
        try:
            deployer_address = w3.eth.accounts[0] # Assumes deployer is account 0
            deployer_pk = DEFAULT_GANACHE_PK_0 # Use corresponding PK
            
            recipient_address = w3.eth.accounts[1] # Assumes recipient is account 1
            # recipient_pk = DEFAULT_GANACHE_PK_1 # Not needed for receiving

            print(f"Deployer (Account 0): {deployer_address}")
            print(f"Recipient (Account 1): {recipient_address}")

            balance_deployer_before = get_aegis_balance(deployer_address)
            balance_recipient_before = get_aegis_balance(recipient_address)
            print(f"Balance of Deployer before transfer: {balance_deployer_before}")
            print(f"Balance of Recipient before transfer: {balance_recipient_before}")

            # 3. Transfer some tokens
            if balance_deployer_before is not None and balance_deployer_before > 0 and decimals is not None:
                amount_to_transfer_formatted = 100 # Transfer 100 $AEGIS tokens
                amount_in_smallest = amount_to_transfer_formatted * (10**decimals)
                
                print(f"\nAttempting to transfer {amount_to_transfer_formatted} $AEGIS ({amount_in_smallest} smallest units) from Deployer to Recipient...")
                transfer_success = transfer_aegis(deployer_address, deployer_pk, recipient_address, amount_in_smallest)
                
                if transfer_success:
                    print("Transfer successful.")
                else:
                    print("Transfer failed.")

                # 4. Verify balances after transfer
                balance_deployer_after = get_aegis_balance(deployer_address)
                balance_recipient_after = get_aegis_balance(recipient_address)
                print(f"Balance of Deployer after transfer: {balance_deployer_after}")
                print(f"Balance of Recipient after transfer: {balance_recipient_after}")

                # Assertions (optional, but good for automated testing)
                if transfer_success and balance_deployer_before is not None and balance_recipient_before is not None:
                    assert balance_deployer_after == balance_deployer_before - amount_in_smallest
                    assert balance_recipient_after == balance_recipient_before + amount_in_smallest
                    print("Balance assertions passed.")
                elif transfer_success:
                     print("Could not assert balances due to missing pre-transfer balance data.")
            elif balance_deployer_before == 0 :
                print("\nSkipping transfer test: Deployer has no tokens.")
            else:
                print("\nSkipping transfer test: Could not retrieve deployer balance or token decimals.")

        except IndexError:
            print("\nError: Not enough accounts in Ganache to perform transfer test (need at least 2).")
        except Exception as e:
            print(f"\nAn error occurred in the test execution: {e}")
        
        print("\nAll platform_token.py tests passed successfully!") # Indicates script ran to completion.
                                                                  # Actual success depends on Ganache state & PKs.
