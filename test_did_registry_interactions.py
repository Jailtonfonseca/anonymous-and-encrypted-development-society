import unittest
import json
import os
import uuid
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware # For Ganache PoA compatibility
import solcx # To compile the contract within the test script

# --- Configuration ---
GANACHE_URL = "http://127.0.0.1:8545"
CONTRACT_SOURCE_PATH = "DIDRegistry.sol" 
# These private keys are default for Ganache instances started with no specific seed/mnemonic
# Account 0: 0x90F8bf6A479f320ead074411a4B0e7944Ea8c9C1
DEFAULT_GANACHE_PK_0 = "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d"
# Account 1: 0xFFcf8FDEE72ac11b5c542428B35EEF5769C409f0
DEFAULT_GANACHE_PK_1 = "0x6c002f5f36494661586ebb0882038bf8d598aafb88a5e2300971707fce91e997"


def compile_contract(source_file_path, contract_name):
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
            solc_version=str(solcx.get_solc_version())
        )
        
        # Try to find the contract interface key
        # Common patterns: <stdin>:ContractName, ContractName, <source_file_name>:ContractName
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
            raise Exception(f"Could not find contract '{contract_name}' in compiled output. Found keys: {list(compiled_sol.keys())}")

        return contract_interface['abi'], contract_interface['bin']
    except Exception as e:
        print(f"Error during contract compilation: {e}")
        raise

def deploy_new_contract(w3, abi, bytecode, deployer_account_address):
    print(f"Deploying contract from account: {deployer_account_address}...")
    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx_hash = Contract.constructor().transact({'from': deployer_account_address})
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Contract deployed at address: {tx_receipt.contractAddress}")
    return w3.eth.contract(address=tx_receipt.contractAddress, abi=abi)

class TestDIDRegistryInteractions(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
        if not cls.w3.is_connected(): # For web3.py v6+, use is_listening()
            try:
                cls.w3.eth.block_number
            except Exception as e:
                raise ConnectionError(f"Failed to connect to Ganache at {GANACHE_URL}: {e}")
        
        cls.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        # Setup accounts
        # It's safer to derive addresses from PKs if PKs are fixed/known for test environment
        cls.owner_account = cls.w3.eth.account.from_key(DEFAULT_GANACHE_PK_0)
        cls.non_owner_account = cls.w3.eth.account.from_key(DEFAULT_GANACHE_PK_1)
        
        # Ensure accounts have Ether (Ganache usually does this by default)
        print(f"Owner account: {cls.owner_account.address} (Balance: {cls.w3.from_wei(cls.w3.eth.get_balance(cls.owner_account.address), 'ether')} ETH)")
        print(f"Non-owner account: {cls.non_owner_account.address} (Balance: {cls.w3.from_wei(cls.w3.eth.get_balance(cls.non_owner_account.address), 'ether')} ETH)")

        cls.abi, cls.bytecode = compile_contract(CONTRACT_SOURCE_PATH, "DIDRegistry")

    def setUp(self):
        # Deploy a new contract instance for each test method
        self.contract = deploy_new_contract(self.w3, self.abi, self.bytecode, self.owner_account.address)
        self.test_did_str_root = f"test-did-{uuid.uuid4().hex[:8]}" 
        self.test_did_bytes = Web3.keccak(text=self.test_did_str_root)
        self.initial_pk = "initial_pk_123"
        self.initial_doc_cid = "QmInitialCID123"

    def _sign_and_send_transaction(self, function_call, account):
        tx = function_call.build_transaction({
            'from': account.address,
            'nonce': self.w3.eth.get_transaction_count(account.address),
            'gas': 2000000, # Adjust as needed, or estimate
            'gasPrice': self.w3.to_wei('1', 'gwei')
        })
        signed_tx = account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

    def test_01_register_did_success(self):
        print("\nRunning test_01_register_did_success...")
        tx_receipt = self._sign_and_send_transaction(
            self.contract.functions.registerDID(self.test_did_bytes, self.initial_pk, self.initial_doc_cid),
            self.owner_account
        )
        self.assertEqual(tx_receipt.status, 1, "DID registration failed")
        
        owner, pk, cid = self.contract.functions.getDIDInfo(self.test_did_bytes).call()
        self.assertEqual(owner, self.owner_account.address)
        self.assertEqual(pk, self.initial_pk)
        self.assertEqual(cid, self.initial_doc_cid)
        self.assertTrue(self.contract.functions.isDIDRegistered(self.test_did_bytes).call())
        print("test_01_register_did_success: PASSED")

    def test_02_reregister_did_fail(self):
        print("\nRunning test_02_reregister_did_fail...")
        # First registration
        self._sign_and_send_transaction(
            self.contract.functions.registerDID(self.test_did_bytes, self.initial_pk, self.initial_doc_cid),
            self.owner_account
        )
        # Attempt to re-register
        with self.assertRaises(Exception, msg="Re-registration should fail/revert"):
             self._sign_and_send_transaction( # This should raise an exception (e.g. ValueError due to revert)
                self.contract.functions.registerDID(self.test_did_bytes, "new_pk", "new_cid"),
                self.owner_account
            )
        print("test_02_reregister_did_fail: PASSED (revert expected)")

    def test_03_update_by_owner(self):
        print("\nRunning test_03_update_by_owner...")
        self._sign_and_send_transaction(
            self.contract.functions.registerDID(self.test_did_bytes, self.initial_pk, self.initial_doc_cid),
            self.owner_account
        )
        
        new_pk = "updated_pk_456"
        tx_receipt_pk = self._sign_and_send_transaction(
            self.contract.functions.updatePublicKey(self.test_did_bytes, new_pk),
            self.owner_account
        )
        self.assertEqual(tx_receipt_pk.status, 1, "Update public key failed")
        self.assertEqual(self.contract.functions.getPublicKey(self.test_did_bytes).call(), new_pk)

        new_doc_cid = "QmUpdatedCID456"
        tx_receipt_cid = self._sign_and_send_transaction(
            self.contract.functions.updateDocumentCID(self.test_did_bytes, new_doc_cid),
            self.owner_account
        )
        self.assertEqual(tx_receipt_cid.status, 1, "Update document CID failed")
        self.assertEqual(self.contract.functions.getDocumentCID(self.test_did_bytes).call(), new_doc_cid)
        print("test_03_update_by_owner: PASSED")

    def test_04_update_by_non_owner_fail(self):
        print("\nRunning test_04_update_by_non_owner_fail...")
        self._sign_and_send_transaction(
            self.contract.functions.registerDID(self.test_did_bytes, self.initial_pk, self.initial_doc_cid),
            self.owner_account
        )
        
        with self.assertRaises(Exception, msg="Update public key by non-owner should fail"):
            self._sign_and_send_transaction(
                self.contract.functions.updatePublicKey(self.test_did_bytes, "pk_by_non_owner"),
                self.non_owner_account
            )
        
        with self.assertRaises(Exception, msg="Update document CID by non-owner should fail"):
            self._sign_and_send_transaction(
                self.contract.functions.updateDocumentCID(self.test_did_bytes, "cid_by_non_owner"),
                self.non_owner_account
            )
        print("test_04_update_by_non_owner_fail: PASSED (reverts expected)")

    def test_05_retrieval_unregistered_did(self):
        print("\nRunning test_05_retrieval_unregistered_did...")
        unregistered_did_bytes = Web3.keccak(text="unregistered-did")
        
        self.assertFalse(self.contract.functions.isDIDRegistered(unregistered_did_bytes).call())
        with self.assertRaises(Exception): # Expect revert for get functions on unregistered DID
            self.contract.functions.getDIDInfo(unregistered_did_bytes).call()
        with self.assertRaises(Exception):
            self.contract.functions.getPublicKey(unregistered_did_bytes).call()
        with self.assertRaises(Exception):
            self.contract.functions.getDocumentCID(unregistered_did_bytes).call()
        with self.assertRaises(Exception):
            self.contract.functions.getDIDOwner(unregistered_did_bytes).call()
        print("test_05_retrieval_unregistered_did: PASSED (reverts expected for getters)")
        
    def test_06_register_empty_did_identifier(self):
        print("\nRunning test_06_register_empty_did_identifier...")
        empty_bytes32 = b'\x00' * 32 
        # The contract does not explicitly prevent registration of empty_bytes32 DID.
        # It will be treated like any other bytes32 value.
        # If this behavior is undesirable, the contract should add a require(did != bytes32(0), "DID cannot be empty");
        tx_receipt = self._sign_and_send_transaction(
            self.contract.functions.registerDID(empty_bytes32, "pk_for_empty", "cid_for_empty"),
            self.owner_account
        )
        self.assertEqual(tx_receipt.status, 1, "Registration of empty bytes32 DID failed unexpectedly")
        self.assertTrue(self.contract.functions.isDIDRegistered(empty_bytes32).call())
        print("test_06_register_empty_did_identifier: PASSED (Note: contract allows registration of empty bytes32 DID)")


if __name__ == '__main__':
    print("--- TestDIDRegistryInteractions: Starting ---")
    print(f"Using Ganache URL: {GANACHE_URL}")
    print("This script will deploy a new DIDRegistry contract for each test method.")
    
    # Check if DIDRegistry.sol exists before running tests
    if not os.path.exists(CONTRACT_SOURCE_PATH):
        print(f"CRITICAL ERROR: Contract source file '{CONTRACT_SOURCE_PATH}' not found.")
        print("Please ensure the contract is in the correct location.")
    else:
        # unittest.main() will run all methods starting with 'test'
        suite = unittest.TestLoader().loadTestsFromTestCase(TestDIDRegistryInteractions)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        if result.wasSuccessful():
            print("\nAll test_did_registry_interactions.py tests passed successfully!")
        else:
            print("\nSome test_did_registry_interactions.py tests FAILED.")
            # Exit with a non-zero code for shell script to pick up
            exit(1)
    print("--- TestDIDRegistryInteractions: Finished ---")
