import React, { useEffect, useRef } from 'react';
import { Input } from '@/components/ui/input';

interface NumberCellEditorProps {
  value: number | string;
  onChange: (value: number | string) => void;
  onCancel?: () => void;
  onBlur?: () => void;
  autoFocus?: boolean;
}

export const NumberCellEditor: React.FC<NumberCellEditorProps> = ({
  value,
  onChange,
  onCancel,
  onBlur,
  autoFocus = true,
}) => {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus();
    }
  }, [autoFocus]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    // Allow empty string or valid number input
    if (val === '' || !isNaN(Number(val))) {
      onChange(val === '' ? '' : Number(val));
    }
  };

  return (
    <Input
      ref={inputRef}
      type="number"
      value={value ?? ''}
      onChange={handleChange}
      onBlur={onBlur}
      onKeyDown={(e) => {
        if (e.key === 'Escape' && onCancel) {
          e.preventDefault();
          onCancel();
        }
      }}
      className="h-full w-full border-none rounded-none focus-visible:ring-0 px-2 bg-background text-right"
    />
  );
};
