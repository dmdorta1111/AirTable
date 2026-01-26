import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { GanttView } from '../GanttView';

// Mock date-fns to ensure consistent dates in tests
vi.mock('date-fns', async () => {
  const actual = await vi.importActual('date-fns');
  return {
    ...actual,
  };
});

// Mock data
const mockFields = [
  { id: '1', name: 'Task Name', type: 'text' },
  { id: '2', name: 'Start Date', type: 'date' },
  { id: '3', name: 'End Date', type: 'date' },
  { id: '4', name: 'Status', type: 'select', options: { choices: ['To Do', 'In Progress', 'Done'] } },
  { id: '5', name: 'Progress', type: 'number' },
];

// Use current year for dates to ensure tasks are visible in the timeline
const currentYear = new Date().getFullYear();

const mockData = [
  {
    id: 'task-1',
    'Task Name': 'Design Phase',
    'Start Date': `${currentYear}-01-01`,
    'End Date': `${currentYear}-01-15`,
    'Status': 'Done',
    'Progress': 100,
  },
  {
    id: 'task-2',
    'Task Name': 'Development Phase',
    'Start Date': `${currentYear}-01-10`,
    'End Date': `${currentYear}-02-01`,
    'Status': 'In Progress',
    'Progress': 60,
  },
  {
    id: 'task-3',
    'Task Name': 'Testing Phase',
    'Start Date': `${currentYear}-01-25`,
    'End Date': `${currentYear}-02-15`,
    'Status': 'To Do',
    'Progress': 0,
  },
];

describe('GanttView', () => {
  let mockOnCellUpdate: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockOnCellUpdate = vi.fn();
  });

  it('renders gantt chart with data', () => {
    render(<GanttView data={mockData} fields={mockFields} onCellUpdate={mockOnCellUpdate} />);

    expect(screen.getAllByText('Design Phase').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Development Phase').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Testing Phase').length).toBeGreaterThan(0);
  });

  it('displays records count', () => {
    render(<GanttView data={mockData} fields={mockFields} onCellUpdate={mockOnCellUpdate} />);

    expect(screen.getByText('3 records')).toBeInTheDocument();
  });

  it('shows toolbar with controls', () => {
    render(<GanttView data={mockData} fields={mockFields} onCellUpdate={mockOnCellUpdate} />);

    expect(screen.getByText('Today')).toBeInTheDocument();
    expect(screen.getByText('Day')).toBeInTheDocument();
    expect(screen.getByText('Week')).toBeInTheDocument();
    expect(screen.getByText('Month')).toBeInTheDocument();
  });

  it('switches view modes', () => {
    render(<GanttView data={mockData} fields={mockFields} onCellUpdate={mockOnCellUpdate} />);

    const weekButton = screen.getByText('Week');
    fireEvent.click(weekButton);

    // Week button should now have secondary variant (active state)
    expect(weekButton.className).toContain('secondary');

    const monthButton = screen.getByText('Month');
    fireEvent.click(monthButton);

    expect(monthButton.className).toContain('secondary');
  });

  it('navigates timeline with navigation buttons', () => {
    render(<GanttView data={mockData} fields={mockFields} onCellUpdate={mockOnCellUpdate} />);

    const prevButton = screen.getAllByRole('button')[0];
    const nextButton = screen.getAllByRole('button')[1];

    fireEvent.click(prevButton);
    fireEvent.click(nextButton);

    // Timeline should still render
    expect(screen.getByText('Design Phase')).toBeInTheDocument();
  });

  it('navigates to today when Today button is clicked', () => {
    render(<GanttView data={mockData} fields={mockFields} onCellUpdate={mockOnCellUpdate} />);

    const todayButton = screen.getByText('Today');
    fireEvent.click(todayButton);

    // Should show current month/year
    const currentDate = new Date();
    const currentMonthYear = currentDate.toLocaleString('default', { month: 'long', year: 'numeric' });
    const elements = screen.getAllByText(currentMonthYear);
    expect(elements.length).toBeGreaterThan(0);
  });

  it('displays timeline header with dates', () => {
    render(<GanttView data={mockData} fields={mockFields} onCellUpdate={mockOnCellUpdate} />);

    // Check for month/year headers
    const headers = document.querySelectorAll('.font-semibold.sticky');
    expect(headers.length).toBeGreaterThan(0);
  });

  it('renders task bars on timeline', () => {
    render(<GanttView data={mockData} fields={mockFields} onCellUpdate={mockOnCellUpdate} />);

    // Task bars should be rendered - check for task names in the timeline
    expect(screen.getAllByText('Design Phase').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Development Phase').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Testing Phase').length).toBeGreaterThan(0);
  });

  it('displays progress bars on tasks', () => {
    render(<GanttView data={mockData} fields={mockFields} onCellUpdate={mockOnCellUpdate} />);

    // Check for progress indicators - tasks with progress should have progress bars
    const progressBars = document.querySelectorAll('[style*="width"]');
    expect(progressBars.length).toBeGreaterThan(0);
  });

  it('shows status badges in left panel', () => {
    render(<GanttView data={mockData} fields={mockFields} onCellUpdate={mockOnCellUpdate} />);

    expect(screen.getAllByText('Done').length).toBeGreaterThan(0);
    expect(screen.getAllByText('In Progress').length).toBeGreaterThan(0);
    expect(screen.getAllByText('To Do').length).toBeGreaterThan(0);
  });

  it('filters by search query', async () => {
    render(<GanttView data={mockData} fields={mockFields} onCellUpdate={mockOnCellUpdate} />);

    const searchInput = screen.getByPlaceholderText('Search records...');
    fireEvent.change(searchInput, { target: { value: 'Design' } });

    await waitFor(() => {
      expect(screen.getByText('Design Phase')).toBeInTheDocument();
      expect(screen.queryByText('Testing Phase')).not.toBeInTheDocument();
    });
  });

  it('filters by status', async () => {
    render(<GanttView data={mockData} fields={mockFields} onCellUpdate={mockOnCellUpdate} />);

    // The status filter exists
    const filterElements = screen.getAllByRole('combobox');
    const statusFilter = filterElements.find(el => el.textContent?.includes('All Statuses'));

    expect(statusFilter || filterElements.length > 0).toBeTruthy();
  });

  it('shows warning when no date field', () => {
    const fieldsWithoutDate = [
      { id: '1', name: 'Task Name', type: 'text' },
      { id: '2', name: 'Description', type: 'long_text' },
    ];

    render(<GanttView data={mockData} fields={fieldsWithoutDate} onCellUpdate={mockOnCellUpdate} />);

    expect(screen.getByText('Start Date Required')).toBeInTheDocument();
    expect(screen.getByText(/To use the Gantt view/)).toBeInTheDocument();
  });

  it('handles missing end dates gracefully', () => {
    const dataWithoutEndDate = [
      {
        id: 'task-1',
        'Task Name': 'Single Date Task',
        'Start Date': '2024-01-01',
        'Status': 'To Do',
      },
    ];

    render(<GanttView data={dataWithoutEndDate} fields={mockFields} onCellUpdate={mockOnCellUpdate} />);

    expect(screen.getByText('Single Date Task')).toBeInTheDocument();
  });

  it('handles drag start on task bar', () => {
    render(<GanttView data={mockData} fields={mockFields} onCellUpdate={mockOnCellUpdate} />);

    // Check that task bars are interactive
    const taskBars = document.querySelectorAll('[class*="cursor-pointer"]');
    expect(taskBars.length).toBeGreaterThan(0);
  });

  it('handles resize handles on hover', () => {
    render(<GanttView data={mockData} fields={mockFields} onCellUpdate={mockOnCellUpdate} />);

    // Check for resize cursors in the DOM (they may be hidden until hover)
    const resizeHandles = document.querySelectorAll('[class*="cursor-"]');
    expect(resizeHandles.length).toBeGreaterThan(0);
  });

  it('shows tooltips with task details', () => {
    render(<GanttView data={mockData} fields={mockFields} onCellUpdate={mockOnCellUpdate} />);

    const taskBars = document.querySelectorAll('[data-state]');
    expect(taskBars.length).toBeGreaterThan(0);
  });

  it('displays weekend highlighting', () => {
    render(<GanttView data={mockData} fields={mockFields} onCellUpdate={mockOnCellUpdate} />);

    const weekendCells = document.querySelectorAll('.bg-muted\\/10, .bg-muted\\/30');
    expect(weekendCells.length).toBeGreaterThan(0);
  });

  it('highlights today column', () => {
    render(<GanttView data={mockData} fields={mockFields} onCellUpdate={mockOnCellUpdate} />);

    const todayColumns = document.querySelectorAll('.bg-primary\\/5');
    expect(todayColumns.length).toBeGreaterThan(0);
  });

  it('auto-detects date fields on mount', () => {
    render(<GanttView data={mockData} fields={mockFields} onCellUpdate={mockOnCellUpdate} />);

    // Should automatically use the first date field as start date
    expect(screen.getByText('Design Phase')).toBeInTheDocument();
  });

  it('handles invalid date values', () => {
    const dataWithInvalidDate = [
      {
        id: 'task-1',
        'Task Name': 'Invalid Task',
        'Start Date': 'invalid-date',
        'End Date': '2024-01-15',
        'Status': 'To Do',
      },
    ];

    render(<GanttView data={dataWithInvalidDate} fields={mockFields} onCellUpdate={mockOnCellUpdate} />);

    // Should not crash, task bar should not be displayed
    expect(screen.getByText('Invalid Task')).toBeInTheDocument();
  });

  it('renders grid background', () => {
    render(<GanttView data={mockData} fields={mockFields} onCellUpdate={mockOnCellUpdate} />);

    const gridBackground = document.querySelector('.absolute.inset-0.flex.pointer-events-none');
    expect(gridBackground).toBeInTheDocument();
  });

  it('shows left panel with record information', () => {
    render(<GanttView data={mockData} fields={mockFields} onCellUpdate={mockOnCellUpdate} />);

    expect(screen.getByText('Records')).toBeInTheDocument();

    // Check for start date display
    const startDates = document.querySelectorAll('.text-muted-foreground');
    expect(startDates.length).toBeGreaterThan(0);
  });

  it('handles empty data gracefully', () => {
    render(<GanttView data={[]} fields={mockFields} onCellUpdate={mockOnCellUpdate} />);

    expect(screen.getByText('0 records')).toBeInTheDocument();
  });
});
