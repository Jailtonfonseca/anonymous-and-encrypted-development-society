# Contributing to Aegis Forge

Thank you for your interest in contributing to Aegis Forge! This document provides guidelines and instructions for contributing.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Making Changes](#making-changes)
5. [Submitting Contributions](#submitting-contributions)
6. [Coding Standards](#coding-standards)
7. [Testing](#testing)

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Welcome newcomers and help them learn
- Keep discussions professional and on-topic

## Getting Started

1. **Fork the repository**
2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/aegis-forge.git
   cd aegis-forge
   ```
3. **Set up the development environment** (see below)

## Development Setup

### Prerequisites

- Python 3.8+
- Node.js & npm (for Ganache)
- IPFS Desktop or CLI
- Git

### Installation

```bash
# Install Python dependencies
make setup

# Or manually:
pip install -r requirements.txt
cp .env.example .env
```

### Start Required Services

```bash
# Terminal 1: Start Ganache
ganache

# Terminal 2: Start IPFS
ipfs daemon
```

### Verify Setup

```bash
make test
```

## Making Changes

### Branch Naming Convention

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation changes
- `refactor/description` - Code refactoring
- `test/description` - Test additions/modifications

### Commit Message Format

```
type(scope): subject

body (optional)

footer (optional)
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Example:
```
feat(did): add batch registration support

Added ability to register multiple DIDs in a single transaction.
This reduces gas costs for bulk operations.

Closes #123
```

## Submitting Contributions

### Pull Request Process

1. **Update documentation** if changing functionality
2. **Add tests** for new features
3. **Ensure all tests pass**: `make test`
4. **Run linter**: `make lint`
5. **Update CHANGELOG.md** (if applicable)
6. **Submit PR** with clear description

### PR Checklist

- [ ] Code follows style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No new warnings
- [ ] Changelog updated (if needed)

## Coding Standards

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with these specifics:

- **Line length**: 100 characters max
- **Indentation**: 4 spaces
- **Imports**: Grouped and sorted
- **Type hints**: Encouraged for function signatures

### Code Organization

```python
# Standard library imports
import os
from pathlib import Path

# Third-party imports
import click
from web3 import Web3

# Local imports
from config import BASE_DIR
from did_system import generate_did_identifier
```

### Security Guidelines

1. **Never commit secrets**: Use environment variables
2. **Validate all inputs**: Especially file paths and user data
3. **Use established libraries**: Don't roll your own crypto
4. **Follow principle of least privilege**

### Example: Secure File Handling

```python
from pathlib import Path

def validate_file_path(user_path: str, base_dir: Path) -> Path | None:
    """Validate and sanitize file path to prevent path traversal."""
    try:
        resolved = Path(user_path).resolve()
        resolved.relative_to(base_dir.resolve())
        return resolved if resolved.is_file() else None
    except (ValueError, OSError):
        return None
```

## Testing

### Running Tests

```bash
# All tests
make test

# With coverage
make test-cov

# Single test file
make test-single FILE=test_config.py
```

### Writing Tests

```python
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
import module_to_test


class TestFeature:
    """Test suite for specific feature."""
    
    def test_happy_path(self):
        """Test normal operation."""
        result = module_to_test.function(input)
        assert result == expected
    
    def test_edge_case(self):
        """Test edge cases."""
        with pytest.raises(ExpectedException):
            module_to_test.function(invalid_input)
```

### Test Coverage Goals

- **Overall**: > 80%
- **Critical modules**: > 90%
  - `did_system.py`
  - `contribution_workflow.py`
  - `p2p_messaging.py`

## Areas Needing Contribution

### High Priority

- [ ] Smart contract security audits
- [ ] Integration tests
- [ ] Docker deployment scripts
- [ ] CI/CD pipeline configuration

### Medium Priority

- [ ] Web frontend
- [ ] Enhanced P2P discovery
- [ ] Mobile wallet integration
- [ ] Multi-language support

### Good First Issues

Look for issues labeled:
- `good first issue`
- `help wanted`
- `documentation`

## Questions?

- **General questions**: Open a GitHub Discussion
- **Bug reports**: Use GitHub Issues
- **Security issues**: See SECURITY.md

## Recognition

Contributors are recognized in:
- README.md contributors section
- Release notes
- Annual contributor highlights

---

Thank you for contributing to Aegis Forge! 🎉
