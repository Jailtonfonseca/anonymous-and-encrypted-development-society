import json
import solcx
import os

def compile_did_registry():
    """
    Compiles DIDRegistry.sol, extracts ABI and bytecode, and saves them to files.
    """
    contract_source_path = "DIDRegistry.sol"
    
    if not os.path.exists(contract_source_path):
        print(f"Error: {contract_source_path} not found.")
        return False

    try:
        # Ensure a compatible solc version is available/installed
        # The contract uses ^0.8.0. Let's try to use a version in that range.
        # solcx.install_solc_pragma('^0.8.0') # This ensures a suitable version is installed
        
        # Find available solc versions and select one
        installed_versions = solcx.get_installed_solc_versions()
        target_version = None
        if installed_versions:
            for v in installed_versions:
                if v.major == 0 and v.minor == 8: # Looking for any 0.8.x
                    target_version = v
                    break
        
        if not target_version:
            print("No suitable 0.8.x solc version found. Attempting to install one...")
            try:
                solcx.install_solc('0.8.4') # Install a specific recent 0.8.x version
                target_version = solcx.set_solc_version('0.8.4', silent=True)
                print(f"Using solc version: {solcx.get_solc_version()}")
            except Exception as e:
                print(f"Failed to install solc 0.8.4: {e}")
                print("Please ensure solc 0.8.x is installed and accessible or try installing it manually.")
                return False
        else:
            solcx.set_solc_version(target_version, silent=True)
            print(f"Using existing solc version: {solcx.get_solc_version()}")


        with open(contract_source_path, 'r') as f:
            contract_source_code = f.read()

        print(f"Compiling {contract_source_path}...")
        compiled_sol = solcx.compile_source(
            contract_source_code,
            output_values=['abi', 'bin'],
            solc_version=str(solcx.get_solc_version()) # Use the string representation of the Version object
        )

        # Contract name will be <source_file_name>:<contract_name_in_source>
        contract_interface_key = f'<stdin>:{os.path.splitext(os.path.basename(contract_source_path))[0]}'
        # Fallback if <stdin> is not used by solcx for single source compilation
        if contract_interface_key not in compiled_sol:
            # Try to find the key if it's different (e.g. just contract name)
            for key in compiled_sol.keys():
                if os.path.splitext(os.path.basename(contract_source_path))[0] in key:
                    contract_interface_key = key
                    break
            if contract_interface_key not in compiled_sol:
                 print(f"Error: Could not find compiled contract interface. Keys: {compiled_sol.keys()}")
                 return False


        contract_interface = compiled_sol[contract_interface_key]

        # Extract ABI
        abi = contract_interface['abi']
        with open("DIDRegistry.abi.json", 'w') as f:
            json.dump(abi, f, indent=4)
        print("ABI saved to DIDRegistry.abi.json")

        # Extract bytecode (bin)
        bytecode = contract_interface['bin']
        with open("DIDRegistry.bytecode.txt", 'w') as f:
            f.write(bytecode)
        print("Bytecode saved to DIDRegistry.bytecode.txt")
        
        return True

    except solcx.exceptions.SolcError as e:
        print(f"Solc compilation error: {e}")
        return False
    except Exception as e:
        print(f"An error occurred during compilation: {e}")
        return False

if __name__ == "__main__":
    if compile_did_registry():
        print("Compilation and extraction successful.")
    else:
        print("Compilation and extraction failed.")
