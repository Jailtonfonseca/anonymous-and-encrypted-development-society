"""Tests for the configuration module."""
import pytest
from pathlib import Path

# Import config module
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import config


class TestConfiguration:
    """Test configuration settings."""
    
    def test_base_dir_exists(self):
        """Test that base directory is properly set."""
        assert config.BASE_DIR.exists()
        assert config.BASE_DIR.is_absolute()
    
    def test_project_data_dir(self):
        """Test that project data directory is configured."""
        assert config.PROJECT_DATA_BASE_DIR == config.BASE_DIR / "project_data"
    
    def test_ganache_url_default(self):
        """Test default Ganache URL."""
        assert config.GANACHE_URL == "http://127.0.0.1:8545"
    
    def test_contract_files_defined(self):
        """Test that contract file paths are defined."""
        assert config.DID_REGISTRY_ABI_FILE.name == "DIDRegistry.abi.json"
        assert config.AEGIS_TOKEN_ABI_FILE.name == "AegisToken.abi.json"
    
    def test_validate_environment_development(self):
        """Test environment validation in development mode."""
        result = config.validate_environment()
        assert "success" in result
        assert "errors" in result
        assert "warnings" in result
    
    def test_default_test_accounts(self):
        """Test that default test accounts are configured."""
        assert len(config.DEFAULT_TEST_ACCOUNTS) >= 3
        assert "address" in config.DEFAULT_TEST_ACCOUNTS[0]
        assert "private_key" in config.DEFAULT_TEST_ACCOUNTS[0]
