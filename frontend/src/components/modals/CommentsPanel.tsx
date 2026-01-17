import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Send, X, MessageSquare } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useWebSocket, getPresenceColor } from '@/hooks/use-websocket'
import type { Field, Record as RecordType } from '@/types'

export interface Comment {
  id: string
  record_id: string
  user_id: string
  user_name: string
  content: string
  created_at: string
  updated_at?: string
}

export interface CommentsPanelProps {
  tableId: string
  record: RecordType | null
  fields: Field[]
  onClose: () => void
}

export default function CommentsPanel({
  tableId,
  record,
  fields,
  onClose
}: CommentsPanelProps) {
  const [commentText, setCommentText] = useState('')
  const queryClient = useQueryClient()
  const { presence } = useWebSocket({ tableId })

  // Fetch comments for the table
  const { data: comments, isLoading } = useQuery({
    queryKey: ['comments', tableId, record?.id],
    queryFn: async () => {
      const params = record ? `record_id=${record.id}` : `table_id=${tableId}`
      const response = await api.get<{ items: Comment[] }>(`/comments?${params}`)
      return response.data.items
    },
    enabled: true,
    refetchInterval: 5000, // Refresh every 5 seconds
  })

  // Post comment mutation
  const postComment = useMutation({
    mutationFn: async (content: string) => {
      return api.post<Comment>('/comments', {
        table_id: tableId,
        record_id: record?.id || null,
        content
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['comments', tableId, record?.id] })
      setCommentText('')
    },
  })

  // Delete comment mutation
  const deleteComment = useMutation({
    mutationFn: async (commentId: string) => {
      return api.delete(`/comments/${commentId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['comments', tableId, record?.id] })
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (commentText.trim()) {
      postComment.mutate(commentText.trim())
    }
  }

  const formatTimestamp = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  }

  const getUserName = (userId: string) => {
    const user = presence.find(p => p.user_id === userId)
    return user?.user_name || 'Unknown User'
  }

  const getUserColor = (userId: string) => {
    const user = presence.find(p => p.user_id === userId)
    return user?.color || getPresenceColor(0)
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5 text-primary" />
              <DialogTitle>
                {record ? `Comments for Record` : 'Table Comments'}
              </DialogTitle>
            </div>
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="h-5 w-5" />
            </Button>
          </div>
        </DialogHeader>

        {/* Comments List */}
        <div className="flex-1 overflow-y-auto space-y-4 px-6 py-4">
          {isLoading ? (
            <div className="text-center text-muted-foreground py-8">
              Loading comments...
            </div>
          ) : comments && comments.length > 0 ? (
            comments.map((comment) => (
              <div
                key={comment.id}
                className="flex gap-3"
              >
                {/* User avatar */}
                <div
                  className="flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center text-white text-sm font-medium"
                  style={{ backgroundColor: getUserColor(comment.user_id) }}
                  title={comment.user_name}
                >
                  {comment.user_name.charAt(0).toUpperCase()}
                </div>

                {/* Comment content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium text-sm">
                      {comment.user_name}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {formatTimestamp(comment.created_at)}
                    </span>
                  </div>
                  <p className="text-sm text-foreground whitespace-pre-wrap break-words">
                    {comment.content}
                  </p>
                  {comment.user_id === 'current-user-id' && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-xs text-muted-foreground hover:text-destructive"
                      onClick={() => deleteComment.mutate(comment.id)}
                    >
                      Delete
                    </Button>
                  )}
                </div>
              </div>
            ))
          ) : (
            <div className="text-center text-muted-foreground py-8">
              {record ? 'No comments yet. Be the first to comment!' : 'No table comments yet.'}
            </div>
          )}
        </div>

        {/* Comment Input */}
        <form onSubmit={handleSubmit} className="flex-shrink-0 px-6 pb-6">
          <div className="flex gap-2">
            <div
              className="flex-shrink-0 h-8 w-8 rounded-full bg-primary flex items-center justify-center text-white text-sm font-medium"
            >
              Y
            </div>
            <div className="flex-1">
              <Input
                type="text"
                placeholder="Write a comment..."
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                disabled={postComment.isPending}
                className="pr-10"
              />
            </div>
            <Button
              type="submit"
              size="icon"
              disabled={!commentText.trim() || postComment.isPending}
              className="flex-shrink-0"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
