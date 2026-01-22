import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { AlertCircle, ArrowRight, CheckCircle2, Sparkles } from 'lucide-react';
import type { ImportPreview } from '../types';

interface FieldMappingDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  preview: ImportPreview;
  onConfirm: (mapping: Record<string, string>) => void;
  onCancel?: () => void;
}

/**
 * FieldMappingDialog allows users to map extracted fields to table columns.
 *
 * Features:
 * - Shows source fields from extracted data
 * - Shows target fields from the table with field types
 * - Displays suggested mappings with visual indicators
 * - Allows users to adjust mappings via select dropdowns
 * - Shows mapping statistics and validation
 */
export const FieldMappingDialog: React.FC<FieldMappingDialogProps> = ({
  open,
  onOpenChange,
  preview,
  onConfirm,
  onCancel,
}) => {
  // State for field mappings (source field -> target field id)
  const [fieldMapping, setFieldMapping] = useState<Record<string, string>>(
    preview.suggested_mapping
  );

  // Update mapping when preview changes
  useEffect(() => {
    setFieldMapping(preview.suggested_mapping);
  }, [preview.suggested_mapping]);

  // Get target field by id
  const getTargetField = (targetId: string) => {
    return preview.target_fields.find((f) => f.id === targetId);
  };

  // Check if a mapping is suggested (matches the suggested mapping)
  const isSuggestedMapping = (sourceField: string, targetId: string) => {
    return preview.suggested_mapping[sourceField] === targetId;
  };

  // Calculate mapping statistics
  const mappedCount = Object.keys(fieldMapping).filter((key) => fieldMapping[key]).length;
  const unmappedSourceFields = preview.source_fields.filter(
    (field) => !fieldMapping[field]
  );
  const allFieldsMapped = unmappedSourceFields.length === 0;

  // Handle mapping change for a source field
  const handleMappingChange = (sourceField: string, targetId: string) => {
    setFieldMapping((prev) => ({
      ...prev,
      [sourceField]: targetId,
    }));
  };

  // Handle unmapping a field
  const handleUnmap = (sourceField: string) => {
    setFieldMapping((prev) => {
      const newMapping = { ...prev };
      delete newMapping[sourceField];
      return newMapping;
    });
  };

  // Handle confirm
  const handleConfirm = () => {
    onConfirm(fieldMapping);
    onOpenChange(false);
  };

  // Handle cancel
  const handleCancel = () => {
    onCancel?.();
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>Map Extracted Fields to Table Columns</DialogTitle>
          <DialogDescription>
            Match the fields from your extracted data to the columns in your table.
            Suggested mappings are highlighted with a sparkle icon.
          </DialogDescription>
        </DialogHeader>

        {/* Mapping Statistics */}
        <div className="flex gap-4 py-3 px-4 bg-muted/30 rounded-lg">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            <span className="text-sm font-medium">
              {mappedCount} of {preview.source_fields.length} fields mapped
            </span>
          </div>
          {!allFieldsMapped && (
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-amber-600" />
              <span className="text-sm text-muted-foreground">
                {unmappedSourceFields.length} unmapped field{unmappedSourceFields.length !== 1 ? 's' : ''}
              </span>
            </div>
          )}
        </div>

        {/* Mapping List */}
        <div className="flex-1 overflow-y-auto space-y-3 pr-2">
          {preview.source_fields.map((sourceField) => {
            const targetId = fieldMapping[sourceField];
            const targetField = targetId ? getTargetField(targetId) : null;
            const isSuggested = targetId ? isSuggestedMapping(sourceField, targetId) : false;

            return (
              <Card
                key={sourceField}
                className={`transition-colors ${
                  isSuggested ? 'border-primary/40 bg-primary/5' : ''
                }`}
              >
                <CardContent className="p-4">
                  <div className="flex items-center gap-4">
                    {/* Source Field */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <Label className="font-semibold text-sm">{sourceField}</Label>
                        {isSuggested && (
                          <Sparkles className="h-3.5 w-3.5 text-primary" aria-label="Suggested mapping" />
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Source field from extracted data
                      </p>
                    </div>

                    {/* Mapping Arrow */}
                    <ArrowRight className="h-5 w-5 text-muted-foreground flex-shrink-0" />

                    {/* Target Field Selector */}
                    <div className="flex-1 min-w-0">
                      <Select
                        value={targetId || ''}
                        onValueChange={(value) => {
                          if (value === '__unmap__') {
                            handleUnmap(sourceField);
                          } else {
                            handleMappingChange(sourceField, value);
                          }
                        }}
                      >
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="Select target field..." />
                        </SelectTrigger>
                        <SelectContent>
                          {/* Option to unmap */}
                          {targetId && (
                            <>
                              <SelectItem value="__unmap__">
                                <span className="text-muted-foreground italic">Don't import</span>
                              </SelectItem>
                            </>
                          )}

                          {/* Target fields */}
                          {preview.target_fields.map((field) => (
                            <SelectItem key={field.id} value={field.id}>
                              <div className="flex items-center gap-2 w-full">
                                <span className="flex-1">{field.name}</span>
                                <Badge variant="secondary" className="text-xs ml-2">
                                  {field.type}
                                </Badge>
                              </div>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>

                      {/* Show selected target field info */}
                      {targetField && (
                        <div className="flex items-center gap-2 mt-1">
                          <Badge variant="outline" className="text-xs">
                            {targetField.type}
                          </Badge>
                          <span className="text-xs text-muted-foreground">
                            Target: {targetField.name}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Unmapped Fields Warning */}
        {unmappedSourceFields.length > 0 && (
          <div className="flex items-start gap-2 p-3 bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900 rounded-lg">
            <AlertCircle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-amber-900 dark:text-amber-200">
                Some fields are unmapped
              </p>
              <p className="text-xs text-amber-700 dark:text-amber-300 mt-1">
                Unmapped fields: {unmappedSourceFields.join(', ')}. These fields will not be imported.
              </p>
            </div>
          </div>
        )}

        {/* Footer Actions */}
        <DialogFooter>
          <Button variant="outline" onClick={handleCancel}>
            Cancel
          </Button>
          <Button onClick={handleConfirm} disabled={mappedCount === 0}>
            Confirm Mapping ({mappedCount} field{mappedCount !== 1 ? 's' : ''})
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
