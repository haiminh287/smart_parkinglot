import { useState } from 'react';
import { format, isSameDay, isAfter, startOfDay } from 'date-fns';
import { vi } from 'date-fns/locale';
import { Calendar as CalendarIcon, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Calendar } from '@/components/ui/calendar';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Badge } from '@/components/ui/badge';

interface MultiDayPickerProps {
  selectedDates: Date[];
  onDatesChange: (dates: Date[]) => void;
  minDate?: Date;
  maxDays?: number;
}

export function MultiDayPicker({ 
  selectedDates, 
  onDatesChange, 
  minDate = new Date(),
  maxDays = 30 
}: MultiDayPickerProps) {
  const [isOpen, setIsOpen] = useState(false);

  const handleDayClick = (day: Date | undefined) => {
    if (!day) return;
    
    const dayStart = startOfDay(day);
    const isAlreadySelected = selectedDates.some(d => isSameDay(d, dayStart));
    
    if (isAlreadySelected) {
      onDatesChange(selectedDates.filter(d => !isSameDay(d, dayStart)));
    } else if (selectedDates.length < maxDays) {
      onDatesChange([...selectedDates, dayStart].sort((a, b) => a.getTime() - b.getTime()));
    }
  };

  const removeDate = (dateToRemove: Date) => {
    onDatesChange(selectedDates.filter(d => !isSameDay(d, dateToRemove)));
  };

  const clearAll = () => {
    onDatesChange([]);
  };

  const isDateDisabled = (date: Date) => {
    return !isAfter(date, startOfDay(new Date())) && !isSameDay(date, startOfDay(new Date()));
  };

  return (
    <div className="space-y-3">
      <Popover open={isOpen} onOpenChange={setIsOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            className={cn(
              "w-full justify-start text-left font-normal",
              selectedDates.length === 0 && "text-muted-foreground"
            )}
          >
            <CalendarIcon className="mr-2 h-4 w-4" />
            {selectedDates.length > 0
              ? `${selectedDates.length} ngày đã chọn`
              : "Chọn ngày đậu xe"}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            mode="multiple"
            selected={selectedDates}
            onSelect={(dates) => onDatesChange(dates || [])}
            disabled={isDateDisabled}
            locale={vi}
            className="p-3 pointer-events-auto"
            modifiers={{
              selected: selectedDates,
            }}
            modifiersStyles={{
              selected: {
                backgroundColor: 'hsl(var(--primary))',
                color: 'hsl(var(--primary-foreground))',
              },
            }}
          />
          <div className="border-t border-border p-3">
            <p className="text-xs text-muted-foreground">
              Nhấp vào ngày để chọn/bỏ chọn. Có thể chọn nhiều ngày không liên tiếp.
            </p>
          </div>
        </PopoverContent>
      </Popover>

      {/* Selected dates display */}
      {selectedDates.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-foreground">
              Ngày đã chọn ({selectedDates.length})
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearAll}
              className="h-auto py-1 px-2 text-xs text-destructive hover:text-destructive"
            >
              Xóa tất cả
            </Button>
          </div>
          <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto">
            {selectedDates.map((date, index) => (
              <Badge
                key={index}
                variant="secondary"
                className="flex items-center gap-1 pr-1"
              >
                {format(date, 'dd/MM/yyyy', { locale: vi })}
                <button
                  onClick={() => removeDate(date)}
                  className="ml-1 rounded-full hover:bg-muted-foreground/20 p-0.5"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
