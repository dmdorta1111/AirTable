import React, { useEffect, useRef } from 'react';
import { Input } from '@/components/ui/input';
import { useEscapeKeydown } from '@/hooks/useEscapeKeydown';

interface DateCellEditorProps {
  value: string; // ISO date string YYYY-MM-DD
  onChange: (value: string) => void;
  onCancel?: () => void;
  onBlur?: () => void;
  autoFocus?: boolean;
}

export const DateCellEditor: React.FC<DateCellEditorProps> = ({
  value,
  onChange,
  onCancel,
  onBlur,
  autoFocus = true,
}) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const handleKeyDown = useEscapeKeydown(onCancel);

  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus();
      // Try to show picker if possible (browser dependent)
      if (typeof inputRef.current.showPicker === 'function') {
        try {
            inputRef.current.showPicker();
        } catch (e) {
            // ignore
        }
      }
    }
  }, [autoFocus]);

  return (
    <Input
      ref={inputRef}
      type="date"
      value={value ? value.split('T')[0] : ''}
      onChange={(e) => onChange(e.target.value)}
      onBlur={onBlur}
      onKeyDown={handleKeyDown}
      className="h-full w-full border-none rounded-none focus-visible:ring-0 px-2 bg-background"
    />
  );
};
