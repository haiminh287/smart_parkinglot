import { useState } from 'react';
import { Car, Bike, Calendar, Clock, MapPin, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useNavigate } from 'react-router-dom';

type VehicleType = 'Car' | 'Motorbike';
type PackageType = 'monthly' | 'weekly' | 'custom';

const packageOptions: { type: PackageType; label: string; discount?: string }[] = [
  { type: 'monthly', label: 'Theo tháng', discount: '-20%' },
  { type: 'weekly', label: 'Theo tuần', discount: '-10%' },
  { type: 'custom', label: 'Chọn ngày' },
];

export function QuickBooking() {
  const navigate = useNavigate();
  const [vehicleType, setVehicleType] = useState<VehicleType>('Car');
  const [packageType, setPackageType] = useState<PackageType>('monthly');

  return (
    <div className="rounded-xl sm:rounded-2xl border border-border bg-card p-4 sm:p-6 animate-slide-up">
      <div className="mb-4 sm:mb-6">
        <h3 className="text-base sm:text-lg font-semibold text-foreground">Đặt chỗ nhanh</h3>
        <p className="text-xs sm:text-sm text-muted-foreground">Đặt chỗ giữ xe chỉ trong vài bước</p>
      </div>

      {/* Vehicle Type Selection */}
      <div className="mb-4 sm:mb-6">
        <label className="mb-2 block text-xs sm:text-sm font-medium text-foreground">
          Loại xe
        </label>
        <div className="grid grid-cols-2 gap-2 sm:gap-3">
          <button
            onClick={() => setVehicleType('Car')}
            className={cn(
              "flex items-center justify-center gap-2 sm:gap-3 rounded-lg sm:rounded-xl border-2 p-3 sm:p-4 transition-all duration-200",
              vehicleType === 'Car'
                ? "border-primary bg-primary/5 text-primary"
                : "border-border bg-background hover:border-primary/50"
            )}
          >
            <Car className="h-4 w-4 sm:h-5 sm:w-5" />
            <span className="font-medium text-sm sm:text-base">Ô tô</span>
          </button>
          <button
            onClick={() => setVehicleType('Motorbike')}
            className={cn(
              "flex items-center justify-center gap-2 sm:gap-3 rounded-lg sm:rounded-xl border-2 p-3 sm:p-4 transition-all duration-200",
              vehicleType === 'Motorbike'
                ? "border-accent bg-accent/5 text-accent"
                : "border-border bg-background hover:border-accent/50"
            )}
          >
            <Bike className="h-4 w-4 sm:h-5 sm:w-5" />
            <span className="font-medium text-sm sm:text-base">Xe máy</span>
          </button>
        </div>
      </div>

      {/* Package Selection */}
      <div className="mb-4 sm:mb-6">
        <label className="mb-2 block text-xs sm:text-sm font-medium text-foreground">
          Gói đặt chỗ
        </label>
        <div className="grid grid-cols-3 gap-1.5 sm:gap-2">
          {packageOptions.map((pkg) => (
            <button
              key={pkg.type}
              onClick={() => setPackageType(pkg.type)}
              className={cn(
                "relative flex flex-col items-center rounded-lg sm:rounded-xl border-2 p-2 sm:p-3 transition-all duration-200",
                packageType === pkg.type
                  ? "border-primary bg-primary/5"
                  : "border-border hover:border-primary/50"
              )}
            >
              <span className={cn(
                "text-xs sm:text-sm font-medium",
                packageType === pkg.type ? "text-primary" : "text-foreground"
              )}>
                {pkg.label}
              </span>
              {pkg.discount && (
                <span className="mt-0.5 sm:mt-1 rounded-full bg-success/20 px-1.5 sm:px-2 py-0.5 text-[10px] sm:text-xs font-medium text-success">
                  {pkg.discount}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Date/Time */}
      <div className="mb-4 sm:mb-6 grid grid-cols-2 gap-2 sm:gap-3">
        <div>
          <label className="mb-1.5 sm:mb-2 block text-xs sm:text-sm font-medium text-foreground">
            Ngày bắt đầu
          </label>
          <div className="flex items-center gap-1.5 sm:gap-2 rounded-lg sm:rounded-xl border border-border bg-background px-2 sm:px-3 py-2 sm:py-2.5">
            <Calendar className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-muted-foreground shrink-0" />
            <input 
              type="date" 
              className="flex-1 bg-transparent text-xs sm:text-sm outline-none min-w-0"
              defaultValue={new Date().toISOString().split('T')[0]}
            />
          </div>
        </div>
        <div>
          <label className="mb-1.5 sm:mb-2 block text-xs sm:text-sm font-medium text-foreground">
            Thời gian
          </label>
          <div className="flex items-center gap-1.5 sm:gap-2 rounded-lg sm:rounded-xl border border-border bg-background px-2 sm:px-3 py-2 sm:py-2.5">
            <Clock className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-muted-foreground shrink-0" />
            <input 
              type="time" 
              className="flex-1 bg-transparent text-xs sm:text-sm outline-none min-w-0"
              defaultValue="08:00"
            />
          </div>
        </div>
      </div>

      {/* Location Preview */}
      <div className="mb-4 sm:mb-6 flex items-center gap-2 sm:gap-3 rounded-lg sm:rounded-xl bg-muted/50 p-3 sm:p-4">
        <div className="flex h-8 w-8 sm:h-10 sm:w-10 items-center justify-center rounded-lg bg-primary/10 shrink-0">
          <MapPin className="h-4 w-4 sm:h-5 sm:w-5 text-primary" />
        </div>
        <div className="min-w-0">
          <p className="font-medium text-foreground text-sm sm:text-base truncate">Bãi xe Quận 1</p>
          <p className="text-xs sm:text-sm text-muted-foreground truncate">123 Nguyễn Huệ, Q.1, TP.HCM</p>
        </div>
      </div>

      {/* Submit Button */}
      <Button variant="hero" className="w-full text-sm sm:text-base" size="lg" onClick={() => navigate('/booking')}>
        Tiếp tục đặt chỗ
        <ArrowRight className="h-4 w-4" />
      </Button>
    </div>
  );
}
