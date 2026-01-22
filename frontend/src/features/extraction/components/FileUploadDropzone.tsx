import React, { useRef, useState } from 'react';
import { cn } from '@/lib/utils';

interface FileUploadDropzoneProps {
  onFileSelect: (files: File[]) => void;
  accept?: string;
  maxFiles?: number;
  className?: string;
}

export const FileUploadDropzone: React.FC<FileUploadDropzoneProps> = ({
  onFileSelect,
  accept = '.pdf,.dxf,.ifc,.step',
  maxFiles = 1,
  className,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    handleFiles(files);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const files = Array.from(e.target.files);
      handleFiles(files);
    }
  };

  const handleFiles = (files: File[]) => {
    const acceptedExtensions = accept.split(',').map(ext => ext.trim().toLowerCase());

    const validFiles = files.filter(file => {
      const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
      return acceptedExtensions.includes(fileExtension);
    });

    const filesToAdd = maxFiles === 1 ? validFiles.slice(0, 1) : validFiles.slice(0, maxFiles);

    setSelectedFiles(filesToAdd);
    onFileSelect(filesToAdd);
  };

  const handleClick = () => {
    inputRef.current?.click();
  };

  const removeFile = (index: number) => {
    const updatedFiles = selectedFiles.filter((_, i) => i !== index);
    setSelectedFiles(updatedFiles);
    onFileSelect(updatedFiles);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className={cn('w-full', className)}>
      <div
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
        className={cn(
          'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
          isDragging
            ? 'border-primary bg-primary/10'
            : 'border-input hover:border-primary/50 hover:bg-accent/50',
        )}
      >
        <input
          ref={inputRef}
          type="file"
          onChange={handleFileChange}
          accept={accept}
          multiple={maxFiles > 1}
          className="hidden"
        />

        <div className="flex flex-col items-center gap-2">
          <svg
            className={cn(
              'w-12 h-12 transition-colors',
              isDragging ? 'text-primary' : 'text-muted-foreground'
            )}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>

          <div className="space-y-1">
            <p className="text-sm font-medium">
              {isDragging ? 'Drop files here' : 'Click to upload or drag and drop'}
            </p>
            <p className="text-xs text-muted-foreground">
              Supported formats: PDF, DXF, IFC, STEP
            </p>
          </div>
        </div>
      </div>

      {selectedFiles.length > 0 && (
        <div className="mt-4 space-y-2">
          <p className="text-sm font-medium">Selected files:</p>
          {selectedFiles.map((file, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-3 bg-accent rounded-md"
            >
              <div className="flex items-center gap-3 flex-1 min-w-0">
                <svg
                  className="w-5 h-5 text-muted-foreground flex-shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{file.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {formatFileSize(file.size)}
                  </p>
                </div>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  removeFile(index);
                }}
                className="text-muted-foreground hover:text-destructive transition-colors flex-shrink-0 ml-2"
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
