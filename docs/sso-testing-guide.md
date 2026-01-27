# SSO Testing Guide

This guide provides comprehensive instructions for testing the Single Sign-On (SSO) integration in PyBase, including both SAML 2.0 and OpenID Connect (OIDC) protocols.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Test Types](#test-types)
- [Setting Up a Test SAML IdP](#setting-up-a-test-saml-idp)
- [Running Integration Tests](#running-integration-tests)
- [Running E2E Tests](#running-e2e-tests)
- [Test Coverage](#test-coverage)
- [Troubleshooting](#troubleshooting)

## Overview

The SAML SSO testing suite includes:

1. **Integration Tests** (`tests/api/v1/test_saml_api.py`)
   - Backend API endpoint testing
   - Mock SAML responses for fast, reliable tests
   - No external IdP required
   - Tests all SAML flows and error cases

2. **E2E Tests** (`frontend/e2e/saml-auth-flow.spec.ts`)
   - Full browser-based testing with Playwright
   - Tests complete authentication flow
   - Requires a real SAML IdP (or mock IdP)
   - Tests frontend components and user interactions

## Prerequisites

### For Integration Tests

```bash
# Python dependencies
pip install -e ".[test]"

# Database running (PostgreSQL)
export DATABASE_URL="postgresql://user:pass@localhost/pybase_test"

# Backend configuration
export SSO_ENABLED=true
```

### For E2E Tests

```bash
# Node.js dependencies
cd frontend
npm install

# Playwright browsers
npx playwright install chromium
```

### For Testing with Real IdP

You'll need a test SAML IdP. Options:

1. **Okta Developer Account** (Recommended - Free)
2. **Azure AD Test Tenant**
3. **Auth0 Developer Account**
4. **Mock SAML IdP** (e.g., SAML-Test-IDP)

## Test Types

### 1. Integration Tests

Fast, isolated tests that mock SAML responses. No external IdP needed.

**Location:** `tests/api/v1/test_saml_api.py`

**Run command:**
```bash
# Run all SAML integration tests
pytest tests/api/v1/test_saml_api.py -v

# Run specific test
pytest tests/api/v1/test_saml_api.py::test_saml_metadata_returns_xml -v

# Run with coverage
pytest tests/api/v1/test_saml_api.py --cov=src/pybase/api/v1/saml --cov-report=html
```

**What it tests:**
- SAML metadata endpoint returns valid XML
- SAML login initiation redirects correctly
- SAML callback processes responses
- JIT user provisioning works
- User identity linking works
- Error handling for invalid responses
- Authentication and authorization

### 2. E2E Tests

Full browser tests that verify the complete user flow.

**Location:** `frontend/e2e/saml-auth-flow.spec.ts`

**Run command:**
```bash
cd frontend

# Run all SAML E2E tests
npm run test:e2e -- saml-auth-flow

# Run specific test
npx playwright test saml-auth-flow.spec.ts -g "should display SSO login button"

# Run with UI
npx playwright test --ui
```

**What it tests:**
- SSO login button visible on login page
- Click redirects to IdP
- IdP authentication flow
- Callback processing
- JWT token storage
- User redirected to dashboard
- Error handling

## Setting Up a Test SAML IdP

### Option 1: Okta Developer Account (Recommended)

1. **Create Okta Developer Account**
   - Go to https://developer.okta.com/signup/
   - Sign up for free developer account

2. **Create SAML Application**
   - Log in to Okta Admin Console
   - Go to Applications → Applications
   - Click "Create App Integration"
   - Select "SAML 2.0"
   - App name: "PyBase Test"

3. **Configure SAML Settings**
   ```
   Single sign-on URL: https://pybase.example.com/api/v1/saml/acs
   Audience URI (SP Entity ID): https://pybase.example.com/sp/entityid
   Name ID Format: emailAddress
   Application username: Email
   ```

4. **Add Attribute Statements**
   ```
   firstName: user.firstName
   lastName: user.lastName
   email: user.email
   displayName: user.firstName + " " + user.lastName
   groups: user.groups
   ```

5. **Get IdP Metadata**
   - Go to "Sign On" tab
   - Copy "Identity Provider metadata" XML URL
   - Or download "Identity Provider metadata" XML file

6. **Extract IdP Details**
   From metadata XML, extract:
   - Entity ID (`<md:EntityDescriptor>`)
   - SSO URL (`<md:SingleSignOnService>`)
   - X.509 Certificate (`<md:KeyInfo>`)

### Option 2: Mock SAML IdP (for local testing)

Use a local mock IdP like [SAML-Test-IDP](https://github.com/mfmohaiyar/SAML-Test-IDP):

```bash
# Clone mock IdP
git clone https://github.com/mfmohaiyar/SAML-Test-IDP.git
cd SAML-Test-IDP

# Configure
cp config/config.example.json config/config.json
# Edit config.json with your settings

# Run
docker-compose up
```

## Running Integration Tests

### Quick Start

```bash
# 1. Ensure test database is running
docker-compose up -d db

# 2. Run tests
pytest tests/api/v1/test_saml_api.py -v
```

### Test Configuration

Create a `.env.test` file:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/pybase_test

# SSO Settings
SSO_ENABLED=true
SSO_ONLY_MODE=false

# JWT Settings
SECRET_KEY=test-secret-key-for-testing-only
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# API Settings
API_V1_PREFIX=/api/v1
BACKEND_CORS_ORIGINS=["http://localhost:3000"]
```

### Example Test Run

```bash
$ pytest tests/api/v1/test_saml_api.py -v

=================== test session starts ===================
collected 15 items

test_saml_api.py::test_saml_metadata_returns_xml PASSED [  6%]
test_saml_api.py::test_saml_metadata_with_specific_config PASSED [ 13%]
test_saml_api.py::test_saml_login_init_redirects PASSED [ 20%]
test_saml_api.py::test_saml_acs_creates_user_on_first_login PASSED [ 26%]
test_saml_api.py::test_saml_acs_links_existing_user PASSED [ 33%]
test_saml_api.py::test_complete_saml_flow PASSED [ 40%]
...

=================== 15 passed in 5.23s ===================
```

## Running E2E Tests

### Setup

1. **Configure Environment Variables**

   Create a `.env.e2e` file:

   ```env
   # Backend
   API_BASE_URL=http://localhost:8000

   # Frontend
   FRONTEND_BASE_URL=http://localhost:3000

   # SAML Configuration
   SAML_IDP_ID=<your-saml-config-id-from-database>

   # Test User Credentials (for real IdP)
   SAML_TEST_USER_EMAIL=test@example.com
   SAML_TEST_USER_PASSWORD=TestPassword123
   ```

2. **Configure SAML in Database**

   ```python
   # Using Python console
   import asyncio
   from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
   from pybase.models.saml_config import SAMLConfig

   async def setup_saml():
       engine = create_async_engine("postgresql+asyncpg://postgres:postgres@localhost:5432/pybase")
       async_session = AsyncSession(engine)

       config = SAMLConfig(
           name="Okta Test",
           is_enabled=True,
           is_default=True,
           # IdP settings from your Okta metadata
           idp_entity_id="https://dev-xxx.okta.com/xxx",
           idp_sso_url="https://dev-xxx.okta.com/app/xxx/xxx/sso/saml",
           idp_x509_cert="-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
           # SP settings
           sp_entity_id="https://pybase.example.com/sp/entityid",
           sp_acs_url="http://localhost:8000/api/v1/saml/acs",
           # JIT provisioning
           enable_jit_provisioning=True,
       )

       async_session.add(config)
       await async_session.commit()
       print(f"SAML config created with ID: {config.id}")

   asyncio.run(setup_saml())
   ```

3. **Start Services**

   ```bash
   # Terminal 1: Backend
   uvicorn src.pybase.main:app --reload --host 0.0.0.0 --port 8000

   # Terminal 2: Frontend
   cd frontend
   npm run dev

   # Terminal 3: E2E Tests
   cd frontend
   npm run test:e2e -- saml-auth-flow
   ```

### Example Test Run

```bash
$ npx playwright test saml-auth-flow.spec.ts

Running 8 tests using 1 worker

✓ saml-auth-flow.spec.ts:15:3 › should display SSO login button (2.1s)
✓ saml-auth-flow.spec.ts:34:3 › should initiate SAML login flow (3.4s)
✓ saml-auth-flow.spec.ts:65:3 › should complete full SAML authentication (12.1s)
✓ saml-auth-flow.spec.ts:127:3 › should handle SAML authentication errors (1.8s)
✓ saml-auth-flow.spec.ts:153:3 › should store JWT token (0.9s)
✓ saml-auth-flow.spec.ts:189:3 › should display user profile (2.3s)
✓ saml-auth-flow.spec.ts:217:3 › should return SAML metadata endpoint (1.1s)
✓ saml-auth-flow.spec.ts:237:3 › should return available SAML configurations (0.8s)

8 passed (24.5s)
```

## Test Coverage

### Integration Test Coverage

- ✅ SAML metadata generation
- ✅ SAML login initiation
- ✅ SAML response processing
- ✅ JIT user provisioning
- ✅ User identity linking
- ✅ Attribute mapping
- ✅ Role mapping
- ✅ Error handling
- ✅ Authentication/authorization
- ✅ Complete SAML flow

### E2E Test Coverage

- ✅ SSO button visibility
- ✅ Login initiation
- ✅ IdP redirection
- ✅ IdP authentication
- ✅ Callback handling
- ✅ Token storage
- ✅ Dashboard redirect
- ✅ Error handling
- ✅ Profile display
- ✅ Protected resource access

## Troubleshooting

### Common Issues

#### 1. "SSO is disabled" Error

**Problem:** Tests fail with "SSO is disabled" message.

**Solution:**
```bash
export SSO_ENABLED=true
```

#### 2. "SAML configuration not found" Error

**Problem:** No SAML config in test database.

**Solution:**
```python
# Create test SAML config (see test fixtures in test_saml_api.py)
# Or run: pytest tests/api/v1/test_saml_api.py::test_saml_metadata_returns_xml
```

#### 3. "Invalid SAML response" in E2E Tests

**Problem:** SAML response from IdP is malformed or expired.

**Solution:**
- Check IdP configuration matches SP settings
- Verify X.509 certificate is current
- Check system time is correct
- Review IdP logs for errors

#### 4. "Redirect timeout" in Playwright

**Problem:** Playwright doesn't detect redirect to IdP.

**Solution:**
```typescript
// Increase timeout
await page.waitForURL(url => url.href.includes('idp'), { timeout: 30000 });
```

#### 5. "User not created" in JIT Provisioning

**Problem:** User not auto-created on first SAML login.

**Solution:**
- Verify `enable_jit_provisioning=True` in SAML config
- Check attribute mappings are correct
- Review backend logs for errors
- Ensure database migrations are applied

### Debug Mode

Enable debug logging:

```bash
# Backend
export LOG_LEVEL=DEBUG

# Run pytest with output
pytest tests/api/v1/test_saml_api.py -v -s

# Playwright with debug
npx playwright test --debug
```

### Test Database Reset

```bash
# Reset test database
dropdb pybase_test
createdb pybase_test
alembic upgrade head --database-url=postgresql+asyncpg://postgres:postgres@localhost:5432/pybase_test
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: SAML SSO Tests

on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: pybase_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e ".[test]"

      - name: Run integration tests
        run: |
          pytest tests/api/v1/test_saml_api.py -v
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/pybase_test
          SSO_ENABLED: "true"

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: |
          cd frontend
          npm install
          npx playwright install --with-deps

      - name: Run E2E tests
        run: |
          cd frontend
          npm run test:e2e -- saml-auth-flow
```

---

# OIDC Testing Guide

OpenID Connect (OIDC) testing instructions for PyBase SSO integration.

## Overview

The OIDC testing suite includes:

1. **Integration Tests** (`tests/api/v1/test_oidc_api.py`)
   - Backend API endpoint testing
   - Mock OIDC responses for fast, reliable tests
   - No external IdP required for basic tests
   - Tests all OIDC flows and error cases

2. **E2E Tests** (`frontend/e2e/oidc-auth-flow.spec.ts`)
   - Full browser-based testing with Playwright
   - Tests complete authentication flow
   - Requires a real OIDC provider (or mock provider)
   - Tests frontend components and user interactions

## Supported OIDC Providers

PyBase OIDC integration supports:
- **Google OAuth2** (Recommended for testing)
- **Azure Active Directory**
- **Okta**
- **Auth0**
- Any OIDC-compliant provider

## Setting Up a Test OIDC Provider

### Option 1: Google Cloud Console (Recommended)

1. **Create Google Cloud Project**
   - Go to https://console.cloud.google.com/
   - Create new project or select existing
   - Enable Google+ API

2. **Create OAuth2 Credentials**
   - Go to APIs & Services → Credentials
   - Click "Create Credentials" → "OAuth client ID"
   - Application type: "Web application"
   - Name: "PyBase Test"

3. **Configure OAuth2 Client**
   ```
   Authorized redirect URIs:
   - http://localhost:8000/api/v1/oidc/callback
   - http://localhost:3000/auth/callback
   ```

4. **Get Credentials**
   - Copy Client ID
   - Copy Client Secret
   - Note: Authorization endpoint, Token endpoint, and JWKS URI are auto-discovered

5. **Configure in PyBase**
   - Navigate to http://localhost:3000/admin/sso
   - Go to OIDC Configuration tab
   - Fill in:
     - Provider Name: "Google"
     - Issuer URL: `https://accounts.google.com`
     - Client ID: <your-client-id>
     - Client Secret: <your-client-secret>
     - Scope: `openid email profile`

### Option 2: Okta Developer Account

1. **Create Okta Application**
   - Go to Okta Admin Console → Applications → Applications
   - Click "Create App Integration"
   - Select "OIDC - OpenID Connect"
   - Application type: "Web Application"
   - App name: "PyBase OIDC Test"

2. **Configure OIDC Settings**
   ```
   Sign-in redirect URIs:
   - http://localhost:8000/api/v1/oidc/callback
   - http://localhost:3000/auth/callback

   Sign-out redirect URIs:
   - http://localhost:3000/login

   Allowed grant types:
   - Authorization Code
   ```

3. **Get Credentials**
   - Copy Client ID
   - Copy Client Secret
   - Copy Issuer URL (Okta domain)

### Option 3: Mock OIDC Provider

For local testing without external dependencies, you can use a mock OIDC provider.

## OIDC Integration Tests

### Running OIDC Integration Tests

```bash
# Run all OIDC integration tests
pytest tests/api/v1/test_oidc_api.py -v

# Run specific test
pytest tests/api/v1/test_oidc_api.py::test_oidc_login_init_redirects -v

# Run with coverage
pytest tests/api/v1/test_oidc_api.py --cov=src/pybase/api/v1/oidc --cov-report=html
```

### What It Tests

**Login Initiation Tests:**
- OIDC login initiation redirects correctly
- Default config selection works
- Provider-specific config selection works
- Disabled config returns 403
- Missing config returns 404
- PKCE parameters are included (code_challenge, code_challenge_method)
- Custom prompt parameter works
- Login hint parameter works

**Callback Processing Tests:**
- Creates new user via JIT provisioning on first login
- Links to existing user on subsequent login
- Invalid authorization code returns error
- Missing code/state parameters return validation errors

**Config Info Tests:**
- Config endpoint requires authentication
- Returns non-sensitive config info to authenticated users
- Doesn't expose client secrets

**Logout Tests:**
- Logout endpoint requires authentication
- Returns logout URL if configured
- Supports post-logout redirect URI

**Error Handling Tests:**
- Returns 403 when SSO disabled globally
- Handles invalid authorization codes
- Handles provider errors gracefully

**Integration Tests:**
- Complete OIDC flow from login to protected resource access
- Multiple provider configurations
- Token refresh mechanism
- UserInfo endpoint fallback

### Test Fixtures

**`oidc_config` fixture:**
Creates a test OIDC configuration with Google OAuth2 endpoints.

**`oidc_config_disabled` fixture:**
Creates a disabled OIDC config for testing disabled scenarios.

**Mock functions:**
- `create_mock_id_token()` - Creates unsigned JWT for testing
- `create_mock_token_response()` - Mock token response from provider
- `create_mock_userinfo()` - Mock UserInfo response

### Environment Variables

```bash
# Required for integration tests
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/pybase_test"
export SSO_ENABLED="true"

# Optional
export OIDC_PROVIDER_ID="<uuid>"  # For specific provider tests
export JWT_SECRET_KEY="test-secret-key"
export JWT_ALGORITHM="HS256"
```

## OIDC E2E Tests

### Running OIDC E2E Tests

```bash
cd frontend

# Run all OIDC E2E tests
npm run test:e2e -- oidc-auth-flow

# Run specific test
npx playwright test oidc-auth-flow.spec.ts -g "should display SSO login button"

# Run with UI
npx playwright test --ui

# Run with headed mode (see browser)
npx playwright test oidc-auth-flow.spec.ts --headed
```

### Environment Variables for E2E Tests

```bash
# Required
export OIDC_PROVIDER_ID="<uuid>"  # OIDC config ID from database
export OIDC_TEST_USER_EMAIL="test@example.com"
export OIDC_TEST_USER_PASSWORD="password123"

# Optional
export API_BASE_URL="http://localhost:8000"
export FRONTEND_BASE_URL="http://localhost:3000"
```

### E2E Test Suites

**1. OIDC Authentication Flow Tests**
- Display SSO login button when OIDC configured
- Initiate OIDC flow on button click
- Complete full OIDC authentication flow
- Handle authentication errors gracefully
- Handle provider authorization errors
- Store JWT token after successful login
- Display user profile after login

**2. OIDC Configuration API Tests**
- Return OIDC configuration info
- Handle OIDC logout endpoint

**3. OIDC Security Tests**
- Use PKCE for authorization code flow
- Include state parameter for CSRF protection

**4. Provider-Specific Tests**
- Google OAuth2
- Azure Active Directory
- Okta
- Auth0

### Running E2E Tests with Real Provider

**Step 1: Configure OIDC Provider**

```bash
# Start backend
cd backend
uvicorn src.pybase.main:app --reload

# Start frontend
cd frontend
npm run dev
```

**Step 2: Create OIDC Configuration**

1. Navigate to http://localhost:3000/admin/sso
2. Go to OIDC Configuration tab
3. Fill in provider details (e.g., Google)
4. Save configuration

**Step 3: Get Config ID**

```bash
# Query database for OIDC config ID
psql $DATABASE_URL

SELECT id, name, issuer_url FROM oidc_configs WHERE is_enabled = true;
# Copy the config ID
```

**Step 4: Run E2E Tests**

```bash
cd frontend

export OIDC_PROVIDER_ID="<config-id-from-step-3>"
export OIDC_TEST_USER_EMAIL="your-test@example.com"
export OIDC_TEST_USER_PASSWORD="your-password"

npx playwright test oidc-auth-flow.spec.ts
```

## OIDC-Specific Considerations

### PKCE (Proof Key for Code Exchange)

OIDC implementation uses PKCE for enhanced security:
- `code_verifier`: Random string generated on login initiation
- `code_challenge`: SHA256 hash of code_verifier
- `code_challenge_method`: Always "S256"

**Verification:**
```bash
# In integration tests
pytest tests/api/v1/test_oidc_api.py::test_oidc_login_init_with_pkce -v
```

### ID Token Validation

OIDC validates ID tokens using:
- **Signature verification** using JWKS from provider
- **Issuer validation** against configured issuer URL
- **Audience validation** against client ID
- **Expiration validation** (exp claim)
- **Nonce validation** for replay protection

### UserInfo Endpoint Fallback

Some providers return minimal claims in ID token. The implementation can:
1. Extract basic claims from ID token
2. Fetch additional claims from UserInfo endpoint (if configured)
3. Merge claims for complete user profile

### Multiple OIDC Providers

You can configure multiple OIDC providers simultaneously:
- Google for users with Google accounts
- Azure AD for enterprise users
- Okta for specific organizations

**Testing multiple providers:**
```bash
pytest tests/api/v1/test_oidc_api.py::test_oidc_with_multiple_providers -v
```

## Troubleshooting OIDC Tests

### Issue: Integration tests fail with "invalid_grant"

**Solution:** Mock httpx client properly
```python
with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
    mock_post.return_value = Response(200, content=json.dumps(mock_response))
    # Your test code here
```

### Issue: E2E tests skip due to missing config

**Solution:** Set environment variables
```bash
export OIDC_PROVIDER_ID="$(psql -tAc "SELECT id FROM oidc_configs WHERE is_default=true LIMIT 1")"
```

### Issue: Redirect URI mismatch

**Solution:** Ensure redirect URI matches what's configured in provider
- Backend: `http://localhost:8000/api/v1/oidc/callback`
- Frontend: `http://localhost:3000/auth/callback`

### Issue: JWKS fetch fails

**Solution:** Check JWKS URI is accessible
```bash
curl "https://www.googleapis.com/oauth2/v3/certs"
# Should return JWKS JSON
```

## OIDC Test Coverage Summary

| Feature | Integration Tests | E2E Tests |
|---------|-------------------|-----------|
| Login initiation | ✅ | ✅ |
| Callback processing | ✅ | ✅ |
| JIT provisioning | ✅ | ✅ |
| User identity linking | ✅ | ✅ |
| Token validation | ✅ | ✅ |
| Error handling | ✅ | ✅ |
| PKCE support | ✅ | ✅ |
| Multiple providers | ✅ | ✅ |
| Logout | ✅ | ⚠️ |
| UserInfo endpoint | ✅ | N/A |
| Role mapping | ✅ | ⚠️ |

Legend: ✅ Fully tested | ⚠️ Partially tested | N/A Not applicable

---

## Next Steps

After successfully running SAML and OIDC tests:

1. **Review test results** - Check for any failures or warnings
2. **Check code coverage** - Ensure adequate coverage of SSO flows
3. **Test with production IdP** - Validate with actual Okta/Azure AD/Google environment
4. **Performance testing** - Test SSO flow under load
5. **Security testing** - Verify SSO security best practices

## Additional Resources

### SAML Resources
- [SAML 2.0 Specification](https://docs.oasis-open.org/security/saml/v2.0/)
- [Okta SAML Documentation](https://developer.okta.com/docs/reference/saml/)

### OIDC Resources
- [OpenID Connect Specification](https://openid.net/connect/)
- [OAuth 2.0 RFC 6749](https://tools.ietf.org/html/rfc6749)
- [PKCE RFC 7636](https://tools.ietf.org/html/rfc7636)
- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Azure AD OIDC Documentation](https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-protocols-oidc)
- [Okta OIDC & OAuth 2.0 API](https://developer.okta.com/docs/reference/api/oidc/)

### Testing Resources
- [FastAPI Testing Guide](https://fastapi.tiangolo.com/tutorial/testing/)
- [Playwright Documentation](https://playwright.dev/)
- [Pytest Documentation](https://docs.pytest.org/)
