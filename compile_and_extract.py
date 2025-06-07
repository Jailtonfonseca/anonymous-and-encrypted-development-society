import json
import solcx
import os
import re
from solcx.exceptions import SolcError, SolcInstallationError

def setup_solc_version(requested_pragma: str = "^0.8.0", specific_version: str = "0.8.20") -> str | None:
    """
    Manages solc version. Tries to find an installed version matching the pragma.
    If not found, attempts to install specific_version.
    Sets the found/installed version using solcx.set_solc_version().

    Args:
        requested_pragma: The pragma string (e.g., "^0.8.0").
        specific_version: The specific version to install if a suitable one isn't found (e.g., "0.8.20").

    Returns:
        The active solc version string if successful, None otherwise.
    """
    try:
        installed_versions = solcx.get_installed_solc_versions()

        # Try to find a version matching the pragma
        if requested_pragma:
            # Simple pragma parsing: assumes format like "^X.Y.Z" or "X.Y.Z"
            match = re.match(r"\^?(\d+)\.(\d+)\.(\d+)", requested_pragma.replace(" ", ""))
            if match:
                req_major, req_minor, req_patch = map(int, match.groups())
                for v_obj in sorted(installed_versions, reverse=True): # Prefer newer compatible versions
                    if v_obj.major == req_major and v_obj.minor == req_minor:
                        if requested_pragma.startswith("^"): # Caret means compatible with newer patch versions
                            if v_obj.patch >= req_patch:
                                print(f"Found installed solc version matching pragma '{requested_pragma}': {v_obj}")
                                solcx.set_solc_version(str(v_obj), silent=True)
                                return str(solcx.get_solc_version())
                        elif str(v_obj) == requested_pragma: # Exact match
                             print(f"Found installed solc version matching exact version '{requested_pragma}': {v_obj}")
                             solcx.set_solc_version(str(v_obj), silent=True)
                             return str(solcx.get_solc_version())


        # If no pragma match or no pragma provided, try installing specific_version if not already installed
        specific_version_obj = None
        for v_obj in installed_versions:
            if str(v_obj) == specific_version:
                specific_version_obj = v_obj
                break

        if specific_version_obj:
            print(f"Using existing installed solc version: {specific_version_obj}")
            solcx.set_solc_version(str(specific_version_obj), silent=True)
        else:
            print(f"Attempting to install solc version: {specific_version}...")
            try:
                solcx.install_solc(specific_version, show_progress=True)
                print(f"Successfully installed solc version {specific_version}.")
                solcx.set_solc_version(specific_version, silent=True)
            except SolcInstallationError as e:
                print(f"Error installing solc version {specific_version}: {e}")
                print("Please check your internet connection or try installing it manually.")
                return None
            except Exception as e:
                print(f"An unexpected error occurred during solc installation: {e}")
                return None

        active_version = str(solcx.get_solc_version())
        print(f"Successfully set active solc version to: {active_version}")
        return active_version

    except Exception as e:
        print(f"An error occurred during solc version setup: {e}")
        return None

def compile_single_contract(contract_source_filename: str, contract_name_in_code: str, solc_version_to_use: str) -> bool:
    """
    Compiles a single Solidity contract, extracts its ABI and bytecode, and saves them to files.

    Args:
        contract_source_filename: The .sol file name (e.g., "DIDRegistry.sol").
        contract_name_in_code: The actual name of the contract declared in the Solidity code (e.g., "DIDRegistry").
        solc_version_to_use: The specific solc version string to use for compilation.

    Returns:
        True if compilation and file saving were successful, False otherwise.
    """
    if not os.path.exists(contract_source_filename):
        print(f"Error: Source file '{contract_source_filename}' not found.")
        return False

    try:
        with open(contract_source_filename, 'r') as f:
            contract_source_code = f.read()

        print(f"\nCompiling '{contract_source_filename}' with contract name '{contract_name_in_code}' using solc {solc_version_to_use}...")
        
        # Ensure the set solc version is indeed what we intend to use for this specific compilation
        # This might be redundant if setup_solc_version was called correctly and globally,
        # but can be a safeguard if this function is called in different contexts.
        current_set_version = str(solcx.get_solc_version())
        if current_set_version != solc_version_to_use:
            print(f"Warning: Current solcx version '{current_set_version}' differs from requested '{solc_version_to_use}'. Attempting to set.")
            try:
                solcx.set_solc_version(solc_version_to_use, silent=True)
            except Exception as e:
                print(f"Error setting solc version to {solc_version_to_use} for {contract_source_filename}: {e}")
                return False


        # Allow relative imports from the current directory (where openzeppelin might be)
        # The import paths in .sol files are like "./openzeppelin/..."
        # solcx needs to know where to find these. The current working directory is usually implicitly included.
        # If issues arise, `import_remappings` or `allow_paths` might be needed.
        # For now, assume standard behavior works if openzeppelin is in the root or a known path.
        # The `allow_paths` argument can specify directories for the compiler to search for imports.
        # Let's add the current directory explicitly to be safe, as this is where `openzeppelin` folder is.
        allowed_paths = [os.getcwd()]

        compiled_sol = solcx.compile_source(
            contract_source_code,
            output_values=['abi', 'bin'],
            solc_version=solc_version_to_use,
            allow_paths=allowed_paths
        )

        # Try to find the contract interface key.
        # Common patterns: "<stdin>:<ContractName>" or "ContractSourceFile.sol:<ContractName>"
        # Given we compile source string, "<stdin>:<ContractName>" is most likely.
        possible_keys = [
            f"<stdin>:{contract_name_in_code}",
            f"{contract_source_filename}:{contract_name_in_code}"
        ]

        contract_interface = None
        found_key = None
        for key_pattern in possible_keys:
            if key_pattern in compiled_sol:
                contract_interface = compiled_sol[key_pattern]
                found_key = key_pattern
                break

        if not contract_interface:
            # Fallback: Iterate through all keys if primary patterns fail
            for key in compiled_sol.keys():
                if contract_name_in_code in key: # Simpler check
                    contract_interface = compiled_sol[key]
                    found_key = key
                    print(f"Found contract interface using fallback key: {found_key}")
                    break
            if not contract_interface:
                print(f"Error: Could not find compiled contract interface for '{contract_name_in_code}' in '{contract_source_filename}'.")
                print(f"  Tried keys: {possible_keys}")
                print(f"  Available keys in compiled output: {list(compiled_sol.keys())}")
                return False

        print(f"Successfully extracted interface for '{contract_name_in_code}' using key '{found_key}'.")

        # Extract ABI
        abi = contract_interface['abi']
        abi_filename = f"{contract_name_in_code}.abi.json"
        with open(abi_filename, 'w') as f:
            json.dump(abi, f, indent=4)
        print(f"ABI saved to '{abi_filename}'")

        # Extract bytecode (bin)
        bytecode = contract_interface['bin']
        bytecode_filename = f"{contract_name_in_code}.bytecode.txt"
        with open(bytecode_filename, 'w') as f:
            f.write(bytecode)
        print(f"Bytecode saved to '{bytecode_filename}'")
        
        return True

    except SolcError as e:
        print(f"Solc compilation error for '{contract_source_filename}': {e}")
        # More detailed error output if available
        if hasattr(e, 'stdout'):
            print(f"Compiler stdout:\n{e.stdout}")
        if hasattr(e, 'stderr'):
            print(f"Compiler stderr:\n{e.stderr}")
        return False
    except FileNotFoundError: # Should be caught by os.path.exists, but as a safeguard
        print(f"Error: Source file '{contract_source_filename}' not found (unexpectedly).")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during compilation of '{contract_source_filename}': {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("--- Aegis Contract Compilation ---")

    # Setup solc version. Using pragma from typical contracts, and a specific fallback.
    # The contracts use ^0.8.20, so specific_version "0.8.20" is good.
    # Pragma could be "^0.8.20" to be more precise.
    active_solc_version = setup_solc_version(requested_pragma="^0.8.20", specific_version="0.8.20")

    if not active_solc_version:
        print("\nCritical: Failed to setup or verify solc version. Aborting compilation.")
    else:
        print(f"\nProceeding with compilations using solc version: {active_solc_version}")

        contracts_to_compile = [
            {"file": "DIDRegistry.sol", "name": "DIDRegistry"},
            {"file": "AegisToken.sol", "name": "AegisToken"},
            {"file": "ProjectToken.sol", "name": "ProjectToken"}
        ]

        all_successful = True
        successful_compilations = 0
        failed_compilations = 0

        for contract_info in contracts_to_compile:
            print("-" * 30)
            success = compile_single_contract(
                contract_source_filename=contract_info["file"],
                contract_name_in_code=contract_info["name"],
                solc_version_to_use=active_solc_version
            )
            if success:
                print(f"Successfully compiled '{contract_info['file']}'.")
                successful_compilations += 1
            else:
                print(f"Failed to compile '{contract_info['file']}'.")
                all_successful = False
                failed_compilations += 1

        print("\n--- Compilation Summary ---")
        if all_successful:
            print(f"All {len(contracts_to_compile)} contracts compiled successfully!")
        else:
            print(f"Compilation finished with errors.")
            print(f"  Successful: {successful_compilations}/{len(contracts_to_compile)}")
            print(f"  Failed:     {failed_compilations}/{len(contracts_to_compile)}")
        print("Please check the output above for details on any errors.")
        print("Make sure your Solidity (.sol) files are in the root directory and OpenZeppelin contracts are under './openzeppelin/contracts/'.")

    print("\n--- End of Aegis Contract Compilation ---")
