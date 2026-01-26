import React, { useCallback, useState } from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useEscapeKeydown } from '@/hooks/useEscapeKeydown';

interface Option {
  id: string;
  name: string;
  color?: string;
}

interface SelectCellEditorProps {
  value: string;
  options?: Option[];
  onChange: (value: string) => void;
  onBlur?: () => void;
  onCancel?: () => void;
  autoFocus?: boolean;
}

export const SelectCellEditor: React.FC<SelectCellEditorProps> = ({
  value,
  options = [],
  onChange,
  onBlur,
  onCancel,
  autoFocus = true,
}) => {
  const [open, setOpen] = useState(autoFocus);

  // Combined handler for escape - close dropdown and cancel
  const handleCancel = useCallback(() => {
    setOpen(false);
    if (onCancel) onCancel();
  }, [onCancel]);

  const handleKeyDown = useEscapeKeydown(handleCancel);

  const handleValueChange = (val: string) => {
    onChange(val);
    if (onBlur) onBlur();
  };

  return (
    <div
        className="h-full w-full"
        onKeyDown={handleKeyDown}
    >
        <Select
            value={value}
            onValueChange={handleValueChange}
            open={open}
            onOpenChange={(isOpen) => {
                setOpen(isOpen);
                if (!isOpen && onBlur) onBlur();
            }}
        >
        <SelectTrigger className="h-full w-full border-none rounded-none focus:ring-0 px-2 bg-background">
            <SelectValue placeholder="Select..." />
        </SelectTrigger>
        <SelectContent>
            {options.map((option) => (
            <SelectItem key={option.id || option.name} value={option.id || option.name}>
                <div className="flex items-center gap-2">
                    {option.color && (
                        <div
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: option.color }}
                        />
                    )}
                    {option.name}
                </div>
            </SelectItem>
            ))}
        </SelectContent>
        </Select>
    </div>
  );
};
