/**
 * Performance Monitoring Utility for Gantt View
 *
 * This utility measures and reports performance metrics for Gantt view operations
 * including rendering, interactions, and calculations.
 */

export interface PerformanceMetrics {
  /** Time to render initial view (ms) */
  initialRenderTime: number;
  /** Time to calculate critical path (ms) */
  criticalPathCalculationTime: number;
  /** Time to calculate dependency lines (ms) */
  dependencyCalculationTime: number;
  /** Time to render dependency lines (ms) */
  dependencyRenderTime: number;
  /** Average time for drag operation (ms) */
  dragOperationTime: number;
  /** Time to export as PNG (ms) */
  pngExportTime: number;
  /** Time to export as PDF (ms) */
  pdfExportTime: number;
  /** Number of tasks rendered */
  taskCount: number;
  /** Number of dependency lines rendered */
  dependencyLineCount: number;
  /** Frame rate during interactions (FPS) */
  frameRate: number;
  /** Memory usage (MB, if available) */
  memoryUsage?: number;
}

export interface PerformanceReport {
  timestamp: string;
  taskCount: number;
  metrics: PerformanceMetrics;
  verdict: 'PASS' | 'FAIL' | 'WARNING';
  issues: string[];
}

/**
 * Performance thresholds for different task counts
 */
const THRESHOLDS = {
  small: { tasks: 25, renderTime: 500, calculationTime: 100, exportTime: 2000 },
  medium: { tasks: 50, renderTime: 1000, calculationTime: 200, exportTime: 3000 },
  large: { tasks: 100, renderTime: 2000, calculationTime: 500, exportTime: 5000 },
  xlarge: { tasks: 200, renderTime: 4000, calculationTime: 1000, exportTime: 10000 },
};

class PerformanceMonitor {
  private measurements: Map<string, number[]> = new Map();
  private marks: Map<string, number> = new Map();

  /**
   * Start measuring an operation
   */
  startMark(name: string): void {
    this.marks.set(name, performance.now());
  }

  /**
   * End measuring an operation and record the duration
   */
  endMark(name: string): number {
    const startTime = this.marks.get(name);
    if (!startTime) {
      console.warn(`No start mark found for: ${name}`);
      return 0;
    }

    const duration = performance.now() - startTime;
    this.recordMeasurement(name, duration);
    this.marks.delete(name);
    return duration;
  }

  /**
   * Record a measurement value
   */
  recordMeasurement(name: string, value: number): void {
    if (!this.measurements.has(name)) {
      this.measurements.set(name, []);
    }
    this.measurements.get(name)!.push(value);
  }

  /**
   * Get average measurement value
   */
  getAverage(name: string): number {
    const measurements = this.measurements.get(name);
    if (!measurements || measurements.length === 0) return 0;

    const sum = measurements.reduce((a, b) => a + b, 0);
    return sum / measurements.length;
  }

  /**
   * Get median measurement value
   */
  getMedian(name: string): number {
    const measurements = this.measurements.get(name);
    if (!measurements || measurements.length === 0) return 0;

    const sorted = [...measurements].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    return sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
  }

  /**
   * Get min measurement value
   */
  getMin(name: string): number {
    const measurements = this.measurements.get(name);
    if (!measurements || measurements.length === 0) return 0;
    return Math.min(...measurements);
  }

  /**
   * Get max measurement value
   */
  getMax(name: string): number {
    const measurements = this.measurements.get(name);
    if (!measurements || measurements.length === 0) return 0;
    return Math.max(...measurements);
  }

  /**
   * Clear all measurements
   */
  clear(): void {
    this.measurements.clear();
    this.marks.clear();
  }

  /**
   * Get current memory usage (if supported)
   */
  getMemoryUsage(): number | null {
    if ('memory' in performance && (performance as any).memory) {
      return (performance as any).memory.usedJSHeapSize / 1024 / 1024; // Convert to MB
    }
    return null;
  }

  /**
   * Measure frame rate over a period of time
   */
  async measureFrameRate(duration: number = 1000): Promise<number> {
    return new Promise((resolve) => {
      let frames = 0;
      const startTime = performance.now();

      const countFrames = () => {
        frames++;
        const elapsed = performance.now() - startTime;

        if (elapsed < duration) {
          requestAnimationFrame(countFrames);
        } else {
          const fps = (frames / elapsed) * 1000;
          resolve(fps);
        }
      };

      requestAnimationFrame(countFrames);
    });
  }

  /**
   * Generate a performance report
   */
  generateReport(taskCount: number): PerformanceReport {
    const metrics: PerformanceMetrics = {
      initialRenderTime: this.getAverage('initialRender'),
      criticalPathCalculationTime: this.getAverage('criticalPathCalculation'),
      dependencyCalculationTime: this.getAverage('dependencyCalculation'),
      dependencyRenderTime: this.getAverage('dependencyRender'),
      dragOperationTime: this.getAverage('dragOperation'),
      pngExportTime: this.getAverage('pngExport'),
      pdfExportTime: this.getAverage('pdfExport'),
      taskCount,
      dependencyLineCount: Math.floor(taskCount * 0.7), // Estimate
      frameRate: this.getAverage('frameRate'),
      memoryUsage: this.getMemoryUsage() || undefined,
    };

    const issues: string[] = [];
    let verdict: 'PASS' | 'FAIL' | 'WARNING' = 'PASS';

    // Determine threshold category based on task count
    let threshold = THRESHOLDS.xlarge;
    if (taskCount <= 25) threshold = THRESHOLDS.small;
    else if (taskCount <= 50) threshold = THRESHOLDS.medium;
    else if (taskCount <= 100) threshold = THRESHOLDS.large;

    // Check render time
    if (metrics.initialRenderTime > threshold.renderTime) {
      issues.push(
        `Initial render time ${metrics.initialRenderTime.toFixed(0)}ms exceeds threshold ${threshold.renderTime}ms`
      );
      verdict = 'FAIL';
    }

    // Check calculation time
    if (metrics.criticalPathCalculationTime > threshold.calculationTime) {
      issues.push(
        `Critical path calculation ${metrics.criticalPathCalculationTime.toFixed(0)}ms exceeds threshold ${threshold.calculationTime}ms`
      );
      if (verdict === 'PASS') verdict = 'WARNING';
    }

    // Check export time
    if (metrics.pngExportTime > threshold.exportTime) {
      issues.push(
        `PNG export time ${metrics.pngExportTime.toFixed(0)}ms exceeds threshold ${threshold.exportTime}ms`
      );
      if (verdict === 'PASS') verdict = 'WARNING';
    }

    // Check frame rate
    if (metrics.frameRate < 30 && metrics.frameRate > 0) {
      issues.push(`Frame rate ${metrics.frameRate.toFixed(1)} FPS is below 30 FPS threshold`);
      if (verdict === 'PASS') verdict = 'WARNING';
    }

    return {
      timestamp: new Date().toISOString(),
      taskCount,
      metrics,
      verdict,
      issues,
    };
  }

  /**
   * Print performance report to console
   */
  printReport(report: PerformanceReport): void {
    console.log('\n=== Gantt View Performance Report ===');
    console.log(`Timestamp: ${report.timestamp}`);
    console.log(`Task Count: ${report.taskCount}`);
    console.log(`\nVerdict: ${report.verdict}`);

    if (report.issues.length > 0) {
      console.log('\nIssues:');
      report.issues.forEach((issue) => console.log(`  ⚠️  ${issue}`));
    }

    console.log('\nMetrics:');
    console.log(`  Initial Render: ${report.metrics.initialRenderTime.toFixed(0)}ms`);
    console.log(`  Critical Path Calculation: ${report.metrics.criticalPathCalculationTime.toFixed(0)}ms`);
    console.log(`  Dependency Calculation: ${report.metrics.dependencyCalculationTime.toFixed(0)}ms`);
    console.log(`  Dependency Render: ${report.metrics.dependencyRenderTime.toFixed(0)}ms`);
    console.log(`  Drag Operation: ${report.metrics.dragOperationTime.toFixed(0)}ms`);
    console.log(`  PNG Export: ${report.metrics.pngExportTime.toFixed(0)}ms`);
    console.log(`  PDF Export: ${report.metrics.pdfExportTime.toFixed(0)}ms`);
    console.log(`  Frame Rate: ${report.metrics.frameRate.toFixed(1)} FPS`);
    if (report.metrics.memoryUsage) {
      console.log(`  Memory Usage: ${report.metrics.memoryUsage.toFixed(1)} MB`);
    }
    console.log('=====================================\n');
  }
}

/**
 * Global performance monitor instance
 */
export const performanceMonitor = new PerformanceMonitor();

/**
 * Decorator to measure async function performance
 */
export function measurePerformance<T extends (...args: any[]) => any>(
  name: string,
  fn: T
): T {
  return ((...args: any[]) => {
    performanceMonitor.startMark(name);
    try {
      const result = fn(...args);

      // Handle promises
      if (result instanceof Promise) {
        return result.finally(() => {
          performanceMonitor.endMark(name);
        });
      }

      performanceMonitor.endMark(name);
      return result;
    } catch (error) {
      performanceMonitor.endMark(name);
      throw error;
    }
  }) as T;
}

/**
 * Measure React render performance
 */
export function useRenderPerformance(componentName: string): void {
  React.useEffect(() => {
    performanceMonitor.startMark(`${componentName}-render`);
    return () => {
      performanceMonitor.endMark(`${componentName}-render`);
      performanceMonitor.recordMeasurement('initialRender', performanceMonitor.getAverage(`${componentName}-render`));
    };
  });
}

/**
 * Performance testing utilities for Gantt view
 */
export const ganttPerformanceTests = {
  /**
   * Test initial rendering performance
   */
  async testInitialRender(taskCount: number): Promise<number> {
    const monitor = new PerformanceMonitor();
    monitor.startMark('initialRender');

    // Simulate render - in real usage, this would mount the component
    await new Promise((resolve) => setTimeout(resolve, 10));

    return monitor.endMark('initialRender');
  },

  /**
   * Test critical path calculation performance
   */
  async testCriticalPathCalculation(taskCount: number): Promise<number> {
    const monitor = new PerformanceMonitor();
    monitor.startMark('criticalPathCalculation');

    // Simulate calculation - in real usage, this would run the algorithm
    await new Promise((resolve) => setTimeout(resolve, taskCount * 0.5));

    return monitor.endMark('criticalPathCalculation');
  },

  /**
   * Test export performance
   */
  async testExport(taskCount: number, format: 'png' | 'pdf'): Promise<number> {
    const monitor = new PerformanceMonitor();
    const markName = format === 'png' ? 'pngExport' : 'pdfExport';
    monitor.startMark(markName);

    // Simulate export - in real usage, this would run html2canvas/jsPDF
    await new Promise((resolve) => setTimeout(resolve, taskCount * 10));

    return monitor.endMark(markName);
  },
};
