import React, { useCallback, useEffect, useRef } from 'react';
import { Checkbox } from '@/components/ui/checkbox';
import { useEscapeKeydown } from '@/hooks/useEscapeKeydown';

interface CheckboxCellEditorProps {
  value: boolean;
  onChange: (value: boolean) => void;
  onBlur?: () => void;
  onCancel?: () => void;
  autoFocus?: boolean;
}

export const CheckboxCellEditor: React.FC<CheckboxCellEditorProps> = ({
  value,
  onChange,
  onBlur,
  onCancel,
  autoFocus = true,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const handleEscapeKeyDown = useEscapeKeydown(onCancel);

  useEffect(() => {
    if (autoFocus && containerRef.current) {
      containerRef.current.focus();
    }
  }, [autoFocus]);

  // Combined keydown handler for toggle and escape
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === ' ' || e.key === 'Enter') {
      e.preventDefault();
      onChange(!value);
    } else {
      handleEscapeKeyDown(e);
    }
  }, [value, onChange, handleEscapeKeyDown]);

  // For checkbox, we might want to toggle immediately when cell is clicked/activated
  // But strictly as an editor, it provides a UI to toggle.
  
  return (
    <div 
        ref={containerRef}
        className="h-full w-full flex items-center justify-center bg-background focus:outline-none"
        tabIndex={0}
        onBlur={onBlur}
        onClick={() => onChange(!value)}
        onKeyDown={handleKeyDown}
    >
      <Checkbox 
        checked={value} 
        onCheckedChange={(checked) => onChange(checked === true)} 
      />
    </div>
  );
};
