import json
import solcx
import os

def compile_aegis_token():
    """
    Compiles AegisToken.sol, extracts ABI and bytecode, and saves them to files.
    """
    contract_source_path = "AegisToken.sol"
    contract_name = "AegisToken"

    if not os.path.exists(contract_source_path):
        print(f"Error: {contract_source_path} not found.")
        return False

    try:
        # Ensure a compatible solc version is available/installed
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
                solcx.install_solc('0.8.20') # Install a specific recent 0.8.x version
                target_version = solcx.set_solc_version('0.8.20', silent=True)
                print(f"Using solc version: {solcx.get_solc_version()}")
            except Exception as e:
                print(f"Failed to install solc 0.8.20: {e}")
                return False
        else:
            solcx.set_solc_version(target_version, silent=True)
            print(f"Using existing solc version: {solcx.get_solc_version()}")


        with open(contract_source_path, 'r') as f:
            contract_source_code = f.read()

        print(f"Compiling {contract_source_path}...")
        # Need to provide the paths to the openzeppelin imports
        allowed_paths = [os.path.abspath("./openzeppelin/contracts")]
        compiled_sol = solcx.compile_source(
            contract_source_code,
            output_values=['abi', 'bin'],
            solc_version=str(solcx.get_solc_version()),
            allow_paths=allowed_paths
        )

        # The key for the contract interface
        contract_interface_key = f'{contract_source_path}:{contract_name}'
        if contract_interface_key not in compiled_sol:
            # Fallback for different key formats
            potential_key = f'<stdin>:{contract_name}'
            if potential_key in compiled_sol:
                contract_interface_key = potential_key
            else:
                print(f"Error: Could not find compiled contract interface for '{contract_name}'. Keys: {compiled_sol.keys()}")
                return False

        contract_interface = compiled_sol[contract_interface_key]

        # Extract ABI
        abi = contract_interface['abi']
        with open(f"{contract_name}.abi.json", 'w') as f:
            json.dump(abi, f, indent=4)
        print(f"ABI saved to {contract_name}.abi.json")

        # Extract bytecode (bin)
        bytecode = contract_interface['bin']
        with open(f"{contract_name}.bytecode.txt", 'w') as f:
            f.write(bytecode)
        print(f"Bytecode saved to {contract_name}.bytecode.txt")

        return True

    except solcx.exceptions.SolcError as e:
        print(f"Solc compilation error: {e}")
        return False
    except Exception as e:
        print(f"An error occurred during compilation: {e}")
        return False

if __name__ == "__main__":
    if compile_aegis_token():
        print("AegisToken compilation and extraction successful.")
    else:
        print("AegisToken compilation and extraction FAILED.")
        exit(1)
