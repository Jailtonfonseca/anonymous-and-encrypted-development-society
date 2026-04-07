"""
Configuration Module for Aegis Forge.

Centralizes all configuration settings and environment variables.
This module should be imported first by all other modules.
"""

import os
from pathlib import Path
from typing import Optional

# --- Base Directories ---
BASE_DIR = Path(__file__).parent.absolute()
PROJECT_DATA_BASE_DIR = BASE_DIR / "project_data"

# --- Blockchain Configuration ---
GANACHE_URL = os.environ.get("GANACHE_URL", "http://127.0.0.1:8545")
GANACHE_CHAIN_ID = int(os.environ.get("GANACHE_CHAIN_ID", "1337"))

# Default Ganache test accounts (FOR DEVELOPMENT ONLY - NEVER USE IN PRODUCTION)
# These are the default private keys from Ganache CLI/GUI
DEFAULT_TEST_ACCOUNTS = {
    0: {
        "address": "0x90F8bf6A479f320ead074411a4B0e7944Ea8c9C1",
        "private_key": os.environ.get(
            "TEST_ACCOUNT_PK_0",
            "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d"
        ),
    },
    1: {
        "address": "0xFFcf8FDEE72ac11b5c542428B35EEF5769C409f0",
        "private_key": os.environ.get(
            "TEST_ACCOUNT_PK_1",
            "0x6c002f5f36494661586ebb0882038bf8d598aafb88a5e2300971707fce91e997"
        ),
    },
    2: {
        "address": "0x976EA74026E726554dB657fA54763abd0C3a0aa9",
        "private_key": os.environ.get(
            "TEST_ACCOUNT_PK_2",
            "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a"
        ),
    },
}

# P2P Testing Keys (can use same as test accounts)
P2P_TEST_PK_DID1 = os.environ.get("P2P_TEST_PK_DID1", DEFAULT_TEST_ACCOUNTS[0]["private_key"])
P2P_TEST_PK_DID2 = os.environ.get("P2P_TEST_PK_DID2", DEFAULT_TEST_ACCOUNTS[1]["private_key"])

# --- Smart Contract Files ---
DID_REGISTRY_ABI_FILE = BASE_DIR / "DIDRegistry.abi.json"
DID_REGISTRY_ADDRESS_FILE = BASE_DIR / "DIDRegistry.address.txt"
DID_REGISTRY_SOL_FILE = BASE_DIR / "DIDRegistry.sol"

AEGIS_TOKEN_ABI_FILE = BASE_DIR / "AegisToken.abi.json"
AEGIS_TOKEN_ADDRESS_FILE = BASE_DIR / "AegisToken.address.txt"
AEGIS_TOKEN_SOL_FILE = BASE_DIR / "AegisToken.sol"

# --- Data Files ---
PROJECTS_FILE = BASE_DIR / "projects.json"
CONTRIBUTIONS_FILE = BASE_DIR / "contributions.json"

# --- IPFS Configuration ---
IPFS_HOST = os.environ.get("IPFS_HOST", "/ip4/127.0.0.1/tcp/5001")

# --- P2P Messaging Configuration ---
P2P_DEFAULT_HOST = os.environ.get("P2P_DEFAULT_HOST", "127.0.0.1")
P2P_DEFAULT_PORT = int(os.environ.get("P2P_DEFAULT_PORT", "9999"))
P2P_CONNECTION_TIMEOUT = int(os.environ.get("P2P_CONNECTION_TIMEOUT", "30"))
P2P_MESSAGE_MAX_SIZE = int(os.environ.get("P2P_MESSAGE_MAX_SIZE", "4096"))

# --- Transaction Configuration ---
DEFAULT_GAS_LIMIT = int(os.environ.get("DEFAULT_GAS_LIMIT", "500000"))
DEFAULT_GAS_PRICE_GWEI = int(os.environ.get("DEFAULT_GAS_PRICE_GWEI", "1"))
TRANSACTION_TIMEOUT = int(os.environ.get("TRANSACTION_TIMEOUT", "120"))

# --- Security Settings ---
ALLOWED_FILE_UPLOAD_DIRS = [
    BASE_DIR,
    PROJECT_DATA_BASE_DIR,
]
MAX_FILE_SIZE_MB = int(os.environ.get("MAX_FILE_SIZE_MB", "10"))

# --- Logging Configuration ---
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = os.environ.get("LOG_FILE", str(BASE_DIR / "aegis_forge.log"))


def validate_environment() -> dict:
    """
    Validates that required environment variables and files are present.
    
    Returns:
        dict: Validation results with 'success' bool and 'errors' list
    """
    errors = []
    warnings = []
    
    # Check if running in production mode (should have env vars set)
    is_production = os.environ.get("AEGIS_ENV", "development") == "production"
    
    if is_production:
        # In production, require explicit env var setup
        if not os.environ.get("GANACHE_URL"):
            errors.append("GANACHE_URL must be set in production mode")
        
        # Warn about using default test keys
        for idx, account in DEFAULT_TEST_ACCOUNTS.items():
            env_var = f"TEST_ACCOUNT_PK_{idx}"
            if not os.environ.get(env_var):
                warnings.append(
                    f"Using default test key for account {idx}. "
                    "Set {env_var} environment variable in production."
                )
    
    # Check contract files exist (warn if not, as they may be deployed later)
    contract_files = {
        "DIDRegistry ABI": DID_REGISTRY_ABI_FILE,
        "DIDRegistry Address": DID_REGISTRY_ADDRESS_FILE,
        "AegisToken ABI": AEGIS_TOKEN_ABI_FILE,
        "AegisToken Address": AEGIS_TOKEN_ADDRESS_FILE,
    }
    
    for name, path in contract_files.items():
        if not path.exists():
            warnings.append(f"{name} file not found: {path}")
    
    return {
        "success": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "is_production": is_production,
    }


def ensure_directories():
    """Creates necessary directories if they don't exist."""
    PROJECT_DATA_BASE_DIR.mkdir(parents=True, exist_ok=True)


# Initialize on import
ensure_directories()

if __name__ == "__main__":
    print("=== Aegis Forge Configuration ===\n")
    
    validation = validate_environment()
    
    print(f"Environment: {'Production' if validation['is_production'] else 'Development'}")
    print(f"Validation Success: {validation['success']}")
    
    if validation['errors']:
        print("\nErrors:")
        for error in validation['errors']:
            print(f"  ❌ {error}")
    
    if validation['warnings']:
        print("\nWarnings:")
        for warning in validation['warnings']:
            print(f"  ⚠️  {warning}")
    
    if not validation['errors']:
        print("\n✅ Configuration validated successfully!")
    
    print(f"\nGanache URL: {GANACHE_URL}")
    print(f"IPFS Host: {IPFS_HOST}")
    print(f"Base Directory: {BASE_DIR}")
    print(f"Project Data Directory: {PROJECT_DATA_BASE_DIR}")
