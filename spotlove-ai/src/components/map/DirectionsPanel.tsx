import { 
  ArrowUp, 
  ArrowLeft, 
  ArrowRight, 
  MapPin, 
  Car,
  Clock,
  Navigation,
  Building2
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { DirectionStep, DirectionType } from '@/types/parking';

interface DirectionsPanelProps {
  steps: DirectionStep[];
  currentBooking?: {
    licensePlate: string;
    vehicleType: 'Car' | 'Motorbike';
    zone: string;
    slot?: string;
    floor: number;
  };
  estimatedTime?: number; // in minutes
  onStartNavigation?: () => void;
  currentStepIndex?: number; // Current step during navigation
}

const directionIcons: Record<DirectionType, React.ElementType> = {
  straight: ArrowUp,
  left: ArrowLeft,
  right: ArrowRight,
  elevator: Building2,
  ramp: ArrowUp,
  destination: MapPin,
};

const directionLabels: Record<DirectionType, string> = {
  straight: 'Đi thẳng',
  left: 'Rẽ trái',
  right: 'Rẽ phải',
  elevator: 'Thang máy',
  ramp: 'Đường dốc',
  destination: 'Đích đến',
};

export function DirectionsPanel({ 
  steps, 
  currentBooking,
  estimatedTime = 3,
  onStartNavigation,
  currentStepIndex
}: DirectionsPanelProps) {
  const isNavigating = currentStepIndex !== undefined;
  return (
    <div className="space-y-4">
      {/* Current Booking Info */}
      {currentBooking && (
        <div className="rounded-2xl border border-border bg-card p-4">
          <h3 className="mb-3 font-semibold text-foreground">Booking hiện tại</h3>
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <Car className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="font-mono font-medium text-foreground">{currentBooking.licensePlate}</p>
                <p className="text-sm text-muted-foreground">
                  {currentBooking.vehicleType === 'Car' ? 'Ô tô' : 'Xe máy'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/10">
                <MapPin className="h-5 w-5 text-accent" />
              </div>
              <div>
                <p className="font-medium text-foreground">
                  {currentBooking.zone}
                  {currentBooking.slot && ` - ${currentBooking.slot}`}
                </p>
                <p className="text-sm text-muted-foreground">Tầng {currentBooking.floor}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Directions Steps */}
      <div className="rounded-2xl border border-border bg-card p-4">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-semibold text-foreground">Hướng dẫn đường đi</h3>
          <div className="flex items-center gap-1 text-sm text-muted-foreground">
            <Clock className="h-4 w-4" />
            ~{estimatedTime} phút
          </div>
        </div>

        <div className="space-y-1">
          {steps.map((step, index) => {
            const Icon = directionIcons[step.direction];
            const isLast = index === steps.length - 1;
            const isActive = isNavigating && index === currentStepIndex;
            const isCompleted = isNavigating && index < (currentStepIndex || 0);

            return (
              <div key={step.id} className="relative flex gap-3">
                {/* Timeline */}
                <div className="flex flex-col items-center">
                  <div className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-full transition-all duration-300",
                    isCompleted
                      ? "bg-success text-success-foreground"
                      : isActive
                        ? "bg-primary text-primary-foreground ring-4 ring-primary/30 animate-pulse"
                        : isLast 
                          ? "bg-success/20 text-success" 
                          : "bg-primary/10 text-primary"
                  )}>
                    <Icon className="h-4 w-4" />
                  </div>
                  {!isLast && (
                    <div className={cn(
                      "my-1 h-8 w-0.5 transition-colors duration-300",
                      isCompleted ? "bg-success" : "bg-border"
                    )} />
                  )}
                </div>

                {/* Step Content */}
                <div className={cn(
                  "flex-1 pb-4 transition-opacity duration-300",
                  isNavigating && !isActive && !isCompleted && "opacity-50"
                )}>
                  <p className={cn(
                    "font-medium",
                    isActive ? "text-primary" : isCompleted ? "text-success" : "text-foreground"
                  )}>
                    {step.instruction}
                  </p>
                  {step.distance && (
                    <p className="text-sm text-muted-foreground">{step.distance}</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Action Button */}
      {onStartNavigation && (
        <Button 
          variant="hero" 
          className="w-full" 
          size="lg"
          onClick={onStartNavigation}
        >
          <Navigation className="h-5 w-5 mr-2" />
          Bắt đầu dẫn đường
        </Button>
      )}
    </div>
  );
}
