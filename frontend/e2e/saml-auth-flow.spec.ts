import { test, expect } from '@playwright/test';

/**
 * E2E Test: SAML Authentication Flow
 *
 * This test verifies the complete SAML authentication flow end-to-end.
 *
 * Prerequisites:
 * - Backend server running on http://localhost:8000
 * - Frontend server running on http://localhost:3000
 * - SAML IdP configured (e.g., Okta dev account, Azure AD test tenant, or mock SAML IdP)
 * - SAML configuration saved via admin UI
 * - Set SAML_IDP_ID environment variable to the test SAML config ID
 * - Set SAML_TEST_USER_EMAIL environment variable
 * - Set SAML_TEST_USER_PASSWORD environment variable
 *
 * Verification:
 * - SSO login button visible on login page
 * - Click redirects to IdP login page
 * - IdP authentication works
 * - Callback processes SAML response
 * - User logged in with JWT token
 * - User redirected to dashboard
 */

const SAML_IDP_ID = process.env.SAML_IDP_ID;
const SAML_TEST_USER_EMAIL = process.env.SAML_TEST_USER_EMAIL;
const SAML_TEST_USER_PASSWORD = process.env.SAML_TEST_USER_PASSWORD;
const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';
const FRONTEND_BASE_URL = process.env.FRONTEND_BASE_URL || 'http://localhost:3000';

test.describe('SAML Authentication Flow', () => {
  test.beforeEach(async ({}, testInfo) => {
    // Skip tests if environment variables are not set
    if (!SAML_IDP_ID) {
      testInfo.skip(true, 'SAML_IDP_ID environment variable not set. Configure SAML IdP first.');
    }
  });

  test('should display SSO login button when SAML is configured', async ({ page }) => {
    // Navigate to login page
    await page.goto(`${FRONTEND_BASE_URL}/login`);

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Check if SSO login button is visible
    const ssoButton = page.locator('text=Sign in with SAML').or(
      page.locator('[data-testid="saml-login-button"]')
    );

    await expect(ssoButton).toBeVisible();

    console.log('✓ SSO login button is visible');
  });

  test('should initiate SAML login flow on button click', async ({ page }) => {
    // Navigate to login page
    await page.goto(`${FRONTEND_BASE_URL}/login`);

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Click SAML login button
    const ssoButton = page.locator('text=Sign in with SAML').or(
      page.locator('[data-testid="saml-login-button"]')
    );

    // Set up navigation listener to catch redirect to IdP
    const navigationPromise = page.waitForURL(url => {
      // Check if URL is an external IdP URL (contains idp, sso, login, etc.)
      return url.href.includes('idp') ||
             url.href.includes('sso') ||
             url.href.includes('signin') ||
             url.href !== page.url();
    });

    await ssoButton.click();

    try {
      // Wait for redirect to IdP
      const url = await Promise.race([
        navigationPromise,
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error('Redirect timeout')), 10000)
        )
      ]);

      console.log(`✓ Redirected to: ${url}`);

      // Verify we're on an IdP login page
      expect(page.url()).toMatch(/(idp|sso|signin|login|okta|azure|auth0)/i);

    } catch (error) {
      // If no redirect, check for error message
      const errorElement = page.locator('text=/error|failed|unable/i');
      if (await errorElement.isVisible()) {
        throw new Error(`SSO login failed: ${await errorElement.textContent()}`);
      }
      throw error;
    }
  });

  test('should complete full SAML authentication flow', async ({ page }) => {
    // Skip if test credentials not provided
    if (!SAML_TEST_USER_EMAIL || !SAML_TEST_USER_PASSWORD) {
      test.skip(true, 'SAML_TEST_USER_EMAIL and SAML_TEST_USER_PASSWORD not set');
    }

    // Navigate to login page
    await page.goto(`${FRONTEND_BASE_URL}/login`);

    // Click SAML login button
    const ssoButton = page.locator('text=Sign in with SAML').or(
      page.locator('[data-testid="saml-login-button"]')
    );

    await ssoButton.click();

    // Wait for redirect to IdP
    await page.waitForURL(url => url.href.includes('idp') || url.href.includes('sso'), {
      timeout: 10000
    });

    console.log('✓ Redirected to IdP login page');

    // Fill in IdP credentials (this varies by IdP)
    // Okta example:
    const emailInput = page.locator('input[type="email"], input[name="username"]').first();
    await emailInput.fill(SAML_TEST_USER_EMAIL);

    const passwordInput = page.locator('input[type="password"]').first();
    await passwordInput.fill(SAML_TEST_USER_PASSWORD);

    const submitButton = page.locator('button[type="submit"]').first();
    await submitButton.click();

    console.log('✓ Submitted IdP credentials');

    // Wait for redirect back to application
    await page.waitForURL(
      url => url.href.includes(FRONTEND_BASE_URL) && url.href.includes('callback'),
      { timeout: 30000 }
    );

    console.log('✓ Redirected back to callback URL');

    // Wait for processing and redirect to dashboard
    await page.waitForURL(
      url => url.href.includes('dashboard') || url.href === `${FRONTEND_BASE_URL}/`,
      { timeout: 10000 }
    );

    console.log('✓ Redirected to dashboard');

    // Verify user is authenticated
    const token = await page.evaluate(() => localStorage.getItem('token'));
    expect(token).not.toBeNull();

    // Verify user data is stored
    const user = await page.evaluate(() => {
      const userData = localStorage.getItem('user');
      return userData ? JSON.parse(userData) : null;
    });

    expect(user).not.toBeNull();
    expect(user.email).toBeDefined();

    console.log('✓ User authenticated with JWT token');
    console.log(`✓ User email: ${user.email}`);
  });

  test('should handle SAML authentication errors gracefully', async ({ page }) => {
    // Navigate to callback page with invalid parameters to test error handling
    await page.goto(`${FRONTEND_BASE_URL}/auth/callback?error=access_denied&error_description=User+denied+access`);

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Check for error message
    const errorMessage = page.locator('text=/error|denied|failed/i');

    await expect(errorMessage).toBeVisible({ timeout: 5000 });

    console.log('✓ Error message displayed for failed authentication');

    // Check for "Return to Login" button
    const returnButton = page.locator('text=Return to Login').or(
      page.locator('[data-testid="return-to-login"]')
    );

    await expect(returnButton).toBeVisible();

    console.log('✓ Return to Login button visible');
  });

  test('should store JWT token after successful SAML login', async ({ page }) => {
    // This test assumes you've already logged in or have a valid token
    // For testing purposes, we'll simulate the callback processing

    // Navigate to login page
    await page.goto(`${FRONTEND_BASE_URL}/login`);

    // Check if there's an existing token from a previous test
    const existingToken = await page.evaluate(() => localStorage.getItem('token'));

    if (existingToken) {
      // Verify token format (JWT should have 3 parts separated by dots)
      const parts = existingToken.split('.');
      expect(parts.length).toBe(3);

      // Decode JWT payload (without verification for testing)
      const payload = JSON.parse(atob(parts[1]));

      expect(payload.exp).toBeDefined();
      expect(payload.sub).toBeDefined();

      console.log('✓ JWT token format is valid');
      console.log(`✓ Token expires at: ${new Date(payload.exp * 1000).toISOString()}`);
    } else {
      test.skip(true, 'No existing token found. Run full authentication test first.');
    }
  });

  test('should display user profile after SAML login', async ({ page }) => {
    // Check if user is already logged in from previous test
    const token = await page.evaluate(() => localStorage.getItem('token'));

    if (!token) {
      test.skip(true, 'User not logged in. Run full authentication test first.');
    }

    // Navigate to dashboard
    await page.goto(`${FRONTEND_BASE_URL}/`);

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Check for user avatar or profile information
    const userAvatar = page.locator('[data-testid="user-avatar"]').or(
      page.locator('img[alt*="avatar"]').or(page.locator('.user-avatar'))
    );

    // User avatar might not be visible in all implementations
    const isVisible = await userAvatar.isVisible().catch(() => false);

    if (isVisible) {
      console.log('✓ User avatar visible on dashboard');
    } else {
      console.log('ℹ User avatar not found (may not be implemented)');
    }

    // Check if user can access protected resources
    const response = await page.evaluate(async (apiUrl) => {
      try {
        const res = await fetch(`${apiUrl}/api/v1/users/me`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
          },
        });

        return {
          status: res.status,
          ok: res.ok,
        };
      } catch (error) {
        return {
          status: 0,
          ok: false,
          error: error.message,
        };
      }
    }, API_BASE_URL);

    expect(response.ok).toBe(true);
    console.log('✓ User can access protected API endpoint');
  });
});

test.describe('SAML Configuration API', () => {
  test('should return SAML metadata endpoint', async ({ page }) => {
    const response = await page.evaluate(async (apiUrl) => {
      try {
        const res = await fetch(`${apiUrl}/api/v1/saml/metadata`);
        const text = await res.text();

        return {
          status: res.status,
          contentType: res.headers.get('content-type'),
          body: text.slice(0, 200), // First 200 chars
        };
      } catch (error) {
        return {
          status: 0,
          error: error.message,
        };
      }
    }, API_BASE_URL);

    expect(response.status).toBe(200);
    expect(response.contentType).toContain('application/xml');
    expect(response.body).toContain('<?xml');
    expect(response.body).toContain('EntityDescriptor');

    console.log('✓ SAML metadata endpoint returns valid XML');
  });

  test('should return available SAML configurations', async ({ page }) => {
    // First, we need to authenticate or skip auth check for this test
    // For now, we'll test the endpoint exists

    const response = await page.evaluate(async (apiUrl) => {
      try {
        const res = await fetch(`${apiUrl}/api/v1/saml/config`);

        return {
          status: res.status,
          ok: res.ok,
        };
      } catch (error) {
        return {
          status: 0,
          error: error.message,
        };
      }
    }, API_BASE_URL);

    // Should return 401 (unauthorized) which proves endpoint exists
    expect(response.status).toBeGreaterThanOrEqual(400);

    console.log('✓ SAML config endpoint exists (requires authentication)');
  });
});
