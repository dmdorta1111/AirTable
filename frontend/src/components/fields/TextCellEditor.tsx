import React, { useEffect, useRef } from 'react';
import { Input } from '@/components/ui/input';
import { useEscapeKeydown } from '@/hooks/useEscapeKeydown';

interface TextCellEditorProps {
  value: string;
  onChange: (value: string) => void;
  onBlur?: () => void;
  onCancel?: () => void;
  autoFocus?: boolean;
}

export const TextCellEditor: React.FC<TextCellEditorProps> = ({
  value,
  onChange,
  onBlur,
  onCancel,
  autoFocus = true,
}) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const handleKeyDown = useEscapeKeydown(onCancel);

  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus();
    }
  }, [autoFocus]);

  return (
    <Input
      ref={inputRef}
      value={value || ''}
      onChange={(e) => onChange(e.target.value)}
      onBlur={onBlur}
      onKeyDown={handleKeyDown}
      className="h-full w-full border-none rounded-none focus-visible:ring-0 px-2 bg-background"
    />
  );
};
