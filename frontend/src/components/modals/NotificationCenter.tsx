import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/dialog'
import { Bell, X, Check, AlertCircle, Info, Trash2 } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface Notification {
  id: string
  type: 'info' | 'success' | 'warning' | 'error'
  title: string
  message: string
  metadata?: {
    table_name?: string
    record_id?: string
    field_name?: string
  }
  is_read: boolean
  created_at: string
  read_at?: string
}

export interface NotificationCenterProps {
  onClose: () => void
}

export default function NotificationCenter({ onClose }: NotificationCenterProps) {
  const queryClient = useQueryClient()
  const [unreadCount, setUnreadCount] = useState(0)

  // Fetch notifications
  const { data: notifications, isLoading } = useQuery({
    queryKey: ['notifications'],
    queryFn: async () => {
      const response = await api.get<{ items: Notification[] }>('/notifications')
      return response.data.items
    },
    refetchInterval: 30000, // Refetch every 30 seconds
  })

  // Calculate unread count
  useEffect(() => {
    if (notifications) {
      const count = notifications.filter(n => !n.is_read).length
      setUnreadCount(count)
    }
  }, [notifications])

  // Mark as read mutation
  const markAsRead = useMutation({
    mutationFn: async (notificationId: string) => {
      return api.patch<Notification>(`/notifications/${notificationId}`, { is_read: true })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })

  // Mark all as read mutation
  const markAllAsRead = useMutation({
    mutationFn: async () => {
      return api.post('/notifications/mark-all-read', {})
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })

  // Delete notification mutation
  const deleteNotification = useMutation({
    mutationFn: async (notificationId: string) => {
      return api.delete(`/notifications/${notificationId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })

  // Clear all notifications mutation
  const clearAll = useMutation({
    mutationFn: async () => {
      return api.delete('/notifications/clear-all')
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })

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

  const getNotificationIcon = (type: Notification['type']) => {
    switch (type) {
      case 'success':
        return <Check className="h-5 w-5 text-green-500" />
      case 'warning':
        return <AlertCircle className="h-5 w-5 text-yellow-500" />
      case 'error':
        return <AlertCircle className="h-5 w-5 text-red-500" />
      case 'info':
      default:
        return <Info className="h-5 w-5 text-blue-500" />
    }
  }

  const getNotificationColor = (type: Notification['type']) => {
    switch (type) {
      case 'success':
        return 'bg-green-50 border-green-200'
      case 'warning':
        return 'bg-yellow-50 border-yellow-200'
      case 'error':
        return 'bg-red-50 border-red-200'
      case 'info':
      default:
        return 'bg-blue-50 border-blue-200'
    }
  }

  // Group notifications by date
  const groupedNotifications = notifications?.reduce((groups: Record<string, Notification[]>, notification) => {
    const date = new Date(notification.created_at).toLocaleDateString()
    return {
      ...groups,
      [date]: [...(groups[date] || []), notification]
    }
  }, {}) || {}

  return (
    <Sheet open onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-full sm:max-w-md">
        <SheetHeader className="flex-shrink-0 space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bell className="h-5 w-5 text-primary" />
              <SheetTitle>Notifications</SheetTitle>
              {unreadCount > 0 && (
                <span className="bg-primary text-primary-foreground text-xs font-medium px-2 py-0.5 rounded-full">
                  {unreadCount}
                </span>
              )}
            </div>
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="h-5 w-5" />
            </Button>
          </div>
          <SheetDescription>
            Stay updated on your activity and system events.
          </SheetDescription>
        </SheetHeader>

        {/* Actions */}
        <div className="flex gap-2 mb-4 flex-shrink-0">
          {unreadCount > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => markAllAsRead.mutate()}
              disabled={markAllAsRead.isPending}
              className="flex-1"
            >
              Mark All as Read
            </Button>
          )}
          {notifications && notifications.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => clearAll.mutate()}
              disabled={clearAll.isPending}
            >
              <Trash2 className="h-4 w-4 mr-1" />
              Clear All
            </Button>
          )}
        </div>

        {/* Notifications List */}
        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary border-t-transparent"></div>
            </div>
          ) : notifications && notifications.length > 0 ? (
            <div className="space-y-4">
              {Object.entries(groupedNotifications).map(([date, dateNotifications]) => (
                <div key={date}>
                  {/* Date Header */}
                  <div className="sticky top-0 bg-background/95 backdrop-blur-sm border-b px-3 py-2 text-sm font-medium text-muted-foreground z-10">
                    {date === new Date().toLocaleDateString() ? 'Today' : date}
                  </div>

                  {/* Notifications for this date */}
                  <div className="space-y-2">
                    {dateNotifications.map((notification) => (
                      <div
                        key={notification.id}
                        className={cn(
                          "p-4 border rounded-lg cursor-pointer transition-all hover:shadow-md",
                          notification.is_read ? "bg-muted/30" : getNotificationColor(notification.type)
                        )}
                        onClick={() => !notification.is_read && markAsRead.mutate(notification.id)}
                      >
                        <div className="flex gap-3">
                          {/* Icon */}
                          <div className="flex-shrink-0 mt-0.5">
                            {getNotificationIcon(notification.type)}
                          </div>

                          {/* Content */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-start justify-between gap-2 mb-1">
                              <h4 className="font-medium text-sm">{notification.title}</h4>
                              <span className="text-xs text-muted-foreground whitespace-nowrap">
                                {formatTimestamp(notification.created_at)}
                              </span>
                            </div>
                            <p className="text-sm text-foreground whitespace-pre-wrap break-words">
                              {notification.message}
                            </p>
                            {notification.metadata && (
                              <div className="mt-2 text-xs text-muted-foreground">
                                {notification.metadata.table_name && (
                                  <span>Table: {notification.metadata.table_name}</span>
                                )}
                              </div>
                            )}
                          </div>

                          {/* Delete button */}
                          <Button
                            variant="ghost"
                            size="icon"
                            className="flex-shrink-0 h-8 w-8"
                            onClick={(e) => {
                              e.stopPropagation()
                              deleteNotification.mutate(notification.id)
                            }}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Bell className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-2">No notifications yet</h3>
              <p className="text-sm text-muted-foreground max-w-sm">
                You're all caught up! Notifications will appear here when there's activity in your tables.
              </p>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
