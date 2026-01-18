import React, { useEffect, useRef } from 'react';
import { Input } from '@/components/ui/input';

// In a real implementation, this would search for records in the linked table.
// For now, we'll treat it as a read-only display or simple ID input.

interface LinkCellEditorProps {
  value: any;
  onChange: (value: any) => void;
  onBlur?: () => void;
  autoFocus?: boolean;
}

export const LinkCellEditor: React.FC<LinkCellEditorProps> = ({
  value,
  onChange,
  onBlur,
  autoFocus = true,
}) => {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus();
    }
  }, [autoFocus]);

  const displayValue = Array.isArray(value) 
    ? value.map(v => v.id || v).join(', ') 
    : (value?.id || value || '');

  return (
    <Input
      ref={inputRef}
      value={displayValue}
      onChange={(e) => onChange(e.target.value)} // Simplified: treats input as ID or text
      onBlur={onBlur}
      placeholder="Enter record ID..."
      className="h-full w-full border-none rounded-none focus-visible:ring-0 px-2 bg-background"
    />
  );
};
