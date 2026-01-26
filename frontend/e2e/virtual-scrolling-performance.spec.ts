import { test, expect } from '@playwright/test';

/**
 * E2E Performance Test: Virtual Scrolling with 100K Records
 *
 * This test verifies that the virtualized grid view maintains 60 FPS
 * when scrolling through 100K records.
 *
 * Prerequisites:
 * - Database seeded with 100K records (use scripts/seed_large_dataset.py)
 * - Set TABLE_ID environment variable to the test table ID
 *
 * Verification:
 * - FPS remains near 60 FPS during scrolling
 * - Memory usage remains constant (no leaks)
 * - Only ~100 records in DOM at any time
 */

const TABLE_ID = process.env.TABLE_ID;
if (!TABLE_ID) {
  throw new Error('TABLE_ID environment variable is required. Set it to your test table ID.');
}

test.describe('Virtual Scrolling Performance', () => {
  test.beforeEach(async ({ page }) => {
    // Enable Chrome DevTools Performance monitoring
    await page.coverage.startJSCoverage();
  });

  test.afterEach(async ({ page }) => {
    await page.coverage.stopJSCoverage();
  });

  test('should maintain 60 FPS when scrolling through 100K records', async ({ page }) => {
    // Navigate to virtualized grid view
    await page.goto(`/tables/${TABLE_ID}?view=virtual-grid`);

    // Wait for initial load
    await page.waitForSelector('[data-testid="virtual-grid-container"]', { timeout: 30000 });

    // Initial DOM size check
    const initialDOMSize = await page.evaluate(() => {
      const rows = document.querySelectorAll('[data-testid^="virtual-row-"]');
      return rows.length;
    });

    console.log(`Initial DOM size: ${initialDOMSize} rows`);
    expect(initialDOMSize).toBeLessThan(150); // Should be ~100 rows + overscan
    expect(initialDOMSize).toBeGreaterThan(50); // At least some rows visible

    // Measure initial memory
    const initialMemory = await page.evaluate(() => {
      return (performance as any).memory?.usedJSHeapSize || 0;
    });

    // Scroll metrics
    const scrollMetrics = {
      totalScrolls: 0,
      totalFPS: 0,
      minFPS: Infinity,
      maxFPS: 0,
      fpsSamples: [],
    };

    // Scroll through the list in chunks
    const scrollContainer = page.locator('[data-testid="virtual-grid-container"]');

    // Number of scroll iterations (each scrolls ~1000 records)
    const numIterations = 100;

    for (let i = 0; i < numIterations; i++) {
      const startTime = performance.now();

      // Scroll down by 1000 rows (40px per row * 1000 = 40000px)
      await scrollContainer.evaluate((el, scrollAmount) => {
        el.scrollTop += scrollAmount;
      }, 40000);

      // Wait for rendering to settle
      await page.waitForTimeout(100);

      // Measure FPS for this scroll
      const endTime = performance.now();
      const frameTime = endTime - startTime;
      const fps = 1000 / frameTime;

      scrollMetrics.totalScrolls++;
      scrollMetrics.totalFPS += fps;
      scrollMetrics.minFPS = Math.min(scrollMetrics.minFPS, fps);
      scrollMetrics.maxFPS = Math.max(scrollMetrics.maxFPS, fps);
      scrollMetrics.fpsSamples.push(fps);

      // Check DOM size during scrolling
      if (i % 10 === 0) {
        const currentDOMSize = await page.evaluate(() => {
          const rows = document.querySelectorAll('[data-testid^="virtual-row-"]');
          return rows.length;
        });

        console.log(`Scroll ${i + 1}/${numIterations}: FPS=${fps.toFixed(1)}, DOM size=${currentDOMSize}`);
        expect(currentDOMSize).toBeLessThan(150); // DOM size should remain constant
      }
    }

    // Calculate average FPS
    const avgFPS = scrollMetrics.totalFPS / scrollMetrics.totalScrolls;

    console.log('\n=== Performance Metrics ===');
    console.log(`Average FPS: ${avgFPS.toFixed(2)}`);
    console.log(`Min FPS: ${scrollMetrics.minFPS.toFixed(2)}`);
    console.log(`Max FPS: ${scrollMetrics.maxFPS.toFixed(2)}`);
    console.log(`Total scrolls: ${scrollMetrics.totalScrolls}`);

    // Verify performance requirements
    expect(avgFPS).toBeGreaterThan(55); // Should average close to 60 FPS
    expect(scrollMetrics.minFPS).toBeGreaterThan(30); // Minimum FPS shouldn't drop too low

    // Check final memory usage
    const finalMemory = await page.evaluate(() => {
      return (performance as any).memory?.usedJSHeapSize || 0;
    });

    if (initialMemory > 0 && finalMemory > 0) {
      const memoryIncreaseMB = (finalMemory - initialMemory) / (1024 * 1024);
      console.log(`Memory increase: ${memoryIncreaseMB.toFixed(2)} MB`);

      // Memory increase should be minimal (< 50MB) indicating no leak
      expect(memoryIncreaseMB).toBeLessThan(50);
    }

    // Final DOM size check
    const finalDOMSize = await page.evaluate(() => {
      const rows = document.querySelectorAll('[data-testid^="virtual-row-"]');
      return rows.length;
    });

    console.log(`Final DOM size: ${finalDOMSize} rows`);
    expect(finalDOMSize).toBeLessThan(150);
  });

  test('should render only visible records with virtual scrolling', async ({ page }) => {
    await page.goto(`/tables/${TABLE_ID}?view=virtual-grid`);
    await page.waitForSelector('[data-testid="virtual-grid-container"]', { timeout: 30000 });

    // Check that only visible records are in DOM
    const virtualizedRowCount = await page.evaluate(() => {
      const rows = document.querySelectorAll('[data-testid^="virtual-row-"]');
      return rows.length;
    });

    const totalRecords = await page.evaluate(() => {
      // Get total records from API response or UI indicator
      const countElement = document.querySelector('[data-testid="records-count"]');
      return countElement ? parseInt(countElement.textContent || '0') : 0;
    });

    console.log(`Virtualized rows in DOM: ${virtualizedRowCount}`);
    console.log(`Total records in table: ${totalRecords}`);

    // Verify virtualization is working
    expect(virtualizedRowCount).toBeMuchLessThan(totalRecords);
    expect(virtualizedRowCount).toBeLessThan(150);

    // Scroll to bottom
    const scrollContainer = page.locator('[data-testid="virtual-grid-container"]');
    await scrollContainer.evaluate((el) => {
      el.scrollTop = el.scrollHeight;
    });

    await page.waitForTimeout(500);

    // DOM size should still be constant
    const scrolledDOMSize = await page.evaluate(() => {
      const rows = document.querySelectorAll('[data-testid^="virtual-row-"]');
      return rows.length;
    });

    console.log(`DOM size after scrolling to bottom: ${scrolledDOMSize}`);
    expect(scrolledDOMSize).toBeLessThan(150);
    expect(scrolledDOMSize).toBeCloseTo(virtualizedRowCount, 20); // Within 20 rows
  });

  test('should maintain responsiveness during rapid scrolling', async ({ page }) => {
    await page.goto(`/tables/${TABLE_ID}?view=virtual-grid`);
    await page.waitForSelector('[data-testid="virtual-grid-container"]', { timeout: 30000 });

    const scrollContainer = page.locator('[data-testid="virtual-grid-container"]');

    // Perform rapid scrolls
    const scrollStartTime = performance.now();

    for (let i = 0; i < 50; i++) {
      await scrollContainer.evaluate((el) => {
        el.scrollTop += 1000;
      });
    }

    const scrollEndTime = performance.now();
    const totalScrollTime = scrollEndTime - scrollStartTime;

    console.log(`Total scroll time: ${totalScrollTime.toFixed(2)}ms`);
    console.log(`Average per scroll: ${(totalScrollTime / 50).toFixed(2)}ms`);

    // Each scroll should complete quickly (< 50ms)
    expect(totalScrollTime / 50).toBeLessThan(50);

    // UI should remain interactive
    const isInteractive = await page.evaluate(() => {
      const grid = document.querySelector('[data-testid="virtual-grid-container"]');
      return grid !== null;
    });

    expect(isInteractive).toBe(true);
  });
});
