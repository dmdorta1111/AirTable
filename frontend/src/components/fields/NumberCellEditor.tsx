import React, { useEffect, useRef } from 'react';
import { Input } from '@/components/ui/input';

interface NumberCellEditorProps {
  value: number | string;
  onChange: (value: number | string) => void;
  onBlur?: () => void;
  autoFocus?: boolean;
}

export const NumberCellEditor: React.FC<NumberCellEditorProps> = ({
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
      className="h-full w-full border-none rounded-none focus-visible:ring-0 px-2 bg-background text-right"
    />
  );
};
