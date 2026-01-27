# SCIM 2.0 Provisioning Testing Guide

Complete guide for testing SCIM 2.0 automated user provisioning with Okta, Azure AD, and other identity providers.

## Table of Contents

1. [Overview](#overview)
2. [SCIM 2.0 Protocol Summary](#scim-20-protocol-summary)
3. [Test Environment Setup](#test-environment-setup)
4. [Okta SCIM Configuration](#okta-scim-configuration)
5. [Azure AD SCIM Configuration](#azure-ad-scim-configuration)
6. [Automated Testing](#automated-testing)
7. [Manual Testing Procedures](#manual-testing-procedures)
8. [Verification Checklist](#verification-checklist)
9. [Troubleshooting](#troubleshooting)
10. [Security Considerations](#security-considerations)

---

## Overview

SCIM 2.0 (System for Cross-domain Identity Management) enables automated user provisioning between identity providers (IdPs) like Okta/Azure AD and PyBase. This guide covers testing the complete SCIM provisioning lifecycle.

### Supported SCIM 2.0 Features

- **User Provisioning**: Create, read, update, deactivate users
- **ServiceProviderConfig**: Capability discovery
- **Resource Types**: User and Group schema definitions
- **Filtering**: Basic filter support (userName, email)
- **Pagination**: Configurable page size
- **Authentication**: OAuth Bearer Token and HTTP Basic

### Not Yet Implemented

- Group provisioning (returns empty list)
- Bulk operations
- ETag support
- Change password via SCIM

---

## SCIM 2.0 Protocol Summary

### Base Endpoint

```
http://localhost:8000/api/v1/scim/v2
```

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ServiceProviderConfig` | GET | Service provider capabilities |
| `/Users` | GET | List users with pagination/filtering |
| `/Users` | POST | Create new user (JIT provisioning) |
| `/Users/{id}` | GET | Get specific user |
| `/Users/{id}` | PUT | Full user update (replace) |
| `/Users/{id}` | PATCH | Partial user update |
| `/Users/{id}` | DELETE | Soft delete user (deactivate) |
| `/ResourceTypes` | GET | List resource types |
| `/Schemas` | GET | List schema definitions |

### Authentication

All SCIM endpoints require superuser authentication:

```bash
# Bearer Token (recommended)
Authorization: Bearer <superuser-jwt-token>

# HTTP Basic (for IdP testing)
Authorization: Basic base64(username:password)
```

---

## Test Environment Setup

### Prerequisites

1. **PyBase Backend Running**
   ```bash
   cd /path/to/pybase
   source .venv/bin/activate
   uvicorn src.pybase.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Database Migrations Applied**
   ```bash
   alembic upgrade head
   ```

3. **Superuser Account Created**
   ```bash
   python scripts/create_superuser.py
   ```

### Environment Variables

Create `.env` for testing:

```bash
# SCIM Configuration
SCIM_BASE_URL=http://localhost:8000/api/v1/scim/v2
SCIM_AUTH_TOKEN=<your-superuser-jwt-token>

# For IdP configuration
PYBASE_BASE_URL=https://your-pybase-domain.com
PYBASE_SCIM_URL=https://your-pybase-domain.com/api/v1/scim/v2
```

### Generate SCIM Auth Token

```bash
# Login as superuser to get JWT token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin-password"}'

# Extract access_token from response
export SCIM_AUTH_TOKEN=<access_token>
```

---

## Okta SCIM Configuration

### Step 1: Create SCIM Application in Okta

1. Log in to Okta Admin Console
2. Go to **Applications** → **Applications**
3. Click **Browse App Catalog**
4. Search for "SCIM" or select "SCIM Provisioner" (if available)
5. Or create a custom app with SCIM enabled

### Step 2: Configure SCIM Integration

1. Go to **Applications** → Your SCIM App → **Provisioning**
2. Click **Configure API Integration**
3. Select **Enable SCIM provisioning**
4. Enter SCIM 2.0 endpoint:
   ```
   https://your-pybase-domain.com/api/v1/scim/v2
   ```
5. Enter authentication:
   - **Option A**: Use OAuth Bearer Token
     - Generate long-lived API token in PyBase
     - Add as HTTP header: `Authorization: Bearer <token>`
   - **Option B**: Use HTTP Basic (for testing only)
     - Username: superuser email
     - Password: superuser password
6. Click **Test API Credentials**
7. Verify connection success

### Step 3: Configure Provisioning Settings

1. Go to **Provisioning** → **To App**
2. Enable provisioning features:
   - ✅ Create Users
   - ✅ Update User Attributes
   - ✅ Deactivate Users
3. Configure attribute mappings (see below)

### Step 4: Configure Attribute Mappings

Okta → PyBase attribute mapping:

| Okta Attribute | PyBase SCIM Attribute | Mapped To |
|----------------|----------------------|-----------|
| `user.userName` | `userName` | email |
| `user.name.givenName` | `name.givenName` | first name |
| `user.name.familyName` | `name.familyName` | last name |
| `user.displayName` | `displayName` | full name |
| `user.active` | `active` | is_active |
| `user.emails` | `emails` | email array |

### Step 5: Test Okta Integration

```bash
# Test ServiceProviderConfig
curl -X GET https://your-pybase-domain.com/api/v1/scim/v2/ServiceProviderConfig \
  -H "Authorization: Bearer $SCIM_AUTH_TOKEN"

# Test User Listing
curl -X GET https://your-pybase-domain.com/api/v1/scim/v2/Users \
  -H "Authorization: Bearer $SCIM_AUTH_TOKEN"
```

Expected response: `200 OK` with valid SCIM JSON.

---

## Azure AD SCIM Configuration

### Step 1: Create Enterprise Application

1. Log in to Azure Portal (portal.azure.com)
2. Go to **Azure Active Directory** → **Enterprise applications**
3. Click **New application**
4. Select **On-premises application** or create custom
5. Name: "PyBase SCIM"
6. Click **Create**

### Step 2: Configure SCIM Provisioning

1. Open your enterprise application
2. Go to **Provisioning** (left sidebar)
3. Click **Get Started**
4. Select:
   - **Mode**: Automatic
   - **Identity**: Azure Active Directory
   - **Target App**: PyBase SCIM
5. Click **Next**

### Step 3: Enter SCIM Configuration

1. **Tenant URL**: `https://your-pybase-domain.com/api/v1/scim/v2`
2. **Secret Token**: Generate long-lived API token in PyBase
3. Click **Test Connection**
4. Wait for "Connection successful" message
5. Click **Save**

### Step 4: Configure Attribute Mappings

Azure AD → PyBase attribute mapping:

| Azure AD Attribute | PyBase SCIM Attribute | Mapped To |
|-------------------|----------------------|-----------|
| `userPrincipalName` | `userName` | email |
| `givenName` | `name.givenName` | first name |
| `surname` | `name.familyName` | last name |
| `displayName` | `displayName` | full name |
| `accountEnabled` | `active` | is_active |
| `mail` | `emails[value]` | email |

### Step 5: Start Provisioning

1. Go to **Provisioning** → **Provisioning Status**
2. Click **Start provisioning**
3. Select:
   - **Scope**: Sync only assigned users and groups
   - **Synchronization**: Enable on-demand sync
4. Click **Save**

### Step 6: Test Azure AD Integration

```bash
# Test connection from Azure AD
# Azure AD will test the following endpoints:
# 1. GET /ServiceProviderConfig
# 2. GET /Users?filter=userName eq 'test@example.com'

curl -X GET https://your-pybase-domain.com/api/v1/scim/v2/ServiceProviderConfig \
  -H "Authorization: Bearer $SCIM_AUTH_TOKEN"
```

---

## Automated Testing

### Backend Integration Tests

Test SCIM API endpoints with pytest:

```bash
# Run all SCIM integration tests
pytest tests/api/v1/test_scim_api.py -v

# Run specific test
pytest tests/api/v1/test_scim_api.py::test_create_user_via_scim -v

# Run with coverage
pytest tests/api/v1/test_scim_api.py --cov=pybase.api.v1.scim --cov-report=html
```

### Frontend E2E Tests

Test SCIM provisioning with Playwright:

```bash
cd frontend

# Install dependencies (if needed)
npm install

# Run SCIM E2E tests
npm run test:e2e -- scim-provisioning.spec.ts

# Run with UI
npm run test:e2e:ui -- scim-provisioning.spec.ts

# Run specific test
npm run test:e2e -- scim-provisioning.spec.ts -g "should create a new user via SCIM"
```

### Test Environment Variables for E2E

Create `.env.test`:

```bash
SCIM_BASE_URL=http://localhost:8000/api/v1/scim/v2
SCIM_AUTH_TOKEN=<your-test-token>
```

---

## Manual Testing Procedures

### Test 1: Verify ServiceProviderConfig

```bash
curl -X GET http://localhost:8000/api/v1/scim/v2/ServiceProviderConfig \
  -H "Authorization: Bearer $SCIM_AUTH_TOKEN" | jq
```

**Expected Result:**
```json
{
  "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"],
  "patch": {"supported": true},
  "bulk": {"supported": false},
  "filter": {"supported": true, "maxResults": 100},
  "changePassword": {"supported": false},
  "sort": {"supported": true},
  "etag": {"supported": false},
  "authenticationSchemes": [
    {
      "name": "OAuth Bearer Token",
      "type": "oauthbearertoken",
      "primary": true
    }
  ]
}
```

### Test 2: Create User via SCIM

```bash
curl -X POST http://localhost:8000/api/v1/scim/v2/Users \
  -H "Authorization: Bearer $SCIM_AUTH_TOKEN" \
  -H "Content-Type: application/scim+json" \
  -d '{
    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
    "userName": "scim.test@example.com",
    "name": {
      "givenName": "SCIM",
      "familyName": "Test",
      "formatted": "SCIM Test"
    },
    "displayName": "SCIM Test User",
    "active": true,
    "emails": [{
      "value": "scim.test@example.com",
      "type": "work",
      "primary": true
    }]
  }' | jq
```

**Expected Result:**
- Status: `201 Created`
- Response includes: `id`, `userName`, `displayName`, `active`, `emails`, `meta`

### Test 3: Retrieve Created User

```bash
# Replace <user-id> with ID from Test 2
curl -X GET http://localhost:8000/api/v1/scim/v2/Users/<user-id> \
  -H "Authorization: Bearer $SCIM_AUTH_TOKEN" | jq
```

**Expected Result:**
- Status: `200 OK`
- User data matches created user

### Test 4: Update User via SCIM

```bash
curl -X PUT http://localhost:8000/api/v1/scim/v2/Users/<user-id> \
  -H "Authorization: Bearer $SCIM_AUTH_TOKEN" \
  -H "Content-Type: application/scim+json" \
  -d '{
    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
    "userName": "scim.test@example.com",
    "displayName": "Updated SCIM User",
    "active": true
  }' | jq
```

**Expected Result:**
- Status: `200 OK`
- `displayName` updated to "Updated SCIM User"

### Test 5: Deactivate User via SCIM

```bash
curl -X PUT http://localhost:8000/api/v1/scim/v2/Users/<user-id> \
  -H "Authorization: Bearer $SCIM_AUTH_TOKEN" \
  -H "Content-Type: application/scim+json" \
  -d '{
    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
    "userName": "scim.test@example.com",
    "active": false
  }' | jq
```

**Expected Result:**
- Status: `200 OK`
- `active` is `false`

### Test 6: Delete User via SCIM

```bash
curl -X DELETE http://localhost:8000/api/v1/scim/v2/Users/<user-id> \
  -H "Authorization: Bearer $SCIM_AUTH_TOKEN" -v
```

**Expected Result:**
- Status: `204 No Content`
- User is soft deleted (deactivated, `deleted_at` set)

### Test 7: List Users with Filter

```bash
curl -X GET "http://localhost:8000/api/v1/scim/v2/Users?filter=userName eq \"scim.test@example.com\"" \
  -H "Authorization: Bearer $SCIM_AUTH_TOKEN" | jq
```

**Expected Result:**
- Status: `200 OK`
- Returns filtered list of users

### Test 8: Pagination

```bash
curl -X GET "http://localhost:8000/api/v1/scim/v2/Users?startIndex=1&count=5" \
  -H "Authorization: Bearer $SCIM_AUTH_TOKEN" | jq
```

**Expected Result:**
- Status: `200 OK`
- Returns paginated results with `startIndex`, `itemsPerPage`, `totalResults`

---

## Verification Checklist

### Manual Verification with Okta

- [ ] Okta can connect to PyBase SCIM endpoint
- [ ] Okta retrieves valid ServiceProviderConfig
- [ ] Creating a user in Okta creates user in PyBase
- [ ] Updating user in Okta updates user in PyBase
- [ ] Deactivating user in Okta deactivates user in PyBase
- [ ] User attributes mapped correctly (name, email, active status)
- [ ] Duplicate user creation is prevented

### Manual Verification with Azure AD

- [ ] Azure AD can connect to PyBase SCIM endpoint
- [ ] Connection test succeeds
- [ ] Creating a user in Azure AD creates user in PyBase
- [ ] Updating user in Azure AD updates user in PyBase
- [ ] Deleting a user in Azure AD deactivates user in PyBase
- [ ] User attributes mapped correctly
- [ ] On-demand provisioning works

### Automated Test Verification

```bash
# Backend tests
pytest tests/api/v1/test_scim_api.py -v
# Expected: All tests pass (50+ test cases)

# Frontend E2E tests
cd frontend && npm run test:e2e -- scim-provisioning.spec.ts
# Expected: All Playwright tests pass
```

---

## Troubleshooting

### Issue: Okta/Azure AD Cannot Connect

**Symptoms:**
- Connection test fails
- Timeout errors
- "Unable to connect" message

**Solutions:**
1. Verify PyBase is running: `curl http://localhost:8000/api/v1/health`
2. Check firewall/security group allows HTTPS traffic
3. Verify SCIM endpoint URL is accessible from IdP
4. Check authentication token is valid:
   ```bash
   curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/scim/v2/ServiceProviderConfig
   ```
5. Review logs: `tail -f logs/pybase.log`

### Issue: User Not Created in PyBase

**Symptoms:**
- IdP shows user as "provisioned"
- User not found in PyBase database

**Solutions:**
1. Check PyBase logs for errors
2. Verify SCIM request format:
   ```bash
   # Enable debug logging to see incoming SCIM requests
   export DEBUG=1
   uvicorn src.pybase.main:app --reload
   ```
3. Check for duplicate email conflicts
4. Verify database connectivity
5. Check superuser permissions

### Issue: User Attributes Not Mapped Correctly

**Symptoms:**
- User created but with wrong name/email
- Fields missing or empty

**Solutions:**
1. Review IdP attribute mappings
2. Check SCIM request payload from IdP
3. Verify attribute names match SCIM schema:
   - `userName` → email
   - `name.givenName` → first name
   - `name.familyName` → last name
   - `displayName` → full name
4. Test with explicit attribute mapping

### Issue: Deactivation Not Working

**Symptoms:**
- User deactivated in IdP
- User still active in PyBase

**Solutions:**
1. Check IdP provisioning settings (deactivation enabled)
2. Verify IdP sends `active: false` in SCIM update
3. Test manual deactivation:
   ```bash
   curl -X PUT /scim/v2/Users/<id> \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"active": false}'
   ```
4. Review soft delete implementation

### Issue: Authentication Failures

**Symptoms:**
- 401 Unauthorized responses
- Token expired errors

**Solutions:**
1. Generate new SCIM auth token:
   ```bash
   # Login as superuser
   curl -X POST /api/v1/auth/login \
     -d '{"email":"admin@example.com","password":"password"}' \
     | jq -r '.access_token'
   ```
2. Update IdP SCIM configuration with new token
3. Use long-lived token for production (24+ hours)
4. Consider implementing token refresh mechanism

### Issue: Pagination Not Working

**Symptoms:**
- All users returned regardless of count parameter
- startIndex parameter ignored

**Solutions:**
1. Verify pagination parameters in request
2. Check database query implementation
3. Test with explicit count:
   ```bash
   curl "/scim/v2/Users?count=2" -H "Authorization: Bearer $TOKEN"
   ```
4. Review list_users endpoint in scim.py

---

## Security Considerations

### Authentication

1. **Use HTTPS in Production**
   - SCIM endpoints should use HTTPS
   - Encrypt all provisioning data in transit

2. **Long-lived API Tokens**
   - Generate dedicated SCIM token with superuser permissions
   - Store securely in IdP (not in code)
   - Rotate tokens regularly (90 days recommended)

3. **HTTP Basic (Testing Only)**
   - Never use HTTP Basic in production
   - Only for initial IdP testing
   - Switch to OAuth Bearer Token before deployment

### Authorization

1. **Superuser Required**
   - All SCIM endpoints require superuser authentication
   - Regular users cannot access SCIM endpoints

2. **IdP Service Account**
   - Create dedicated service account in PyBase for SCIM
   - Assign superuser role
   - Use separate credentials from admin account

### Data Privacy

1. **PII in Transit**
   - SCIM transmits user PII (names, emails)
   - Always use HTTPS in production

2. **Audit Logging**
   - Log all SCIM provisioning operations
   - Include: timestamp, user_id, operation, IP address
   - Review logs regularly for suspicious activity

3. **Soft Delete**
   - SCIM DELETE performs soft delete (deactivation)
   - User data retained in database
   - Implement data retention policy

### Rate Limiting

Consider implementing rate limiting for SCIM endpoints:

```python
# Example: 100 requests per minute per IdP
from slowapi import Limiter
limiter = Limiter(key_func=get_api_key)

@router.post("/v2/Users")
@limiter.limit("100/minute")
async def create_user(...):
    ...
```

### Monitoring

Monitor SCIM provisioning:

1. **Metrics to Track**
   - Provisioning success rate
   - Average response time
   - Error rate by type
   - User lifecycle events (create, update, deactivate)

2. **Alerts to Configure**
   - High error rate (>5%)
   - Authentication failures
   - Connection timeouts
   - Duplicate user attempts

---

## Additional Resources

### SCIM 2.0 Specifications

- [RFC 7643: SCIM Core Schema](https://datatracker.ietf.org/doc/html/rfc7643)
- [RFC 7644: SCIM Protocol](https://datatracker.ietf.org/doc/html/rfc7644)
- [SCIM 2.0 Overview](https://www.simplecloud.info/)

### IdP Documentation

- [Okta SCIM Provisioning Guide](https://help.okta.com/en-us/Content/Topics/Provisioning/configscim.htm)
- [Azure AD SCIM Provisioning Tutorial](https://docs.microsoft.com/en-us/azure/active-directory/app-provisioning/use-scim-to-provision-users-and-groups)

### Testing Tools

- [Postman SCIM Collection](https://github.com/scimtester/scim-tester)
- [SCIM Tester](https://scimtester.com/)
- [curl](https://curl.se/) for manual testing

---

## Summary

This testing guide covers:

✅ SCIM 2.0 protocol implementation
✅ Okta SCIM integration setup
✅ Azure AD SCIM integration setup
✅ Automated integration tests (50+ test cases)
✅ End-to-end Playwright tests
✅ Manual testing procedures
✅ Verification checklist
✅ Troubleshooting guide
✅ Security best practices

The SCIM 2.0 provisioning implementation is production-ready for user lifecycle management with enterprise identity providers.
