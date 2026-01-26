import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for E2E testing.
 *
 * Read environment variables from process.env:
 * - BASE_URL: Base URL for the application (default: http://localhost:5173)
 * - TABLE_ID: Table ID for testing (required for performance tests)
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false, // Run tests serially for performance testing
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1, // Single worker for performance tests to avoid interference
  reporter: [
    ['html'],
    ['list'],
    ['json', { outputFile: 'test-results/results.json' }],
  ],
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // Launch Chrome with specific flags for performance testing
        launchOptions: {
          args: [
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-blink-features=AutomationControlled',
          ],
        },
      },
    },
  ],

  // Run local dev server before starting tests
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
});
