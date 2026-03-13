import { useMemo } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { format } from 'date-fns';
import { vi } from 'date-fns/locale';
import { Download, Share2, Car, Bike, MapPin, Calendar, Clock, CheckCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface BookingQRCodeProps {
  bookingId: string;
  vehicleType: 'Car' | 'Motorbike';
  licensePlate: string;
  zone: string;
  slot: string;
  dates: Date[];
  status: 'confirmed' | 'pending' | 'expired';
}

export function BookingQRCode({
  bookingId,
  vehicleType,
  licensePlate,
  zone,
  slot,
  dates,
  status,
}: BookingQRCodeProps) {
  const qrData = useMemo(() => {
    return JSON.stringify({
      id: bookingId,
      plate: licensePlate,
      zone,
      slot,
      dates: dates.map(d => d.toISOString()),
      type: vehicleType,
    });
  }, [bookingId, licensePlate, zone, slot, dates, vehicleType]);

  const statusConfig = {
    confirmed: {
      label: 'Đã xác nhận',
      color: 'text-success bg-success/10 border-success/20',
      icon: CheckCircle,
    },
    pending: {
      label: 'Chờ thanh toán',
      color: 'text-warning bg-warning/10 border-warning/20',
      icon: Clock,
    },
    expired: {
      label: 'Đã hết hạn',
      color: 'text-destructive bg-destructive/10 border-destructive/20',
      icon: Clock,
    },
  };

  const currentStatus = statusConfig[status];
  const StatusIcon = currentStatus.icon;

  const handleDownload = () => {
    const svg = document.getElementById('booking-qr-code');
    if (svg) {
      const svgData = new XMLSerializer().serializeToString(svg);
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      const img = new Image();
      
      img.onload = () => {
        canvas.width = img.width;
        canvas.height = img.height;
        ctx?.drawImage(img, 0, 0);
        const pngFile = canvas.toDataURL('image/png');
        const downloadLink = document.createElement('a');
        downloadLink.download = `booking-${bookingId}.png`;
        downloadLink.href = pngFile;
        downloadLink.click();
      };
      
      img.src = 'data:image/svg+xml;base64,' + btoa(svgData);
    }
  };

  const handleShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: `Đặt chỗ đậu xe - ${licensePlate}`,
          text: `Mã đặt chỗ: ${bookingId}\nVị trí: ${zone} - ${slot}`,
        });
      } catch (error) {
        console.log('Share cancelled');
      }
    }
  };

  return (
    <div className="rounded-xl sm:rounded-2xl border border-border bg-card overflow-hidden">
      {/* Header */}
      <div className="gradient-primary p-3 sm:p-4 text-center">
        <h3 className="text-base sm:text-lg font-bold text-primary-foreground">Mã QR Đặt Chỗ</h3>
        <p className="text-xs sm:text-sm text-primary-foreground/80">Quét mã để check-in tại bãi đậu</p>
      </div>

      <div className="p-4 sm:p-6 space-y-4 sm:space-y-6">
        {/* Status Badge */}
        <div className="flex justify-center">
          <div className={cn(
            "inline-flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-1.5 sm:py-2 rounded-full border",
            currentStatus.color
          )}>
            <StatusIcon className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
            <span className="font-medium text-xs sm:text-sm">{currentStatus.label}</span>
          </div>
        </div>

        {/* QR Code */}
        <div className="flex justify-center">
          <div className="p-3 sm:p-4 bg-white rounded-xl shadow-inner">
            <QRCodeSVG
              id="booking-qr-code"
              value={qrData}
              size={140}
              level="H"
              includeMargin={true}
              fgColor="#0f172a"
              className="w-[120px] h-[120px] sm:w-[180px] sm:h-[180px]"
            />
          </div>
        </div>

        {/* Booking ID */}
        <div className="text-center">
          <p className="text-[10px] sm:text-xs text-muted-foreground mb-1">Mã đặt chỗ</p>
          <p className="font-mono text-sm sm:text-lg font-bold text-foreground tracking-wider">
            {bookingId.toUpperCase()}
          </p>
        </div>

        {/* Booking Details */}
        <div className="grid grid-cols-2 gap-2 sm:gap-4 p-3 sm:p-4 rounded-xl bg-muted/50">
          <div className="flex items-center gap-1.5 sm:gap-2">
            {vehicleType === 'Car' ? (
              <Car className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-muted-foreground shrink-0" />
            ) : (
              <Bike className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-muted-foreground shrink-0" />
            )}
            <div className="min-w-0">
              <p className="text-[10px] sm:text-xs text-muted-foreground">Biển số</p>
              <p className="text-xs sm:text-sm font-medium truncate">{licensePlate}</p>
            </div>
          </div>

          <div className="flex items-center gap-1.5 sm:gap-2">
            <MapPin className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-muted-foreground shrink-0" />
            <div className="min-w-0">
              <p className="text-[10px] sm:text-xs text-muted-foreground">Vị trí</p>
              <p className="text-xs sm:text-sm font-medium truncate">{zone} - {slot}</p>
            </div>
          </div>

          <div className="col-span-2 flex items-center gap-1.5 sm:gap-2">
            <Calendar className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-muted-foreground shrink-0" />
            <div className="min-w-0">
              <p className="text-[10px] sm:text-xs text-muted-foreground">Ngày đậu</p>
              <p className="text-xs sm:text-sm font-medium">
                {dates.length === 1 
                  ? format(dates[0], 'dd/MM/yyyy', { locale: vi })
                  : `${dates.length} ngày (${format(dates[0], 'dd/MM')} - ${format(dates[dates.length - 1], 'dd/MM/yyyy', { locale: vi })})`
                }
              </p>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2 sm:gap-3">
          <Button
            variant="outline"
            className="flex-1 text-xs sm:text-sm h-9 sm:h-10"
            onClick={handleDownload}
          >
            <Download className="h-3.5 w-3.5 sm:h-4 sm:w-4 mr-1.5 sm:mr-2" />
            Tải về
          </Button>
          <Button
            variant="outline"
            className="flex-1 text-xs sm:text-sm h-9 sm:h-10"
            onClick={handleShare}
          >
            <Share2 className="h-3.5 w-3.5 sm:h-4 sm:w-4 mr-1.5 sm:mr-2" />
            Chia sẻ
          </Button>
        </div>

        {/* Warning for pending */}
        {status === 'pending' && (
          <div className="p-2 sm:p-3 rounded-lg bg-warning/10 border border-warning/20">
            <p className="text-xs sm:text-sm text-warning text-center">
              ⚠️ Vui lòng thanh toán trong vòng 3 giờ để giữ chỗ
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
