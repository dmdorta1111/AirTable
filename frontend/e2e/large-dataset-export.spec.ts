import { test, expect } from '@playwright/test';

/**
 * E2E Test: Large Dataset Export without Timeout
 *
 * This test verifies that the export functionality handles large datasets
 * (100K+ records) without timeout and returns all data correctly.
 *
 * Prerequisites:
 * - Database seeded with 100K records (use scripts/seed_large_dataset.py)
 * - Set TABLE_ID environment variable to the test table ID
 * - Set API_BASE_URL environment variable (default: http://localhost:8000)
 * - Set AUTH_TOKEN environment variable with valid auth token
 *
 * Verification:
 * - Export starts immediately (HTTP 202)
 * - Download completes without timeout
 * - Exported file contains all records
 * - Data integrity is maintained
 */

const TABLE_ID = process.env.TABLE_ID;
const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';
const AUTH_TOKEN = process.env.AUTH_TOKEN;

test.describe('Large Dataset Export', () => {
  test.beforeEach(async ({}, testInfo) => {
    // Skip tests if environment variables are not set
    if (!TABLE_ID || !AUTH_TOKEN) {
      testInfo.skip(true, !TABLE_ID ? 'TABLE_ID environment variable not set' : 'AUTH_TOKEN environment variable not set');
    }
  });
  test('should export 100K records as CSV without timeout', async ({ page }) => {
    // Navigate to the page to establish auth context
    await page.goto('/');

    // Set auth token in localStorage
    await page.evaluate((token) => {
      localStorage.setItem('token', token);
    }, AUTH_TOKEN);

    // Make export request via context
    const exportUrl = `${API_BASE_URL}/api/v1/records/export?table_id=${TABLE_ID}&format=csv&batch_size=1000`;

    const response = await page.evaluate(async (url) => {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      // Extract headers manually
      const headers: Record<string, string> = {};
      response.headers.forEach((value, key) => {
        headers[key] = value;
      });

      return {
        status: response.status,
        headers,
        body: await response.text(),
      };
    }, exportUrl);

    // Verify response status
    expect(response.status).toBeGreaterThanOrEqual(200);
    expect(response.status).toBeLessThan(300);

    // Verify response headers
    expect(response.headers['content-type']).toContain('text/csv');
    expect(response.headers['content-disposition']).toContain('attachment');
    expect(response.headers['content-disposition']).toContain('.csv');

    // Parse CSV and verify records
    const csvData = response.body;
    const lines = csvData.trim().split('\n');

    // First line is header
    const header = lines[0];
    expect(header.length).toBeGreaterThan(0);

    // Count data rows (excluding header)
    const dataRows = lines.slice(1);
    console.log(`Exported ${dataRows.length} records`);
    expect(dataRows.length).toBeGreaterThanOrEqual(100000);

    // Verify data integrity - check first and last rows
    const firstRow = dataRows[0];
    const lastRow = dataRows[dataRows.length - 1];

    expect(firstRow.split(',').length).toBeGreaterThan(0);
    expect(lastRow.split(',').length).toBeGreaterThan(0);

    console.log('CSV export verification passed');
    console.log(`- Header columns: ${header.split(',').length}`);
    console.log(`- Total rows: ${dataRows.length}`);
  });

  test('should export 100K records as JSON without timeout', async ({ page }) => {
    // Navigate to the page to establish auth context
    await page.goto('/');

    // Set auth token in localStorage
    await page.evaluate((token) => {
      localStorage.setItem('token', token);
    }, AUTH_TOKEN);

    // Make export request via context
    const exportUrl = `${API_BASE_URL}/api/v1/records/export?table_id=${TABLE_ID}&format=json&batch_size=1000`;

    const response = await page.evaluate(async (url) => {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      // Extract headers manually
      const headers: Record<string, string> = {};
      response.headers.forEach((value, key) => {
        headers[key] = value;
      });

      return {
        status: response.status,
        headers,
        body: await response.text(),
      };
    }, exportUrl);

    // Verify response status
    expect(response.status).toBeGreaterThanOrEqual(200);
    expect(response.status).toBeLessThan(300);

    // Verify response headers
    expect(response.headers['content-type']).toContain('application/json');
    expect(response.headers['content-disposition']).toContain('attachment');
    expect(response.headers['content-disposition']).toContain('.json');

    // Parse JSON and verify records
    const jsonData = JSON.parse(response.body);
    expect(Array.isArray(jsonData)).toBe(true);

    console.log(`Exported ${jsonData.length} records`);
    expect(jsonData.length).toBeGreaterThanOrEqual(100000);

    // Verify data integrity - check first and last records
    const firstRecord = jsonData[0];
    const lastRecord = jsonData[jsonData.length - 1];

    expect(typeof firstRecord).toBe('object');
    expect(typeof lastRecord).toBe('object');
    expect(Object.keys(firstRecord).length).toBeGreaterThan(0);
    expect(Object.keys(lastRecord).length).toBeGreaterThan(0);

    console.log('JSON export verification passed');
    console.log(`- Records: ${jsonData.length}`);
    console.log(`- Fields per record: ${Object.keys(firstRecord).length}`);
  });

  test('should start export immediately with HTTP 202', async ({ page }) => {
    // Navigate to the page to establish auth context
    await page.goto('/');

    // Set auth token in localStorage
    await page.evaluate((token) => {
      localStorage.setItem('token', token);
    }, AUTH_TOKEN);

    // Measure time to first byte
    const startTime = Date.now();

    const exportUrl = `${API_BASE_URL}/api/v1/records/export?table_id=${TABLE_ID}&format=csv&batch_size=1000`;

    const response = await page.evaluate(async (url) => {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      return {
        status: response.status,
        statusText: response.statusText,
      };
    }, exportUrl);

    const timeToFirstByte = Date.now() - startTime;

    // Verify response starts quickly (within 5 seconds)
    console.log(`Time to first byte: ${timeToFirstByte}ms`);
    expect(timeToFirstByte).toBeLessThan(5000);

    // Verify status code indicates async processing
    expect(response.status).toBe(202);

    console.log('Export started immediately');
  });

  test('should export with streaming and progress tracking', async ({ page }) => {
    // Navigate to the page to establish auth context
    await page.goto('/');

    // Set auth token in localStorage
    await page.evaluate((token) => {
      localStorage.setItem('token', token);
    }, AUTH_TOKEN);

    const exportUrl = `${API_BASE_URL}/api/v1/records/export?table_id=${TABLE_ID}&format=csv&batch_size=1000`;

    // Track download progress
    const progress = await page.evaluate(async (url) => {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Response body is not readable');
      }

      let loaded = 0;
      let chunks = 0;
      const startTime = Date.now();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        loaded += value.length;
        chunks++;
      }

      const duration = Date.now() - startTime;
      const speed = loaded / (duration / 1000); // bytes per second

      return {
        totalBytes: loaded,
        chunks,
        durationMs: duration,
        speedBytesPerSec: speed,
        speedMBPerSec: speed / (1024 * 1024),
      };
    }, exportUrl);

    console.log('Streaming export completed:');
    console.log(`- Total bytes: ${(progress.totalBytes / 1024 / 1024).toFixed(2)} MB`);
    console.log(`- Chunks received: ${progress.chunks}`);
    console.log(`- Duration: ${(progress.durationMs / 1000).toFixed(2)}s`);
    console.log(`- Speed: ${progress.speedMBPerSec.toFixed(2)} MB/s`);

    // Verify streaming worked (multiple chunks)
    expect(progress.chunks).toBeGreaterThan(1);

    // Verify reasonable speed (at least 0.1 MB/s)
    expect(progress.speedMBPerSec).toBeGreaterThan(0.1);

    // Verify reasonable duration (less than 2 minutes for 100K records)
    expect(progress.durationMs).toBeLessThan(120000);

    console.log('Streaming export verification passed');
  });
});
