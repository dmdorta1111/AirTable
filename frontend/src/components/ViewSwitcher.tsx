import { useLocation, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Grid3X3, Kanban, Calendar, AlignHorizontalSpaceAround } from 'lucide-react'
import { cn } from '@/lib/utils'

type ViewMode = 'grid' | 'kanban' | 'calendar' | 'gallery'

interface ViewSwitcherProps {
  baseId: string
  tableId: string
  defaultView?: ViewMode
}

export default function ViewSwitcher({ baseId, tableId, defaultView = 'grid' }: ViewSwitcherProps) {
  const navigate = useNavigate()
  const location = useLocation()

  // Determine current view from query param or default
  const params = new URLSearchParams(location.search)
  const currentView = (params.get('view') as ViewMode) || defaultView

  const setView = (view: ViewMode) => {
    params.set('view', view)
    navigate({
      pathname: location.pathname,
      search: params.toString()
    })
  }

  return (
    <div className="flex items-center gap-2">
      <Button
        variant={currentView === 'grid' ? 'default' : 'outline'}
        size="sm"
        onClick={() => setView('grid')}
        className={cn('flex items-center gap-1')}
      >
        <Grid3X3 className="h-4 w-4" />
        Grid
      </Button>
      <Button
        variant={currentView === 'kanban' ? 'default' : 'outline'}
        size="sm"
        onClick={() => setView('kanban')}
        className={cn('flex items-center gap-1')}
      >
        <Kanban className="h-4 w-4" />
        Kanban
      </Button>
      <Button
        variant={currentView === 'calendar' ? 'default' : 'outline'}
        size="sm"
        onClick={() => setView('calendar')}
        className={cn('flex items-center gap-1')}
      >
        <Calendar className="h-4 w-4" />
        Calendar
      </Button>
      <Button
        variant={currentView === 'gallery' ? 'default' : 'outline'}
        size="sm"
        onClick={() => setView('gallery')}
        className={cn('flex items-center gap-1')}
      >
        <AlignHorizontalSpaceAround className="h-4 w-4" />
        Gallery
      </Button>
    </div>
  )
}
