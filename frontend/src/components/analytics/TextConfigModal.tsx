import React, { useCallback, useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';

export type FontSize = 'xs' | 'sm' | 'base' | 'lg' | 'xl' | '2xl' | '3xl';

export interface TextConfig {
  title: string;
  content: string;
  fontSize: FontSize;
  fontColor: string;
  backgroundColor?: string;
  alignment: 'left' | 'center' | 'right' | 'justify';
}

interface TextConfigModalProps {
  open: boolean;
  onClose: () => void;
  onSave: (config: TextConfig) => void;
  initialConfig?: Partial<TextConfig>;
}

const DEFAULT_COLORS = [
  '#000000',
  '#3b82f6',
  '#ef4444',
  '#10b981',
  '#f59e0b',
  '#8b5cf6',
  '#ec4899',
  '#06b6d4',
];

const FONT_SIZE_OPTIONS: Array<{ value: FontSize; label: string; preview: string }> = [
  { value: 'xs', label: 'Extra Small', preview: 'text-xs' },
  { value: 'sm', label: 'Small', preview: 'text-sm' },
  { value: 'base', label: 'Base', preview: 'text-base' },
  { value: 'lg', label: 'Large', preview: 'text-lg' },
  { value: 'xl', label: 'Extra Large', preview: 'text-xl' },
  { value: '2xl', label: '2X Large', preview: 'text-2xl' },
  { value: '3xl', label: '3X Large', preview: 'text-3xl' },
];

export const TextConfigModal: React.FC<TextConfigModalProps> = ({
  open,
  onClose,
  onSave,
  initialConfig,
}) => {
  const [config, setConfig] = useState<TextConfig>({
    title: 'Text Widget',
    content: '',
    fontSize: 'base',
    fontColor: '#000000',
    backgroundColor: '',
    alignment: 'left',
    ...initialConfig,
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (initialConfig) {
      setConfig((prev) => ({
        ...prev,
        ...initialConfig,
      }));
    }
  }, [initialConfig]);

  const handleChange = useCallback((field: keyof TextConfig, value: unknown) => {
    setConfig((prev) => ({
      ...prev,
      [field]: value,
    }));
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  }, [errors]);

  const handleSave = useCallback(() => {
    const newErrors: Record<string, string> = {};

    // Validate required fields
    if (!config.title.trim()) {
      newErrors.title = 'Title is required';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    onSave(config);
  }, [config, onSave]);

  const getFontSizeClass = (size: FontSize): string => {
    const sizeMap: Record<FontSize, string> = {
      xs: 'text-xs',
      sm: 'text-sm',
      base: 'text-base',
      lg: 'text-lg',
      xl: 'text-xl',
      '2xl': 'text-2xl',
      '3xl': 'text-3xl',
    };
    return sizeMap[size] || 'text-base';
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Configure Text Widget</DialogTitle>
          <DialogDescription>
            Customize your text widget by editing content and styling options.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Title */}
          <div className="space-y-2">
            <Label htmlFor="title">Title</Label>
            <Input
              id="title"
              value={config.title}
              onChange={(e) => handleChange('title', e.target.value)}
              placeholder="Text widget title"
              className={cn(errors.title && 'border-destructive')}
            />
            {errors.title && (
              <p className="text-sm text-destructive">{errors.title}</p>
            )}
          </div>

          {/* Content - Rich Text Editor */}
          <div className="space-y-2">
            <Label htmlFor="content">Content</Label>
            <Textarea
              id="content"
              value={config.content}
              onChange={(e) => handleChange('content', e.target.value)}
              placeholder="Enter your text content here..."
              rows={8}
              className={cn(errors.content && 'border-destructive', 'resize-y')}
            />
            {errors.content && (
              <p className="text-sm text-destructive">{errors.content}</p>
            )}
            <p className="text-xs text-muted-foreground">
              Tip: You can use plain text or basic HTML for formatting
            </p>
          </div>

          {/* Font Size */}
          <div className="space-y-2">
            <Label htmlFor="fontSize">Font Size</Label>
            <Select
              value={config.fontSize}
              onValueChange={(value) => handleChange('fontSize', value as FontSize)}
            >
              <SelectTrigger id="fontSize">
                <SelectValue placeholder="Select font size" />
              </SelectTrigger>
              <SelectContent>
                {FONT_SIZE_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    <div className="flex items-center gap-2">
                      <span className={option.preview}>{option.label}</span>
                      <span className="text-muted-foreground">({option.value})</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Text Alignment */}
          <div className="space-y-2">
            <Label htmlFor="alignment">Text Alignment</Label>
            <Select
              value={config.alignment}
              onValueChange={(value) => handleChange('alignment', value as TextConfig['alignment'])}
            >
              <SelectTrigger id="alignment">
                <SelectValue placeholder="Select alignment" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="left">Left</SelectItem>
                <SelectItem value="center">Center</SelectItem>
                <SelectItem value="right">Right</SelectItem>
                <SelectItem value="justify">Justify</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Visual Configuration */}
          <div className="space-y-4 pt-4 border-t">
            <h3 className="text-sm font-semibold">Visual Configuration</h3>

            {/* Font Color */}
            <div className="space-y-2">
              <Label htmlFor="fontColor">Font Color</Label>
              <div className="flex items-center gap-2">
                <div className="flex flex-wrap gap-2">
                  {DEFAULT_COLORS.map((color) => (
                    <button
                      key={color}
                      type="button"
                      className={cn(
                        "w-8 h-8 rounded border-2 transition-all hover:scale-110",
                        config.fontColor === color
                          ? 'border-foreground scale-110'
                          : 'border-transparent'
                      )}
                      style={{ backgroundColor: color }}
                      onClick={() => handleChange('fontColor', color)}
                      aria-label={`Select color ${color}`}
                    />
                  ))}
                </div>
                <Input
                  id="fontColor"
                  type="color"
                  value={config.fontColor}
                  onChange={(e) => handleChange('fontColor', e.target.value)}
                  className="w-20 h-8"
                />
              </div>
            </div>

            {/* Background Color (Optional) */}
            <div className="space-y-2">
              <Label htmlFor="backgroundColor">Background Color (Optional)</Label>
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => handleChange('backgroundColor', '')}
                  className={!config.backgroundColor ? 'border-primary' : ''}
                >
                  Transparent
                </Button>
                <Input
                  id="backgroundColor"
                  type="color"
                  value={config.backgroundColor || '#ffffff'}
                  onChange={(e) => handleChange('backgroundColor', e.target.value)}
                  className="w-20 h-8"
                />
              </div>
            </div>
          </div>

          {/* Preview */}
          <div className="space-y-2 pt-4 border-t">
            <Label>Preview</Label>
            <div
              className={cn(
                "p-4 rounded border min-h-[120px] transition-all",
                getFontSizeClass(config.fontSize)
              )}
              style={{
                color: config.fontColor,
                backgroundColor: config.backgroundColor || 'transparent',
                textAlign: config.alignment,
              }}
            >
              {config.content || (
                <span className="text-muted-foreground italic">Your content will appear here...</span>
              )}
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSave}>
            Save Configuration
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default TextConfigModal;
