# Security Policy

## Reporting a Vulnerability

We take the security of Aegis Forge seriously. If you discover a security vulnerability, please report it responsibly.

### How to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, report vulnerabilities by:

1. **Email**: Send details to the maintainers (contact information in README)
2. **Include**: 
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to Expect

- **Initial Response**: Within 48 hours
- **Status Update**: Within 5 business days
- **Resolution Timeline**: Depends on severity
  - Critical: 24-72 hours
  - High: 1 week
  - Medium: 2-4 weeks
  - Low: Next release cycle

## Security Best Practices

### For Developers

1. **Private Keys**
   - NEVER commit private keys to version control
   - Use environment variables or secure secret managers
   - The `.env` file is gitignored by default

2. **Smart Contracts**
   - Always audit contracts before deployment
   - Use established libraries (OpenZeppelin)
   - Test thoroughly on testnets before mainnet

3. **File Uploads**
   - Path traversal protection is implemented
   - File size limits are enforced
   - Only allowed directories can be accessed

4. **P2P Communications**
   - Messages are encrypted using ECIES
   - Public keys are verified via DID Registry
   - Connection timeouts prevent resource exhaustion

### For Users

1. **Development Mode**
   - Default test keys are ONLY for local development
   - Never use test accounts with real funds
   - Run Ganache only on localhost

2. **Production Deployment**
   - Set `AEGIS_ENV=production`
   - Configure proper RPC endpoints
   - Use hardware wallets for key management
   - Enable HTTPS for all communications

3. **IPFS**
   - Run IPFS daemon with appropriate access controls
   - Consider pinning services for persistence
   - Validate CIDs before retrieval

## Known Limitations

1. **Local Development Only**: This MVP is designed for local development and testing. Production deployment requires additional security measures.

2. **Test Accounts**: Default Ganache accounts should never hold real value.

3. **No Rate Limiting**: CLI commands don't have rate limiting. Implement at infrastructure level for production.

4. **Private Key Input**: CLI accepts private keys as arguments. In production, use hardware wallets or secure key management services.

## Security Checklist for Production

- [ ] Replace all test private keys
- [ ] Configure production RPC endpoints
- [ ] Enable TLS/HTTPS
- [ ] Set up proper logging and monitoring
- [ ] Implement rate limiting
- [ ] Configure firewall rules
- [ ] Set up intrusion detection
- [ ] Regular security audits
- [ ] Backup and recovery procedures
- [ ] Incident response plan

## Dependencies Security

We use the following critical dependencies:

| Dependency | Purpose | Security Notes |
|------------|---------|----------------|
| web3.py | Blockchain interaction | Keep updated for security patches |
| eciespy | P2P encryption | Audited library |
| eth-keys | Key management | Ethereum Foundation maintained |
| ipfshttpclient | IPFS integration | Verify IPFS daemon security |

## Version Support

| Version | Supported | Security Updates |
|---------|-----------|------------------|
| Current | ✅ Yes | Active |
| Previous | ⚠️ Limited | Critical only |
| Older | ❌ No | None |

Always use the latest version for security updates.

---

**Remember**: Security is a shared responsibility. Report issues responsibly and keep your systems updated.
