"""
DID System Module - CORRIGIDO
Problemas críticos resolvidos:
1. Remoção de chaves privadas hardcoded → variáveis de ambiente
2. Adicionada verificação de saldo ETH antes de transações
3. Logging adequado implementado
"""

import json
import uuid
import os
import logging
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Configuration via Environment Variables ---
GANACHE_URL = os.environ.get("GANACHE_URL", "http://127.0.0.1:8545")
ABI_FILE_PATH = "DIDRegistry.abi.json"
CONTRACT_ADDRESS_FILE = "DIDRegistry.address.txt"

# --- Global Web3 and Contract Instances ---
w3 = None
did_registry_contract = None
contract_address = None


def _init_web3_and_contract():
    global w3, did_registry_contract, contract_address

    if not os.path.exists(ABI_FILE_PATH):
        raise FileNotFoundError(f"ABI file not found: {ABI_FILE_PATH}")
    if not os.path.exists(CONTRACT_ADDRESS_FILE):
        raise FileNotFoundError(f"Contract address file not found: {CONTRACT_ADDRESS_FILE}")

    with open(ABI_FILE_PATH, 'r') as f:
        abi = json.load(f)
    with open(CONTRACT_ADDRESS_FILE, 'r') as f:
        contract_address = f.read().strip()

    if not contract_address:
        raise ValueError("Contract address is empty.")
    if not Web3.is_address(contract_address):
        logger.warning(f"Contract address {contract_address} is not a checksum address.")

    w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    if not w3.is_connected():
        try:
            w3.eth.block_number
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Ganache: {e}")

    did_registry_contract = w3.eth.contract(address=contract_address, abi=abi)
    logger.info(f"Connected to DIDRegistry at {contract_address}")


def generate_did_identifier(unique_input: str) -> bytes:
    """Generates a Keccak-256 hash of the input string."""
    return Web3.keccak(text=unique_input)


def _get_account_balance(address: str) -> int:
    """Get ETH balance of an address."""
    if w3 is None:
        raise ConnectionError("Web3 not initialized")
    return w3.eth.get_balance(address)


def _validate_sufficient_balance(address: str, private_key: str, gas_estimate: int):
    """
    CRÍTICO #3: Verifica se o endereço tem saldo suficiente para a transação.
    Raises ValueError se saldo insuficiente.
    """
    balance = _get_account_balance(address)
    # Custo total = gas * gas_price
    gas_price = w3.eth.gas_price
    total_cost = gas_estimate * gas_price
    
    if balance < total_cost:
        raise ValueError(
            f"Insufficient ETH balance. Required: {w3.from_wei(total_cost, 'ether'):.6f} ETH, "
            f"Available: {w3.from_wei(balance, 'ether'):.6f} ETH"
        )
    return True


# --- Initialize on import ---
try:
    _init_web3_and_contract()
except Exception as e:
    logger.error(f"Critical error during initialization: {e}")
    w3 = None
    did_registry_contract = None


if __name__ == '__main__':
    if w3 and did_registry_contract:
        print("\n--- Testing did_system.py (CORRIGIDO) ---")
        test_uuid = str(uuid.uuid4())
        did_bytes = generate_did_identifier(test_uuid)
        print(f"Generated DID: 0x{did_bytes.hex()[:20]}...")
    else:
        print("\nWeb3 initialization failed.")


# --- Core Functionality ---


def register_did(did_bytes32: bytes, public_key: str, document_cid: str, 
                 owner_eth_address: str, owner_eth_private_key: str) -> bool:
    """
    Registers a DID on-chain with balance validation.
    """
    if not did_registry_contract:
        logger.error("Contract not initialized")
        return False

    try:
        # Estimar gas primeiro
        try:
            gas_estimate = did_registry_contract.functions.registerDID(
                did_bytes32, public_key, document_cid
            ).estimate_gas({'from': owner_eth_address})
        except:
            gas_estimate = 300000  # Default fallback

        # CRÍTICO #3: Verificar saldo antes de enviar transação
        _validate_sufficient_balance(owner_eth_address, owner_eth_private_key, gas_estimate)

        txn = did_registry_contract.functions.registerDID(
            did_bytes32, public_key, document_cid
        ).build_transaction({
            'from': owner_eth_address,
            'nonce': w3.eth.get_transaction_count(owner_eth_address),
            'gas': gas_estimate,
            'gasPrice': w3.eth.gas_price
        })

        signed_txn = w3.eth.account.sign_transaction(txn, owner_eth_private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        logger.info(f"DID registered successfully. Tx: {tx_hash.hex()}")
        return receipt.status == 1

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to register DID: {e}")
        return False


def update_public_key(did_bytes32: bytes, new_public_key: str,
                      owner_eth_address: str, owner_eth_private_key: str) -> bool:
    """Updates the public key for a DID."""
    if not did_registry_contract:
        return False

    try:
        try:
            gas_estimate = did_registry_contract.functions.updatePublicKey(
                did_bytes32, new_public_key
            ).estimate_gas({'from': owner_eth_address})
        except:
            gas_estimate = 300000

        _validate_sufficient_balance(owner_eth_address, owner_eth_private_key, gas_estimate)

        txn = did_registry_contract.functions.updatePublicKey(
            did_bytes32, new_public_key
        ).build_transaction({
            'from': owner_eth_address,
            'nonce': w3.eth.get_transaction_count(owner_eth_address),
            'gas': gas_estimate,
            'gasPrice': w3.eth.gas_price
        })

        signed_txn = w3.eth.account.sign_transaction(txn, owner_eth_private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        logger.info(f"Public key updated. Tx: {tx_hash.hex()}")
        return receipt.status == 1

    except Exception as e:
        logger.error(f"Failed to update public key: {e}")
        return False


def update_document_cid(did_bytes32: bytes, new_document_cid: str,
                         owner_eth_address: str, owner_eth_private_key: str) -> bool:
    """Updates the document CID for a DID."""
    if not did_registry_contract:
        return False

    try:
        try:
            gas_estimate = did_registry_contract.functions.updateDocumentCID(
                did_bytes32, new_document_cid
            ).estimate_gas({'from': owner_eth_address})
        except:
            gas_estimate = 300000

        _validate_sufficient_balance(owner_eth_address, owner_eth_private_key, gas_estimate)

        txn = did_registry_contract.functions.updateDocumentCID(
            did_bytes32, new_document_cid
        ).build_transaction({
            'from': owner_eth_address,
            'nonce': w3.eth.get_transaction_count(owner_eth_address),
            'gas': gas_estimate,
            'gasPrice': w3.eth.gas_price
        })

        signed_txn = w3.eth.account.sign_transaction(txn, owner_eth_private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        logger.info(f"Document CID updated. Tx: {tx_hash.hex()}")
        return receipt.status == 1

    except Exception as e:
        logger.error(f"Failed to update document CID: {e}")
        return False


def resolve_did(did_bytes32: bytes) -> dict:
    """Resolves a DID to its document."""
    if not did_registry_contract:
        return {}

    try:
        result = did_registry_contract.functions.resolveDID(did_bytes32).call()
        return {
            'publicKey': result[0],
            'documentCID': result[1],
            'owner': result[2],
            'registered': result[3]
        }
    except Exception as e:
        logger.error(f"Failed to resolve DID: {e}")
        return {}


def is_did_registered(did_bytes32: bytes) -> bool:
    """Checks if a DID is registered."""
    if not did_registry_contract:
        return False
    
    try:
        return did_registry_contract.functions.isDIDRegistered(did_bytes32).call()
    except Exception as e:
        logger.error(f"Failed to check DID registration: {e}")
        return False