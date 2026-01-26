import React, { useRef } from 'react';
import { Input } from '@/components/ui/input';

interface AttachmentCellEditorProps {
  value: any[];
  onChange: (value: any[]) => void;
  onBlur?: () => void;
  onCancel?: () => void;
  autoFocus?: boolean;
}

export const AttachmentCellEditor: React.FC<AttachmentCellEditorProps> = ({
  value,
  onChange,
  onBlur,
  onCancel,
}) => {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      // In a real app, we would upload the file here and get a URL/ID back.
      // For this mock/prototype, we'll just store the file name object.
      const newFiles = Array.from(e.target.files).map(file => ({
        name: file.name,
        size: file.size,
        type: file.type,
        url: URL.createObjectURL(file) // Temporary local URL
      }));
      
      onChange([...(value || []), ...newFiles]);
    }
  };

  return (
    <div className="h-full w-full flex items-center px-2 bg-background">
        <Input
            ref={inputRef}
            type="file"
            onChange={handleFileChange}
            onBlur={onBlur}
            onKeyDown={(e) => {
                if (e.key === 'Escape' && onCancel) {
                    e.preventDefault();
                    onCancel();
                }
            }}
            className="border-none text-xs"
            multiple
        />
    </div>
  );
};
