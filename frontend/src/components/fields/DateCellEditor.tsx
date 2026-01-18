import React, { useEffect, useRef } from 'react';
import { Input } from '@/components/ui/input';

interface DateCellEditorProps {
  value: string; // ISO date string YYYY-MM-DD
  onChange: (value: string) => void;
  onBlur?: () => void;
  autoFocus?: boolean;
}

export const DateCellEditor: React.FC<DateCellEditorProps> = ({
  value,
  onChange,
  onBlur,
  autoFocus = true,
}) => {
  const inputRef = useRef<HTMLInputElement>(null);

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
      className="h-full w-full border-none rounded-none focus-visible:ring-0 px-2 bg-background"
    />
  );
};
