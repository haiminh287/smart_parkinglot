import { ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { LucideIcon } from 'lucide-react';

interface StatsCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: {
    value: number;
    positive: boolean;
  };
  variant?: 'default' | 'primary' | 'accent' | 'success' | 'warning';
  className?: string;
}

export function StatsCard({ 
  title, 
  value, 
  subtitle, 
  icon: Icon,
  trend,
  variant = 'default',
  className 
}: StatsCardProps) {
  const variants = {
    default: 'bg-card',
    primary: 'gradient-primary text-primary-foreground',
    accent: 'gradient-accent text-accent-foreground',
    success: 'bg-success/10 border-success/20',
    warning: 'bg-warning/10 border-warning/20',
  };

  const iconVariants = {
    default: 'bg-primary/10 text-primary',
    primary: 'bg-primary-foreground/20 text-primary-foreground',
    accent: 'bg-accent-foreground/20 text-accent-foreground',
    success: 'bg-success/20 text-success',
    warning: 'bg-warning/20 text-warning',
  };

  return (
    <div className={cn(
      "relative overflow-hidden rounded-xl sm:rounded-2xl border border-border p-3 sm:p-6 transition-all duration-300 hover:shadow-lg animate-fade-in",
      variants[variant],
      className
    )}>
      <div className="flex items-start justify-between gap-2">
        <div className="space-y-1 sm:space-y-2 min-w-0 flex-1">
          <p className={cn(
            "text-xs sm:text-sm font-medium truncate",
            variant === 'default' ? 'text-muted-foreground' : 'opacity-80'
          )}>
            {title}
          </p>
          <p className="text-xl sm:text-3xl font-bold tracking-tight">
            {value}
          </p>
          {subtitle && (
            <p className={cn(
              "text-xs sm:text-sm truncate",
              variant === 'default' ? 'text-muted-foreground' : 'opacity-70'
            )}>
              {subtitle}
            </p>
          )}
          {trend && (
            <div className={cn(
              "inline-flex items-center gap-1 rounded-full px-1.5 sm:px-2 py-0.5 sm:py-1 text-[10px] sm:text-xs font-medium",
              trend.positive 
                ? 'bg-success/20 text-success' 
                : 'bg-destructive/20 text-destructive'
            )}>
              {trend.positive ? '↑' : '↓'} {Math.abs(trend.value)}%
            </div>
          )}
        </div>
        <div className={cn(
          "flex h-8 w-8 sm:h-12 sm:w-12 items-center justify-center rounded-lg sm:rounded-xl shrink-0",
          iconVariants[variant]
        )}>
          <Icon className="h-4 w-4 sm:h-6 sm:w-6" />
        </div>
      </div>

      {/* Decorative element */}
      <div className={cn(
        "absolute -right-4 -top-4 h-16 w-16 sm:h-24 sm:w-24 rounded-full opacity-10",
        variant === 'default' ? 'bg-primary' : 'bg-current'
      )} />
    </div>
  );
}
