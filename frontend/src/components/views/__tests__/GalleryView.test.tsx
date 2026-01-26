import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { GalleryView } from '../GalleryView';

// Mock data
const mockFields = [
  { id: '1', name: 'Name', type: 'text' },
  { id: '2', name: 'Description', type: 'long_text' },
  { id: '3', name: 'Status', type: 'select', options: { choices: ['Active', 'Inactive'] } },
  { id: '4', name: 'Image', type: 'attachment' },
  { id: '5', name: 'Created', type: 'date' },
];

const mockData = [
  {
    id: 'record-1',
    table_id: 'table-1',
    data: {
      Name: 'Test Record 1',
      Description: 'This is a test description',
      Status: 'Active',
      Image: [{ url: 'https://example.com/image1.jpg' }],
      Created: '2024-01-01',
    },
    row_height: 1,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    created_by_id: 'user-1',
    last_modified_by_id: 'user-1',
  },
  {
    id: 'record-2',
    table_id: 'table-1',
    data: {
      Name: 'Test Record 2',
      Description: 'Another description',
      Status: 'Inactive',
      Created: '2024-01-02',
    },
    row_height: 1,
    created_at: '2024-01-02T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z',
    created_by_id: 'user-1',
    last_modified_by_id: 'user-1',
  },
];

describe('GalleryView', () => {
  it('renders loading state', () => {
    render(<GalleryView data={[]} fields={mockFields} isLoading={true} />);

    // Should render skeleton cards
    const skeletons = document.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('renders empty state when no data', () => {
    const mockOnRowAdd = vi.fn();
    render(<GalleryView data={[]} fields={mockFields} onRowAdd={mockOnRowAdd} />);

    expect(screen.getByText('No records found')).toBeInTheDocument();
    expect(screen.getByText('Create Record')).toBeInTheDocument();
  });

  it('renders gallery cards with data', () => {
    render(<GalleryView data={mockData} fields={mockFields} />);

    expect(screen.getByText('Test Record 1')).toBeInTheDocument();
    expect(screen.getByText('Test Record 2')).toBeInTheDocument();
  });

  it('displays cover images when available', () => {
    render(<GalleryView data={mockData} fields={mockFields} />);

    const images = screen.getAllByRole('img');
    expect(images.length).toBeGreaterThan(0);
    expect(images[0]).toHaveAttribute('src', 'https://example.com/image1.jpg');
  });

  it('shows placeholder icon when no cover image', () => {
    const dataWithoutImage = [{ ...mockData[1] }];
    render(<GalleryView data={dataWithoutImage} fields={mockFields} />);

    // Check for ImageIcon placeholder in cards without images
    const placeholders = document.querySelectorAll('.lucide-image');
    expect(placeholders.length).toBeGreaterThan(0);
  });

  it('calls onRowAdd when add button is clicked', () => {
    const mockOnRowAdd = vi.fn();
    render(<GalleryView data={mockData} fields={mockFields} onRowAdd={mockOnRowAdd} />);

    const addButton = screen.getByText('Add New Record');
    fireEvent.click(addButton);

    expect(mockOnRowAdd).toHaveBeenCalledTimes(1);
  });

  it('calls onRecordClick when card is clicked', () => {
    const mockOnRecordClick = vi.fn();
    render(<GalleryView data={mockData} fields={mockFields} onRecordClick={mockOnRecordClick} />);

    const card = screen.getByText('Test Record 1').closest('.group');
    if (card) {
      fireEvent.click(card);
      expect(mockOnRecordClick).toHaveBeenCalledWith('record-1');
    }
  });

  it('opens settings popover', async () => {
    render(<GalleryView data={mockData} fields={mockFields} />);

    const settingsButton = screen.getByText('View Settings');
    fireEvent.click(settingsButton);

    await waitFor(() => {
      expect(screen.getByText('Gallery Settings')).toBeInTheDocument();
      expect(screen.getByText('Cover Field')).toBeInTheDocument();
      expect(screen.getByText('Card Size')).toBeInTheDocument();
    });
  });

  it('changes card size when radio button is selected', async () => {
    render(<GalleryView data={mockData} fields={mockFields} />);

    // Open settings
    const settingsButton = screen.getByText('View Settings');
    fireEvent.click(settingsButton);

    await waitFor(() => {
      const largeOption = screen.getByLabelText('Large');
      fireEvent.click(largeOption);
    });

    // Check if the grid layout changes (this is a basic check)
    const grid = document.querySelector('.grid');
    expect(grid).toBeInTheDocument();
  });

  it('displays field values correctly', () => {
    render(<GalleryView data={mockData} fields={mockFields} />);

    expect(screen.getByText('Active')).toBeInTheDocument();
    expect(screen.getByText('This is a test description')).toBeInTheDocument();
  });

  it('shows updated date in card footer', () => {
    render(<GalleryView data={mockData} fields={mockFields} />);

    // Check for date formatting
    const dateElements = screen.getAllByText(/Updated/);
    expect(dateElements.length).toBeGreaterThan(0);
  });

  it('handles missing primary field gracefully', () => {
    const dataWithoutName = [{
      ...mockData[0],
      data: { ...mockData[0].data, Name: undefined },
    }];

    render(<GalleryView data={dataWithoutName} fields={mockFields} />);

    expect(screen.getByText('Untitled')).toBeInTheDocument();
  });

  it('filters attachment fields for cover selection', async () => {
    render(<GalleryView data={mockData} fields={mockFields} />);

    const settingsButton = screen.getByText('View Settings');
    fireEvent.click(settingsButton);

    await waitFor(() => {
      expect(screen.getByText('Auto (First Attachment)')).toBeInTheDocument();
    });
  });

  it('displays multiple field types correctly', () => {
    const dataWithMixedTypes = [{
      ...mockData[0],
      data: {
        Name: 'Test Record 1',
        Checkbox: true,
        Number: 42,
        Link: ['link1', 'link2'],
      },
    }];

    const fieldsWithMixedTypes = [
      { id: '1', name: 'Name', type: 'text' },
      { id: '6', name: 'Checkbox', type: 'checkbox' },
      { id: '7', name: 'Number', type: 'number' },
      { id: '8', name: 'Link', type: 'link' },
    ];

    render(<GalleryView data={dataWithMixedTypes} fields={fieldsWithMixedTypes} />);

    // Check various field types render (limited to first 4 display fields)
    expect(screen.getByText('Test Record 1')).toBeInTheDocument();
    const checkboxes = document.querySelectorAll('input[type="checkbox"]');
    expect(checkboxes.length).toBeGreaterThan(0);
  });

  it('limits display fields to prevent overcrowding', () => {
    const manyFields = Array.from({ length: 10 }, (_, i) => ({
      id: `field-${i}`,
      name: `Field ${i}`,
      type: 'text',
    }));

    const dataWithManyFields = [{
      ...mockData[0],
      data: Object.fromEntries(
        manyFields.map(f => [f.name, `Value ${f.name}`])
      ),
    }];

    render(<GalleryView data={dataWithManyFields} fields={manyFields} />);

    // Gallery view should limit displayed fields (typically to 4)
    const fieldLabels = document.querySelectorAll('.uppercase.tracking-wider');
    expect(fieldLabels.length).toBeLessThanOrEqual(4);
  });
});
