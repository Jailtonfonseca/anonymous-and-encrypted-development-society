import asyncio
import json
import os
import uuid
from ecies import encrypt, decrypt # Using eciespy
from eth_keys import keys # Using eth-keys
from hexbytes import HexBytes

# Assuming did_system.py is in the same directory or accessible in PYTHONPATH
import did_system # To fetch public keys from DIDs

# --- Configuration & Helper ---
# Default Ganache private keys for testing (replace with actual keys from your Ganache instance)
# These correspond to the first few default accounts in Ganache.
# Account 0: (Address: often 0x90F8bf6A479f320ead074411a4B0e7944Ea8c9C1)
TEST_PK_HEX_DID1 = os.environ.get("P2P_TEST_PK_DID1", "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d")
# Account 1: (Address: often 0xFFcf8FDEE72ac11b5c542428B35EEF5769C409f0)
TEST_PK_HEX_DID2 = os.environ.get("P2P_TEST_PK_DID2", "0x6c002f5f36494661586ebb0882038bf8d598aafb88a5e2300971707fce91e997")

# --- Key Management Utilities ---

def get_eth_keys_private_key(hex_private_key: str) -> keys.PrivateKey | None:
    """Converts a hex private key string to an eth_keys.PrivateKey object."""
    try:
        return keys.PrivateKey(HexBytes(hex_private_key))
    except Exception as e:
        print(f"Error creating PrivateKey object: {e}")
        return None

def get_hex_public_key_from_private(hex_private_key: str) -> str | None:
    """Derives the hex uncompressed public key from a hex private key."""
    pk_obj = get_eth_keys_private_key(hex_private_key)
    if pk_obj:
        return "0x04" + pk_obj.public_key.to_bytes().hex() # Prepend 0x04 for uncompressed
    return None

# --- Encryption/Decryption Functions ---

def encrypt_message(recipient_hex_public_key: str, message: str) -> bytes | None:
    """
    Encrypts a message using ECIES for the given recipient's public key.
    Assumes recipient_hex_public_key is uncompressed (starts with "0x04").
    """
    try:
        # eciespy expects bytes for the public key.
        # If it starts with "0x04" (uncompressed), it's 65 bytes.
        # If it's compressed (starts with "0x02" or "0x03"), it's 33 bytes.
        # eciespy handles secp256k1 keys directly.
        
        if not recipient_hex_public_key.startswith("0x04"):
            print("Warning: Public key does not seem to be in uncompressed format (missing 0x04 prefix). eciespy might expect uncompressed keys.")
            # Depending on eciespy's specific requirements, conversion might be needed here if it only accepts one format.
            # For now, we pass it as bytes.
            
        public_key_bytes = HexBytes(recipient_hex_public_key)
        encrypted_payload = encrypt(public_key_bytes, message.encode('utf-8'))
        return encrypted_payload
    except Exception as e:
        print(f"Error encrypting message: {e}")
        return None

def decrypt_message(recipient_hex_private_key: str, encrypted_payload: bytes) -> str | None:
    """
    Decrypts an ECIES encrypted payload using the recipient's private key.
    """
    try:
        private_key_bytes = HexBytes(recipient_hex_private_key)
        decrypted_message_bytes = decrypt(private_key_bytes, encrypted_payload)
        return decrypted_message_bytes.decode('utf-8')
    except Exception as e:
        print(f"Error decrypting message: {e}")
        # Common error: "No solution for an equation" if wrong key or corrupted data
        return None

# --- P2P Server Logic ---

# Global queue for tests to retrieve received messages
test_message_queue = asyncio.Queue()

async def handle_connection_for_test(reader, writer, local_did_identifier_string: str, local_hex_private_key: str):
    """
    Test-specific connection handler that puts decrypted messages into a queue.
    """
    addr = writer.get_extra_info('peername')
    print(f"[Test Server - {local_did_identifier_string}] Accepted connection from {addr}")

    try:
        encrypted_data = await reader.read(4096) 
        if not encrypted_data:
            print(f"[Test Server - {local_did_identifier_string}] No data received from {addr}. Connection closed.")
            return

        print(f"[Test Server - {local_did_identifier_string}] Received {len(encrypted_data)} encrypted bytes from {addr}")
        
        decrypted_message = decrypt_message(local_hex_private_key, encrypted_data)

        if decrypted_message:
            print(f"[Test Server - {local_did_identifier_string}] Message decrypted: '{decrypted_message}'")
            await test_message_queue.put(decrypted_message) # Put message in queue for test validation
        else:
            print(f"[Test Server - {local_did_identifier_string}] Failed to decrypt message from {addr}.")
            await test_message_queue.put(None) # Signal failure or empty message

    except Exception as e:
        print(f"[Test Server - {local_did_identifier_string}] Error handling connection from {addr}: {e}")
        await test_message_queue.put(None) # Signal error
    finally:
        print(f"[Test Server - {local_did_identifier_string}] Closing connection from {addr}")
        writer.close()
        await writer.wait_closed()

async def start_server(host: str, port: int, did_identifier_string: str, hex_private_key: str, use_test_handler: bool = False):
    """
    Starts the P2P server.
    Args:
        use_test_handler: If True, uses `handle_connection_for_test` which integrates with `test_message_queue`.
    """
    if use_test_handler:
        handler_func = handle_connection_for_test
        print(f"[Test System] Starting server with TEST handler for DID {did_identifier_string}")
    else:
        # This would be the production handler, which is currently the same as test for simplicity
        # but could be different (e.g. logging to a file, processing commands, etc.)
        # For now, let's make the original handle_connection the default one if we differentiate later
        async def default_handle_connection(reader, writer, local_did_id_str_arg, local_pk_hex_arg):
            addr = writer.get_extra_info('peername')
            print(f"[Server - {local_did_id_str_arg}] Accepted connection from {addr}")
            try:
                encrypted_data = await reader.read(4096)
                if not encrypted_data:
                    print(f"[Server - {local_did_id_str_arg}] No data from {addr}.")
                    return
                decrypted_message = decrypt_message(local_pk_hex_arg, encrypted_data)
                if decrypted_message:
                    print(f"[Server - {local_did_id_str_arg}] Decrypted: '{decrypted_message}'")
                else:
                    print(f"[Server - {local_did_id_str_arg}] Failed to decrypt from {addr}.")
            except Exception as e:
                print(f"[Server - {local_did_id_str_arg}] Error: {e}")
            finally:
                print(f"[Server - {local_did_id_str_arg}] Closing connection from {addr}")
                writer.close()
                await writer.wait_closed()
        handler_func = default_handle_connection
        print(f"[System] Starting server with REGULAR handler for DID {did_identifier_string}")


    async def client_connected_cb(reader, writer):
        # Pass the specific DID and PK for this server instance
        await handler_func(reader, writer, did_identifier_string, hex_private_key)

    server = await asyncio.start_server(client_connected_cb, host, port)
    
    addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    print(f"P2P Server started for DID '{did_identifier_string}' on {addrs}")

    try:
        async with server:
            await server.serve_forever()
    except asyncio.CancelledError:
        print(f"Server for DID '{did_identifier_string}' cancelled.")
    finally:
        print(f"Server for DID '{did_identifier_string}' on {addrs} is shutting down.")
        server.close()
        await server.wait_closed()
        print(f"Server for DID '{did_identifier_string}' fully closed.")


# --- P2P Client Logic ---

async def send_message_p2p(target_host: str, target_port: int, 
                           recipient_did_identifier_string: str, 
                           message: str) -> bool:
    print(f"\nAttempting to send message to DID '{recipient_did_identifier_string}' at {target_host}:{target_port}")

    # 1. Retrieve recipient's public key using did_system
    if not did_system.w3 or not did_system.did_registry_contract:
        print("Error: did_system (Web3 or DIDRegistry contract) not initialized. Cannot fetch recipient public key.")
        return False
        
    recipient_did_bytes32 = did_system.generate_did_identifier(recipient_did_identifier_string)
    did_info = did_system.get_did_info(recipient_did_bytes32)

    if not did_info or not did_info.get("publicKey"):
        print(f"Error: Could not retrieve public key for recipient DID '{recipient_did_identifier_string}'. Ensure DID is registered with a public key.")
        return False
    
    recipient_hex_public_key = did_info["publicKey"]
    # Ensure it's uncompressed hex format "0x04..." if eciespy expects it.
    # The DIDRegistry stores it as a string; assume it's stored correctly.
    # For eth_keys, public keys are often handled as bytes. eciespy might be similar.
    # If the stored key is compressed, it might need conversion.
    # For this example, we assume the stored publicKey string is directly usable or convertible.
    print(f"Retrieved public key for {recipient_did_identifier_string}: {recipient_hex_public_key[:30]}...")


    # 2. Encrypt the message
    encrypted_payload = encrypt_message(recipient_hex_public_key, message)
    if not encrypted_payload:
        print(f"Error: Failed to encrypt message for {recipient_did_identifier_string}.")
        return False
    print(f"Message encrypted successfully ({len(encrypted_payload)} bytes).")

    # 3. Connect and send
    try:
        reader, writer = await asyncio.open_connection(target_host, target_port)
        print(f"Connected to server at {target_host}:{target_port}")

        writer.write(encrypted_payload)
        await writer.drain()
        print("Encrypted message sent.")

        writer.close()
        await writer.wait_closed()
        print("Connection closed by sender.")
        return True
        
    except ConnectionRefusedError:
        print(f"Error: Connection refused by {target_host}:{target_port}. Ensure server is running.")
        return False
    except Exception as e:
        print(f"Error sending message to {target_host}:{target_port}: {e}")
        return False

# --- Example Usage ---
async def main_test():
    # This test assumes DIDRegistry.sol is deployed and accessible via did_system.py
    # And that the DIDs below are registered with their corresponding public keys.
    
    # Test variables
    test_did1_id_str = f"p2p-test-did1-{uuid.uuid4().hex[:6]}"
    test_did1_pk_hex = TEST_PK_HEX_DID1 # Corresponds to Ganache account 0 by default
    
    test_did2_id_str = f"p2p-test-did2-{uuid.uuid4().hex[:6]}"
    test_did2_pk_hex = TEST_PK_HEX_DID2 # Corresponds to Ganache account 1 by default

    server_host = "127.0.0.1"
    server_port = 9998 # Use a different port for testing
    test_message_content = f"Hello {test_did1_id_str} from {test_did2_id_str}! Random: {uuid.uuid4().hex[:8]}"
    
    server_task = None
    all_tests_passed = True # Flag to track overall test success

    try:
        # --- Prerequisite: Register DIDs with their public keys ---
        if not (did_system.w3 and did_system.did_registry_contract):
            print("CRITICAL: did_system.py (Web3/Contract) not initialized. Cannot register DIDs for test.")
            raise RuntimeError("did_system.py not initialized for P2P test setup.")

        # DID1 Setup (Server)
        pk1_obj = get_eth_keys_private_key(test_did1_pk_hex)
        did1_eth_address = pk1_obj.public_key.to_address()
        did1_hex_public_key = "0x04" + pk1_obj.public_key.to_bytes().hex()
        did1_bytes32 = did_system.generate_did_identifier(test_did1_id_str)
        if not did_system.is_did_registered(did1_bytes32):
            print(f"Registering DID1 '{test_did1_id_str}' (Owner: {did1_eth_address}, PK: {did1_hex_public_key[:20]}...) for server...")
            reg_success = did_system.register_did(did1_bytes32, did1_hex_public_key, "QmP2PServerCID", did1_eth_address, test_did1_pk_hex)
            if not reg_success:
                raise RuntimeError(f"Failed to register DID1 '{test_did1_id_str}' for P2P test.")
        else:
            # Ensure public key is up-to-date if DID already exists
            # This is important if the stored PK in DIDRegistry is different from what we expect for decryption
            current_info = did_system.get_did_info(did1_bytes32)
            if not current_info or current_info.get('publicKey') != did1_hex_public_key:
                print(f"Updating public key for DID1 '{test_did1_id_str}'...")
                update_success = did_system.update_public_key(did1_bytes32, did1_hex_public_key, did1_eth_address, test_did1_pk_hex)
                if not update_success:
                     raise RuntimeError(f"Failed to update public key for DID1 '{test_did1_id_str}'.")
            print(f"DID1 '{test_did1_id_str}' already registered or updated with PK: {did1_hex_public_key[:20]}...")


        # DID2 Setup (Client) - only needs its PK for this test if we were signing, but not for sending.
        # Its existence isn't strictly required on-chain for it to *send* a message,
        # but the recipient (DID1) must be on-chain for the sender (DID2) to find its public key.
        pk2_obj = get_eth_keys_private_key(test_did2_pk_hex)
        # did2_eth_address = pk2_obj.public_key.to_address()
        # did2_hex_public_key = "0x04" + pk2_obj.public_key.to_bytes().hex()
        # did2_bytes32 = did_system.generate_did_identifier(test_did2_id_str)
        # if not did_system.is_did_registered(did2_bytes32):
        #     print(f"Registering DID2 '{test_did2_id_str}' (Owner: {did2_eth_address}, PK: {did2_hex_public_key[:20]}...) for client...")
        #     reg_success = did_system.register_did(did2_bytes32, did2_hex_public_key, "QmP2PClientCID", did2_eth_address, test_did2_pk_hex)
        #     if not reg_success:
        #         print(f"Warning: Failed to register DID2 '{test_did2_id_str}' for P2P test. Sending might still work if recipient is findable.")
        # else:
        #     print(f"DID2 '{test_did2_id_str}' already registered.")


        # --- Test Flow ---
        print(f"\nStarting P2P server for DID '{test_did1_id_str}' on {server_host}:{server_port} using TEST HANDLER...")
        server_task = asyncio.create_task(
            start_server(server_host, server_port, test_did1_id_str, test_did1_pk_hex, use_test_handler=True)
        )
        await asyncio.sleep(0.5) # Give server a moment to start

        print(f"\nClient (DID: {test_did2_id_str}) sending message: '{test_message_content}' to DID '{test_did1_id_str}'")
        send_success = await send_message_p2p(
            server_host, server_port, 
            recipient_did_identifier_string=test_did1_id_str, 
            message=test_message_content
        )
        
        if not send_success:
            print("Test FAILED: Client failed to send message.")
            all_tests_passed = False
        else:
            print("Client: Message sent. Waiting for server to process and put in queue...")
            try:
                # Retrieve message from queue with a timeout
                received_message = await asyncio.wait_for(test_message_queue.get(), timeout=5.0)
                
                if received_message == test_message_content:
                    print(f"Test PASSED: Server for DID '{test_did1_id_str}' correctly received and decrypted: '{received_message}'")
                else:
                    print(f"Test FAILED: Mismatch in sent and received message.")
                    print(f"  Sent:     '{test_message_content}'")
                    print(f"  Received: '{received_message}'")
                    all_tests_passed = False
                test_message_queue.task_done() # Notify queue item processed
            except asyncio.TimeoutError:
                print("Test FAILED: Timed out waiting for message from server queue.")
                all_tests_passed = False
            except Exception as e_queue:
                print(f"Test FAILED: Error retrieving message from queue: {e_queue}")
                all_tests_passed = False
                
    except RuntimeError as e_setup:
        print(f"P2P Test Setup FAILED: {e_setup}")
        all_tests_passed = False
    except Exception as e_main:
        print(f"An unexpected error occurred during main_test: {e_main}")
        all_tests_passed = False
    finally:
        if server_task and not server_task.done():
            print("Attempting to cancel server task...")
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                print("P2P Server task explicitly cancelled.")
            except Exception as e_cancel:
                print(f"Error during server task cancellation: {e_cancel}")
        else:
            print("Server task was not running or already completed.")
        print("\n--- P2P Messaging Test Scenario Finished ---")

    return all_tests_passed


if __name__ == "__main__":
    # This setup is for demonstration. In a real application,
    # server and client would run in separate processes/machines.
    
    print("--- p2p_messaging.py Integration Test ---")
    final_status = False
    try:
        # Check if required contract files for did_system are present
        abi_ok = os.path.exists(did_system.ABI_FILE_PATH)
        addr_ok = os.path.exists(did_system.CONTRACT_ADDRESS_FILE)

        if abi_ok and addr_ok:
            print("Found DIDRegistry ABI and Address files for did_system.")
            final_status = asyncio.run(main_test())
        else:
            print("CRITICAL: DIDRegistry ABI or Address file not found for did_system.")
            print(f"  ABI path checked: {os.path.abspath(did_system.ABI_FILE_PATH)}")
            print(f"  Address path checked: {os.path.abspath(did_system.CONTRACT_ADDRESS_FILE)}")
            print("Cannot run p2p_messaging.py tests as it relies on did_system.py for public key retrieval.")
            print("Please ensure DIDRegistry.sol is compiled and deployed first.")
            print("p2p_messaging.py tests SKIPPED.")
            
    except ConnectionRefusedError:
        print("\nCONNECTION REFUSED: Could not connect to Ganache.")
        print("Please ensure Ganache is running for did_system initialization and DID registration.")
    except FileNotFoundError as e: # For did_system's files if _init_web3 fails before check
        print(f"\nFILE NOT FOUND during initialization: {e}.")
    except Exception as e:
        print(f"\nAn unexpected error occurred outside main_test: {e}")
    
    if final_status:
        print("\nAll p2p_messaging.py tests passed successfully!")
        exit(0)
    else:
        print("\nSome p2p_messaging.py tests FAILED or were SKIPPED.")
        exit(1)

```
