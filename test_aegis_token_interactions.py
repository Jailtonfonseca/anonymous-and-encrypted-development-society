import unittest
import json
import os
import uuid
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
import solcx
import decimal

# --- Configuration ---
GANACHE_URL = "http://127.0.0.1:8545"
CONTRACT_SOURCE_PATH = "AegisToken.sol"
OPENZEPPELIN_BASE_PATH = "./openzeppelin" # Assuming openzeppelin folder is in the same dir

# Default Ganache private keys for testing
def compile_contract_with_oz(source_file_path, contract_name, allow_paths_list):
    print(f"Compiling contract {source_file_path}...")
    try:
        installed_versions = solcx.get_installed_solc_versions()
        target_version = None
        if installed_versions:
            for v_obj in installed_versions:
                if v_obj.major == 0 and v_obj.minor == 8:
                    target_version = v_obj
                    break
        
        if not target_version:
            print("No suitable 0.8.x solc version found. Attempting to install 0.8.4...")
            solcx.install_solc('0.8.4')
            target_version = solcx.set_solc_version('0.8.4', silent=True)
        else:
            solcx.set_solc_version(target_version, silent=True)
        
        print(f"Using solc version: {solcx.get_solc_version()}")

        with open(source_file_path, 'r') as f:
            source_code = f.read()
        
        compiled_sol = solcx.compile_source(
            source_code,
            output_values=['abi', 'bin'],
            solc_version=str(solcx.get_solc_version()),
            allow_paths=allow_paths_list # Crucial for OpenZeppelin imports from a local folder
        )
        
        keys_to_try = [
            f"<stdin>:{contract_name}", 
            contract_name, 
            f"{os.path.basename(source_file_path)}:{contract_name}"
        ]
        contract_interface = None
        for key_try in keys_to_try:
            if key_try in compiled_sol:
                contract_interface = compiled_sol[key_try]
                break
        
        if not contract_interface:
            # Check if the key might be just the source file name if only one contract is in it
            if f"{os.path.basename(source_file_path)}:{contract_name}" not in compiled_sol and len(compiled_sol) == 1:
                 # This case is tricky, let's assume the first key is the one if it's the only one
                 # More robust would be to ensure contract_name is part of the key
                 first_key = list(compiled_sol.keys())[0]
                 if contract_name in first_key:
                     contract_interface = compiled_sol[first_key]

            if not contract_interface:
                 raise Exception(f"Could not find contract '{contract_name}' in compiled output. Found keys: {list(compiled_sol.keys())}")


        return contract_interface['abi'], contract_interface['bin']
    except Exception as e:
        print(f"Error during contract compilation: {e}")
        raise

def deploy_new_aegis_token(w3, abi, bytecode, deployer_address):
    print(f"Deploying AegisToken from account: {deployer_address}...")
    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    # AegisToken constructor takes 'initialOwner'
    tx_hash = Contract.constructor(deployer_address).transact({'from': deployer_address})
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"AegisToken deployed at address: {tx_receipt.contractAddress}")
    return w3.eth.contract(address=tx_receipt.contractAddress, abi=abi)

class TestAegisTokenInteractions(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
        if not cls.w3.is_connected():
            try: cls.w3.eth.block_number
            except Exception as e: raise ConnectionError(f"Failed to connect to Ganache: {e}")
        
        cls.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        # Use available accounts from Ganache
        accounts = cls.w3.eth.accounts
        if len(accounts) < 3:
            raise Exception("Ganache needs at least 3 unlocked accounts.")

        cls.deployer_owner_address = accounts[0]
        cls.recipient1_address = accounts[1]
        cls.recipient2_address = accounts[2]

        print(f"\nUsing Deployer/Owner: {cls.deployer_owner_address} (Balance: {cls.w3.from_wei(cls.w3.eth.get_balance(cls.deployer_owner_address), 'ether')} ETH)")
        print(f"Using Recipient1: {cls.recipient1_address} (Balance: {cls.w3.from_wei(cls.w3.eth.get_balance(cls.recipient1_address), 'ether')} ETH)")
        print(f"Using Recipient2: {cls.recipient2_address} (Balance: {cls.w3.from_wei(cls.w3.eth.get_balance(cls.recipient2_address), 'ether')} ETH)")

        # Compile contract (once for all tests in the class)
        # Allow paths for solcx to find local OpenZeppelin imports
        # The path should be relative to where solcx is invoked or absolute.
        # If openzeppelin folder is sibling to AegisToken.sol, and script is run from parent of both:
        allow_paths = [os.path.abspath(OPENZEPPELIN_BASE_PATH)] 
        cls.abi, cls.bytecode = compile_contract_with_oz(CONTRACT_SOURCE_PATH, "AegisToken", allow_paths)
        cls.decimals = 18 # Standard for AegisToken as per its ERC20 inheritance
        cls.initial_supply_readable = 1_000_000_000 
        cls.initial_supply_smallest_units = cls.initial_supply_readable * (10**cls.decimals)


    def setUp(self):
        # Deploy a new contract instance for each test method for isolation
        self.token_contract = deploy_new_aegis_token(self.w3, self.abi, self.bytecode, self.deployer_owner_address)

    def _sign_and_send_transaction(self, function_call, account_address):
        # Using unlocked accounts
        tx_hash = function_call.transact({'from': account_address})
        return self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

    def test_01_deployment_and_initial_state(self):
        print("\nRunning test_01_deployment_and_initial_state...")
        self.assertEqual(self.token_contract.functions.name().call(), "Aegis Platform Token")
        self.assertEqual(self.token_contract.functions.symbol().call(), "$AEGIS")
        self.assertEqual(self.token_contract.functions.decimals().call(), self.decimals)
        self.assertEqual(self.token_contract.functions.totalSupply().call(), self.initial_supply_smallest_units)
        self.assertEqual(self.token_contract.functions.balanceOf(self.deployer_owner_address).call(), self.initial_supply_smallest_units)
        self.assertEqual(self.token_contract.functions.owner().call(), self.deployer_owner_address)
        print("test_01_deployment_and_initial_state: PASSED")

    def test_02_balance_of(self):
        print("\nRunning test_02_balance_of...")
        self.assertEqual(self.token_contract.functions.balanceOf(self.deployer_owner_address).call(), self.initial_supply_smallest_units)
        self.assertEqual(self.token_contract.functions.balanceOf(self.recipient1_address).call(), 0)
        print("test_02_balance_of: PASSED")

    def test_03_transfer_success(self):
        print("\nRunning test_03_transfer_success...")
        amount_to_transfer = 100 * (10**self.decimals)
        
        tx_receipt = self._sign_and_send_transaction(
            self.token_contract.functions.transfer(self.recipient1_address, amount_to_transfer),
            self.deployer_owner_address
        )
        self.assertEqual(tx_receipt.status, 1, "Transfer transaction failed")
        
        self.assertEqual(self.token_contract.functions.balanceOf(self.deployer_owner_address).call(), self.initial_supply_smallest_units - amount_to_transfer)
        self.assertEqual(self.token_contract.functions.balanceOf(self.recipient1_address).call(), amount_to_transfer)
        
        # Optional: Check for Transfer event (more advanced)
        # logs = self.token_contract.events.Transfer().get_logs(fromBlock=tx_receipt.blockNumber, toBlock=tx_receipt.blockNumber)
        # self.assertEqual(len(logs), 1)
        # self.assertEqual(logs[0].args.frm, self.deployer_owner_address) # 'from' is a keyword
        # self.assertEqual(logs[0].args.to, self.recipient1_address)
        # self.assertEqual(logs[0].args.value, amount_to_transfer)
        print("test_03_transfer_success: PASSED")

    def test_04_transfer_insufficient_funds(self):
        print("\nRunning test_04_transfer_insufficient_funds...")
        amount_too_high = self.initial_supply_smallest_units + (1 * (10**self.decimals))
        
        with self.assertRaises(Exception, msg="Transfer of insufficient funds should fail/revert"):
            self._sign_and_send_transaction(
                self.token_contract.functions.transfer(self.recipient1_address, amount_too_high),
                self.deployer_owner_address
            )
        print("test_04_transfer_insufficient_funds: PASSED (revert expected)")

    def test_05_approve_and_allowance(self):
        print("\nRunning test_05_approve_and_allowance...")
        amount_to_approve = 50 * (10**self.decimals)
        tx_receipt = self._sign_and_send_transaction(
            self.token_contract.functions.approve(self.recipient1_address, amount_to_approve),
            self.deployer_owner_address
        )
        self.assertEqual(tx_receipt.status, 1, "Approve transaction failed")
        self.assertEqual(self.token_contract.functions.allowance(self.deployer_owner_address, self.recipient1_address).call(), amount_to_approve)
        print("test_05_approve_and_allowance: PASSED")

    def test_06_transfer_from_success(self):
        print("\nRunning test_06_transfer_from_success...")
        approved_amount = 60 * (10**self.decimals)
        transfer_amount = 40 * (10**self.decimals)

        # Owner approves recipient1
        self._sign_and_send_transaction(
            self.token_contract.functions.approve(self.recipient1_address, approved_amount),
            self.deployer_owner_address
        )
        
        # Recipient1 transfers from owner to recipient2
        tx_receipt = self._sign_and_send_transaction(
            self.token_contract.functions.transferFrom(self.deployer_owner_address, self.recipient2_address, transfer_amount),
            self.recipient1_address # Spender is recipient1
        )
        self.assertEqual(tx_receipt.status, 1, "transferFrom transaction failed")

        self.assertEqual(self.token_contract.functions.balanceOf(self.deployer_owner_address).call(), self.initial_supply_smallest_units - transfer_amount)
        self.assertEqual(self.token_contract.functions.balanceOf(self.recipient2_address).call(), transfer_amount)
        self.assertEqual(self.token_contract.functions.allowance(self.deployer_owner_address, self.recipient1_address).call(), approved_amount - transfer_amount)
        print("test_06_transfer_from_success: PASSED")

    def test_07_transfer_from_exceeds_allowance(self):
        print("\nRunning test_07_transfer_from_exceeds_allowance...")
        approved_amount = 30 * (10**self.decimals)
        transfer_amount_too_high = 35 * (10**self.decimals)

        self._sign_and_send_transaction(
            self.token_contract.functions.approve(self.recipient1_address, approved_amount),
            self.deployer_owner_address
        )
        
        with self.assertRaises(Exception, msg="transferFrom exceeding allowance should fail"):
            self._sign_and_send_transaction(
                self.token_contract.functions.transferFrom(self.deployer_owner_address, self.recipient2_address, transfer_amount_too_high),
                self.recipient1_address
            )
        print("test_07_transfer_from_exceeds_allowance: PASSED (revert expected)")

    def test_08_transfer_from_no_allowance(self):
        print("\nRunning test_08_transfer_from_no_allowance...")
        transfer_amount = 10 * (10**self.decimals)
        
        with self.assertRaises(Exception, msg="transferFrom with no allowance should fail"):
            self._sign_and_send_transaction(
                self.token_contract.functions.transferFrom(self.deployer_owner_address, self.recipient2_address, transfer_amount),
                self.recipient1_address
            )
        print("test_08_transfer_from_no_allowance: PASSED (revert expected)")


if __name__ == '__main__':
    print("--- TestAegisTokenInteractions: Starting ---")
    print(f"Using Ganache URL: {GANACHE_URL}")
    
    if not os.path.exists(CONTRACT_SOURCE_PATH):
        print(f"CRITICAL ERROR: Contract source file '{CONTRACT_SOURCE_PATH}' not found.")
    elif not os.path.exists(OPENZEPPELIN_BASE_PATH) or not os.path.isdir(OPENZEPPELIN_BASE_PATH):
        print(f"CRITICAL ERROR: OpenZeppelin contracts directory '{OPENZEPPELIN_BASE_PATH}' not found.")
        print("Please ensure the 'openzeppelin' folder with its contracts is in the same directory as this test script.")
    else:
        suite = unittest.TestLoader().loadTestsFromTestCase(TestAegisTokenInteractions)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        if result.wasSuccessful():
            print("\nAll test_aegis_token_interactions.py tests passed successfully!")
        else:
            print("\nSome test_aegis_token_interactions.py tests FAILED.")
            exit(1) # Important for run_tests.sh
    print("--- TestAegisTokenInteractions: Finished ---")
