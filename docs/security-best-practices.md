# Security Best Practices

## Overview
Security is critical for PyBase, especially given its role in handling engineering data and CAD files. This document outlines essential security practices to protect credentials, data, and infrastructure.

## Credential Management

### 1. Never Commit .env Files
**CRITICAL:** Never commit `.env` files or any files containing real credentials to version control.

```bash
# .gitignore should always include:
.env
.env.local
.env.*.local
*.key
*.pem
credentials.json
secrets/
```

**Why:** Even if `.env` is in `.gitignore`, accidental commits can expose production credentials. Once committed, credentials remain in git history even after removal.

**What to do instead:**
- Use `.env.example` as a template with placeholder values
- Store real credentials in environment variables or secret management systems
- Use `git diff --cached` to review staged files before committing
- Run pre-commit hooks to detect secrets (see [Secrets Scanning](#secrets-scanning))

### 2. Use Environment Variables in Production
Always use environment variables for sensitive configuration in production deployments.

**Development:**
```bash
# .env file is acceptable for local development
DATABASE_URL=postgresql+asyncpg://pybase:pybase@localhost:5432/pybase
SECRET_KEY=development-key-only
```

**Production:**
```bash
# Set environment variables in your deployment platform
export DATABASE_URL="postgresql+asyncpg://user:STRONG_PASSWORD@host:5432/db"
export SECRET_KEY="$(openssl rand -hex 32)"
```

**Deployment Platforms:**
- **Docker:** Use `--env-file` or Docker secrets
- **Kubernetes:** Use Secret objects (not ConfigMap for secrets)
- **AWS:** Use Systems Manager Parameter Store or Secrets Manager
- **GCP:** Use Secret Manager
- **Azure:** Use Key Vault

**Configuration Validation:**
PyBase's `config.py` validates that production environments don't use placeholder values:

```python
# src/pybase/core/config.py automatically rejects insecure values:
# - 'localhost' in DATABASE_URL
# - 'change-this' or 'placeholder' in any credential
# - Default/minioadmin for S3 credentials
```

### 3. Rotate Compromised Credentials Immediately
If credentials are exposed or suspected to be compromised, rotate them immediately.

**When to Rotate:**
- Credentials committed to version control
- Credentials found in logs or error messages
- Suspicious activity in access logs
- Team member with access leaves the project
- Periodic rotation (recommended every 90 days for high-privilege accounts)

**Rotation Process:**
1. **Generate new credentials**
   ```bash
   # Example: Generate new database password
   openssl rand -base64 32
   ```

2. **Update in production first**
   - Update environment variables in your deployment platform
   - Restart services to load new credentials
   - Verify connectivity with new credentials

3. **Update development environments**
   - Update `.env` files for local/staging environments
   - Ensure all developers update their local configurations

4. **Invalidate old credentials**
   - Change passwords in database consoles
   - Delete old API keys in cloud provider consoles
   - Revoke old certificates

5. **Monitor for access failures**
   - Check logs for any systems still using old credentials
   - Investigate failed authentication attempts

**Incident Response:**
If credentials were committed to a public repository:
1. Assume credentials are compromised
2. Rotate immediately (don't wait)
3. Review access logs for unauthorized activity
4. Consider rotating all credentials (credentials often stored together)
5. Document the incident (see [Security Incidents](#security-incidents))

### 4. Use Different Credentials Per Environment
Never use the same credentials across development, staging, and production environments.

**Environment Isolation:**
```bash
# Development
DATABASE_URL=postgresql://dev_user:dev_pass@localhost:5432/pybase_dev
S3_BUCKET=pybase-dev-files

# Staging
DATABASE_URL=postgresql://stage_user:stage_pass@stage-db.example.com:5432/pybase_stage
S3_BUCKET=pybase-staging-files

# Production
DATABASE_URL=postgresql://prod_user:STRONG_PASS@prod-db.example.com:5432/pybase_prod
S3_BUCKET=pybase-production-files
```

**Benefits:**
- **Accidental data prevention:** Dev code can't accidentally modify production data
- **Testing:** Staging uses production-like configuration without risk
- **Blast radius:** Compromise of one environment doesn't expose others
- **Access control:** Developers don't need production credentials for daily work

**Access Levels:**
- **Development:** Local databases with minimal security
- **Staging:** Separate production-like credentials with reduced privileges
- **Production:** Strongest credentials, limited to essential personnel

**Cloud Provider Separation:**
- Use separate AWS/GCP/Azure accounts or projects per environment
- Use different IAM roles with least-privilege access
- Implement cross-account guards where possible

## Secrets Scanning

### Pre-Commit Hooks
PyBase uses pre-commit hooks to automatically scan for secrets before commits:

```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Hooks configured in .pre-commit-config.yaml:
# - trufflehog: Scans for 600+ secret types
# - detect-secrets: Detects high-entropy strings
```

### Manual Scanning
Run the secrets validation script manually:

```bash
# Quick check of current changes
python scripts/utils/validate_secrets.py --check

# Comprehensive scan of all files
python scripts/utils/validate_secrets.py --scan-all

# Strict mode (fails on placeholders too)
python scripts/utils/validate_secrets.py --scan-all --strict

# Verbose output
python scripts/utils/validate_secrets.py --scan-all --verbose
```

### What Gets Detected
The script scans for:
- **Critical secrets:** Neon database passwords, B2 application keys, known production hosts
- **Generic patterns:** API keys, tokens, passwords in URLs, private keys
- **Placeholders:** CHANGE_ME, placeholder values (in strict mode)

## Additional Security Measures

### Database Security
- **Strong passwords:** Use minimum 32-character random passwords
- **SSL connections:** Force SSL for database connections in production
- **Network restrictions:** Whitelist backend IP addresses only
- **Regular backups:** Enable automated backups with point-in-time recovery
- **Least privilege:** Use read-only replicas for reporting workloads

### API Security
- **SECRET_KEY:** Use cryptographically random keys (minimum 32 bytes)
- **HTTPS only:** Redirect HTTP to HTTPS in production
- **Rate limiting:** Implement rate limiting on authentication endpoints
- **CORS:** Restrict CORS to specific origins only
- **Input validation:** Validate all user input with Pydantic schemas

### Storage Security
- **S3 bucket policies:** restrict access to specific IAM roles only
- **Encryption:** Enable server-side encryption for all stored files
- **Signed URLs:** Use temporary signed URLs for file access, not public URLs
- **File validation:** Validate file types and scan for malware on upload

### Dependency Security
- **Regular updates:** Keep dependencies updated to patch vulnerabilities
- **Vendoring:** Review third-party code before integrating
- **SCA scanning:** Use tools like `pip-audit` or `safety` to scan for vulnerabilities
  ```bash
  pip-audit
  safety check --file requirements.txt
  ```

## Security Incidents

### Incident Response Process
If a security incident occurs (e.g., credentials exposed):

1. **Contain** - Stop the bleeding
   - Rotate compromised credentials immediately
   - Disable affected accounts
   - Revoke exposed API keys

2. **Assess** - Understand the impact
   - Review access logs for suspicious activity
   - Identify what data was accessible
   - Determine time window of exposure

3. **Remediate** - Fix the root cause
   - Add validation/prevention measures
   - Update security documentation
   - Patch vulnerabilities

4. **Document** - Learn from the incident
   - Create incident report (see template below)
   - Update security practices
   - Train team on lessons learned

### Incident Report Template
Document security incidents using this structure:

```markdown
# Security Incident Report

## Incident Summary
[Brief description of what happened]

## Timeline
- **Discovered:** [Date/time]
- **Occurred:** [Date/time range]
- **Resolved:** [Date/time]

## Impact
- **Exposed credentials:** [Which credentials]
- **Data accessed:** [What data was accessible]
- **Systems affected:** [Which systems]

## Root Cause
[Why did this happen?]

## Remediation Steps
1. [Step 1]
2. [Step 2]
...

## Prevention Measures
[What changes were made to prevent recurrence]
```

## Compliance Considerations

### Data Protection
- **GDPR:** Implement right-to-deletion, data export, and consent management
- **SOC 2:** Maintain access logs, audit trails, and security policies
- **HIPAA:** (If handling healthcare data) Encrypt data at rest and in transit

### Audit Logging
- **Access logs:** Log all authentication attempts and access to sensitive data
- **Change logs:** Track modifications to security settings and credentials
- **Retention:** Maintain logs for minimum 90 days (longer for compliance)

### Penetration Testing
- **Regular testing:** Conduct penetration tests at least annually
- **Dependency scanning:** Scan for vulnerabilities in dependencies
- **Code review:** Have security-focused code reviews for sensitive features

## Security Checklist

Use this checklist when deploying or auditing PyBase:

- [ ] `.env` files are in `.gitignore` and never committed
- [ ] Production uses environment variables, not `.env` files
- [ ] Different credentials for dev/staging/production
- [ ] Strong, random passwords (minimum 32 characters)
- [ ] Pre-commit hooks installed and running
- [ ] Secrets scan passes with no findings
- [ ] SSL/TLS enabled for all external connections
- [ ] Database access restricted to backend IPs only
- [ ] S3 buckets are not publicly accessible
- [ ] SECRET_KEY is unique per environment
- [ ] Dependencies are up-to-date and scanned for vulnerabilities
- [ ] Access logs are enabled and monitored
- [ ] Incident response plan is documented

---

**Remember:** Security is an ongoing process, not a one-time setup. Regular audits, updates, and team training are essential to maintaining a secure deployment.
