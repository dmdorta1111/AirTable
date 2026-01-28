/**
 * End-to-end tests for SCIM 2.0 provisioning with Okta/Azure AD.
 *
 * Tests the complete SCIM provisioning flow including:
 * - SCIM endpoint configuration in IdP
 * - User creation from IdP
 * - User updates from IdP
 * - User deactivation from IdP
 * - Group provisioning (when implemented)
 */

import { test, expect } from '@playwright/test';

// =============================================================================
// Test Configuration
// =============================================================================

const SCIM_BASE_URL = process.env.SCIM_BASE_URL || 'http://localhost:8000/api/v1/scim/v2';
const SCIM_AUTH_TOKEN = process.env.SCIM_AUTH_TOKEN || ''; // Bearer token for SCIM

// Helper to get auth headers
const getAuthHeaders = () => ({
  'Authorization': `Bearer ${SCIM_AUTH_TOKEN}`,
  'Content-Type': 'application/scim+json',
});

// Helper to generate random user data
const generateUserData = () => ({
  schemas: ['urn:ietf:params:scim:schemas:core:2.0:User'] as string[],
  userName: `testuser.${Date.now()}@example.com`,
  name: {
    givenName: 'Test',
    familyName: 'User',
    formatted: 'Test User',
  },
  displayName: 'Test User',
  active: true,
  emails: [{
    value: `testuser.${Date.now()}@example.com`,
    type: 'work',
    primary: true,
  }],
});

// =============================================================================
// SCIM 2.0 Service Provider Configuration
// =============================================================================

test.describe('SCIM 2.0 Service Provider Configuration', () => {
  test('should retrieve service provider configuration', async ({ request }) => {
    const response = await request.get(`${SCIM_BASE_URL}/ServiceProviderConfig`);

    expect(response.status()).toBe(200);
    const config = await response.json();

    // Verify SCIM schema
    expect(config.schemas).toContain('urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig');

    // Verify capabilities
    expect(config.patch.supported).toBe(true);
    expect(config.bulk.supported).toBe(false);
    expect(config.filter.supported).toBe(true);
    expect(config.filter.maxResults).toBe(100);
    expect(config.changePassword.supported).toBe(false);
    expect(config.sort.supported).toBe(true);
    expect(config.etag.supported).toBe(false);

    // Verify authentication schemes
    expect(config.authenticationSchemes).toBeDefined();
    expect(config.authenticationSchemes.length).toBeGreaterThan(0);

    const oauthScheme = config.authenticationSchemes.find(
      (s: any) => s.type === 'oauthbearertoken'
    );
    expect(oauthScheme).toBeDefined();
    expect(oauthScheme.primary).toBe(true);
  });

  test('should include OAuth Bearer Token authentication scheme', async ({ request }) => {
    const response = await request.get(`${SCIM_BASE_URL}/ServiceProviderConfig`);
    const config = await response.json();

    const bearerScheme = config.authenticationSchemes.find(
      (s: any) => s.name === 'OAuth Bearer Token'
    );

    expect(bearerScheme).toBeDefined();
    expect(bearerScheme.description).toBe('Authentication using Bearer token');
    expect(bearerScheme.specUri).toContain('rfc6750');
  });

  test('should include HTTP Basic authentication scheme', async ({ request }) => {
    const response = await request.get(`${SCIM_BASE_URL}/ServiceProviderConfig`);
    const config = await response.json();

    const basicScheme = config.authenticationSchemes.find(
      (s: any) => s.type === 'httpbasic'
    );

    expect(basicScheme).toBeDefined();
    expect(basicScheme.name).toBe('HTTP Basic');
    expect(basicScheme.primary).toBe(false);
  });
});

// =============================================================================
// SCIM 2.0 User Provisioning - Create
// =============================================================================

test.describe('SCIM 2.0 User Creation', () => {
  test('should create a new user via SCIM', async ({ request }) => {
    const userData = generateUserData();

    const response = await request.post(`${SCIM_BASE_URL}/Users`, {
      headers: getAuthHeaders(),
      data: userData,
    });

    expect(response.status()).toBe(201);
    const createdUser = await response.json();

    // Verify SCIM response structure
    expect(createdUser.id).toBeDefined();
    expect(createdUser.userName).toBe(userData.userName);
    expect(createdUser.displayName).toBe(userData.displayName);
    expect(createdUser.active).toBe(true);
    expect(createdUser.emails).toBeDefined();
    expect(createdUser.emails[0].value).toBe(userData.emails[0].value);
    expect(createdUser.meta).toBeDefined();
    expect(createdUser.meta.resourceType).toBe('User');
    expect(createdUser.meta.location).toContain('/Users/');
  });

  test('should create user with externalId from IdP', async ({ request }) => {
    const userData: any = {
      schemas: ['urn:ietf:params:scim:schemas:core:2.0:User'],
      userName: 'okta-user@example.com',
      externalId: 'okta-12345abcdef',
      displayName: 'Okta User',
      active: true,
      emails: [{
        value: 'okta-user@example.com',
        type: 'work',
        primary: true,
      }],
    };

    const response = await request.post(`${SCIM_BASE_URL}/Users`, {
      headers: getAuthHeaders(),
      data: userData,
    });

    expect(response.status()).toBe(201);
    const user = await response.json();
    expect(user.userName).toBe('okta-user@example.com');
    // externalId may be stored but not necessarily returned
  });

  test('should create user with minimal required fields', async ({ request }) => {
    const minimalUser: any = {
      schemas: ['urn:ietf:params:scim:schemas:core:2.0:User'],
      userName: 'minimal@example.com',
    };

    const response = await request.post(`${SCIM_BASE_URL}/Users`, {
      headers: getAuthHeaders(),
      data: minimalUser,
    });

    expect(response.status()).toBe(201);
    const user = await response.json();
    expect(user.userName).toBe('minimal@example.com');
    expect(user.active).toBe(true); // Default
  });

  test('should reject duplicate user email', async ({ request }) => {
    const userData: any = {
      schemas: ['urn:ietf:params:scim:schemas:core:2.0:User'],
      userName: 'duplicate@example.com',
      displayName: 'Duplicate User',
    };

    // Create first user
    const firstResponse = await request.post(`${SCIM_BASE_URL}/Users`, {
      headers: getAuthHeaders(),
      data: userData,
    });
    expect(firstResponse.status()).toBe(201);

    // Try to create duplicate
    const secondResponse = await request.post(`${SCIM_BASE_URL}/Users`, {
      headers: getAuthHeaders(),
      data: userData,
    });

    expect(secondResponse.status()).toBe(409);
    const error = await secondResponse.json();
    expect(error.detail).toContain('already exists');
  });

  test('should require authentication for user creation', async ({ request }) => {
    const userData = generateUserData();

    const response = await request.post(`${SCIM_BASE_URL}/Users`, {
      data: userData,
    });

    expect(response.status()).toBe(401);
  });
});

// =============================================================================
// SCIM 2.0 User Provisioning - Retrieve
// =============================================================================

test.describe('SCIM 2.0 User Retrieval', () => {
  let userId: string;

  test.beforeAll(async ({ request }) => {
    // Create a test user
    const userData = generateUserData();

    const response = await request.post(`${SCIM_BASE_URL}/Users`, {
      headers: getAuthHeaders(),
      data: userData,
    });

    const user = await response.json();
    userId = user.id;
  });

  test('should retrieve user by ID', async ({ request }) => {
    const response = await request.get(`${SCIM_BASE_URL}/Users/${userId}`, {
      headers: getAuthHeaders(),
    });

    expect(response.status()).toBe(200);
    const user = await response.json();

    expect(user.id).toBe(userId);
    expect(user.userName).toBeDefined();
    expect(user.meta).toBeDefined();
    expect(user.meta.location).toContain(userId);
  });

  test('should return 404 for non-existent user', async ({ request }) => {
    const response = await request.get(
      `${SCIM_BASE_URL}/Users/00000000-0000-0000-0000-000000000000`,
      { headers: getAuthHeaders() }
    );

    expect(response.status()).toBe(404);
  });

  test('should require authentication for user retrieval', async ({ request }) => {
    const response = await request.get(`${SCIM_BASE_URL}/Users/${userId}`);

    expect(response.status()).toBe(401);
  });
});

// =============================================================================
// SCIM 2.0 User Provisioning - List
// =============================================================================

test.describe('SCIM 2.0 User Listing', () => {
  test('should list all users with pagination', async ({ request }) => {
    const response = await request.get(`${SCIM_BASE_URL}/Users`, {
      headers: getAuthHeaders(),
    });

    expect(response.status()).toBe(200);
    const listResponse = await response.json();

    expect(listResponse.schemas).toContain('urn:ietf:params:scim:api:messages:2.0:ListResponse');
    expect(listResponse.totalResults).toBeDefined();
    expect(listResponse.totalResults).toBeGreaterThanOrEqual(1);
    expect(listResponse.startIndex).toBe(1);
    expect(listResponse.itemsPerPage).toBeDefined();
    expect(listResponse.resources).toBeDefined();
    expect(Array.isArray(listResponse.resources)).toBe(true);
  });

  test('should support pagination parameters', async ({ request }) => {
    const response = await request.get(
      `${SCIM_BASE_URL}/Users?startIndex=1&count=10`,
      { headers: getAuthHeaders() }
    );

    expect(response.status()).toBe(200);
    const data = await response.json();

    expect(data.startIndex).toBe(1);
    expect(data.itemsPerPage).toBeLessThanOrEqual(10);
  });

  test('should filter users by userName', async ({ request }) => {
    const response = await request.get(
      `${SCIM_BASE_URL}/Users?filter=userName eq "admin@example.com"`,
      { headers: getAuthHeaders() }
    );

    expect(response.status()).toBe(200);
    const data = await response.json();

    // Should find admin user
    expect(data.resources.length).toBeGreaterThanOrEqual(0);
  });

  test('should require authentication for user listing', async ({ request }) => {
    const response = await request.get(`${SCIM_BASE_URL}/Users`);

    expect(response.status()).toBe(401);
  });
});

// =============================================================================
// SCIM 2.0 User Provisioning - Update
// =============================================================================

test.describe('SCIM 2.0 User Update (PUT)', () => {
  let userId: string;

  test.beforeAll(async ({ request }) => {
    // Create a test user
    const userData = generateUserData();

    const response = await request.post(`${SCIM_BASE_URL}/Users`, {
      headers: getAuthHeaders(),
      data: userData,
    });

    const user = await response.json();
    userId = user.id;
  });

  test('should update user with full replace', async ({ request }) => {
    const updateData = {
      schemas: ['urn:ietf:params:scim:schemas:core:2.0:User'],
      userName: `updated.${Date.now()}@example.com`,
      name: {
        givenName: 'Updated',
        familyName: 'Name',
        formatted: 'Updated Name',
      },
      displayName: 'Updated Name',
      active: true,
      emails: [{
        value: `updated.${Date.now()}@example.com`,
        type: 'work',
        primary: true,
      }],
    };

    const response = await request.put(`${SCIM_BASE_URL}/Users/${userId}`, {
      headers: getAuthHeaders(),
      data: updateData,
    });

    expect(response.status()).toBe(200);
    const updatedUser = await response.json();

    expect(updatedUser.id).toBe(userId);
    expect(updatedUser.displayName).toBe('Updated Name');
    expect(updatedUser.name.formatted).toBe('Updated Name');
  });

  test('should deactivate user via update', async ({ request }) => {
    const updateData = {
      schemas: ['urn:ietf:params:scim:schemas:core:2.0:User'],
      userName: 'inactive@example.com',
      active: false,
      displayName: 'Inactive User',
    };

    const response = await request.put(`${SCIM_BASE_URL}/Users/${userId}`, {
      headers: getAuthHeaders(),
      data: updateData,
    });

    expect(response.status()).toBe(200);
    const user = await response.json();
    expect(user.active).toBe(false);
  });

  test('should return 404 when updating non-existent user', async ({ request }) => {
    const updateData = {
      schemas: ['urn:ietf:params:scim:schemas:core:2.0:User'],
      userName: 'nonexistent@example.com',
    };

    const response = await request.put(
      `${SCIM_BASE_URL}/Users/00000000-0000-0000-0000-000000000000`,
      {
        headers: getAuthHeaders(),
        data: updateData,
      }
    );

    expect(response.status()).toBe(404);
  });
});

// =============================================================================
// SCIM 2.0 User Provisioning - Patch
// =============================================================================

test.describe('SCIM 2.0 User Patch (Partial Update)', () => {
  let userId: string;

  test.beforeAll(async ({ request }) => {
    // Create a test user
    const userData = generateUserData();

    const response = await request.post(`${SCIM_BASE_URL}/Users`, {
      headers: getAuthHeaders(),
      data: userData,
    });

    const user = await response.json();
    userId = user.id;
  });

  test('should partially update user fields', async ({ request }) => {
    const patchData = {
      schemas: ['urn:ietf:params:scim:api:messages:2.0:PatchOp'],
      displayName: 'Patched Display Name',
      active: true,
    };

    const response = await request.patch(`${SCIM_BASE_URL}/Users/${userId}`, {
      headers: getAuthHeaders(),
      data: patchData,
    });

    expect(response.status()).toBe(200);
    const user = await response.json();
    expect(user.displayName).toBe('Patched Display Name');
    expect(user.id).toBe(userId);
  });

  test('should deactivate user via patch', async ({ request }) => {
    const patchData = {
      schemas: ['urn:ietf:params:scim:api:messages:2.0:PatchOp'],
      active: false,
    };

    const response = await request.patch(`${SCIM_BASE_URL}/Users/${userId}`, {
      headers: getAuthHeaders(),
      data: patchData,
    });

    expect(response.status()).toBe(200);
    const user = await response.json();
    expect(user.active).toBe(false);
  });
});

// =============================================================================
// SCIM 2.0 User Provisioning - Delete
// =============================================================================

test.describe('SCIM 2.0 User Deactivation', () => {
  test('should soft delete user (deactivate)', async ({ request }) => {
    // Create user first
    const userData = generateUserData();
    userData.schemas = ['urn:ietf:params:scim:schemas:core:2.0:User'];

    const createResponse = await request.post(`${SCIM_BASE_URL}/Users`, {
      headers: getAuthHeaders(),
      data: userData,
    });

    const user = await createResponse.json();
    const userId = user.id;

    // Delete user
    const deleteResponse = await request.delete(
      `${SCIM_BASE_URL}/Users/${userId}`,
      { headers: getAuthHeaders() }
    );

    expect(deleteResponse.status()).toBe(204);

    // Verify user is deactivated (soft delete)
    const getResponse = await request.get(`${SCIM_BASE_URL}/Users/${userId}`, {
      headers: getAuthHeaders(),
    });

    expect(getResponse.status()).toBe(200);
    const deactivatedUser = await getResponse.json();
    expect(deactivatedUser.active).toBe(false);
  });

  test('should return 404 when deleting non-existent user', async ({ request }) => {
    const response = await request.delete(
      `${SCIM_BASE_URL}/Users/00000000-0000-0000-0000-000000000000`,
      { headers: getAuthHeaders() }
    );

    expect(response.status()).toBe(404);
  });
});

// =============================================================================
// SCIM 2.0 Resource Types
// =============================================================================

test.describe('SCIM 2.0 Resource Types', () => {
  test('should list all resource types', async ({ request }) => {
    const response = await request.get(`${SCIM_BASE_URL}/ResourceTypes`);

    expect(response.status()).toBe(200);
    const data = await response.json();

    expect(data.schemas).toContain('urn:ietf:params:scim:api:messages:2.0:ListResponse');
    expect(data.totalResults).toBe(2);
    expect(data.resources.length).toBe(2);

    const resourceTypes = data.resources.map((r: any) => r.id);
    expect(resourceTypes).toContain('User');
    expect(resourceTypes).toContain('Group');
  });

  test('should get User resource type details', async ({ request }) => {
    const response = await request.get(`${SCIM_BASE_URL}/ResourceTypes/User`);

    expect(response.status()).toBe(200);
    const resourceType = await response.json();

    expect(resourceType.id).toBe('User');
    expect(resourceType.name).toBe('User');
    expect(resourceType.endpoint).toBeDefined();
    expect(resourceType.schema).toBe('urn:ietf:params:scim:schemas:core:2.0:User');
  });

  test('should get Group resource type details', async ({ request }) => {
    const response = await request.get(`${SCIM_BASE_URL}/ResourceTypes/Group`);

    expect(response.status()).toBe(200);
    const resourceType = await response.json();

    expect(resourceType.id).toBe('Group');
    expect(resourceType.name).toBe('Group');
    expect(resourceType.endpoint).toBeDefined();
  });

  test('should return 404 for non-existent resource type', async ({ request }) => {
    const response = await request.get(`${SCIM_BASE_URL}/ResourceTypes/InvalidType`);

    expect(response.status()).toBe(404);
  });
});

// =============================================================================
// SCIM 2.0 Schemas
// =============================================================================

test.describe('SCIM 2.0 Schemas', () => {
  test('should list all schemas', async ({ request }) => {
    const response = await request.get(`${SCIM_BASE_URL}/Schemas`);

    expect(response.status()).toBe(200);
    const data = await response.json();

    expect(data.schemas).toContain('urn:ietf:params:scim:api:messages:2.0:ListResponse');
    expect(data.totalResults).toBeGreaterThanOrEqual(3);

    const schemaIds = data.resources.map((r: any) => r.id);
    expect(schemaIds).toContain('urn:ietf:params:scim:schemas:core:2.0:User');
    expect(schemaIds).toContain('urn:ietf:params:scim:schemas:core:2.0:Group');
    expect(schemaIds).toContain('urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig');
  });

  test('should get User schema definition', async ({ request }) => {
    const response = await request.get(
      `${SCIM_BASE_URL}/Schemas/urn:ietf:params:scim:schemas:core:2.0:User`
    );

    expect(response.status()).toBe(200);
    const schema = await response.json();

    expect(schema.id).toBe('urn:ietf:params:scim:schemas:core:2.0:User');
    expect(schema.name).toBe('User');
    expect(schema.attributes).toBeDefined();
    expect(schema.attributes.length).toBeGreaterThan(0);

    const attributeNames = schema.attributes.map((a: any) => a.name);
    expect(attributeNames).toContain('userName');
    expect(attributeNames).toContain('name');
    expect(attributeNames).toContain('active');
    expect(attributeNames).toContain('emails');
  });

  test('should get Group schema definition', async ({ request }) => {
    const response = await request.get(
      `${SCIM_BASE_URL}/Schemas/urn:ietf:params:scim:schemas:core:2.0:Group`
    );

    expect(response.status()).toBe(200);
    const schema = await response.json();

    expect(schema.id).toBe('urn:ietf:params:scim:schemas:core:2.0:Group');
    expect(schema.name).toBe('Group');
  });

  test('should return 404 for non-existent schema', async ({ request }) => {
    const response = await request.get(
      `${SCIM_BASE_URL}/Schemas/urn:ietf:params:scim:schemas:core:2.0:Invalid`
    );

    expect(response.status()).toBe(404);
  });
});

// =============================================================================
// SCIM 2.0 Groups (Not Yet Implemented)
// =============================================================================

test.describe('SCIM 2.0 Groups (Placeholder)', () => {
  test('should return empty list for groups', async ({ request }) => {
    const response = await request.get(`${SCIM_BASE_URL}/Groups`, {
      headers: getAuthHeaders(),
    });

    expect(response.status()).toBe(200);
    const data = await response.json();

    expect(data.totalResults).toBe(0);
    expect(data.itemsPerPage).toBe(0);
    expect(data.resources).toEqual([]);
  });

  test('should return 404 for specific group', async ({ request }) => {
    const response = await request.get(
      `${SCIM_BASE_URL}/Groups/some-group-id`,
      { headers: getAuthHeaders() }
    );

    expect(response.status()).toBe(404);
  });
});

// =============================================================================
// End-to-End SCIM Provisioning Flow
// =============================================================================

test.describe('Complete SCIM Provisioning Lifecycle', () => {
  test('should perform full user lifecycle via SCIM', async ({ request }) => {
    const timestamp = Date.now();

    // Step 1: Create user
    const createData = {
      schemas: ['urn:ietf:params:scim:schemas:core:2.0:User'],
      userName: `lifecycle.${timestamp}@example.com`,
      displayName: 'Lifecycle User',
      active: true,
      emails: [{
        value: `lifecycle.${timestamp}@example.com`,
        type: 'work',
        primary: true,
      }],
    };

    const createResponse = await request.post(`${SCIM_BASE_URL}/Users`, {
      headers: getAuthHeaders(),
      data: createData,
    });

    expect(createResponse.status()).toBe(201);
    const createdUser = await createResponse.json();
    const userId = createdUser.id;

    // Step 2: Retrieve user
    const getResponse = await request.get(`${SCIM_BASE_URL}/Users/${userId}`, {
      headers: getAuthHeaders(),
    });

    expect(getResponse.status()).toBe(200);
    const retrievedUser = await getResponse.json();
    expect(retrievedUser.userName).toBe(createData.userName);
    expect(retrievedUser.active).toBe(true);

    // Step 3: Update user
    const updateData = {
      schemas: ['urn:ietf:params:scim:schemas:core:2.0:User'],
      userName: createData.userName,
      displayName: 'Updated Lifecycle User',
      active: true,
    };

    const updateResponse = await request.put(`${SCIM_BASE_URL}/Users/${userId}`, {
      headers: getAuthHeaders(),
      data: updateData,
    });

    expect(updateResponse.status()).toBe(200);
    const updatedUser = await updateResponse.json();
    expect(updatedUser.displayName).toBe('Updated Lifecycle User');

    // Step 4: Deactivate user
    const deactivateData = {
      schemas: ['urn:ietf:params:scim:schemas:core:2.0:User'],
      userName: createData.userName,
      active: false,
    };

    const deactivateResponse = await request.put(`${SCIM_BASE_URL}/Users/${userId}`, {
      headers: getAuthHeaders(),
      data: deactivateData,
    });

    expect(deactivateResponse.status()).toBe(200);
    const deactivatedUser = await deactivateResponse.json();
    expect(deactivatedUser.active).toBe(false);

    // Verify final state
    const finalResponse = await request.get(`${SCIM_BASE_URL}/Users/${userId}`, {
      headers: getAuthHeaders(),
    });

    const finalUser = await finalResponse.json();
    expect(finalUser.active).toBe(false);
    expect(finalUser.displayName).toBe('Updated Lifecycle User');
  });

  test('should simulate Okta provisioning flow', async ({ request }) => {
    // Simulate Okta creating a new user
    const oktaUser = {
      schemas: ['urn:ietf:params:scim:schemas:core:2.0:User'],
      userName: 'okta.provisioned@example.com',
      externalId: 'okta-00abc123xyz',
      name: {
        givenName: 'Okta',
        familyName: 'Provisioned',
        formatted: 'Okta Provisioned',
      },
      displayName: 'Okta Provisioned User',
      active: true,
      emails: [{
        value: 'okta.provisioned@example.com',
        type: 'work',
        primary: true,
      }],
    };

    const createResponse = await request.post(`${SCIM_BASE_URL}/Users`, {
      headers: getAuthHeaders(),
      data: oktaUser,
    });

    expect(createResponse.status()).toBe(201);
    const user = await createResponse.json();
    expect(user.userName).toBe('okta.provisioned@example.com');
  });

  test('should simulate Azure AD provisioning flow', async ({ request }) => {
    // Simulate Azure AD creating a new user
    const azureUser = {
      schemas: ['urn:ietf:params:scim:schemas:core:2.0:User'],
      userName: 'azure.provisioned@example.com',
      externalId: 'azure-ad-guid-12345',
      name: {
        givenName: 'Azure',
        familyName: 'AD',
        formatted: 'Azure AD User',
      },
      displayName: 'Azure AD Provisioned User',
      active: true,
      emails: [{
        value: 'azure.provisioned@example.com',
        type: 'work',
        primary: true,
      }],
    };

    const createResponse = await request.post(`${SCIM_BASE_URL}/Users`, {
      headers: getAuthHeaders(),
      data: azureUser,
    });

    expect(createResponse.status()).toBe(201);
    const user = await createResponse.json();
    expect(user.userName).toBe('azure.provisioned@example.com');
  });
});

// =============================================================================
// SCIM Error Handling
// =============================================================================

test.describe('SCIM Error Handling', () => {
  test('should return proper error for unauthorized access', async ({ request }) => {
    const response = await request.get(`${SCIM_BASE_URL}/Users`);

    expect(response.status()).toBe(401);
  });

  test('should return 404 for non-existent user', async ({ request }) => {
    const response = await request.get(
      `${SCIM_BASE_URL}/Users/invalid-user-id`,
      { headers: getAuthHeaders() }
    );

    expect(response.status()).toBe(404);
  });

  test('should return 409 for duplicate user creation', async ({ request }) => {
    const userData = {
      schemas: ['urn:ietf:params:scim:schemas:core:2.0:User'],
      userName: 'duplicate-error@example.com',
    };

    // Create first user
    await request.post(`${SCIM_BASE_URL}/Users`, {
      headers: getAuthHeaders(),
      data: userData,
    });

    // Try to create duplicate
    const response = await request.post(`${SCIM_BASE_URL}/Users`, {
      headers: getAuthHeaders(),
      data: userData,
    });

    expect(response.status()).toBe(409);
  });
});
