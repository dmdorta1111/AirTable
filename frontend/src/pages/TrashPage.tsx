import React from 'react';
import { Trash2 } from 'lucide-react';
import TrashBin from '@/features/trash/components/TrashBin';

/**
 * Trash Page
 *
 * Displays deleted records that can be restored or permanently deleted.
 * Accessible at /trash route.
 */
export const TrashPage: React.FC = () => {
  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Trash2 className="h-8 w-8 text-muted-foreground" />
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Trash Bin</h1>
            <p className="text-muted-foreground mt-1">
              Restore deleted records or permanently delete them
            </p>
          </div>
        </div>
      </div>

      {/* Trash Bin Component */}
      <TrashBin />
    </div>
  );
};

export default TrashPage;
