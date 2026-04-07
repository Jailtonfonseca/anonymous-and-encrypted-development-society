"""Security-related tests."""
import pytest
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPathValidation:
    """Test path validation and security."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures."""
        try:
            import contribution_workflow
            self.contribution_workflow = contribution_workflow
        except ImportError:
            pytest.skip("contribution_workflow module not available")
    
    def test_validate_safe_path(self):
        """Test that safe paths are accepted."""
        # Create a temporary test file
        test_file = Path(__file__).parent / "test_file.txt"
        test_file.write_text("test content")
        
        try:
            result = self.contribution_workflow._validate_and_sanitize_path(
                str(test_file),
                base_dir=str(Path(__file__).parent)
            )
            assert result is not None
            assert Path(result).exists()
        finally:
            test_file.unlink(missing_ok=True)
    
    def test_block_path_traversal(self):
        """Test that path traversal attacks are blocked."""
        malicious_path = "../../../etc/passwd"
        result = self.contribution_workflow._validate_and_sanitize_path(
            malicious_path,
            base_dir=str(Path(__file__).parent)
        )
        assert result is None
    
    def test_block_nonexistent_file(self):
        """Test that non-existent files are rejected."""
        result = self.contribution_workflow._validate_and_sanitize_path(
            "/nonexistent/path/file.txt",
            base_dir=str(Path(__file__).parent)
        )
        assert result is None
