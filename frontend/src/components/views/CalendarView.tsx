import React from 'react';
import { Card, CardContent } from '@/components/ui/card';

interface CalendarViewProps {
  data: any[];
  fields: any[];
}

export const CalendarView: React.FC<CalendarViewProps> = ({ data, fields }) => {
  const dateField = fields.find(f => f.type === 'date');

  if (!dateField) {
      return (
          <div className="p-4 text-muted-foreground">
              Please add a Date field to use Calendar view.
          </div>
      );
  }

  // Simplified "Calendar" -> Just a list of dates for now, or a simple grid representing the current month.
  // Implementing a full calendar is complex without a library like 'react-big-calendar'.
  // I'll create a simple month grid for the current month.
  
  const today = new Date();
  const currentMonth = today.toLocaleString('default', { month: 'long', year: 'numeric' });
  const daysInMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0).getDate();
  const startDay = new Date(today.getFullYear(), today.getMonth(), 1).getDay(); // 0 = Sun

  const days = Array.from({ length: daysInMonth }, (_, i) => i + 1);
  const padding = Array.from({ length: startDay }, () => null);

  const getEventsForDay = (day: number) => {
      return data.filter(item => {
          const d = new Date(item[dateField.name]);
          return d.getDate() === day && d.getMonth() === today.getMonth() && d.getFullYear() === today.getFullYear();
      });
  };

  return (
    <div className="flex flex-col h-full p-4">
        <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold">{currentMonth}</h2>
            <div className="flex gap-2">
                <button className="px-3 py-1 text-sm border rounded">Today</button>
            </div>
        </div>
        
        <div className="grid grid-cols-7 gap-px bg-border border border-border flex-1">
            {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
                <div key={day} className="bg-muted/20 p-2 text-center text-sm font-semibold">
                    {day}
                </div>
            ))}
            
            {padding.map((_, i) => (
                <div key={`pad-${i}`} className="bg-background min-h-[100px]" />
            ))}

            {days.map(day => {
                const events = getEventsForDay(day);
                return (
                    <div key={day} className="bg-background p-1 min-h-[100px] border-t border-l flex flex-col gap-1">
                        <div className="text-right text-sm text-muted-foreground p-1">{day}</div>
                        {events.map(event => (
                            <div key={event.id} className="text-xs bg-primary/10 text-primary p-1 rounded truncate cursor-pointer hover:bg-primary/20">
                                {event[fields[0].name] || 'Untitled'}
                            </div>
                        ))}
                    </div>
                );
            })}
        </div>
    </div>
  );
};
