import React, { useState } from 'react';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import {
  Image as ImageIcon,
  AlertCircle,
  Settings,
  ZoomIn,
  Download,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Image fit options
export type ImageFit = 'contain' | 'cover' | 'fill' | 'none' | 'scale-down';

// Image position options
export type ImagePosition = 'center' | 'top' | 'bottom' | 'left' | 'right';

// Image section configuration
export interface ImageSectionConfig {
  src: string; // URL or base64 data URI
  alt?: string;
  title?: string;
  description?: string;
  fit?: ImageFit;
  position?: ImagePosition;
  width?: number; // in pixels
  height?: number; // in pixels
  maxWidth?: string; // CSS max-width value (e.g., '100%', '500px')
  maxHeight?: string; // CSS max-height value (e.g., '100%', '500px')
  rounded?: boolean;
  bordered?: boolean;
  shadow?: boolean;
  clickable?: boolean;
  onConfigure?: () => void;
  onClick?: () => void;
}

interface ImageSectionProps {
  config: ImageSectionConfig;
  className?: string;
  isLoading?: boolean;
  error?: string;
}

// Get object-fit class
const getObjectFitClass = (fit?: ImageFit) => {
  switch (fit) {
    case 'contain':
      return 'object-contain';
    case 'cover':
      return 'object-cover';
    case 'fill':
      return 'object-fill';
    case 'none':
      return 'object-none';
    case 'scale-down':
      return 'object-scale-down';
    default:
      return 'object-contain';
  }
};

// Get object-position class
const getObjectPositionClass = (position?: ImagePosition) => {
  switch (position) {
    case 'top':
      return 'object-top';
    case 'bottom':
      return 'object-bottom';
    case 'left':
      return 'object-left';
    case 'right':
      return 'object-right';
    case 'center':
    default:
      return 'object-center';
  }
};

export const ImageSection: React.FC<ImageSectionProps> = ({
  config,
  className,
  isLoading = false,
  error,
}) => {
  const [imageError, setImageError] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);

  const {
    src,
    alt = 'Image',
    title,
    description,
    fit = 'contain',
    position = 'center',
    width,
    height,
    maxWidth = '100%',
    maxHeight = '100%',
    rounded = false,
    bordered = false,
    shadow = false,
    clickable = false,
    onConfigure,
    onClick,
  } = config;

  const handleImageError = () => {
    setImageError(true);
  };

  const handleImageLoad = () => {
    setIsLoaded(true);
  };

  const handleClick = () => {
    if (clickable && onClick) {
      onClick();
    }
  };

  // Render loading state
  if (isLoading) {
    return (
      <Card className={cn('h-full', className)}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              {title && (
                <CardTitle className="text-base font-medium flex items-center gap-2">
                  <ImageIcon className="h-5 w-5" />
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
          <div className="h-full flex items-center justify-center">
            <div className="space-y-3 w-full">
              <div className="aspect-video bg-muted animate-pulse rounded" />
              <div className="h-4 bg-muted animate-pulse rounded w-3/4 mx-auto" />
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Render error state
  if (error || imageError) {
    return (
      <Card className={cn('h-full border-destructive', className)}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              {title && (
                <CardTitle className="text-base font-medium flex items-center gap-2">
                  <ImageIcon className="h-5 w-5" />
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
              <p className="text-sm font-medium">Image Error</p>
              <p className="text-xs text-muted-foreground">{error || 'Failed to load image'}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Render empty state
  if (!src) {
    return (
      <Card className={cn('h-full', className)}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              {title && (
                <CardTitle className="text-base font-medium flex items-center gap-2">
                  <ImageIcon className="h-5 w-5" />
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
              <ImageIcon className="h-12 w-12 mx-auto mb-2" />
              <p className="text-sm">No image</p>
              <p className="text-xs mt-1">Click settings to add an image</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn('h-full flex flex-col', className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex-1 min-w-0">
            {title && (
              <CardTitle className="text-base font-medium flex items-center gap-2">
                <ImageIcon className="h-5 w-5" />
                <span className="truncate">{title}</span>
              </CardTitle>
            )}
            {description && (
              <CardDescription className="truncate">{description}</CardDescription>
            )}
          </div>
          {onConfigure && (
            <button
              onClick={onConfigure}
              className="p-2 hover:bg-accent rounded-md transition-colors flex-shrink-0"
            >
              <Settings className="h-4 w-4" />
            </button>
          )}
        </div>
      </CardHeader>
      <CardContent className="flex-1 flex items-center justify-center overflow-auto p-4">
        <div
          className={cn(
            'relative',
            rounded && 'rounded-lg',
            bordered && 'border-2 border-border',
            shadow && 'shadow-lg',
            clickable && 'cursor-pointer hover:opacity-80 transition-opacity'
          )}
          onClick={handleClick}
          style={{
            maxWidth,
            maxHeight,
          }}
        >
          {!isLoaded && (
            <div
              className="absolute inset-0 bg-muted animate-pulse rounded"
              style={{
                width: width || '100%',
                height: height || 'auto',
              }}
            />
          )}
          <img
            src={src}
            alt={alt}
            width={width}
            height={height}
            onError={handleImageError}
            onLoad={handleImageLoad}
            className={cn(
              getObjectFitClass(fit),
              getObjectPositionClass(position),
              'max-w-full h-auto',
              rounded && 'rounded-lg',
              bordered && 'border-2 border-border',
              shadow && 'shadow-lg',
              !isLoaded && 'opacity-0'
            )}
            style={{
              maxWidth,
              maxHeight,
            }}
          />
          {clickable && (
            <div className="absolute inset-0 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity bg-black/50 rounded-lg">
              <ZoomIn className="h-8 w-8 text-white" />
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default ImageSection;
