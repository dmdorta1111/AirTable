/**
 * Test Data Generator for Gantt View Performance Testing
 *
 * This utility generates large datasets for testing Gantt view performance
 * with 100+ tasks, various dependencies, and realistic project structures.
 */

import { addDays, startOfMonth } from 'date-fns';

export interface GanttTestTask {
  id: string;
  name: string;
  startDate: string;
  endDate: string;
  status: 'Not Started' | 'In Progress' | 'Completed' | 'Blocked';
  progress: number;
  dependencies?: string[];
  assignee?: string;
  category?: string;
}

/**
 * Generate a single task with random properties
 */
function generateTask(
  id: string,
  startDate: Date,
  durationDays: number,
  dependencies: string[] = []
): GanttTestTask {
  const endDate = addDays(startDate, durationDays);

  const statuses: Array<'Not Started' | 'In Progress' | 'Completed' | 'Blocked'> =
    ['Not Started', 'In Progress', 'Completed', 'Blocked'];
  const status = statuses[Math.floor(Math.random() * statuses.length)];

  const assignees = ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve', 'Frank', 'Grace', 'Henry'];
  const categories = ['Design', 'Development', 'Testing', 'Documentation', 'Deployment'];

  return {
    id,
    name: `Task ${id}`,
    startDate: startDate.toISOString(),
    endDate: endDate.toISOString(),
    status,
    progress: status === 'Completed' ? 100 : status === 'Not Started' ? 0 : Math.floor(Math.random() * 100),
    dependencies: dependencies.length > 0 ? dependencies : undefined,
    assignee: assignees[Math.floor(Math.random() * assignees.length)],
    category: categories[Math.floor(Math.random() * categories.length)],
  };
}

/**
 * Generate a linear chain of tasks (simplest dependency pattern)
 */
export function generateLinearChain(
  count: number,
  startDate: Date = new Date(),
  taskDurationDays: number = 5
): GanttTestTask[] {
  const tasks: GanttTestTask[] = [];
  let currentDate = startDate;

  for (let i = 0; i < count; i++) {
    const taskId = `task-${i + 1}`;
    const dependencies = i > 0 ? [`task-${i}`] : [];
    tasks.push(generateTask(taskId, currentDate, taskDurationDays, dependencies));

    // Start next task after current task ends
    currentDate = addDays(currentDate, taskDurationDays + 1);
  }

  return tasks;
}

/**
 * Generate a complex project with multiple dependency chains
 */
export function generateComplexProject(
  taskCount: number,
  startDate: Date = new Date(),
  chains: number = 3
): GanttTestTask[] {
  const tasks: GanttTestTask[] = [];
  const tasksPerChain = Math.floor(taskCount / chains);

  // Generate parallel chains
  for (let chain = 0; chain < chains; chain++) {
    const chainStartDate = addDays(startDate, chain * 10);
    const chainTasks = generateLinearChain(tasksPerChain, chainStartDate, 7);
    tasks.push(...chainTasks);
  }

  // Add cross-chain dependencies to create diamond patterns
  if (tasks.length >= 4) {
    // Connect some tasks across chains
    const mergePoint = tasks.length - Math.min(5, tasks.length);
    const predecessors = [
      tasks[Math.floor(tasks.length / 4)].id,
      tasks[Math.floor(tasks.length / 2)].id,
    ];

    if (tasks[mergePoint]) {
      tasks[mergePoint].dependencies = [...(tasks[mergePoint].dependencies || []), ...predecessors];
    }
  }

  // Add some independent tasks
  const remainingTasks = taskCount - tasks.length;
  for (let i = 0; i < remainingTasks; i++) {
    const randomOffset = Math.floor(Math.random() * 60);
    const randomStart = addDays(startDate, randomOffset);
    tasks.push(generateTask(`independent-${i + 1}`, randomStart, Math.floor(Math.random() * 10) + 3));
  }

  return tasks;
}

/**
 * Generate a realistic software development project
 */
export function generateSoftwareProject(taskCount: number = 100): GanttTestTask[] {
  const tasks: GanttTestTask[] = [];
  const projectStart = startOfMonth(new Date());

  // Phase 1: Requirements & Design (15% of tasks)
  const requirementsCount = Math.floor(taskCount * 0.15);
  for (let i = 0; i < requirementsCount; i++) {
    const startDate = addDays(projectStart, i * 2);
    const dependencies = i > 0 ? [`req-${i}`] : [];
    tasks.push({
      id: `req-${i + 1}`,
      name: `Requirement Task ${i + 1}`,
      startDate: startDate.toISOString(),
      endDate: addDays(startDate, 3).toISOString(),
      status: 'Completed',
      progress: 100,
      dependencies: dependencies.length > 0 ? dependencies : undefined,
      assignee: 'Alice',
      category: 'Design',
    });
  }

  // Phase 2: Development (50% of tasks) - depends on requirements
  const devCount = Math.floor(taskCount * 0.5);
  const devStart = addDays(projectStart, requirementsCount * 2);
  for (let i = 0; i < devCount; i++) {
    const startDate = addDays(devStart, i * 1);
    const dependencies = i === 0 ? [`req-${requirementsCount}`] : [`dev-${i}`];
    tasks.push({
      id: `dev-${i + 1}`,
      name: `Development Task ${i + 1}`,
      startDate: startDate.toISOString(),
      endDate: addDays(startDate, 5).toISOString(),
      status: i < devCount / 2 ? 'Completed' : 'In Progress',
      progress: i < devCount / 2 ? 100 : Math.floor(Math.random() * 80),
      dependencies: dependencies.length > 0 ? dependencies : undefined,
      assignee: ['Bob', 'Charlie', 'Diana'][i % 3],
      category: 'Development',
    });
  }

  // Phase 3: Testing (25% of tasks) - depends on development
  const testCount = Math.floor(taskCount * 0.25);
  const testStart = addDays(devStart, devCount);
  for (let i = 0; i < testCount; i++) {
    const startDate = addDays(testStart, i * 2);
    const dependencies = i === 0 ? [`dev-${devCount}`] : [`test-${i}`];
    tasks.push({
      id: `test-${i + 1}`,
      name: `Testing Task ${i + 1}`,
      startDate: startDate.toISOString(),
      endDate: addDays(startDate, 4).toISOString(),
      status: 'Not Started',
      progress: 0,
      dependencies: dependencies.length > 0 ? dependencies : undefined,
      assignee: 'Eve',
      category: 'Testing',
    });
  }

  // Phase 4: Deployment (10% of tasks) - depends on testing
  const deployCount = taskCount - requirementsCount - devCount - testCount;
  const deployStart = addDays(testStart, testCount * 2);
  for (let i = 0; i < deployCount; i++) {
    const startDate = addDays(deployStart, i * 3);
    const dependencies = i === 0 ? [`test-${testCount}`] : [`deploy-${i}`];
    tasks.push({
      id: `deploy-${i + 1}`,
      name: `Deployment Task ${i + 1}`,
      startDate: startDate.toISOString(),
      endDate: addDays(startDate, 2).toISOString(),
      status: 'Not Started',
      progress: 0,
      dependencies: dependencies.length > 0 ? dependencies : undefined,
      assignee: 'Frank',
      category: 'Deployment',
    });
  }

  return tasks;
}

/**
 * Generate tasks with maximum complexity (all tasks connected)
 */
export function generateMaxComplexityProject(taskCount: number = 100): GanttTestTask[] {
  const tasks: GanttTestTask[] = [];
  const startDate = new Date();

  for (let i = 0; i < taskCount; i++) {
    const currentDate = addDays(startDate, i * 2);

    // Each task depends on multiple previous tasks
    const dependencies: string[] = [];
    if (i > 0) dependencies.push(`task-${i}`);
    if (i > 5) dependencies.push(`task-${i - 5}`);
    if (i > 10) dependencies.push(`task-${i - 10}`);

    tasks.push({
      id: `task-${i + 1}`,
      name: `Complex Task ${i + 1}`,
      startDate: currentDate.toISOString(),
      endDate: addDays(currentDate, 3).toISOString(),
      status: ['Not Started', 'In Progress', 'Completed'][i % 3] as any,
      progress: (i * 10) % 100,
      dependencies: dependencies.length > 0 ? dependencies : undefined,
      assignee: ['Alice', 'Bob', 'Charlie'][i % 3],
      category: ['Design', 'Development', 'Testing'][i % 3],
    });
  }

  return tasks;
}

/**
 * Preset configurations for common test scenarios
 */
export const testPresets = {
  small: {
    taskCount: 25,
    generator: generateComplexProject,
    description: 'Small project with 25 tasks',
  },
  medium: {
    taskCount: 50,
    generator: generateComplexProject,
    description: 'Medium project with 50 tasks',
  },
  large: {
    taskCount: 100,
    generator: generateComplexProject,
    description: 'Large project with 100 tasks (standard test)',
  },
  xlarge: {
    taskCount: 200,
    generator: generateComplexProject,
    description: 'Extra large project with 200 tasks (stress test)',
  },
  software: {
    taskCount: 100,
    generator: generateSoftwareProject,
    description: 'Realistic software development project with 100 tasks',
  },
  maxComplexity: {
    taskCount: 100,
    generator: generateMaxComplexityProject,
    description: 'Maximum complexity project with 100 tasks and dense dependencies',
  },
};

/**
 * Get test data by preset name
 */
export function getTestData(preset: keyof typeof testPresets = 'large'): GanttTestTask[] {
  const config = testPresets[preset];
  return config.generator(config.taskCount);
}
