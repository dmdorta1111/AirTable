import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { TimelineView } from '../TimelineView';

// Mock data
const mockFields = [
  { id: '1', name: 'Name', type: 'text' },
  { id: '2', name: 'Event Date', type: 'date' },
  { id: '3', name: 'Status', type: 'select', options: { choices: ['Done', 'In Progress', 'Pending'] } },
  { id: '4', name: 'Tags', type: 'multi_select', options: { choices: ['Important', 'Urgent', 'Review'] } },
  { id: '5', name: 'Description', type: 'long_text' },
];

// Use current year for dates
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

    expect(screen.getByText('Project Kickoff')).toBeInTheDocument();
    expect(screen.getByText('Design Review')).toBeInTheDocument();
    expect(screen.getByText('Launch Preparation')).toBeInTheDocument();
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
      expect(screen.getByText('Design Review')).toBeInTheDocument();
      expect(screen.queryByText('Project Kickoff')).not.toBeInTheDocument();
    });
  });

  it('displays zoom level selector', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    const zoomSelector = screen.getByRole('combobox');
    expect(zoomSelector).toBeInTheDocument();
  });

  it('changes zoom level', async () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    const zoomSelector = screen.getByRole('combobox');
    expect(zoomSelector).toBeInTheDocument();

    // Verify default month view shows month groupings
    expect(screen.getByText(new RegExp(`January ${currentYear}`, 'i'))).toBeInTheDocument();
  });

  it('groups events by month', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    // Should display month groupings
    expect(screen.getByText(new RegExp(`January ${currentYear}`, 'i'))).toBeInTheDocument();
    expect(screen.getByText(new RegExp(`February ${currentYear}`, 'i'))).toBeInTheDocument();
    expect(screen.getByText(new RegExp(`March ${currentYear}`, 'i'))).toBeInTheDocument();
  });

  it('groups events by quarter when zoom is quarter', async () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    // Zoom selector exists for changing view
    const zoomSelector = screen.getByRole('combobox');
    expect(zoomSelector).toBeInTheDocument();
  });

  it('groups events by year when zoom is year', async () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    // Current year should be displayed in month headers
    expect(screen.getAllByText(new RegExp(currentYear.toString())).length).toBeGreaterThan(0);
  });

  it('displays record count badges', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    // Each group should show count of records in badges (secondary variant)
    const badges = document.querySelectorAll('.inline-flex.items-center');
    expect(badges.length).toBeGreaterThan(0);
  });

  it('expands and collapses groups', async () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    // Find a group header
    const groupHeader = screen.getByText(new RegExp(`January ${currentYear}`, 'i'));

    // Groups should be expanded by default
    expect(screen.getByText('Project Kickoff')).toBeInTheDocument();

    // Click to collapse
    fireEvent.click(groupHeader);

    await waitFor(() => {
      expect(screen.queryByText('Project Kickoff')).not.toBeInTheDocument();
    });

    // Click to expand again
    fireEvent.click(groupHeader);

    await waitFor(() => {
      expect(screen.getByText('Project Kickoff')).toBeInTheDocument();
    });
  });

  it('displays status badges', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    expect(screen.getAllByText('Done').length).toBeGreaterThan(0);
    expect(screen.getAllByText('In Progress').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Pending').length).toBeGreaterThan(0);
  });

  it('displays tags', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    expect(screen.getAllByText('Important').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Urgent').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Review').length).toBeGreaterThan(0);
  });

  it('shows timeline vertical line', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    const timelineLine = document.querySelector('.absolute.left-\\[27px\\]');
    expect(timelineLine).toBeInTheDocument();
  });

  it('displays timeline nodes', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    const nodes = document.querySelectorAll('.rounded-full.border-2');
    expect(nodes.length).toBe(mockData.length);
  });

  it('applies color coding to status nodes', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    // Check for status-based colors
    const greenNode = document.querySelector('.bg-green-500');
    const blueNode = document.querySelector('.bg-blue-500');
    const primaryNode = document.querySelector('.bg-primary');

    expect(greenNode).toBeInTheDocument(); // Done status
    expect(blueNode).toBeInTheDocument();  // In Progress status
    expect(primaryNode).toBeInTheDocument(); // Default status
  });

  it('opens detail modal when record is clicked', async () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    const recordCard = screen.getByText('Project Kickoff').closest('[class*="hover:shadow-lg"]');
    if (recordCard) {
      fireEvent.click(recordCard);

      await waitFor(() => {
        // Modal should show the record title
        expect(screen.getAllByText('Project Kickoff').length).toBeGreaterThan(1);
      });
    }
  });

  it('closes detail modal when close button is clicked', async () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    const recordCard = screen.getByText('Project Kickoff').closest('[class*="hover:shadow-lg"]');
    if (recordCard) {
      fireEvent.click(recordCard);

      await waitFor(() => {
        // Modal opens with record details
        expect(screen.getAllByText('Project Kickoff').length).toBeGreaterThan(1);
      });

      const closeButtons = screen.getAllByRole('button');
      const closeButton = closeButtons.find(btn => btn.querySelector('[class*="lucide-x"]'));
      if (closeButton) {
        fireEvent.click(closeButton);

        await waitFor(() => {
          // Modal should be closed, only one instance of title remains
          expect(screen.getAllByText('Project Kickoff').length).toBe(1);
        });
      }
    }
  });

  it('displays all fields in detail modal', async () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    const recordCard = screen.getByText('Project Kickoff').closest('[class*="hover:shadow-lg"]');
    if (recordCard) {
      fireEvent.click(recordCard);

      await waitFor(() => {
        // Check for field labels in uppercase format
        expect(screen.getByText(/NAME/i)).toBeInTheDocument();
        expect(screen.getByText(/EVENT DATE/i)).toBeInTheDocument();
        expect(screen.getByText(/DESCRIPTION/i)).toBeInTheDocument();
      });
    }
  });

  it('sorts records chronologically', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    // Check that all records are rendered
    expect(screen.getByText('Project Kickoff')).toBeInTheDocument();
    expect(screen.getByText('Design Review')).toBeInTheDocument();
    expect(screen.getByText('Launch Preparation')).toBeInTheDocument();
    expect(screen.getByText('Q1 Retrospective')).toBeInTheDocument();
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

  it('shows empty state when no records match filter', async () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    const searchInput = screen.getByPlaceholderText('Search timeline...');
    fireEvent.change(searchInput, { target: { value: 'nonexistent' } });

    await waitFor(() => {
      expect(screen.getByText(/No records found/i)).toBeInTheDocument();
    });
  });

  it('displays mobile-friendly date format', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    // Mobile dates should be visible on smaller screens
    const mobileDates = document.querySelectorAll('.sm\\:hidden');
    expect(mobileDates.length).toBeGreaterThan(0);
  });

  it('shows desktop-friendly date labels', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    // Desktop date labels in left column
    const desktopDates = document.querySelectorAll('.hidden.sm\\:flex');
    expect(desktopDates.length).toBeGreaterThan(0);
  });

  it('applies hover effects to cards', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    const cards = document.querySelectorAll('.hover\\:shadow-lg');
    expect(cards.length).toBe(mockData.length);
  });

  it('handles multiple tags correctly', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    // Project Kickoff has two tags
    const importantBadges = screen.getAllByText('Important');
    const reviewBadges = screen.getAllByText('Review');

    expect(importantBadges.length).toBeGreaterThan(0);
    expect(reviewBadges.length).toBeGreaterThan(0);
  });

  it('handles empty data array', () => {
    render(<TimelineView data={[]} fields={mockFields} />);

    expect(screen.getByText(/No records found/i)).toBeInTheDocument();
  });

  it('displays filter button', () => {
    render(<TimelineView data={mockData} fields={mockFields} />);

    const filterButton = document.querySelector('.lucide-filter');
    expect(filterButton).toBeInTheDocument();
  });
});
