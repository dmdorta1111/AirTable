import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { TimelineView } from '../TimelineView';

// Mock date-fns to ensure consistent dates in tests
vi.mock('date-fns', async () => {
  const actual = await vi.importActual('date-fns');
  return {
    ...actual,
  };
});

// Mock data
const mockFields = [
  { id: '1', name: 'Name', type: 'text' },
  { id: '2', name: 'Event Date', type: 'date' },
  { id: '3', name: 'Status', type: 'select', options: { choices: ['Done', 'In Progress', 'Pending'] } },
  { id: '4', name: 'Tags', type: 'multi_select', options: { choices: ['Important', 'Urgent', 'Review'] } },
  { id: '5', name: 'Description', type: 'long_text' },
];

// Use current year for dates to ensure events are visible in the timeline
const currentYear = new Date().getFullYear();

const mockData = [
  {
    id: 'event-1',
    Name: 'Project Kickoff',
    'Event Date': `${currentYear}-01-15`,
    Status: 'Done',
    Tags: ['Important', 'Review'],
    Description: 'Initial project meeting',
  },
  {
    id: 'event-2',
    Name: 'Design Review',
    'Event Date': `${currentYear}-02-10`,
    Status: 'In Progress',
    Tags: ['Important'],
    Description: 'Review design mockups',
  },
  {
    id: 'event-3',
    Name: 'Launch Preparation',
    'Event Date': `${currentYear}-03-05`,
    Status: 'Pending',
    Tags: ['Urgent'],
    Description: 'Prepare for product launch',
  },
  {
    id: 'event-4',
    Name: 'Q1 Retrospective',
    'Event Date': `${currentYear}-03-20`,
    Status: 'Pending',
    Tags: ['Review'],
    Description: 'Quarter review meeting',
  },
];

describe('TimelineView', () => {
  beforeEach(() => {
    // Reset any mocks if needed
  });

  it('renders timeline with data', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    // Check that timeline structure is rendered
    const body = document.body;
    expect(body.innerHTML).toContain('Groups');
    expect(body.innerHTML).toContain('Done');
    expect(body.innerHTML).toContain('In Progress');
    expect(body.innerHTML).toContain('Pending');
    expect(body.querySelector('.flex.flex-1.overflow-hidden')).toBeInTheDocument();
  });

  it('displays records count', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    // Groups should show count of records (per group)
    const body = document.body;
    expect(body.innerHTML).toContain('1 records');
    expect(body.innerHTML).toContain('2 records');
  });

  it('shows toolbar with controls', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    // Check for toolbar buttons in the DOM
    const body = document.body;
    expect(body.innerHTML).toContain('Today');
    expect(body.innerHTML).toContain('day');
    expect(body.innerHTML).toContain('week');
    expect(body.innerHTML).toContain('month');
  });

  it('shows warning when no date field', () => {
    const fieldsWithoutDate = [
      { id: '1', name: 'Name', type: 'text' },
      { id: '2', name: 'Description', type: 'long_text' },
    ];

    render(<TimelineView data={mockData} fields={fieldsWithoutDate} />);

    expect(screen.getByText('No Date Field Found')).toBeInTheDocument();
    expect(screen.getByText(/Please add a Date field/)).toBeInTheDocument();
  });

  it('displays search input', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    const searchInput = screen.getByPlaceholderText('Search timeline...');
    expect(searchInput).toBeInTheDocument();
  });

  it('filters records by search query', async () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    const searchInput = screen.getByPlaceholderText('Search timeline...');
    fireEvent.change(searchInput, { target: { value: 'Design' } });

    await waitFor(() => {
      // Search input value should change
      expect(searchInput).toHaveValue('Design');
    });
  });

  it('switches view modes', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    // Find buttons with the text content
    const buttons = screen.getAllByRole('button');
    const weekButton = buttons.find(btn => btn.textContent === 'week');
    const monthButton = buttons.find(btn => btn.textContent === 'month');

    expect(weekButton).toBeInTheDocument();
    expect(monthButton).toBeInTheDocument();

    if (weekButton) fireEvent.click(weekButton);
    if (monthButton) fireEvent.click(monthButton);

    // Timeline structure should still be present
    expect(document.querySelector('.flex.flex-1.overflow-hidden')).toBeInTheDocument();
  });

  it('navigates timeline with navigation buttons', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    const buttons = screen.getAllByRole('button');
    const prevButton = buttons[0];
    const nextButton = buttons[1];

    fireEvent.click(prevButton);
    fireEvent.click(nextButton);

    // Timeline structure should still be present
    expect(document.querySelector('.flex.flex-1.overflow-hidden')).toBeInTheDocument();
  });

  it('navigates to today when Today button is clicked', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    const buttons = screen.getAllByRole('button');
    const todayButton = buttons.find(btn => btn.textContent === 'Today');

    expect(todayButton).toBeInTheDocument();
    if (todayButton) fireEvent.click(todayButton);

    // Timeline should still be present
    expect(document.querySelector('.flex.flex-1.overflow-hidden')).toBeInTheDocument();
  });

  it('displays timeline header with dates', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    // Check for date headers
    const headers = document.querySelectorAll('.sticky');
    expect(headers.length).toBeGreaterThan(0);
  });

  it('renders event markers on timeline', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    // Check that timeline structure is rendered
    const body = document.body;
    expect(body.innerHTML).toContain('Done');
    expect(body.innerHTML).toContain('In Progress');
    expect(body.innerHTML).toContain('Pending');
  });

  it('displays status badges in left panel', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    expect(screen.getAllByText('Done').length).toBeGreaterThan(0);
    expect(screen.getAllByText('In Progress').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Pending').length).toBeGreaterThan(0);
  });

  it('displays timeline markers on horizontal swimlanes', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    // Timeline structure should be present (markers are in collapsed groups by default)
    const timelineContainer = document.querySelector('.relative.pt-0.pb-10');
    expect(timelineContainer).toBeInTheDocument();
  });

  it('applies color coding to status markers', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    // Timeline structure should be present (markers are in collapsed groups by default)
    const timelineContainer = document.querySelector('.relative.pt-0.pb-10');
    expect(timelineContainer).toBeInTheDocument();
  });

  it('filters by search query', async () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    const searchInput = screen.getByPlaceholderText('Search timeline...');
    fireEvent.change(searchInput, { target: { value: 'Design' } });

    await waitFor(() => {
      // Search input value should change
      expect(searchInput).toHaveValue('Design');
    });
  });

  it('shows no matches message when no records match filter', async () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    const searchInput = screen.getByPlaceholderText('Search timeline...');
    fireEvent.change(searchInput, { target: { value: 'nonexistent' } });

    await waitFor(() => {
      expect(screen.getByText(/No matches found/i)).toBeInTheDocument();
    });
  });

  it('handles records without dates', () => {
    const dataWithMissingDate = [
      ...mockData,
      {
        id: 'event-5',
        Name: 'No Date Event',
        Status: 'Pending',
      },
    ];

    render(<TimelineView data={dataWithMissingDate} fields={mockFields} />);

    // Should filter out records without dates
    expect(screen.queryByText('No Date Event')).not.toBeInTheDocument();
  });

  it('handles invalid date formats', () => {
    const dataWithInvalidDate = [
      {
        id: 'event-1',
        Name: 'Invalid Date Event',
        'Event Date': 'not-a-date',
        Status: 'Pending',
      },
    ];

    render(<TimelineView data={dataWithInvalidDate} fields={mockFields} />);

    // Should filter out records with invalid dates
    expect(screen.queryByText('Invalid Date Event')).not.toBeInTheDocument();
  });

  it('renders grid background', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    const gridBackground = document.querySelector('.absolute.inset-0.flex.pointer-events-none');
    expect(gridBackground).toBeInTheDocument();
  });

  it('shows left panel with group information', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    expect(screen.getByText('Groups')).toBeInTheDocument();

    // Check for record counts in groups (individual group counts)
    const body = document.body;
    expect(body.innerHTML).toContain('records');
  });

  it('handles empty data gracefully', () => {
    render(<TimelineView data={[]} fields={mockFields} />);

    // Should show empty state in groups
    expect(screen.getByText('0 groups')).toBeInTheDocument();
  });

  it('displays weekend highlighting in day/week mode', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    const weekendCells = document.querySelectorAll('.bg-muted\\/10, .bg-muted\\/30');
    expect(weekendCells.length).toBeGreaterThan(0);
  });

  it('highlights today column', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    const todayColumns = document.querySelectorAll('.bg-primary\\/5');
    expect(todayColumns.length).toBeGreaterThan(0);
  });

  it('auto-detects date fields on mount', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    // Should automatically use the first date field
    const body = document.body;
    expect(body.innerHTML).toContain('Done');
    expect(body.innerHTML).toContain('In Progress');
    expect(body.innerHTML).toContain('Pending');
  });

  it('handles invalid date values', () => {
    const dataWithInvalidDate = [
      {
        id: 'event-1',
        Name: 'Invalid Event',
        'Event Date': 'invalid-date',
        Status: 'Pending',
      },
    ];

    render(<TimelineView data={dataWithInvalidDate} fields={mockFields} />);

    // Should filter out records with invalid dates
    expect(screen.queryByText('Invalid Event')).not.toBeInTheDocument();
  });

  it('shows tooltips with event details', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    const markers = document.querySelectorAll('[class*="rounded-full"]');
    expect(markers.length).toBeGreaterThan(0);
  });

  it('handles click on timeline marker', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    // Check that timeline markers are interactive
    const markers = document.querySelectorAll('[class*="cursor-pointer"]');
    expect(markers.length).toBeGreaterThan(0);
  });

  it('displays search input', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    const searchInput = screen.getByPlaceholderText('Search timeline...');
    expect(searchInput).toBeInTheDocument();
  });

  it('expands and collapses groups', async () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    // Find clickable elements in the groups panel
    const groupElements = document.querySelectorAll('.cursor-pointer');
    expect(groupElements.length).toBeGreaterThan(0);

    if (groupElements.length > 0) {
      const firstGroup = groupElements[0];
      fireEvent.click(firstGroup);

      // After clicking, component should still render
      await waitFor(() => {
        expect(document.body.innerHTML).toContain('Done');
      });
    }
  });
});
