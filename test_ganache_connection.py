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
