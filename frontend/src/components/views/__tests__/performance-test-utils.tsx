/**
 * Performance Testing Utilities for Gantt View
 *
 * Provides utilities to generate large test datasets and measure performance
 * for the Gantt chart component.
 */

import { Field } from '../GanttView';

export interface TestDataOptions {
  numTasks: number;
  dependencyChance?: number; // 0-1, chance of task having dependencies
  startDate?: Date;
  averageDuration?: number; // days
}

/**
 * Generates mock fields for Gantt view testing
 */
export const generateMockFields = (): Field[] => [
  { id: '1', name: 'Task Name', type: 'text' },
  { id: '2', name: 'Start Date', type: 'date' },
  { id: '3', name: 'End Date', type: 'date' },
  { id: '4', name: 'Status', type: 'select', options: { choices: ['To Do', 'In Progress', 'Done', 'Blocked'] } },
  { id: '5', name: 'Progress', type: 'number' },
  { id: '6', name: 'Dependencies', type: 'text' }, // For storing dependency task IDs
];

/**
 * Generates a large dataset of tasks for performance testing
 *
 * @param options - Configuration for test data generation
 * @returns Array of task records
 */
export const generateLargeDataset = (options: TestDataOptions) => {
  const {
    numTasks,
    dependencyChance = 0.3,
    startDate = new Date('2024-01-01'),
    averageDuration = 7,
  } = options;

  const tasks: any[] = [];
  const statuses = ['To Do', 'In Progress', 'Done', 'Blocked'];

  for (let i = 0; i < numTasks; i++) {
    // Calculate start date with some overlap and gaps
    const taskStart = new Date(startDate);
    taskStart.setDate(taskStart.getDate() + Math.floor(i * averageDuration * 0.6));

    const duration = averageDuration + Math.floor(Math.random() * 10) - 5; // ±5 days variation
    const taskEnd = new Date(taskStart);
    taskEnd.setDate(taskEnd.getDate() + duration);

    const task: any = {
      id: `task-${i + 1}`,
      'Task Name': `Task ${i + 1}`,
      'Start Date': taskStart.toISOString().split('T')[0],
      'End Date': taskEnd.toISOString().split('T')[0],
      'Status': statuses[Math.floor(Math.random() * statuses.length)],
      'Progress': Math.floor(Math.random() * 101),
    };

    // Add dependencies if random chance hits
    if (i > 0 && Math.random() < dependencyChance) {
      const numDependencies = Math.floor(Math.random() * 3) + 1; // 1-3 dependencies
      const dependencyIds: string[] = [];
      for (let d = 0; d < numDependencies; d++) {
        const depIndex = Math.floor(Math.random() * i);
        dependencyIds.push(`task-${depIndex + 1}`);
      }
      task['Dependencies'] = dependencyIds.join(',');
    }

    tasks.push(task);
  }

  return tasks;
};

/**
 * Generates datasets of different sizes for performance scaling tests
 */
export const generatePerformanceTestSuites = () => ({
  small: generateLargeDataset({ numTasks: 20 }),
  medium: generateLargeDataset({ numTasks: 50 }),
  large: generateLargeDataset({ numTasks: 100 }),
  xlarge: generateLargeDataset({ numTasks: 200 }),
  xxlarge: generateLargeDataset({ numTasks: 500 }),
});

/**
 * Measures execution time of a function
 *
 * @param fn - Function to measure
 * @returns Object with result and execution time in ms
 */
export const measurePerformance = async <T>(
  fn: () => T | Promise<T>
): Promise<{ result: T; duration: number }> => {
  const startTime = performance.now();
  const result = await fn();
  const endTime = performance.now();
  return {
    result,
    duration: endTime - startTime,
  };
};

/**
 * Performance thresholds for different operations (in milliseconds)
 */
export const PERFORMANCE_THRESHOLDS = {
  render: {
    small: 100,    // 20 tasks
    medium: 200,   // 50 tasks
    large: 500,    // 100 tasks
    xlarge: 1000,  // 200 tasks
    xxlarge: 2000, // 500 tasks
  },
  criticalPath: {
    small: 10,
    medium: 20,
    large: 50,
    xlarge: 100,
    xxlarge: 200,
  },
  dependencyLines: {
    small: 10,
    medium: 20,
    large: 50,
    xlarge: 100,
    xxlarge: 200,
  },
  filter: {
    small: 10,
    medium: 20,
    large: 30,
    xlarge: 50,
    xxlarge: 100,
  },
  export: {
    small: 500,
    medium: 1000,
    large: 2000,
    xlarge: 4000,
    xxlarge: 5000, // Max 5 seconds per spec
  },
};
