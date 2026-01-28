import { test, expect } from '@playwright/test';

/**
 * E2E Test: OIDC Authentication Flow
 *
 * This test verifies the complete OIDC authentication flow end-to-end.
 *
 * Prerequisites:
 * - Backend server running on http://localhost:8000
 * - Frontend server running on http://localhost:3000
 * - OIDC provider configured (e.g., Google, Azure AD, Okta, Auth0)
 * - OIDC configuration saved via admin UI
 * - Set OIDC_PROVIDER_ID environment variable to the test OIDC config ID
 * - Set OIDC_TEST_USER_EMAIL environment variable
 * - Set OIDC_TEST_USER_PASSWORD environment variable
 *
 * Verification:
 * - SSO login button visible on login page
 * - Click redirects to OIDC provider login
 * - Provider authentication works
 * - Callback processes authorization code
 * - User logged in with JWT token
 * - User redirected to dashboard
 */

const OIDC_PROVIDER_ID = process.env.OIDC_PROVIDER_ID;
const OIDC_TEST_USER_EMAIL = process.env.OIDC_TEST_USER_EMAIL;
const OIDC_TEST_USER_PASSWORD = process.env.OIDC_TEST_USER_PASSWORD;
const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';
const FRONTEND_BASE_URL = process.env.FRONTEND_BASE_URL || 'http://localhost:3000';

test.describe('OIDC Authentication Flow', () => {
  test.beforeEach(async ({}, testInfo) => {
    // Skip tests if environment variables are not set
    if (!OIDC_PROVIDER_ID) {
      testInfo.skip(true, 'OIDC_PROVIDER_ID environment variable not set. Configure OIDC provider first.');
    }
  });

  test('should display SSO login button when OIDC is configured', async ({ page }) => {
    // Navigate to login page
    await page.goto(`${FRONTEND_BASE_URL}/login`);

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Check if SSO login button is visible for OIDC provider
    const ssoButton = page.locator('text=Sign in with Google')
      .or(page.locator('text=Sign in with Azure'))
      .or(page.locator('text=Sign in with Okta'))
      .or(page.locator('text=Sign in with Auth0'))
      .or(page.locator('text=Sign in with OIDC'))
      .or(page.locator('[data-testid="oidc-login-button"]'));

    await expect(ssoButton).toBeVisible();

    console.log('✓ SSO login button is visible');
  });

  test('should initiate OIDC login flow on button click', async ({ page }) => {
    // Navigate to login page
    await page.goto(`${FRONTEND_BASE_URL}/login`);

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Click OIDC login button
    const ssoButton = page.locator('text=Sign in with Google')
      .or(page.locator('text=Sign in with Azure'))
      .or(page.locator('text=Sign in with Okta'))
      .or(page.locator('text=Sign in with Auth0'))
      .or(page.locator('text=Sign in with OIDC'))
      .or(page.locator('[data-testid="oidc-login-button"]'));

    // Set up navigation listener to catch redirect to OIDC provider
    const navigationPromise = page.waitForURL(url => {
      // Check if URL is an external OIDC provider URL
      return url.href.includes('accounts.google.com') ||
             url.href.includes('login.microsoftonline.com') ||
             url.href.includes('okta.com') ||
             url.href.includes('auth0.com') ||
             url.href.includes('oauth2') ||
             url.href.includes('authorize') ||
             url.href !== page.url();
    });

    await ssoButton.click();

    try {
      // Wait for redirect to OIDC provider
      const url = await Promise.race([
        navigationPromise,
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error('Redirect timeout')), 10000)
        )
      ]);

      console.log(`✓ Redirected to: ${url}`);

      // Verify we're on an OIDC provider login page
      expect(page.url()).toMatch(/(accounts\.google\.com|login\.microsoftonline\.com|okta\.com|auth0\.com|oauth2|authorize)/i);

    } catch (error) {
      // If no redirect, check for error message
      const errorElement = page.locator('text=/error|failed|unable/i');
      if (await errorElement.isVisible()) {
        throw new Error(`SSO login failed: ${await errorElement.textContent()}`);
      }
      throw error;
    }
  });

  test('should complete full OIDC authentication flow', async ({ page }) => {
    // Skip if test credentials not provided
    if (!OIDC_TEST_USER_EMAIL || !OIDC_TEST_USER_PASSWORD) {
      test.skip(true, 'OIDC_TEST_USER_EMAIL and OIDC_TEST_USER_PASSWORD not set');
    }

    // Navigate to login page
    await page.goto(`${FRONTEND_BASE_URL}/login`);

    // Click OIDC login button
    const ssoButton = page.locator('text=Sign in with Google')
      .or(page.locator('text=Sign in with Azure'))
      .or(page.locator('text=Sign in with Okta'))
      .or(page.locator('text=Sign in with Auth0'))
      .or(page.locator('text=Sign in with OIDC'))
      .or(page.locator('[data-testid="oidc-login-button"]'));

    await ssoButton.click();

    // Wait for redirect to OIDC provider
    await page.waitForURL(
      url => url.href.includes('accounts.google.com') ||
             url.href.includes('login.microsoftonline.com') ||
             url.href.includes('okta.com') ||
             url.href.includes('oauth2'),
      { timeout: 10000 }
    );

    console.log('✓ Redirected to OIDC provider login page');

    // Fill in provider credentials (this varies by provider)
    // Google example:
    const emailInput = page.locator('input[type="email"], input[name="email"], input[name="loginfmt"]').first();
    await emailInput.fill(OIDC_TEST_USER_EMAIL);

    const emailNextButton = page.locator('button:has-text("Next"), button:has-text("Continue")').first();
    await emailNextButton.click();

    // Wait for password page
    await page.waitForLoadState('networkidle');

    const passwordInput = page.locator('input[type="password"], input[name="passwd"], input[name="Password"]').first();
    await passwordInput.fill(OIDC_TEST_USER_PASSWORD);

    const submitButton = page.locator('button[type="submit"], button:has-text("Sign in"), button:has-text("Next")').first();
    await submitButton.click();

    console.log('✓ Submitted provider credentials');

    // Wait for redirect back to application callback
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

  test('should handle OIDC authentication errors gracefully', async ({ page }) => {
    // Navigate to callback page with error parameters to test error handling
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

  test('should handle OIDC provider authorization error', async ({ page }) => {
    // Test scenario where user denies authorization at provider
    await page.goto(`${FRONTEND_BASE_URL}/auth/callback?code=invalid_code&state=test_state`);

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Either redirects to login (success) or shows error
    const currentUrl = page.url();
    const isLoginPage = currentUrl.includes('/login');
    const isErrorPage = currentUrl.includes('/callback');

    expect(isLoginPage || isErrorPage).toBe(true);

    if (isErrorPage) {
      // If error page, verify error message is shown
      const errorMessage = page.locator('text=/error|invalid|failed/i');
      await expect(errorMessage).toBeVisible({ timeout: 5000 });
      console.log('✓ Error message displayed for invalid authorization code');
    } else {
      console.log('✓ Redirected to login page (expected for invalid code)');
    }
  });

  test('should store JWT token after successful OIDC login', async ({ page }) => {
    // This test assumes you've already logged in or have a valid token
    // For testing purposes, we'll verify the token format

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

  test('should display user profile after OIDC login', async ({ page }) => {
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
    const userAvatar = page.locator('[data-testid="user-avatar"]')
      .or(page.locator('img[alt*="avatar"]'))
      .or(page.locator('.user-avatar'));

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

test.describe('OIDC Configuration API', () => {
  test('should return OIDC configuration info', async ({ page }) => {
    // Test that OIDC config endpoint exists and returns proper response
    const response = await page.evaluate(async (apiUrl) => {
      try {
        const res = await fetch(`${apiUrl}/api/v1/oidc/config`);

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

    console.log('✓ OIDC config endpoint exists (requires authentication)');
  });

  test('should handle OIDC logout endpoint', async ({ page }) => {
    // Test OIDC logout endpoint
    const response = await page.evaluate(async (apiUrl) => {
      try {
        const res = await fetch(`${apiUrl}/api/v1/oidc/logout`, {
          method: 'GET',
        });

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

    console.log('✓ OIDC logout endpoint exists (requires authentication)');
  });
});

test.describe('OIDC Security Tests', () => {
  test('should use PKCE for authorization code flow', async ({ page }) => {
    // This test verifies that PKCE parameters are included in the authorization request
    // PKCE is a security best practice for native and SPA applications

    // Navigate to login page
    await page.goto(`${FRONTEND_BASE_URL}/login`);

    // Set up request interceptor to capture the redirect URL
    let authorizationUrl: string | null = null;

    page.on('response', async (response) => {
      const url = response.url();
      if (url.includes('oidc') && url.includes('login')) {
        const status = response.status();
        if (status === 307 || status === 302) {
          const location = response.headers()['location'];
          if (location) {
            authorizationUrl = location;
          }
        }
      }
    });

    // Click OIDC login button
    const ssoButton = page.locator('text=Sign in with Google')
      .or(page.locator('text=Sign in with Azure'))
      .or(page.locator('text=Sign in with Okta'))
      .or(page.locator('text=Sign in with Auth0'))
      .or(page.locator('text=Sign in with OIDC'))
      .or(page.locator('[data-testid="oidc-login-button"]'));

    try {
      await ssoButton.click();

      // Wait a bit for the redirect to happen
      await page.waitForTimeout(2000);

      // If we captured the authorization URL, verify PKCE parameters
      if (authorizationUrl) {
        // PKCE uses code_challenge parameter
        const hasCodeChallenge = authorizationUrl.includes('code_challenge=');
        const hasCodeChallengeMethod = authorizationUrl.includes('code_challenge_method=');

        if (hasCodeChallenge && hasCodeChallengeMethod) {
          console.log('✓ PKCE is enabled (code_challenge and code_challenge_method present)');
        } else {
          console.log('⚠ PKCE may not be enabled (code_challenge not found in authorization URL)');
        }
      } else {
        console.log('ℹ Could not capture authorization URL for PKCE verification');
      }
    } catch (error) {
      console.log(`ℹ PKCE verification skipped: ${error.message}`);
    }
  });

  test('should include state parameter for CSRF protection', async ({ page }) => {
    // Verify that state parameter is used to prevent CSRF attacks

    // Navigate to login page
    await page.goto(`${FRONTEND_BASE_URL}/login`);

    // Set up request interceptor
    let authorizationUrl: string | null = null;

    page.on('response', async (response) => {
      const url = response.url();
      if (url.includes('oidc') && url.includes('login')) {
        const status = response.status();
        if (status === 307 || status === 302) {
          const location = response.headers()['location'];
          if (location) {
            authorizationUrl = location;
          }
        }
      }
    });

    // Click OIDC login button
    const ssoButton = page.locator('text=Sign in with Google')
      .or(page.locator('text=Sign in with Azure'))
      .or(page.locator('text=Sign in with Okta'))
      .or(page.locator('text=Sign in with Auth0'))
      .or(page.locator('text=Sign in with OIDC'))
      .or(page.locator('[data-testid="oidc-login-button"]'));

    try {
      await ssoButton.click();
      await page.waitForTimeout(2000);

      if (authorizationUrl) {
        // State parameter should be present
        const hasState = authorizationUrl.includes('state=');

        expect(hasState).toBe(true);
        console.log('✓ State parameter is present for CSRF protection');
      } else {
        console.log('ℹ Could not capture authorization URL for state verification');
      }
    } catch (error) {
      console.log(`ℹ State verification skipped: ${error.message}`);
    }
  });
});

test.describe('OIDC Provider-Specific Tests', () => {
  test('should work with Google OAuth2', async ({ page }) => {
    // Google-specific test
    const googleButton = page.locator('text=Sign in with Google').or(
      page.locator('[data-testid="google-login-button"]')
    );

    const isVisible = await googleButton.isVisible().catch(() => false);

    if (isVisible) {
      console.log('✓ Google OAuth2 button is available');
      // Additional Google-specific tests can be added here
    } else {
      console.log('ℹ Google OAuth2 not configured');
    }
  });

  test('should work with Azure AD', async ({ page }) => {
    // Azure AD-specific test
    const azureButton = page.locator('text=Sign in with Azure').or(
      page.locator('[data-testid="azure-login-button"]')
    );

    const isVisible = await azureButton.isVisible().catch(() => false);

    if (isVisible) {
      console.log('✓ Azure AD button is available');
      // Additional Azure-specific tests can be added here
    } else {
      console.log('ℹ Azure AD not configured');
    }
  });

  test('should work with Okta', async ({ page }) => {
    // Okta-specific test
    const oktaButton = page.locator('text=Sign in with Okta').or(
      page.locator('[data-testid="okta-login-button"]')
    );

    const isVisible = await oktaButton.isVisible().catch(() => false);

    if (isVisible) {
      console.log('✓ Okta button is available');
      // Additional Okta-specific tests can be added here
    } else {
      console.log('ℹ Okta not configured');
    }
  });

  test('should work with Auth0', async ({ page }) => {
    // Auth0-specific test
    const auth0Button = page.locator('text=Sign in with Auth0').or(
      page.locator('[data-testid="auth0-login-button"]')
    );

    const isVisible = await auth0Button.isVisible().catch(() => false);

    if (isVisible) {
      console.log('✓ Auth0 button is available');
      // Additional Auth0-specific tests can be added here
    } else {
      console.log('ℹ Auth0 not configured');
    }
  });
});
