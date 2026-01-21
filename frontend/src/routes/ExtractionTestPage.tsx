import { useState } from 'react';
import { FileUploadDropzone } from '@/features/extraction/components/FileUploadDropzone';
import { ExtractionPreview } from '@/features/extraction/components/ExtractionPreview';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import type { ImportPreview } from '@/features/extraction/types';

// Mock preview data for testing
const mockPreview: ImportPreview = {
  source_fields: ['Part Number', 'Description', 'Quantity', 'Unit Price', 'Material', 'Finish'],
  target_fields: [
    { id: 'field_1', name: 'Part Number', type: 'text' },
    { id: 'field_2', name: 'Description', type: 'text' },
    { id: 'field_3', name: 'Quantity', type: 'number' },
    { id: 'field_4', name: 'Unit Price', type: 'number' },
    { id: 'field_5', name: 'Material', type: 'select' },
    { id: 'field_6', name: 'Surface Finish', type: 'text' },
  ],
  suggested_mapping: {
    'Part Number': 'field_1',
    'Description': 'field_2',
    'Quantity': 'field_3',
    'Unit Price': 'field_4',
    'Material': 'field_5',
    'Finish': 'field_6',
  },
  sample_data: [
    {
      'Part Number': 'PN-12345',
      'Description': 'Hex Bolt M8x40',
      'Quantity': 100,
      'Unit Price': 0.45,
      'Material': 'Steel',
      'Finish': 'Zinc Plated',
    },
    {
      'Part Number': 'PN-12346',
      'Description': 'Washer M8',
      'Quantity': 200,
      'Unit Price': 0.12,
      'Material': 'Steel',
      'Finish': 'Zinc Plated',
    },
    {
      'Part Number': 'PN-12347',
      'Description': 'Nut M8',
      'Quantity': '150',
      'Unit Price': 'invalid',
      'Material': 'Stainless Steel',
      'Finish': '',
    },
    {
      'Part Number': 'PN-12348',
      'Description': 'Spacer 10mm',
      'Quantity': 75,
      'Unit Price': 0.89,
      'Material': 'Aluminum',
      'Finish': 'Anodized',
    },
    {
      'Part Number': 'PN-12349',
      'Description': 'O-Ring 20mm',
      'Quantity': 50,
      'Unit Price': 1.25,
      'Material': 'NBR Rubber',
      'Finish': null,
    },
  ],
  total_records: 150,
};

export default function ExtractionTestPage() {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [showPreview, setShowPreview] = useState(false);
  const [selectedRows, setSelectedRows] = useState<number[]>([]);

  const handleFileSelect = (files: File[]) => {
    setSelectedFiles(files);
    // Automatically show preview when files are selected
    if (files.length > 0) {
      setShowPreview(true);
    }
  };

  const handleSelectionChange = (indices: number[]) => {
    setSelectedRows(indices);
  };

  return (
    <div className="container mx-auto p-8 space-y-8">
      <Card>
        <CardHeader>
          <CardTitle>File Upload Dropzone Test</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <FileUploadDropzone onFileSelect={handleFileSelect} maxFiles={5} />

          {selectedFiles.length > 0 && (
            <div className="mt-6 p-4 bg-accent rounded-md">
              <h3 className="text-sm font-medium mb-2">Debug Info:</h3>
              <pre className="text-xs overflow-auto">
                {JSON.stringify(
                  selectedFiles.map((f) => ({
                    name: f.name,
                    size: f.size,
                    type: f.type,
                  })),
                  null,
                  2
                )}
              </pre>
            </div>
          )}

          <div className="flex gap-2">
            <Button onClick={() => setShowPreview(!showPreview)}>
              {showPreview ? 'Hide' : 'Show'} Preview (Mock Data)
            </Button>
            {selectedRows.length > 0 && (
              <Button variant="outline">
                Import {selectedRows.length} Selected Rows
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {showPreview && (
        <div>
          <ExtractionPreview
            preview={mockPreview}
            onSelectionChange={handleSelectionChange}
          />
        </div>
      )}
    </div>
  );
}
