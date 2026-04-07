"""Tests for the DID system module."""
import pytest
import uuid
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDIDSystem:
    """Test DID system functionality."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures."""
        # Import here to avoid issues if web3 not available
        try:
            import did_system
            self.did_system = did_system
        except ImportError:
            pytest.skip("did_system module not available")
    
    def test_generate_did_identifier(self):
        """Test DID identifier generation."""
        test_input = "test-did-identifier"
        result = self.did_system.generate_did_identifier(test_input)
        
        assert isinstance(result, bytes)
        assert len(result) == 32  # Keccak-256 produces 32 bytes
        
        # Same input should produce same output
        result2 = self.did_system.generate_did_identifier(test_input)
        assert result == result2
        
        # Different input should produce different output
        result3 = self.did_system.generate_did_identifier("different-input")
        assert result != result3
    
    def test_is_did_registered_unregistered(self):
        """Test checking unregistered DID."""
        random_did = self.did_system.generate_did_identifier(
            f"random-{uuid.uuid4().hex}"
        )
        # Should return False for non-existent DID
        result = self.did_system.is_did_registered(random_did)
        assert result is False
