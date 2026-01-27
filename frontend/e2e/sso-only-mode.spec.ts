/**
 * E2E Tests for SSO-Only Mode Enforcement
 *
 * Tests the SSO-only mode feature including:
 * - Local login disabled for regular users
 * - Admin recovery account access
 * - Registration disabled
 * - SSO login still works
 * - UI properly indicates SSO-only mode
 */

import { expect, test } from "@playwright/test";

// =============================================================================
// Test Configuration
// =============================================================================

const BASE_URL = process.env.BASE_URL || "http://localhost:3000";
const API_URL = process.env.API_URL || "http://localhost:8000";

// Test credentials
const ADMIN_RECOVERY_EMAIL = "admin-recovery@example.com";
const ADMIN_RECOVERY_PASSWORD = "adminPassword123";
const REGULAR_USER_EMAIL = "regularuser@example.com";
const REGULAR_USER_PASSWORD = "userPassword123";

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Setup SSO-only mode via API
 */
async function enableSSOOnlyMode(request: any) {
  await request.patch(`${API_URL}/api/v1/sso/settings`, {
    data: {
      sso_only_mode: true,
      sso_admin_recovery_email: ADMIN_RECOVERY_EMAIL,
    },
  });
}

/**
 * Disable SSO-only mode via API
 */
async function disableSSOOnlyMode(request: any) {
  await request.patch(`${API_URL}/api/v1/sso/settings`, {
    data: {
      sso_only_mode: false,
      sso_admin_recovery_email: null,
    },
  });
}

/**
 * Create test user via API
 */
async function createTestUser(request: any, email: string, password: string) {
  await request.post(`${API_URL}/api/v1/auth/register`, {
    data: {
      email,
      password,
      name: email.split("@")[0],
    },
  });
}

/**
 * Login via API
 */
async function loginViaAPI(request: any, email: string, password: string) {
  const response = await request.post(`${API_URL}/api/v1/auth/login`, {
    data: {
      email,
      password,
    },
  });

  if (!response.ok()) {
    return { success: false, status: response.status(), body: await response.text() };
  }

  const data = await response.json();
  return { success: true, token: data.access_token, user: data.user };
}

// =============================================================================
// SSO-Only Mode - Local Login Tests
// =============================================================================

test.describe("SSO-Only Mode - Local Login", () => {
  test.beforeEach(async ({ request }) => {
    // Ensure SSO-only mode is disabled before each test
    await disableSSOOnlyMode(request);
  });

  test.afterEach(async ({ request }) => {
    // Clean up - disable SSO-only mode
    await disableSSOOnlyMode(request);
  });

  test("should disable local login for regular users", async ({ page, request }) => {
    // Given: SSO-only mode is enabled and regular user exists
    await createTestUser(request, REGULAR_USER_EMAIL, REGULAR_USER_PASSWORD);
    await enableSSOOnlyMode(request);

    // When: Regular user navigates to login page
    await page.goto(`${BASE_URL}/login`);

    // Then: Login form should show SSO-only mode message
    await expect(page.locator("text=SSO-only mode is enabled")).toBeVisible();

    // When: Regular user attempts to login with email/password
    await page.fill('input[type="email"]', REGULAR_USER_EMAIL);
    await page.fill('input[type="password"]', REGULAR_USER_PASSWORD);
    await page.click('button[type="submit"]');

    // Then: Login should fail with SSO-only mode error
    await expect(page.locator("text=SSO-only mode is enabled")).toBeVisible();
    await expect(page.locator("text=Please use single sign-on")).toBeVisible();

    // And: User should not be redirected to dashboard
    expect(page.url()).not.toContain("/dashboard");
  });

  test("should allow admin recovery login in SSO-only mode", async ({ page, request }) => {
    // Given: SSO-only mode is enabled with admin recovery email
    await createTestUser(request, ADMIN_RECOVERY_EMAIL, ADMIN_RECOVERY_PASSWORD);
    await enableSSOOnlyMode(request);

    // When: Admin recovery user navigates to login page
    await page.goto(`${BASE_URL}/login`);

    // Then: SSO-only mode message should be visible
    await expect(page.locator("text=SSO-only mode")).toBeVisible();

    // When: Admin recovery user logs in
    await page.fill('input[type="email"]', ADMIN_RECOVERY_EMAIL);
    await page.fill('input[type="password"]', ADMIN_RECOVERY_PASSWORD);
    await page.click('button[type="submit"]');

    // Then: Login should succeed
    await page.waitForURL("**/dashboard**");
    expect(page.url()).toContain("/dashboard");

    // And: User should see their email in the UI
    await expect(page.locator(`text=${ADMIN_RECOVERY_EMAIL}`)).toBeVisible();
  });

  test("should work normally when SSO-only mode is disabled", async ({ page, request }) => {
    // Given: SSO-only mode is disabled and regular user exists
    await createTestUser(request, REGULAR_USER_EMAIL, REGULAR_USER_PASSWORD);

    // When: Regular user logs in
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[type="email"]', REGULAR_USER_EMAIL);
    await page.fill('input[type="password"]', REGULAR_USER_PASSWORD);
    await page.click('button[type="submit"]');

    // Then: Login should succeed
    await page.waitForURL("**/dashboard**");
    expect(page.url()).toContain("/dashboard");
  });
});

// =============================================================================
// SSO-Only Mode - Registration Tests
// =============================================================================

test.describe("SSO-Only Mode - Registration", () => {
  test.beforeEach(async ({ request }) => {
    await disableSSOOnlyMode(request);
  });

  test.afterEach(async ({ request }) => {
    await disableSSOOnlyMode(request);
  });

  test("should disable registration in SSO-only mode", async ({ page, request }) => {
    // Given: SSO-only mode is enabled
    await enableSSOOnlyMode(request);

    // When: User navigates to registration page
    await page.goto(`${BASE_URL}/register`);

    // Then: Registration should be disabled
    await expect(page.locator("text=SSO-only mode is enabled")).toBeVisible();
    await expect(
      page.locator("text=Please use single sign-on to register")
    ).toBeVisible();

    // Registration form might be hidden or disabled
    const registerButton = page.locator('button[type="submit"]');
    if (await registerButton.isVisible()) {
      await expect(registerButton).toBeDisabled();
    }
  });

  test("should show SSO registration option when SSO-only mode is enabled", async ({
    page,
    request,
  }) => {
    // Given: SSO-only mode is enabled
    await enableSSOOnlyMode(request);

    // When: User navigates to login page
    await page.goto(`${BASE_URL}/login`);

    // Then: SSO login buttons should be visible and enabled
    const ssoButton = page.locator('button:has-text("Sign in with")');
    await expect(ssoButton.first()).toBeVisible();
    await expect(ssoButton.first()).toBeEnabled();
  });
});

// =============================================================================
// SSO-Only Mode - Admin Configuration Tests
// =============================================================================

test.describe("SSO-Only Mode - Admin Configuration", () => {
  test("should allow admin to enable SSO-only mode", async ({ page, request }) => {
    // Given: Admin user is logged in
    await createTestUser(request, ADMIN_RECOVERY_EMAIL, ADMIN_RECOVERY_PASSWORD);
    const loginResult = await loginViaAPI(
      request,
      ADMIN_RECOVERY_EMAIL,
      ADMIN_RECOVERY_PASSWORD
    );

    // When: Admin navigates to SSO configuration page
    await page.goto(`${BASE_URL}/admin/sso`);

    // Then: SSO configuration form should be visible
    await expect(page.locator("h1:has-text('SSO Configuration')")).toBeVisible();

    // When: Admin enables SSO-only mode
    await page.click('input[type="checkbox"]#sso-only-mode');
    await page.fill('input[name="admin_recovery_email"]', ADMIN_RECOVERY_EMAIL);

    // And: Saves configuration
    await page.click('button:has-text("Save Settings")');

    // Then: Success message should be shown
    await expect(page.locator("text=Settings saved successfully")).toBeVisible();

    // And: Configuration should be persisted
    await page.reload();
    await expect(page.locator('input[type="checkbox"]#sso-only-mode')).toBeChecked();
    await expect(page.locator('input[name="admin_recovery_email"]')).toHaveValue(
      ADMIN_RECOVERY_EMAIL
    );
  });

  test("should validate admin recovery email format", async ({ page, request }) => {
    // Given: Admin is logged in
    await createTestUser(request, ADMIN_RECOVERY_EMAIL, ADMIN_RECOVERY_PASSWORD);
    await page.goto(`${BASE_URL}/admin/sso`);

    // When: Admin enters invalid email format
    await page.click('input[type="checkbox"]#sso-only-mode');
    await page.fill('input[name="admin_recovery_email"]', "invalid-email");

    // Then: Validation error should be shown
    await expect(page.locator("text=Invalid email format")).toBeVisible();

    // And: Save button should be disabled
    await expect(page.locator('button:has-text("Save Settings")')).toBeDisabled();
  });

  test("should warn when enabling SSO-only mode without admin recovery", async ({
    page,
    request,
  }) => {
    // Given: Admin is logged in
    await createTestUser(request, ADMIN_RECOVERY_EMAIL, ADMIN_RECOVERY_PASSWORD);
    await page.goto(`${BASE_URL}/admin/sso`);

    // When: Admin enables SSO-only mode without setting admin recovery email
    await page.click('input[type="checkbox"]#sso-only-mode');

    // Then: Warning message should be shown
    await expect(
      page.locator("text=Admin recovery email is strongly recommended")
    ).toBeVisible();
  });
});

// =============================================================================
// SSO-Only Mode - SSO Login Tests
// =============================================================================

test.describe("SSO-Only Mode - SSO Login", () => {
  test("should show SSO login options in SSO-only mode", async ({ page, request }) => {
    // Given: SSO-only mode is enabled
    await enableSSOOnlyMode(request);

    // When: User navigates to login page
    await page.goto(`${BASE_URL}/login`);

    // Then: SSO login buttons should be visible
    const ssoButtons = page.locator('button:has-text("Sign in with")');
    await expect(ssoButtons.first()).toBeVisible();

    // And: SSO buttons should be enabled
    await expect(ssoButtons.first()).toBeEnabled();

    // And: Local login form should show SSO-only message
    await expect(page.locator("text=SSO-only mode")).toBeVisible();
  });

  test("should redirect SSO login to IdP in SSO-only mode", async ({ page, request }) => {
    // Given: SSO-only mode is enabled with SAML configured
    await enableSSOOnlyMode(request);

    // When: User clicks SAML login button
    await page.goto(`${BASE_URL}/login`);
    const samlButton = page.locator('button:has-text("Sign in with SAML")');

    if (await samlButton.isVisible()) {
      // Note: In a real test, this would redirect to IdP
      // For testing, we verify the click action initiates the flow
      await Promise.all([
        page.waitForURL(/\/api\/v1\/saml/),
        samlButton.click(),
      ]);

      // Then: User should be redirected to SAML login
      expect(page.url()).toContain("/api/v1/saml");
    }
  });
});

// =============================================================================
// SSO-Only Mode - Security Tests
// =============================================================================

test.describe("SSO-Only Mode - Security", () => {
  test("should not allow password reset in SSO-only mode", async ({ page, request }) => {
    // Given: SSO-only mode is enabled
    await enableSSOOnlyMode(request);

    // When: User navigates to password reset page
    await page.goto(`${BASE_URL}/forgot-password`);

    // Then: SSO-only mode message should be shown
    await expect(
      page.locator("text=SSO-only mode is enabled")
    ).toBeVisible();

    // And: Password reset form should be disabled or hidden
    const resetButton = page.locator('button[type="submit"]');
    if (await resetButton.isVisible()) {
      await expect(resetButton).toBeDisabled();
    }
  });

  test("should show clear error message for local login attempts", async ({ page, request }) => {
    // Given: SSO-only mode is enabled
    await enableSSOOnlyMode(request);

    // When: User attempts to login with credentials
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[type="email"]', REGULAR_USER_EMAIL);
    await page.fill('input[type="password"]', REGULAR_USER_PASSWORD);
    await page.click('button[type="submit"]');

    // Then: Clear error message should be shown
    await expect(page.locator("text=SSO-only mode")).toBeVisible();
    await expect(
      page.locator("text=Please use single sign-on to login")
    ).toBeVisible();
  });

  test("should not expose admin recovery email to users", async ({ page, request }) => {
    // Given: SSO-only mode is enabled
    await enableSSOOnlyMode(request);

    // When: Regular user views login page
    await page.goto(`${BASE_URL}/login`);

    // Then: Admin recovery email should not be visible in the UI
    const adminEmail = page.locator(`text=${ADMIN_RECOVERY_EMAIL}`);
    await expect(adminEmail).not.toBeVisible();

    // And: SSO-only mode message should be generic
    await expect(page.locator("text=SSO-only mode")).toBeVisible();
  });
});

// =============================================================================
// SSO-Only Mode - Integration Tests
// =============================================================================

test.describe("SSO-Only Mode - Integration", () => {
  test("should maintain SSO-only mode across page navigation", async ({ page, request }) => {
    // Given: SSO-only mode is enabled
    await enableSSOOnlyMode(request);

    // When: User navigates between pages
    await page.goto(`${BASE_URL}/login`);
    await expect(page.locator("text=SSO-only mode")).toBeVisible();

    await page.goto(`${BASE_URL}/register`);
    await expect(page.locator("text=SSO-only mode")).toBeVisible();

    await page.goto(`${BASE_URL}/forgot-password`);
    await expect(page.locator("text=SSO-only mode")).toBeVisible();

    // Then: SSO-only mode message should be consistent
  });

  test("should allow admin to disable SSO-only mode", async ({ page, request }) => {
    // Given: SSO-only mode is enabled
    await enableSSOOnlyMode(request);
    await createTestUser(request, ADMIN_RECOVERY_EMAIL, ADMIN_RECOVERY_PASSWORD);

    // When: Admin logs in and disables SSO-only mode
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[type="email"]', ADMIN_RECOVERY_EMAIL);
    await page.fill('input[type="password"]', ADMIN_RECOVERY_PASSWORD);
    await page.click('button[type="submit"]');

    await page.waitForURL("**/dashboard**");
    await page.goto(`${BASE_URL}/admin/sso`);

    await page.click('input[type="checkbox"]#sso-only-mode');
    await page.click('button:has-text("Save Settings")');

    await expect(page.locator("text=Settings saved successfully")).toBeVisible();

    // Then: SSO-only mode should be disabled
    await page.goto(`${BASE_URL}/login`);
    await expect(page.locator("text=SSO-only mode")).not.toBeVisible();

    // And: Regular login should work
    await createTestUser(request, REGULAR_USER_EMAIL, REGULAR_USER_PASSWORD);
    await page.fill('input[type="email"]', REGULAR_USER_EMAIL);
    await page.fill('input[type="password"]', REGULAR_USER_PASSWORD);
    await page.click('button[type="submit"]');

    await page.waitForURL("**/dashboard**");
    expect(page.url()).toContain("/dashboard");
  });
});
