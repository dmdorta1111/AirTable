import React, { useEffect, useRef } from 'react';
import { Checkbox } from '@/components/ui/checkbox';

interface CheckboxCellEditorProps {
  value: boolean;
  onChange: (value: boolean) => void;
  onBlur?: () => void;
  autoFocus?: boolean;
}

export const CheckboxCellEditor: React.FC<CheckboxCellEditorProps> = ({
  value,
  onChange,
  onBlur,
  autoFocus = true,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoFocus && containerRef.current) {
      containerRef.current.focus();
    }
  }, [autoFocus]);

  // For checkbox, we might want to toggle immediately when cell is clicked/activated
  // But strictly as an editor, it provides a UI to toggle.
  
  return (
    <div 
        ref={containerRef}
        className="h-full w-full flex items-center justify-center bg-background focus:outline-none"
        tabIndex={0}
        onBlur={onBlur}
        onClick={() => onChange(!value)}
        onKeyDown={(e) => {
            if (e.key === ' ' || e.key === 'Enter') {
                e.preventDefault();
                onChange(!value);
            }
        }}
    >
      <Checkbox 
        checked={value} 
        onCheckedChange={(checked) => onChange(checked === true)} 
      />
    </div>
  );
};
