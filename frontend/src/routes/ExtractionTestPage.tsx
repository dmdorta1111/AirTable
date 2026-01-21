import { useState } from 'react';
import { FileUploadDropzone } from '@/features/extraction/components/FileUploadDropzone';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';

export default function ExtractionTestPage() {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);

  const handleFileSelect = (files: File[]) => {
    setSelectedFiles(files);
  };

  return (
    <div className="container mx-auto p-8">
      <Card>
        <CardHeader>
          <CardTitle>File Upload Dropzone Test</CardTitle>
        </CardHeader>
        <CardContent>
          <FileUploadDropzone onFileSelect={handleFileSelect} maxFiles={5} />

          {selectedFiles.length > 0 && (
            <div className="mt-6 p-4 bg-accent rounded-md">
              <h3 className="text-sm font-medium mb-2">Debug Info:</h3>
              <pre className="text-xs overflow-auto">
                {JSON.stringify(
                  selectedFiles.map(f => ({
                    name: f.name,
                    size: f.size,
                    type: f.type
                  })),
                  null,
                  2
                )}
              </pre>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
