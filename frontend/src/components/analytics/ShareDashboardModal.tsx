import React, { useCallback, useState } from 'react';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Copy, Link as LinkIcon, UserPlus, Check, Loader2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

export type PermissionLevel = 'view' | 'edit';

export interface SharedUser {
  user_id: string;
  email: string;
  permission: PermissionLevel;
}

export interface ShareConfig {
  shareToken?: string;
  sharedUsers: SharedUser[];
}

interface ShareDashboardModalProps {
  open: boolean;
  onClose: () => void;
  onSave: (config: ShareConfig) => void;
  dashboardId: string;
  initialConfig?: ShareConfig;
}

export const ShareDashboardModal: React.FC<ShareDashboardModalProps> = ({
  open,
  onClose,
  onSave,
  dashboardId,
  initialConfig,
}) => {
  const { toast } = useToast();

  const [config, setConfig] = useState<ShareConfig>({
    shareToken: initialConfig?.shareToken || '',
    sharedUsers: initialConfig?.sharedUsers || [],
  });

  const [isGenerating, setIsGenerating] = useState(false);
  const [isCopied, setIsCopied] = useState(false);
  const [newUserEmail, setNewUserEmail] = useState('');
  const [newUserPermission, setNewUserPermission] = useState<PermissionLevel>('view');
  const [isAddingUser, setIsAddingUser] = useState(false);

  const handleGenerateLink = useCallback(async () => {
    setIsGenerating(true);
    try {
      // Call API to generate share token
      const response = await fetch(`/api/v1/dashboards/${dashboardId}/share-token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to generate share link');
      }

      const data = await response.json();
      setConfig((prev) => ({
        ...prev,
        shareToken: data.share_token,
      }));

      toast({
        title: 'Share link generated',
        description: 'Public share link has been created successfully.',
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to generate share link. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsGenerating(false);
    }
  }, [dashboardId, toast]);

  const handleCopyLink = useCallback(async () => {
    if (!config.shareToken) return;

    const shareUrl = `${window.location.origin}/shared/${config.shareToken}`;

    try {
      await navigator.clipboard.writeText(shareUrl);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);

      toast({
        title: 'Link copied',
        description: 'Share link has been copied to clipboard.',
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to copy link to clipboard.',
        variant: 'destructive',
      });
    }
  }, [config.shareToken, toast]);

  const handleAddUser = useCallback(async () => {
    if (!newUserEmail.trim()) {
      toast({
        title: 'Email required',
        description: 'Please enter an email address.',
        variant: 'destructive',
      });
      return;
    }

    setIsAddingUser(true);
    try {
      // Call API to share dashboard with user
      const response = await fetch(`/api/v1/dashboards/${dashboardId}/share`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: newUserEmail,
          permission: newUserPermission,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to share dashboard');
      }

      const data = await response.json();

      setConfig((prev) => ({
        ...prev,
        sharedUsers: [
          ...prev.sharedUsers,
          {
            user_id: data.user_id,
            email: newUserEmail,
            permission: newUserPermission,
          },
        ],
      }));

      setNewUserEmail('');
      setNewUserPermission('view');

      toast({
        title: 'User added',
        description: `Dashboard has been shared with ${newUserEmail}.`,
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to share dashboard. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsAddingUser(false);
    }
  }, [dashboardId, newUserEmail, newUserPermission, toast]);

  const handleRemoveUser = useCallback(async (userId: string) => {
    try {
      // Call API to remove user sharing
      const response = await fetch(`/api/v1/dashboards/${dashboardId}/share`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to remove user');
      }

      setConfig((prev) => ({
        ...prev,
        sharedUsers: prev.sharedUsers.filter((u) => u.user_id !== userId),
      }));

      toast({
        title: 'User removed',
        description: 'User access has been revoked.',
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to remove user. Please try again.',
        variant: 'destructive',
      });
    }
  }, [dashboardId, toast]);

  const handleSave = useCallback(() => {
    onSave(config);
  }, [config, onSave]);

  const shareUrl = config.shareToken
    ? `${window.location.origin}/shared/${config.shareToken}`
    : '';

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Share Dashboard</DialogTitle>
          <DialogDescription>
            Manage sharing settings for this dashboard. Generate a public link or share with specific users.
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="public-link" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="public-link">
              <LinkIcon className="h-4 w-4 mr-2" />
              Public Link
            </TabsTrigger>
            <TabsTrigger value="people">
              <UserPlus className="h-4 w-4 mr-2" />
              People
            </TabsTrigger>
          </TabsList>

          {/* Public Link Tab */}
          <TabsContent value="public-link" className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label>Public Sharing</Label>
              <p className="text-sm text-muted-foreground">
                Generate a public link to share this dashboard with anyone. Anyone with the link can view the dashboard.
              </p>
            </div>

            {config.shareToken ? (
              <div className="space-y-2">
                <Label htmlFor="share-link">Share Link</Label>
                <div className="flex gap-2">
                  <Input
                    id="share-link"
                    value={shareUrl}
                    readOnly
                    className="flex-1"
                  />
                  <Button
                    onClick={handleCopyLink}
                    variant="outline"
                    className="min-w-[100px]"
                  >
                    {isCopied ? (
                      <>
                        <Check className="h-4 w-4 mr-2" />
                        Copied
                      </>
                    ) : (
                      <>
                        <Copy className="h-4 w-4 mr-2" />
                        Copy
                      </>
                    )}
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  Anyone with this link can view this dashboard.
                </p>
              </div>
            ) : (
              <Button
                onClick={handleGenerateLink}
                disabled={isGenerating}
                className="w-full"
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <LinkIcon className="h-4 w-4 mr-2" />
                    Generate Share Link
                  </>
                )}
              </Button>
            )}
          </TabsContent>

          {/* People Tab */}
          <TabsContent value="people" className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label>Share with People</Label>
              <p className="text-sm text-muted-foreground">
                Give specific users access to this dashboard.
              </p>
            </div>

            {/* Add User Form */}
            <div className="flex gap-2">
              <Input
                placeholder="Enter email address"
                value={newUserEmail}
                onChange={(e) => setNewUserEmail(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleAddUser();
                  }
                }}
                className="flex-1"
              />
              <Select
                value={newUserPermission}
                onValueChange={(value) => setNewUserPermission(value as PermissionLevel)}
              >
                <SelectTrigger className="w-[120px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="view">Can view</SelectItem>
                  <SelectItem value="edit">Can edit</SelectItem>
                </SelectContent>
              </Select>
              <Button
                onClick={handleAddUser}
                disabled={isAddingUser || !newUserEmail.trim()}
              >
                {isAddingUser ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <UserPlus className="h-4 w-4" />
                )}
              </Button>
            </div>

            {/* Shared Users List */}
            {config.sharedUsers.length > 0 && (
              <div className="space-y-2">
                <Label>People with access</Label>
                <div className="border rounded-md divide-y">
                  {config.sharedUsers.map((user) => (
                    <div
                      key={user.user_id}
                      className="flex items-center justify-between p-3"
                    >
                      <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                          <span className="text-xs font-medium text-primary">
                            {user.email.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <p className="text-sm font-medium">{user.email}</p>
                          <p className="text-xs text-muted-foreground capitalize">
                            {user.permission === 'edit' ? 'Can edit' : 'Can view'}
                          </p>
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRemoveUser(user.user_id)}
                        className="text-destructive hover:text-destructive"
                      >
                        Remove
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {config.sharedUsers.length === 0 && (
              <div className="border-2 border-dashed rounded-md p-8 text-center">
                <p className="text-sm text-muted-foreground">
                  No users have been given access yet. Add users above to share this dashboard.
                </p>
              </div>
            )}
          </TabsContent>
        </Tabs>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSave}>
            Save Changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ShareDashboardModal;
