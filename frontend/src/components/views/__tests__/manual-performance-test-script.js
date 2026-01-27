/**
 * Manual Performance Testing Script for Gantt View
 *
 * This script can be run in the browser console to test performance
 * with a live Gantt view component.
 *
 * USAGE:
 * 1. Open the application with a Gantt view
 * 2. Open browser console (F12)
 * 3. Copy and paste this script
 * 4. Call test functions as needed
 *
 * EXAMPLES:
 *   - runAllTests()           // Run all performance tests
 *   - testRendering(100)      // Test rendering with 100 tasks
 *   - testDragPerformance()   // Test drag operation smoothness
 *   - testExportPerformance() // Test export performance
 */

(window.manualGanttPerformanceTests = function() {
  const results = [];

  /**
   * Utility: Measure execution time
   */
  function measure(name, fn) {
    const start = performance.now();
    const result = fn();
    const end = performance.now();
    const duration = end - start;

    results.push({
      test: name,
      duration: duration,
      timestamp: new Date().toISOString()
    });

    console.log(`✓ ${name}: ${duration.toFixed(2)}ms`);
    return { result, duration };
  }

  /**
   * Utility: Find Gantt view component in DOM
   */
  function findGanttView() {
    // Look for the Gantt view card container
    const ganttCard = document.querySelector('[class*="rounded-lg"][class*="border"]');
    if (!ganttCard) {
      console.error('❌ Gantt view not found. Make sure you are on a page with a Gantt view.');
      return null;
    }
    return ganttCard;
  }

  /**
   * Utility: Find buttons by text content
   */
  function findButton(textOrPredicate) {
    const buttons = Array.from(document.querySelectorAll('button'));
    const predicate =
      typeof textOrPredicate === 'string'
        ? (btn) => btn.textContent?.includes(textOrPredicate)
        : textOrPredicate;

    return buttons.find(predicate);
  }

  /**
   * Utility: Find input by placeholder
   */
  function findInput(placeholder) {
    const inputs = Array.from(document.querySelectorAll('input'));
    return inputs.find(input => input.placeholder?.includes(placeholder));
  }

  /**
   * Test: Initial rendering performance
   */
  function testRendering(taskCount) {
    console.log(`\n🧪 Testing Rendering Performance (${taskCount} tasks)`);

    const ganttView = findGanttView();
    if (!ganttView) return;

    // Count actual rendered tasks
    const taskBars = ganttView.querySelectorAll('[class*="bg-"][class*="rounded"]');
    const actualCount = taskBars.length;

    console.log(`   Found ${actualCount} task bars rendered`);

    // Measure frame rate during idle
    measure('Frame Rate (idle)', () => {
      let frames = 0;
      const startTime = performance.now();

      return new Promise((resolve) => {
        function countFrames() {
          frames++;
          const elapsed = performance.now() - startTime;
          if (elapsed < 1000) {
            requestAnimationFrame(countFrames);
          } else {
            const fps = (frames / elapsed) * 1000;
            console.log(`   Frame Rate: ${fps.toFixed(1)} FPS`);
            resolve(fps);
          }
        }
        requestAnimationFrame(countFrames);
      });
    });
  }

  /**
   * Test: Toggle dependencies performance
   */
  function testDependencyToggle() {
    console.log('\n🧪 Testing Dependency Toggle Performance');

    const button = findButton(btn =>
      btn.getAttribute('aria-label')?.includes('dependency') ||
      btn.textContent?.includes('Dependencies')
    );

    if (!button) {
      console.log('⚠️  Dependency toggle button not found (feature may not be enabled)');
      return;
    }

    measure('Toggle Dependencies', () => {
      button.click();
      // Wait for UI update
      return new Promise(resolve => setTimeout(resolve, 100));
    });

    // Toggle back
    setTimeout(() => button.click(), 200);
  }

  /**
   * Test: Toggle critical path performance
   */
  function testCriticalPathToggle() {
    console.log('\n🧪 Testing Critical Path Toggle Performance');

    const button = findButton(btn =>
      btn.getAttribute('aria-label')?.includes('Critical') ||
      btn.querySelector('svg')?.innerHTML.includes('triangle')
    );

    if (!button) {
      console.log('⚠️  Critical path toggle button not found (feature may not be enabled)');
      return;
    }

    measure('Toggle Critical Path', () => {
      button.click();
      return new Promise(resolve => setTimeout(resolve, 100));
    });

    // Toggle back
    setTimeout(() => button.click(), 200);
  }

  /**
   * Test: View mode switching performance
   */
  function testViewModeSwitching() {
    console.log('\n🧪 Testing View Mode Switching Performance');

    const modes = ['Day', 'Week', 'Month', 'Quarter', 'Year'];

    modes.forEach(mode => {
      const button = findButton(mode);
      if (button) {
        measure(`Switch to ${mode} View`, () => {
          button.click();
          return new Promise(resolve => setTimeout(resolve, 50));
        });
      }
    });
  }

  /**
   * Test: Filter/search performance
   */
  function testFiltering() {
    console.log('\n🧪 Testing Filter Performance');

    const searchInput = findInput('Search');

    if (!searchInput) {
      console.log('⚠️  Search input not found');
      return;
    }

    measure('Filter Tasks', () => {
      searchInput.value = 'Task 50';
      searchInput.dispatchEvent(new Event('input', { bubbles: true }));
      return new Promise(resolve => setTimeout(resolve, 100));
    });

    // Clear search
    setTimeout(() => {
      searchInput.value = '';
      searchInput.dispatchEvent(new Event('input', { bubbles: true }));
    }, 200);
  }

  /**
   * Test: Drag operation smoothness (requires manual interaction)
   */
  function testDragPerformance() {
    console.log('\n🧪 Testing Drag Operation Performance');
    console.log('⚠️  This test requires manual interaction:');
    console.log('   1. Click and drag a task bar');
    console.log('   2. Observe if the drag is smooth (no lag)');
    console.log('   3. Report: Smooth (✓) or Laggy (✗)');

    const ganttView = findGanttView();
    if (!ganttView) return;

    // Find a draggable task bar
    const taskBars = ganttView.querySelectorAll('[class*="cursor-move"]');
    if (taskBars.length > 0) {
      console.log(`   Found ${taskBars.length} draggable task bars`);
      console.log('   Drag any task to test smoothness');
    }
  }

  /**
   * Test: Export performance
   */
  function testExportPerformance() {
    console.log('\n🧪 Testing Export Performance');

    // Find export button (usually has Download icon)
    const exportButton = findButton(btn =>
      btn.textContent?.includes('Export') ||
      btn.querySelector('svg')?.innerHTML.includes('download')
    );

    if (!exportButton) {
      console.log('⚠️  Export button not found');
      return;
    }

    // Click export button to show dropdown
    exportButton.click();

    setTimeout(() => {
      // Find PNG export option
      const pngOption = Array.from(document.querySelectorAll('[role="menuitem"]'))
        .find(item => item.textContent?.includes('PNG'));

      if (pngOption) {
        measure('Export as PNG', () => {
          pngOption.click();
          return new Promise(resolve => setTimeout(resolve, 100));
        });
      }
    }, 100);
  }

  /**
   * Test: Memory usage (if available)
   */
  function testMemoryUsage() {
    console.log('\n🧪 Testing Memory Usage');

    if ('memory' in performance && (performance.memory).usedJSHeapSize) {
      const usedMB = (performance.memory.usedJSHeapSize / 1024 / 1024).toFixed(2);
      const totalMB = (performance.memory.totalJSHeapSize / 1024 / 1024).toFixed(2);
      const limitMB = (performance.memory.jsHeapSizeLimit / 1024 / 1024).toFixed(2);

      console.log(`   Used: ${usedMB} MB`);
      console.log(`   Total: ${totalMB} MB`);
      console.log(`   Limit: ${limitMB} MB`);
      console.log(`   Usage: ${((usedMB / limitMB) * 100).toFixed(1)}%`);
    } else {
      console.log('⚠️  Memory API not available in this browser');
      console.log('   Try Chrome or Edge for memory measurements');
    }
  }

  /**
   * Generate performance report
   */
  function generateReport() {
    console.log('\n📊 Performance Report');
    console.log('=' .repeat(60));

    if (results.length === 0) {
      console.log('No test results available. Run some tests first.');
      return;
    }

    const report = {
      timestamp: new Date().toISOString(),
      tests: results,
      summary: {
        totalTests: results.length,
        averageDuration: results.reduce((sum, r) => sum + r.duration, 0) / results.length,
        maxDuration: Math.max(...results.map(r => r.duration)),
        minDuration: Math.min(...results.map(r => r.duration))
      }
    };

    console.log(`Total Tests: ${report.summary.totalTests}`);
    console.log(`Average Duration: ${report.summary.averageDuration.toFixed(2)}ms`);
    console.log(`Min Duration: ${report.summary.minDuration.toFixed(2)}ms`);
    console.log(`Max Duration: ${report.summary.maxDuration.toFixed(2)}ms`);

    console.log('\nDetailed Results:');
    results.forEach(r => {
      const status = r.duration < 500 ? '✓' : r.duration < 1000 ? '⚠️' : '❌';
      console.log(`  ${status} ${r.test}: ${r.duration.toFixed(2)}ms`);
    });

    console.log('\n' + '='.repeat(60));

    return report;
  }

  /**
   * Run all performance tests
   */
  async function runAllTests() {
    console.clear();
    console.log('🚀 Starting Gantt View Performance Tests');
    console.log('=' .repeat(60));

    await new Promise(resolve => setTimeout(resolve, 100));

    testRendering('detect');
    await new Promise(resolve => setTimeout(resolve, 500));

    testDependencyToggle();
    await new Promise(resolve => setTimeout(resolve, 500));

    testCriticalPathToggle();
    await new Promise(resolve => setTimeout(resolve, 500));

    testViewModeSwitching();
    await new Promise(resolve => setTimeout(resolve, 500));

    testFiltering();
    await new Promise(resolve => setTimeout(resolve, 500));

    testDragPerformance();
    await new Promise(resolve => setTimeout(resolve, 500));

    testMemoryUsage();
    await new Promise(resolve => setTimeout(resolve, 500));

    generateReport();

    console.log('\n✅ Performance Testing Complete!');
    console.log('📝 Copy the report above for documentation');
  }

  // Export functions to global scope
  return {
    runAllTests,
    testRendering,
    testDependencyToggle,
    testCriticalPathToggle,
    testViewModeSwitching,
    testFiltering,
    testDragPerformance,
    testExportPerformance,
    testMemoryUsage,
    generateReport,
    results
  };
})();

// Auto-display instructions
console.log('%c🎯 Manual Performance Testing Suite Loaded', 'font-size: 16px; font-weight: bold; color: #10b981;');
console.log('%cAvailable commands:', 'font-weight: bold; color: #3b82f6;');
console.log('  - runAllTests()           // Run all performance tests');
console.log('  - testRendering(100)      // Test rendering with task count');
console.log('  - testDependencyToggle()  // Test dependency toggle');
console.log('  - testCriticalPathToggle() // Test critical path toggle');
console.log('  - testViewModeSwitching() // Test view mode switches');
console.log('  - testFiltering()         // Test search/filter');
console.log('  - testDragPerformance()   // Test drag smoothness');
console.log('  - testExportPerformance() // Test export speed');
console.log('  - testMemoryUsage()       // Check memory usage');
console.log('  - generateReport()        // Show test results');
console.log('\n%cExample: runAllTests()', 'color: #f59e0b;');
