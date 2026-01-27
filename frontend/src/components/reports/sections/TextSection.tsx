import React from 'react';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import {
  Type,
  AlertCircle,
  Settings,
  AlignLeft,
  AlignCenter,
  AlignRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Text content types
export type TextContentType = 'plain' | 'markdown' | 'html';

// Text alignment options
export type TextAlignment = 'left' | 'center' | 'right' | 'justify';

// Text section configuration
export interface TextSectionConfig {
  content: string;
  contentType?: TextContentType;
  title?: string;
  description?: string;
  alignment?: TextAlignment;
  fontSize?: 'xs' | 'sm' | 'base' | 'lg' | 'xl';
  fontWeight?: 'normal' | 'medium' | 'semibold' | 'bold';
  color?: string; // CSS color value
  maxHeight?: number; // Max height in pixels, with scroll
  onConfigure?: () => void;
}

interface TextSectionProps {
  config: TextSectionConfig;
  className?: string;
  isLoading?: boolean;
  error?: string;
}

// Get font size class
const getFontSizeClass = (size?: 'xs' | 'sm' | 'base' | 'lg' | 'xl') => {
  switch (size) {
    case 'xs':
      return 'text-xs';
    case 'sm':
      return 'text-sm';
    case 'base':
      return 'text-base';
    case 'lg':
      return 'text-lg';
    case 'xl':
      return 'text-xl';
    default:
      return 'text-sm';
  }
};

// Get font weight class
const getFontWeightClass = (weight?: 'normal' | 'medium' | 'semibold' | 'bold') => {
  switch (weight) {
    case 'normal':
      return 'font-normal';
    case 'medium':
      return 'font-medium';
    case 'semibold':
      return 'font-semibold';
    case 'bold':
      return 'font-bold';
    default:
      return 'font-normal';
  }
};

// Get text alignment class
const getAlignmentClass = (alignment?: TextAlignment) => {
  switch (alignment) {
    case 'left':
      return 'text-left';
    case 'center':
      return 'text-center';
    case 'right':
      return 'text-right';
    case 'justify':
      return 'text-justify';
    default:
      return 'text-left';
  }
};

// Get alignment icon
const getAlignmentIcon = (alignment?: TextAlignment) => {
  switch (alignment) {
    case 'center':
      return <AlignCenter className="h-4 w-4" />;
    case 'right':
      return <AlignRight className="h-4 w-4" />;
    case 'justify':
      return <AlignLeft className="h-4 w-4" />;
    default:
      return <AlignLeft className="h-4 w-4" />;
  }
};

// Simple markdown parser (basic implementation)
const parseMarkdown = (text: string): React.ReactNode => {
  const lines = text.split('\n');
  return lines.map((line, index) => {
    // Headers
    if (line.startsWith('### ')) {
      return <h3 key={index} className="text-lg font-semibold mt-4 mb-2">{line.slice(4)}</h3>;
    }
    if (line.startsWith('## ')) {
      return <h2 key={index} className="text-xl font-semibold mt-4 mb-2">{line.slice(3)}</h2>;
    }
    if (line.startsWith('# ')) {
      return <h1 key={index} className="text-2xl font-bold mt-4 mb-2">{line.slice(2)}</h1>;
    }

    // Bold
    let content = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Italic
    content = content.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Code
    content = content.replace(/`(.*?)`/g, '<code class="bg-muted px-1 py-0.5 rounded text-sm">$1</code>');

    // Lists
    if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
      return <li key={index} className="ml-4">{line.trim().slice(2)}</li>;
    }

    // Paragraph
    if (content.trim()) {
      return <p key={index} className="mb-2" dangerouslySetInnerHTML={{ __html: content }} />;
    }

    return <br key={index} />;
  });
};

// Render content based on type
const renderContent = (content: string, contentType: TextContentType = 'plain'): React.ReactNode => {
  switch (contentType) {
    case 'markdown':
      return <div className="prose prose-sm max-w-none">{parseMarkdown(content)}</div>;
    case 'html':
      return <div dangerouslySetInnerHTML={{ __html: content }} />;
    case 'plain':
    default:
      return <p className="whitespace-pre-wrap">{content}</p>;
  }
};

export const TextSection: React.FC<TextSectionProps> = ({
  config,
  className,
  isLoading = false,
  error,
}) => {
  const {
    content,
    contentType = 'plain',
    title,
    description,
    alignment = 'left',
    fontSize = 'sm',
    fontWeight = 'normal',
    color,
    maxHeight,
    onConfigure,
  } = config;

  // Render loading state
  if (isLoading) {
    return (
      <Card className={cn('h-full', className)}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              {title && (
                <CardTitle className="text-base font-medium flex items-center gap-2">
                  <Type className="h-5 w-5" />
                  {title}
                </CardTitle>
              )}
              {description && <CardDescription>{description}</CardDescription>}
            </div>
            {onConfigure && (
              <button
                onClick={onConfigure}
                className="p-2 hover:bg-accent rounded-md transition-colors"
              >
                <Settings className="h-4 w-4" />
              </button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="h-4 bg-muted animate-pulse rounded w-full" />
            <div className="h-4 bg-muted animate-pulse rounded w-5/6" />
            <div className="h-4 bg-muted animate-pulse rounded w-4/6" />
          </div>
        </CardContent>
      </Card>
    );
  }

  // Render error state
  if (error) {
    return (
      <Card className={cn('h-full border-destructive', className)}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              {title && (
                <CardTitle className="text-base font-medium flex items-center gap-2">
                  <Type className="h-5 w-5" />
                  {title}
                </CardTitle>
              )}
            </div>
            {onConfigure && (
              <button
                onClick={onConfigure}
                className="p-2 hover:bg-accent rounded-md transition-colors"
              >
                <Settings className="h-4 w-4" />
              </button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center text-destructive">
            <div className="text-center space-y-2">
              <AlertCircle className="h-8 w-8 mx-auto" />
              <p className="text-sm font-medium">Text Error</p>
              <p className="text-xs text-muted-foreground">{error}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Render empty state
  if (!content || content.trim() === '') {
    return (
      <Card className={cn('h-full', className)}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              {title && (
                <CardTitle className="text-base font-medium flex items-center gap-2">
                  <Type className="h-5 w-5" />
                  {title}
                </CardTitle>
              )}
              {description && <CardDescription>{description}</CardDescription>}
            </div>
            {onConfigure && (
              <button
                onClick={onConfigure}
                className="p-2 hover:bg-accent rounded-md transition-colors"
              >
                <Settings className="h-4 w-4" />
              </button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="h-full flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              <Type className="h-12 w-12 mx-auto mb-2" />
              <p className="text-sm">No content</p>
              <p className="text-xs mt-1">Click settings to add text</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn('h-full', className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex-1">
            {title && (
              <CardTitle className="text-base font-medium flex items-center gap-2">
                <Type className="h-5 w-5" />
                {title}
              </CardTitle>
            )}
            {description && <CardDescription>{description}</CardDescription>}
          </div>
          <div className="flex items-center gap-2">
            {getAlignmentIcon(alignment)}
            {onConfigure && (
              <button
                onClick={onConfigure}
                className="p-2 hover:bg-accent rounded-md transition-colors"
              >
                <Settings className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent
        className={cn(
          'overflow-auto',
          getAlignmentClass(alignment),
          getFontSizeClass(fontSize),
          getFontWeightClass(fontWeight)
        )}
        style={{
          color: color || undefined,
          maxHeight: maxHeight ? `${maxHeight}px` : undefined,
        }}
      >
        {renderContent(content, contentType)}
      </CardContent>
    </Card>
  );
};

export default TextSection;
