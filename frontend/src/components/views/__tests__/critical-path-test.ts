/**
 * Simple test to verify critical path algorithm logic
 * This can be run with: node --loader ts-node critical-path-test.ts
 */

interface MockRecord {
  id: string;
  [key: string]: any;
}

// Mock data for testing
const mockData: MockRecord[] = [
  { id: 'task1', startDate: '2024-01-01', endDate: '2024-01-05', dependencies: [] }, // 4 days
  { id: 'task2', startDate: '2024-01-06', endDate: '2024-01-10', dependencies: ['task1'] }, // 4 days
  { id: 'task3', startDate: '2024-01-06', endDate: '2024-01-08', dependencies: ['task1'] }, // 2 days
  { id: 'task4', startDate: '2024-01-11', endDate: '2024-01-15', dependencies: ['task2', 'task3'] }, // 4 days
];

console.log('Mock Data:', JSON.stringify(mockData, null, 2));

// Simulate the critical path algorithm
function calculateCriticalPath(
  data: MockRecord[],
  startDateFieldId: string,
  endDateFieldId: string,
  dependencyFieldId: string
): Set<string> {
  const taskIds = new Set<string>();
  const predecessors = new Map<string, string[]>();
  const successors = new Map<string, string[]>();
  const durations = new Map<string, number>();
  const validTasks = new Set<string>();

  // Initialize
  data.forEach(record => {
    const id = record.id;
    taskIds.add(id);
    predecessors.set(id, []);
    successors.set(id, []);

    const start = new Date(record[startDateFieldId]);
    const end = new Date(record[endDateFieldId]);

    const duration = Math.floor((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));
    durations.set(id, Math.max(1, duration));
    validTasks.add(id);
  });

  // Build relationships
  data.forEach(record => {
    const successorId = record.id;
    const dependencies = record[dependencyFieldId] || [];

    dependencies.forEach((predecessorId: string) => {
      if (taskIds.has(predecessorId)) {
        predecessors.get(successorId)?.push(predecessorId);
        successors.get(predecessorId)?.push(successorId);
      }
    });
  });

  // Forward pass
  const es = new Map<string, number>();
  const ef = new Map<string, number>();

  validTasks.forEach(taskId => {
    const preds = predecessors.get(taskId) || [];
    if (preds.length === 0) {
      es.set(taskId, 0);
      ef.set(taskId, durations.get(taskId) || 1);
    }
  });

  let changed = true;
  let iterations = 0;
  const maxIterations = data.length + 1;

  while (changed && iterations < maxIterations) {
    changed = false;
    iterations++;

    validTasks.forEach(taskId => {
      const preds = predecessors.get(taskId) || [];
      if (preds.length > 0) {
        const maxPredEF = Math.max(0, ...preds.map(predId => ef.get(predId) || 0));
        const currentES = es.get(taskId) || 0;

        if (maxPredEF > currentES) {
          es.set(taskId, maxPredEF);
          ef.set(taskId, maxPredEF + (durations.get(taskId) || 1));
          changed = true;
        } else if (currentES === 0 && !es.has(taskId)) {
          es.set(taskId, maxPredEF);
          ef.set(taskId, maxPredEF + (durations.get(taskId) || 1));
          changed = true;
        }
      }
    });
  }

  // Find project duration
  const projectDuration = Math.max(0, ...Array.from(validTasks).map(taskId => {
    const succs = successors.get(taskId) || [];
    return succs.length === 0 ? (ef.get(taskId) || 0) : 0;
  }));

  // Backward pass
  const lf = new Map<string, number>();
  const ls = new Map<string, number>();

  validTasks.forEach(taskId => {
    const succs = successors.get(taskId) || [];
    if (succs.length === 0) {
      lf.set(taskId, projectDuration);
      ls.set(taskId, projectDuration - (durations.get(taskId) || 1));
    }
  });

  changed = true;
  iterations = 0;

  while (changed && iterations < maxIterations) {
    changed = false;
    iterations++;

    validTasks.forEach(taskId => {
      const succs = successors.get(taskId) || [];
      if (succs.length > 0) {
        const minSuccLS = Math.min(...succs.map(succId => ls.get(succId) || Infinity));
        const currentLF = lf.get(taskId);

        if (minSuccLS !== Infinity && (!currentLF || minSuccLS < currentLF)) {
          lf.set(taskId, minSuccLS);
          ls.set(taskId, minSuccLS - (durations.get(taskId) || 1));
          changed = true;
        }
      }
    });
  }

  // Calculate slack
  const criticalTasks = new Set<string>();

  console.log('\nTask Analysis:');
  validTasks.forEach(taskId => {
    const taskES = es.get(taskId) || 0;
    const taskLS = ls.get(taskId) || 0;
    const slack = taskLS - taskES;

    console.log(`  ${taskId}: ES=${taskES}, LS=${taskLS}, Slack=${slack}`);

    if (Math.abs(slack) < 0.1) {
      criticalTasks.add(taskId);
    }
  });

  console.log(`\nProject Duration: ${projectDuration} days`);
  console.log(`Critical Path: ${Array.from(criticalTasks).join(' -> ')}`);

  return criticalTasks;
}

// Run the test
console.log('Testing Critical Path Algorithm...\n');
const criticalPath = calculateCriticalPath(mockData, 'startDate', 'endDate', 'dependencies');

console.log('\n✅ Test completed!');
console.log(`Critical tasks: ${Array.from(criticalPath).join(', ')}`);

// Expected result: task1 -> task2 -> task4 (12 days total)
// task3 has 2 days of slack, so it's not on the critical path
console.log('\nExpected: task1, task2, task4 (critical path = 12 days)');
console.log('task3 should NOT be on critical path (has 2 days slack)');

export {};
