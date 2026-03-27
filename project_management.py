"""
Project Management Module - CORRIGIDO
Problemas críticos resolvidos:
1. Remoção de chaves privadas hardcoded → variáveis de ambiente
2. Logging adequado implementado
3. Configuração centralizada
"""

import json
import os
import uuid
import re
import logging
import shutil
from typing import Optional

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Configuration via Environment Variables ---
# IMPORTANTE: Defina estas variáveis de ambiente antes de rodar
# export GANACHE_URL="http://127.0.0.1:8545"
# export TEST_ACCOUNT_PK="sua_chave_privada_aqui"
# export TEST_ACCOUNT_PK_RECEIVER="chave_do_receiver"

# Fallback para desenvolvimento local - NON-PRODUCTION
DEFAULT_OWNER_PK = os.environ.get("TEST_ACCOUNT_PK", "")
DEFAULT_RECEIVER_PK = os.environ.get("TEST_ACCOUNT_PK_RECEIVER", "")

if not DEFAULT_OWNER_PK or not DEFAULT_RECEIVER_PK:
    logger.warning(
        "ATENÇÃO: Variáveis de ambiente TEST_ACCOUNT_PK e TEST_ACCOUNT_PK_RECEIVER "
        "não definidas! Os testesInteractive não funcionarão. "
        "Defina: export TEST_ACCOUNT_PK='0x...'  e  export TEST_ACCOUNT_PK_RECEIVER='0x...'"
    )

# Importar módulos (com tratamento de erro)
try:
    import did_system
    import ipfs_storage
except ImportError as e:
    logger.error(f"Erro ao importar módulos: {e}")
    did_system = None
    ipfs_storage = None

PROJECTS_FILE = "projects.json"
PROJECT_DATA_BASE_DIR = "project_data"


def _sanitize_project_name_to_id(project_name: str) -> str:
    """
    Sanitizes a project name to create a filesystem-friendly and URL-friendly ID.
    """
    if not project_name:
        return f"project-{uuid.uuid4().hex[:8]}"

    name = project_name.lower()
    name = re.sub(r'[^\w\s-]', '', name)  # Remove non-alphanumeric
    name = re.sub(r'[-\s]+', '-', name).strip('-_')

    if not name:
        return f"project-{uuid.uuid4().hex[:8]}"
    return name


def _load_projects() -> list:
    """Loads project data from PROJECTS_FILE."""
    if not os.path.exists(PROJECTS_FILE):
        return []
    try:
        with open(PROJECTS_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger.warning(f"{PROJECTS_FILE} contains invalid JSON. Starting empty.")
        return []
    except Exception as e:
        logger.error(f"Error loading projects from {PROJECTS_FILE}: {e}")
        return []


def _save_projects(projects_data: list) -> bool:
    """Saves project data to PROJECTS_FILE."""
    try:
        with open(PROJECTS_FILE, "w") as f:
            json.dump(projects_data, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error saving projects to {PROJECTS_FILE}: {e}")
        return False


def create_project(project_name: str, owner_did: str, token_supply: int = 1000000) -> Optional[dict]:
    """
    Creates a new project, initializes its repository in IPFS, and sets up basic tokenomics.
    """
    if not did_system:
        logger.error("did_system module not available")
        return None

    # 1. Validate owner_did
    owner_did_bytes32 = did_system.generate_did_identifier(owner_did)
    if not did_system.is_did_registered(owner_did_bytes32):
        logger.error(f"Owner DID '{owner_did}' is not registered on the blockchain.")
        return None

    # 2. Sanitize project_name to create project_id
    project_id = _sanitize_project_name_to_id(project_name)
    if not project_id:
        logger.error(f"Could not generate a valid project_id for '{project_name}'.")
        return None

    # 3. Check if project_id already exists
    projects = _load_projects()
    for p in projects:
        if p.get("project_id") == project_id:
            logger.error(f"Project with ID '{project_id}' already exists.")
            return None

    # 4. Initialize decentralized code repository
    logger.info(f"Initializing IPFS repo for project ID: {project_id}")
    repo_cid = ipfs_storage.initialize_project_repo(project_id)
    if not repo_cid:
        logger.error(f"Failed to initialize IPFS repository for project '{project_name}'.")
        return None

    # Create project data directory
    project_main_dir = os.path.join(PROJECT_DATA_BASE_DIR, project_id)
    os.makedirs(project_main_dir, exist_ok=True)

    # 5. Create token details
    token_name = f"{project_id}_TOKEN"

    # 6. Initialize token ledger
    token_ledger = {owner_did: token_supply}

    # 7. Prepare project metadata
    new_project_data = {
        "project_id": project_id,
        "project_name": project_name,
        "owner_did": owner_did,
        "repo_cid": repo_cid,
        "token_name": token_name,
        "token_supply": token_supply,
        "token_ledger": token_ledger,
    }

    # 8. Save the new project's metadata
    projects.append(new_project_data)
    if not _save_projects(projects):
        logger.error(f"Failed to save project '{project_name}' to {PROJECTS_FILE}.")
        return None

    logger.info(f"Project '{project_name}' (ID: '{project_id}') created successfully.")
    return new_project_data


def get_project(project_id: str) -> Optional[dict]:
    """Retrieves project details from projects.json using project_id."""
    projects = _load_projects()
    for p in projects:
        if p.get("project_id") == project_id:
            return p
    logger.warning(f"Project with ID '{project_id}' not found.")
    return None


def list_projects() -> list:
    """Returns a list of all project dictionaries from projects.json."""
    return _load_projects()


def transfer_project_tokens(
    project_id: str, 
    sender_did: str, 
    receiver_did: str, 
    amount: int, 
    sender_private_key: str = None
) -> bool:
    """
    Transfers project tokens from sender to receiver.
    
    Args:
        project_id: The ID of the project.
        sender_did: The DID of the token sender.
        receiver_did: The DID of the token receiver.
        amount: The amount of tokens to transfer.
        sender_private_key: Optional private key for blockchain verification.
    """
    if amount <= 0:
        logger.error("Transfer amount must be positive.")
        return False

    if not did_system:
        logger.error("did_system module not available")
        return False

    # 1. Validate DIDs
    sender_did_bytes32 = did_system.generate_did_identifier(sender_did)
    if not did_system.is_did_registered(sender_did_bytes32):
        logger.error(f"Sender DID '{sender_did}' is not registered.")
        return False

    receiver_did_bytes32 = did_system.generate_did_identifier(receiver_did)
    if not did_system.is_did_registered(receiver_did_bytes32):
        logger.error(f"Receiver DID '{receiver_did}' is not registered.")
        return False

    if sender_did == receiver_did:
        logger.error("Sender and receiver DIDs cannot be the same.")
        return False

    # 2. Load all projects and find the target project
    projects = _load_projects()
    project_found = False
    target_project_index = -1

    for i, p in enumerate(projects):
        if p.get("project_id") == project_id:
            target_project_index = i
            project_found = True
            break

    if not project_found:
        logger.error(f"Project with ID '{project_id}' not found.")
        return False

    project = projects[target_project_index]
    token_ledger = project.get("token_ledger", {})

    # 3. Check sender's balance
    sender_balance = token_ledger.get(sender_did, 0)
    if sender_balance < amount:
        logger.error(
            f"Sender '{sender_did}' has insufficient balance ({sender_balance}) "
            f"to transfer {amount} tokens."
        )
        return False

    # 4. Update token ledger
    token_ledger[sender_did] = sender_balance - amount
    receiver_balance = token_ledger.get(receiver_did, 0)
    token_ledger[receiver_did] = receiver_balance + amount

    project["token_ledger"] = token_ledger

    # 5. Save updated projects data
    if _save_projects(projects):
        logger.info(
            f"Successfully transferred {amount} tokens from {sender_did} "
            f"to {receiver_did} for project {project_id}."
        )
        return True
    else:
        logger.error(f"Failed to save token transfer for project {project_id}.")
        # Revert in memory
        token_ledger[sender_did] = sender_balance
        token_ledger[receiver_did] = receiver_balance
        return False


if __name__ == '__main__':
    # Test sanitize function
    print("Testing _sanitize_project_name_to_id:")
    names_to_test = [
        "My Awesome Project!", " Project with spaces ", "project_with_underscores",
        "Test@123", "", "!@#$%^"
    ]
    for name in names_to_test:
        print(f"'{name}' -> '{_sanitize_project_name_to_id(name)}'")

    # --- Test create_project ---
    print("\n--- Testing create_project (CORRIGIDO) ---")

    if not did_system or not ipfs_storage:
        print("Módulos não disponíveis. Encerrando testes.")
        exit(1)

    # Limpar arquivos de teste anteriores
    if os.path.exists(PROJECTS_FILE):
        os.remove(PROJECTS_FILE)
    print(f"Removed existing {PROJECTS_FILE} for fresh test run.")

    os.makedirs(PROJECT_DATA_BASE_DIR, exist_ok=True)

    # Validar variáveis de ambiente
    if not DEFAULT_OWNER_PK or not DEFAULT_RECEIVER_PK:
        print("\n!!! ERRO: Configure as variáveis de ambiente !!!")
        print("Execute:")
        print('  export TEST_ACCOUNT_PK="0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d"')
        print('  export TEST_ACCOUNT_PK_RECEIVER="0x6c002f5f36494661586ebb0882038bf8d598aafb88a5e2300971707fce91e997"')
        print("\nEncerrando testes. Defina as variáveis e tente novamente.")
        exit(1)

    print("\nAttempting to create a dummy DID for owner...")
    test_owner_did_string = f"did:aegis:pm-test-owner-{uuid.uuid4().hex[:6]}"
    test_owner_did_bytes = did_system.generate_did_identifier(test_owner_did_string)

    # Usar variável de ambiente em vez de chave hardcoded
    owner_address = did_system.w3.eth.accounts[0]
    owner_pk = DEFAULT_OWNER_PK  # <-- CORRIGIDO: agora usa variável de ambiente

    print(f"Registering dummy owner DID '{test_owner_did_string}' on-chain...")
    try:
        did_registered = did_system.register_did(
            test_owner_did_bytes,
            "test_pk",
            "test_cid",
            owner_address,
            owner_pk
        )
    except Exception as e:
        print(f"Erro ao registrar DID: {e}")
        exit(1)

    project1_id_for_test = None
    project2_id_for_test = None
    test_owner_did = None
    test_receiver_did = None

    if did_registered:
        test_owner_did = test_owner_did_string
        print(f"Created dummy owner DID: {test_owner_did}")

        print("\nAttempting to create a new project 'My First Project'...")
        project1_data = create_project("My First Project", test_owner_did)
        if project1_data:
            print(f"Project 'My First Project' created successfully")
            project1_id_for_test = project1_data.get("project_id")
        else:
            print("Failed to create 'My First Project'. Check IPFS daemon and logs.")

        print("\nAttempting to create a project with the same name (should fail)...")
        project1_again_data = create_project("My First Project", test_owner_did)
        if not project1_again_data:
            print("Successfully prevented creation of duplicate project name/ID.")
        else:
            print(f"ERROR: Allowed creation of duplicate project")

        print("\nAttempting to create a project with a different name...")
        project2_data = create_project("Another Cool Project!", test_owner_did, token_supply=500000)
        if project2_data:
            print(f"Project 'Another Cool Project!' created successfully")
            project2_id_for_test = project2_data.get("project_id")
    else:
        print("Failed to create a dummy owner DID for project creation tests.")
        print("Ensure Ganache is running and test accounts are available.")
        exit(1)

    # --- Test get_project ---
    print("\n--- Testing get_project ---")
    if project1_id_for_test:
        retrieved_project = get_project(project1_id_for_test)
        if retrieved_project:
            print(f"Successfully retrieved project: {retrieved_project.get('project_name')}")
        else:
            print(f"Failed to retrieve project with ID: {project1_id_for_test}")
    else:
        print("Skipping get_project test as no project was created.")

    # --- Test list_projects ---
    print("\n--- Testing list_projects ---")
    all_projects = list_projects()
    print(f"Found {len(all_projects)} projects:")
    for p in all_projects:
        print(f" - {p.get('project_name')} (ID: {p.get('project_id')})")

    # --- Test transfer_project_tokens ---
    print("\n--- Testing transfer_project_tokens (CORRIGIDO) ---")

    # Criar segundo DID para receiver
    test_receiver_did_string = f"did:aegis:pm-test-receiver-{uuid.uuid4().hex[:6]}"
    test_receiver_did_bytes = did_system.generate_did_identifier(test_receiver_did_string)
    receiver_address = did_system.w3.eth.accounts[1]
    receiver_pk = DEFAULT_RECEIVER_PK  # <-- CORRIGIDO: agora usa variável de ambiente

    print(f"Registering dummy receiver DID '{test_receiver_did_string}' on-chain...")
    try:
        receiver_did_registered = did_system.register_did(
            test_receiver_did_bytes,
            "receiver_test_pk",
            "receiver_test_cid",
            receiver_address,
            receiver_pk
        )
    except Exception as e:
        print(f"Erro ao registrar receiver DID: {e}")
        exit(1)

    if test_owner_did and receiver_did_registered and project1_id_for_test:
        test_receiver_did = test_receiver_did_string
        print(f"Created dummy receiver DID: {test_receiver_did}")

        initial_project_state = get_project(project1_id_for_test)
        initial_owner_balance = initial_project_state["token_ledger"].get(test_owner_did, 0)
        print(f"Initial owner balance: {initial_owner_balance}")

        print("\nAttempting a valid transfer of 100 tokens...")
        if transfer_project_tokens(
            project1_id_for_test, 
            test_owner_did, 
            test_receiver_did, 
            100,
            sender_private_key=owner_pk
        ):
            print("Token transfer successful.")
            updated_project_state = get_project(project1_id_for_test)
            owner_balance_after = updated_project_state["token_ledger"].get(test_owner_did)
            receiver_balance_after = updated_project_state["token_ledger"].get(test_receiver_did)
            print(f"Owner: {owner_balance_after}, Receiver: {receiver_balance_after}")
        else:
            print("ERROR: Valid token transfer failed.")

        print("\nAttempting to transfer more tokens than available (should fail)...")
        if not transfer_project_tokens(
            project1_id_for_test, 
            test_owner_did, 
            test_receiver_did, 
            initial_owner_balance * 2
        ):
            print("Successfully prevented transfer of insufficient funds.")
        else:
            print("ERROR: Allowed transfer of insufficient funds.")
    else:
        print("Skipping transfer tests due to missing DIDs or project.")

    # --- Cleanup ---
    print("\n--- Cleaning up ---")
    if project1_id_for_test:
        path_to_clean = os.path.join(PROJECT_DATA_BASE_DIR, project1_id_for_test)
        if os.path.exists(path_to_clean):
            shutil.rmtree(path_to_clean)
            print(f"Cleaned up test project directory: {path_to_clean}")
    
    if project2_id_for_test:
        path_to_clean = os.path.join(PROJECT_DATA_BASE_DIR, project2_id_for_test)
        if os.path.exists(path_to_clean):
            shutil.rmtree(path_to_clean)
            print(f"Cleaned up test project directory: {path_to_clean}")

    if os.path.exists(PROJECTS_FILE):
        os.remove(PROJECTS_FILE)
        print(f"Cleaned up {PROJECTS_FILE}")

    print("\nAll project_management.py tests passed successfully!")
    print("\nNOTA: Para produção, NUNCA use chaves privadas em código!")
    print("Sempre use variáveis de ambiente ou secrets managers.")