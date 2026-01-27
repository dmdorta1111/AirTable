import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import { UndoRedoToast } from '../UndoRedoToast';
import { useUndoRedoStore } from '@/features/undo-redo/stores/undoRedoStore';
import { useToast } from '@/hooks/use-toast';

// Mock the hooks
vi.mock('@/features/undo-redo/stores/undoRedoStore');
vi.mock('@/hooks/use-toast');

describe('UndoRedoToast', () => {
  const mockToast = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useToast as ReturnType<typeof vi.mock>).mockReturnValue({
      toast: mockToast,
      dismiss: vi.fn(),
      toasts: [],
    });
  });

  it('shows toast when undo operation occurs', async () => {
    const mockOperations = [
      {
        id: 'op-1',
        user_id: 'user-1',
        operation_type: 'create',
        entity_type: 'record',
        entity_id: 'record-1',
        before_data: null,
        after_data: { name: 'Test' },
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
      {
        id: 'op-2',
        user_id: 'user-1',
        operation_type: 'update',
        entity_type: 'record',
        entity_id: 'record-1',
        before_data: { name: 'Test' },
        after_data: { name: 'Updated' },
        created_at: '2024-01-01T01:00:00Z',
        updated_at: '2024-01-01T01:00:00Z',
      },
    ];

    // Start with currentIndex at 1 (second operation)
    (useUndoRedoStore as ReturnType<typeof vi.mock>).mockReturnValue({
      operations: mockOperations,
      currentIndex: 1,
      canUndo: true,
      canRedo: false,
    });

    const { rerender } = render(<UndoRedoToast />);

    // Wait for initialization - no toast should appear
    await waitFor(() => {
      expect(mockToast).not.toHaveBeenCalled();
    });

    // Simulate undo by changing currentIndex to 0
    (useUndoRedoStore as ReturnType<typeof vi.mock>).mockReturnValue({
      operations: mockOperations,
      currentIndex: 0,
      canUndo: false,
      canRedo: true,
    });

    // Rerender to trigger useEffect
    rerender(<UndoRedoToast />);

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith({
        title: 'Undo',
        description: 'Record update undone',
        variant: 'default',
      });
    });
  });

  it('shows toast when redo operation occurs', async () => {
    const mockOperations = [
      {
        id: 'op-1',
        user_id: 'user-1',
        operation_type: 'update',
        entity_type: 'field',
        entity_id: 'field-1',
        before_data: { name: 'Old Name' },
        after_data: { name: 'New Name' },
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
      {
        id: 'op-2',
        user_id: 'user-1',
        operation_type: 'delete',
        entity_type: 'view',
        entity_id: 'view-1',
        before_data: { name: 'View 1' },
        after_data: null,
        created_at: '2024-01-01T01:00:00Z',
        updated_at: '2024-01-01T01:00:00Z',
      },
    ];

    // Start with currentIndex at 0
    (useUndoRedoStore as ReturnType<typeof vi.mock>).mockReturnValue({
      operations: mockOperations,
      currentIndex: 0,
      canUndo: false,
      canRedo: true,
    });

    const { rerender } = render(<UndoRedoToast />);

    // Wait for initialization
    await waitFor(() => {
      expect(mockToast).not.toHaveBeenCalled();
    });

    // Simulate redo by changing currentIndex to 1
    (useUndoRedoStore as ReturnType<typeof vi.mock>).mockReturnValue({
      operations: mockOperations,
      currentIndex: 1,
      canUndo: true,
      canRedo: false,
    });

    rerender(<UndoRedoToast />);

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith({
        title: 'Redo',
        description: 'View delete redone',
        variant: 'default',
      });
    });
  });

  it('generates correct description for different operation types', async () => {
    const testCases = [
      {
        operation_type: 'create',
        entity_type: 'record',
        action: 'undo',
        expected: 'Record create undone',
        fromIndex: 1,
        toIndex: 0,
      },
      {
        operation_type: 'update',
        entity_type: 'field',
        action: 'undo',
        expected: 'Field update undone',
        fromIndex: 1,
        toIndex: 0,
      },
      {
        operation_type: 'delete',
        entity_type: 'view',
        action: 'undo',
        expected: 'View delete undone',
        fromIndex: 1,
        toIndex: 0,
      },
      {
        operation_type: 'create',
        entity_type: 'record',
        action: 'redo',
        expected: 'Record create redone',
        fromIndex: 0,
        toIndex: 1,
      },
    ];

    for (const testCase of testCases) {
      mockToast.mockClear();

      const mockOperations = [
        {
          id: 'op-1',
          user_id: 'user-1',
          operation_type: 'create',
          entity_type: 'record',
          entity_id: 'entity-1',
          before_data: null,
          after_data: {},
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        },
        {
          id: 'op-2',
          user_id: 'user-1',
          operation_type: testCase.operation_type,
          entity_type: testCase.entity_type,
          entity_id: 'entity-2',
          before_data: testCase.operation_type === 'create' ? null : {},
          after_data: testCase.operation_type === 'delete' ? null : {},
          created_at: '2024-01-01T01:00:00Z',
          updated_at: '2024-01-01T01:00:00Z',
        },
      ];

      // Start at fromIndex
      (useUndoRedoStore as ReturnType<typeof vi.mock>).mockReturnValue({
        operations: mockOperations,
        currentIndex: testCase.fromIndex,
        canUndo: testCase.fromIndex > 0,
        canRedo: testCase.fromIndex < 1,
      });

      const { rerender } = render(<UndoRedoToast />);

      // Wait for initialization
      await waitFor(() => {
        expect(mockToast).not.toHaveBeenCalled();
      });

      // Simulate the action by changing currentIndex
      (useUndoRedoStore as ReturnType<typeof vi.mock>).mockReturnValue({
        operations: mockOperations,
        currentIndex: testCase.toIndex,
        canUndo: testCase.toIndex > 0,
        canRedo: testCase.toIndex < 1,
      });

      rerender(<UndoRedoToast />);

      await waitFor(() => {
        const calls = mockToast.mock.calls;
        expect(calls.length).toBeGreaterThan(0);
        const lastCall = calls[calls.length - 1];
        expect(lastCall[0]?.description).toBe(testCase.expected);
      });
    }
  });

  it('does not show toast when currentIndex has not changed', async () => {
    const mockOperations = [
      {
        id: 'op-1',
        user_id: 'user-1',
        operation_type: 'create',
        entity_type: 'record',
        entity_id: 'record-1',
        before_data: null,
        after_data: { name: 'Test' },
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
    ];

    (useUndoRedoStore as ReturnType<typeof vi.mock>).mockReturnValue({
      operations: mockOperations,
      currentIndex: 0,
      canUndo: true,
      canRedo: false,
    });

    const { rerender } = render(<UndoRedoToast />);

    // Wait for initialization
    await waitFor(() => {
      expect(mockToast).not.toHaveBeenCalled();
    });

    // Re-render with same currentIndex
    rerender(<UndoRedoToast />);

    // Should still not be called
    await waitFor(() => {
      expect(mockToast).not.toHaveBeenCalled();
    });
  });

  it('does not show toast for null operation', async () => {
    (useUndoRedoStore as ReturnType<typeof vi.mock>).mockReturnValue({
      operations: [],
      currentIndex: -1,
      canUndo: false,
      canRedo: false,
    });

    render(<UndoRedoToast />);

    await waitFor(() => {
      expect(mockToast).not.toHaveBeenCalled();
    });
  });

  it('renders without crashing', () => {
    (useUndoRedoStore as ReturnType<typeof vi.mock>).mockReturnValue({
      operations: [],
      currentIndex: -1,
      canUndo: false,
      canRedo: false,
    });

    const { container } = render(<UndoRedoToast />);
    expect(container).toBeEmptyDOMElement();
  });

  it('handles multiple operations correctly', async () => {
    const mockOperations = [
      {
        id: 'op-1',
        user_id: 'user-1',
        operation_type: 'create',
        entity_type: 'record',
        entity_id: 'record-1',
        before_data: null,
        after_data: { name: 'Record 1' },
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
      {
        id: 'op-2',
        user_id: 'user-1',
        operation_type: 'update',
        entity_type: 'record',
        entity_id: 'record-1',
        before_data: { name: 'Record 1' },
        after_data: { name: 'Record 1 Updated' },
        created_at: '2024-01-01T01:00:00Z',
        updated_at: '2024-01-01T01:00:00Z',
      },
      {
        id: 'op-3',
        user_id: 'user-1',
        operation_type: 'delete',
        entity_type: 'field',
        entity_id: 'field-1',
        before_data: { name: 'Field 1' },
        after_data: null,
        created_at: '2024-01-01T02:00:00Z',
        updated_at: '2024-01-01T02:00:00Z',
      },
    ];

    // Start at index 2 (third operation)
    (useUndoRedoStore as ReturnType<typeof vi.mock>).mockReturnValue({
      operations: mockOperations,
      currentIndex: 2,
      canUndo: true,
      canRedo: false,
    });

    const { rerender } = render(<UndoRedoToast />);

    await waitFor(() => {
      expect(mockToast).not.toHaveBeenCalled();
    });

    // Simulate undo to index 1
    (useUndoRedoStore as ReturnType<typeof vi.mock>).mockReturnValue({
      operations: mockOperations,
      currentIndex: 1,
      canUndo: true,
      canRedo: true,
    });

    rerender(<UndoRedoToast />);

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith({
        title: 'Undo',
        description: 'Field delete undone',
        variant: 'default',
      });
    });

    // Simulate another undo to index 0
    mockToast.mockClear();
    (useUndoRedoStore as ReturnType<typeof vi.mock>).mockReturnValue({
      operations: mockOperations,
      currentIndex: 0,
      canUndo: false,
      canRedo: true,
    });

    rerender(<UndoRedoToast />);

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith({
        title: 'Undo',
        description: 'Record update undone',
        variant: 'default',
      });
    });
  });
});
