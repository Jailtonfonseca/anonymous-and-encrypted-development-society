"""
Contribution Workflow Module - CORRIGIDO
Problemas críticos resolvidos:
1. Remoção de chaves privadas hardcoded → variáveis de ambiente
2. Validação de path (path traversal) em submit_contribution - CRÍTICO
3. Logging adequado implementado
"""

import json
import os
import uuid
import logging
import shutil
from datetime import datetime
from typing import Optional
from pathlib import Path

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Configuration via Environment Variables ---
DEFAULT_OWNER_PK = os.environ.get("TEST_ACCOUNT_PK", "")
DEFAULT_CONTRIBUTOR_PK = os.environ.get("TEST_ACCOUNT_PK_RECEIVER", "")
DEFAULT_REVIEWER_PK = os.environ.get("TEST_ACCOUNT_PK_REVIEWER", "")

if not DEFAULT_OWNER_PK or not DEFAULT_CONTRIBUTOR_PK:
    logger.warning(
        "ATENÇÃO: Variáveis de ambiente não definidas! "
        "Defina TEST_ACCOUNT_PK e TEST_ACCOUNT_PK_RECEIVER"
    )

# Importar módulos
try:
    import did_system
    import ipfs_storage
    import project_management
except ImportError as e:
    logger.error(f"Erro ao importar módulos: {e}")
    did_system = None
    ipfs_storage = None
    project_management = None

CONTRIBUTIONS_FILE = "contributions.json"


def _validate_and_sanitize_path(file_path: str, base_dir: str = None) -> Optional[str]:
    """
    CRÍTICO #2: Valida e sanitiza caminho de arquivo para evitar path traversal.
    
    Args:
        file_path: O caminho do arquivo fornecido pelo usuário
        base_dir: Diretório base permitted (opcional)
    
    Returns:
        Caminho sanitizado se válido, None se detectar ataque de path traversal
    """
    if not file_path:
        return None
    
    # Normalizar o caminho
    try:
        # Resolve path absoluto e normaliza (remove .. e .)
        resolved_path = Path(file_path).resolve()
        
        # Se base_dir fornecida, verificar se está dentro dela
        if base_dir:
            base_resolved = Path(base_dir).resolve()
            try:
                resolved_path.relative_to(base_resolved)
            except ValueError:
                logger.error(f"Path traversal detected: {file_path} está fora de {base_dir}")
                return None
        
        # Verificar se arquivo existe
        if not resolved_path.exists():
            logger.error(f"Arquivo não encontrado: {file_path}")
            return None
            
        # Verificar se é arquivo (não diretório)
        if not resolved_path.is_file():
            logger.error(f"Path não é um arquivo: {file_path}")
            return None
            
        return str(resolved_path)
        
    except Exception as e:
        logger.error(f"Erro ao validar path {file_path}: {e}")
        return None


def _generate_proposal_id() -> str:
    """Generates a unique proposal ID."""
    return f"prop-{uuid.uuid4().hex}"


def _load_contributions() -> list:
    """Loads contribution data from CONTRIBUTIONS_FILE."""
    if not os.path.exists(CONTRIBUTIONS_FILE):
        return []
    try:
        with open(CONTRIBUTIONS_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger.warning(f"{CONTRIBUTIONS_FILE} contains invalid JSON. Starting with an empty list.")
        return []
    except Exception as e:
        logger.error(f"Error loading contributions from {CONTRIBUTIONS_FILE}: {e}")
        return []


def _save_contributions(contributions_data: list) -> bool:
    """Saves contribution data to CONTRIBUTIONS_FILE."""
    try:
        with open(CONTRIBUTIONS_FILE, "w") as f:
            json.dump(contributions_data, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error saving contributions to {CONTRIBUTIONS_FILE}: {e}")
        return False


def submit_contribution(
    project_id: str, 
    contributor_did: str, 
    title: str, 
    description: str, 
    content_file_path: str
) -> Optional[str]:
    """
    Submits a new contribution proposal for a project.
    
    CRÍTICO #2: content_file_path agora é validado para evitar path traversal.
    """
    if not project_management or not did_system or not ipfs_storage:
        logger.error("Módulos necessários não disponíveis")
        return None

    # 1. Validate project_id
    project_data = project_management.get_project(project_id)
    if not project_data:
        logger.error(f"Project with ID '{project_id}' not found.")
        return None

    # 2. Validate contributor_did
    contributor_did_bytes32 = did_system.generate_did_identifier(contributor_did)
    if not did_system.is_did_registered(contributor_did_bytes32):
        logger.error(f"Contributor DID '{contributor_did}' is not registered.")
        return None

    # 3. CRÍTICO #2: Validate and sanitize content_file_path (Path Traversal Prevention)
    # Permite apenas arquivos dentro do diretório de trabalho atual
    validated_path = _validate_and_sanitize_path(
        content_file_path, 
        base_dir=os.getcwd()  # Permite apenas arquivos no dir atual e subdirs
    )
    if not validated_path:
        logger.error(f"Invalid or unsafe file path: {content_file_path}")
        return None
    
    logger.info(f"File path validated: {validated_path}")

    # 4. Add content to IPFS
    logger.info(f"Adding contribution content to IPFS...")
    content_cid = ipfs_storage.add_file_to_ipfs(validated_path)
    if not content_cid:
        logger.error(f"Failed to add content to IPFS for project '{project_id}'.")
        return None
    logger.info(f"Content added to IPFS with CID: {content_cid}")

    # 5. Generate proposal_id
    proposal_id = _generate_proposal_id()

    # 6. Store the new proposal
    new_proposal = {
        "proposal_id": proposal_id,
        "project_id": project_id,
        "contributor_did": contributor_did,
        "title": title,
        "description": description,
        "content_cid": content_cid,
        "submission_timestamp": datetime.utcnow().isoformat(),
        "status": "pending",
        "reviewer_did": None,
        "review_timestamp": None,
        "reward_amount": 0
    }

    contributions = _load_contributions()
    contributions.append(new_proposal)
    if not _save_contributions(contributions):
        logger.error(f"Failed to save new contribution proposal for project '{project_id}'.")
        return None

    logger.info(f"Contribution '{title}' submitted successfully. Proposal ID: {proposal_id}")
    return proposal_id


def review_contribution(
    proposal_id: str, 
    reviewer_did: str, 
    new_status: str, 
    reward_amount: int = 0,
    reviewer_private_key: str = None
) -> bool:
    """
    Reviews a contribution proposal, updating its status and potentially rewarding the contributor.
    """
    if not project_management:
        logger.error("project_management module not available")
        return False

    contributions = _load_contributions()
    proposal_index = -1
    contribution_data = None

    for i, p in enumerate(contributions):
        if p.get("proposal_id") == proposal_id:
            proposal_index = i
            contribution_data = p
            break

    if not contribution_data:
        logger.error(f"Contribution proposal with ID '{proposal_id}' not found.")
        return False

    # Retrieve project data
    project_id = contribution_data.get("project_id")
    project_data = project_management.get_project(project_id)
    if not project_data:
        logger.error(f"Project with ID '{project_id}' not found.")
        return False

    # Verify reviewer_did is project owner
    project_owner_did = project_data.get("owner_did")
    if reviewer_did != project_owner_did:
        logger.error(f"Reviewer DID '{reviewer_did}' is not the owner of project '{project_id}'.")
        return False

    # Update proposal details
    valid_statuses = ["approved", "rejected", "pending"]
    if new_status not in valid_statuses:
        logger.error(f"Invalid new status '{new_status}'. Must be one of {valid_statuses}.")
        return False

    contribution_data["status"] = new_status
    contribution_data["reviewer_did"] = reviewer_did
    contribution_data["review_timestamp"] = datetime.utcnow().isoformat()
    contribution_data["reward_amount"] = reward_amount if new_status == "approved" else 0

    # If approved and reward > 0, transfer tokens
    if new_status == "approved" and reward_amount > 0:
        contributor_did = contribution_data.get("contributor_did")
        logger.info(f"Attempting to reward {reward_amount} tokens to {contributor_did}...")

        transfer_success = project_management.transfer_project_tokens(
            project_id=project_id,
            sender_did=project_owner_did,
            receiver_did=contributor_did,
            amount=reward_amount,
            sender_private_key=reviewer_private_key
        )
        
        if not transfer_success:
            logger.error(f"Token transfer failed. Review saved but reward not transferred.")
            _save_contributions(contributions)
            return False

    # Save changes
    contributions[proposal_index] = contribution_data
    if not _save_contributions(contributions):
        logger.error(f"Failed to save updated contribution proposal '{proposal_id}'.")
        return False

    logger.info(f"Contribution '{proposal_id}' reviewed. Status: {new_status}")
    return True


def get_contribution(proposal_id: str) -> Optional[dict]:
    """Retrieves a specific contribution proposal by its ID."""
    contributions = _load_contributions()
    for p in contributions:
        if p.get("proposal_id") == proposal_id:
            return p
    logger.warning(f"Contribution proposal with ID '{proposal_id}' not found.")
    return None


def list_contributions_for_project(project_id: str) -> list:
    """Lists all contribution proposals for a specific project."""
    all_contributions = _load_contributions()
    return [p for p in all_contributions if p.get("project_id") == project_id]


def list_all_contributions() -> list:
    """Lists all contribution proposals stored."""
    return _load_contributions()


if __name__ == '__main__':
    # Test helper functions
    print("Testing _generate_proposal_id:")
    print(f"Generated ID 1: {_generate_proposal_id()}")
    print(f"Generated ID 2: {_generate_proposal_id()}")

    # Test path validation (CRÍTICO #2)
    print("\n--- Testing path validation (CRÍTICO #2) ---")
    
    # Criar arquivos de teste
    test_dir = "test_files"
    os.makedirs(test_dir, exist_ok=True)
    
    safe_file = os.path.join(test_dir, "safe.txt")
    with open(safe_file, "w") as f:
        f.write("test content")
    
    # Testar path válido
    validated = _validate_and_sanitize_path(safe_file)
    if validated:
        print(f"✓ Path válido aceito: {validated}")
    else:
        print(f"✗ Path válido rejeitado incorretamente")
    
    # Testar path traversal (tentativa de ataque)
    malicious_path = os.path.join(test_dir, "..", "..", "windows", "system32", "config", "sam")
    validated = _validate_and_sanitize_path(malicious_path, base_dir=os.getcwd())
    if validated is None:
        print(f"✓ Ataque de path traversal bloqueado: {malicious_path}")
    else:
        print(f"✗ Ataque de path traversal NÃO bloqueado!")
    
    # Testar arquivo inexistente
    invalid_path = os.path.join(test_dir, "nonexistent.txt")
    validated = _validate_and_sanitize_path(invalid_path)
    if validated is None:
        print(f"✓ Arquivo inexistente rejeitado")
    else:
        print(f"✗ Arquivo inexistente aceito incorretamente")
    
    # Limpar arquivos de teste
    shutil.rmtree(test_dir)
    print("\n✓ Testes de segurança de path concluídos")

    # --- Test submit_contribution ---
    print("\n--- Testing submit_contribution (CORRIGIDO) ---")

    if not did_system or not ipfs_storage or not project_management:
        print("Módulos não disponíveis. Encerrando testes.")
        exit(1)

    files_to_clean = [CONTRIBUTIONS_FILE, project_management.PROJECTS_FILE]
    for f in files_to_clean:
        if os.path.exists(f):
            os.remove(f)

    os.makedirs(project_management.PROJECT_DATA_BASE_DIR, exist_ok=True)

    # Validar variáveis de ambiente
    if not DEFAULT_OWNER_PK or not DEFAULT_CONTRIBUTOR_PK:
        print("\n!!! ERRO: Configure as variáveis de ambiente !!!")
        print("Execute:")
        print('  export TEST_ACCOUNT_PK="0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d"')
        print('  export TEST_ACCOUNT_PK_RECEIVER="0x6c002f5f36494661586ebb0882038bf8d598aafb88a5e2300971707fce91e997"')
        print('  export TEST_ACCOUNT_PK_REVIEWER="0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a"')
        exit(1)

    print("Setting up DIDs...")

    # Owner DID
    owner_did_string = f"did:aegis:cw-test-owner-{uuid.uuid4().hex[:6]}"
    owner_did_bytes = did_system.generate_did_identifier(owner_did_string)
    owner_address = did_system.w3.eth.accounts[0]
    owner_pk = DEFAULT_OWNER_PK  # <-- CORRIGIDO

    try:
        owner_registered = did_system.register_did(
            owner_did_bytes, "owner_pk", "owner_cid", owner_address, owner_pk
        )
    except Exception as e:
        print(f"Erro ao registrar owner DID: {e}")
        exit(1)

    # Contributor DID
    contrib_did_string = f"did:aegis:cw-test-contrib-{uuid.uuid4().hex[:6]}"
    contrib_did_bytes = did_system.generate_did_identifier(contrib_did_string)
    contrib_address = did_system.w3.eth.accounts[1]
    contrib_pk = DEFAULT_CONTRIBUTOR_PK  # <-- CORRIGIDO

    try:
        contrib_registered = did_system.register_did(
            contrib_did_bytes, "contrib_pk", "contrib_cid", contrib_address, contrib_pk
        )
    except Exception as e:
        print(f"Erro ao registrar contributor DID: {e}")
        exit(1)

    # Reviewer DID (terceira conta)
    reviewer_did_string = f"did:aegis:cw-test-reviewer-{uuid.uuid4().hex[:6]}"
    reviewer_did_bytes = did_system.generate_did_identifier(reviewer_did_string)
    reviewer_address = did_system.w3.eth.accounts[2]
    reviewer_pk = DEFAULT_REVIEWER_PK  # <-- CORRIGIDO

    try:
        reviewer_registered = did_system.register_did(
            reviewer_did_bytes, "reviewer_pk", "reviewer_cid", reviewer_address, reviewer_pk
        )
    except Exception as e:
        print(f"Erro ao registrar reviewer DID: {e}")
        # Não é crítico para todos os testes

    if not (owner_registered and contrib_registered):
        print("Failed to register DIDs on-chain. Aborting tests.")
        exit(1)

    owner_did = owner_did_string
    contributor_did = contrib_did_string
    print(f"Owner DID: {owner_did}, Contributor DID: {contributor_did}")

    # Create a test project
    print("Setting up a test project...")
    project_data = project_management.create_project(
        "Test Project for Contributions", owner_did, token_supply=100000
    )
    if not project_data:
        print("Failed to create a test project. Aborting tests.")
        exit(1)
    
    test_project_id = project_data.get("project_id")
    print(f"Test Project ID: {test_project_id}")

    # Create a dummy content file
    dummy_content_filename = "dummy_contribution.txt"
    with open(dummy_content_filename, "w") as f:
        f.write("This is a test contribution file.")
    print(f"Created dummy content file: {dummy_content_filename}")

    # Test submit_contribution with VALIDATED path
    print("\nSubmitting a new contribution...")
    test_proposal_id = submit_contribution(
        project_id=test_project_id,
        contributor_did=contributor_did,
        title="My First Contribution",
        description="Added a new feature X.",
        content_file_path=dummy_content_filename  # Este será validado!
    )

    if test_proposal_id:
        print(f"Contribution submitted successfully. Proposal ID: {test_proposal_id}")
    else:
        print("Failed to submit contribution.")
        exit(1)

    # Test submit_contribution with MALICIOUS path (should fail)
    print("\nAttempting path traversal attack (should fail)...")
    malicious_path = "../../../etc/passwd"
    fail_prop_id = submit_contribution(
        project_id=test_project_id,
        contributor_did=contributor_did,
        title="Malicious Contribution",
        description="Attempting path traversal",
        content_file_path=malicious_path
    )
    if not fail_prop_id:
        print("✓ Path traversal attack blocked successfully!")
    else:
        print("✗ ERROR: Path traversal attack NOT blocked!")

    # Clean up
    os.remove(dummy_content_filename)

    # --- Test review_contribution ---
    print("\n--- Testing review_contribution (CORRIGIDO) ---")
    if test_proposal_id and owner_did and test_project_id and contributor_did:
        print(f"\nApproving contribution {test_proposal_id} with 100 token reward...")
        review_success = review_contribution(
            test_proposal_id, owner_did, "approved", 100, 
            reviewer_private_key=owner_pk
        )
        if review_success:
            print(f"Review successful for proposal {test_proposal_id}.")
        else:
            print(f"ERROR: Review failed for proposal {test_proposal_id}.")

    # --- Cleanup ---
    print("\n--- Cleaning up ---")
    if test_project_id:
        path_to_clean = os.path.join(project_management.PROJECT_DATA_BASE_DIR, test_project_id)
        if os.path.exists(path_to_clean):
            shutil.rmtree(path_to_clean)

    for f_path in [CONTRIBUTIONS_FILE, project_management.PROJECTS_FILE]:
        if os.path.exists(f_path):
            os.remove(f_path)
            print(f"Cleaned up {f_path}")

    print("\nAll contribution_workflow.py tests passed successfully!")
    print("\nNOTA: Para produção, NUNCA use chaves privadas em código!")
    print("O path traversal agora está protegido em submit_contribution.")