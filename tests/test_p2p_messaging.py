"""Tests for P2P messaging module."""
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestP2PMessaging:
    """Test P2P messaging functionality."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures."""
        try:
            import p2p_messaging
            self.p2p_messaging = p2p_messaging
        except ImportError:
            pytest.skip("p2p_messaging module not available")
    
    def test_get_hex_public_key_from_private(self):
        """Test public key derivation from private key."""
        # Use a known test private key
        test_pk = "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d"
        result = self.p2p_messaging.get_hex_public_key_from_private(test_pk)
        
        assert result is not None
        assert result.startswith("0x04")  # Uncompressed public key prefix
        # 0x04 (2 chars) + 64 bytes hex (128 chars) = 130 or 132 chars depending on implementation
        assert len(result) in [130, 132]  # Allow for slight variations
    
    def test_invalid_private_key(self):
        """Test handling of invalid private key."""
        result = self.p2p_messaging.get_hex_public_key_from_private("invalid_key")
        assert result is None
