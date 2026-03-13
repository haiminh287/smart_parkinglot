import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  MapPin, 
  Clock, 
  Shield, 
  Sparkles, 
  Navigation,
  CheckCircle,
  Car,
  Bike,
  ArrowRight,
  Loader2,
  AlertTriangle,
  TrendingDown,
  Star
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { VehicleType } from '@/types/parking';

interface AutoGuaranteeBookingProps {
  onComplete: (data: {
    destination: string;
    arrivalTime: string;
    vehicleType: VehicleType;
    selectedLot?: ParkingLotResult;
  }) => void;
}

interface ParkingLotResult {
  id: string;
  name: string;
  distance: string;
  availableSlots: number;
  price: number;
  rating: number;
  isBestMatch: boolean;
  almostFull: boolean;
  estimatedFillTime?: string;
}

const popularDestinations = [
  { name: 'Vincom Center', address: 'Đồng Khởi, Quận 1' },
  { name: 'Landmark 81', address: 'Bình Thạnh' },
  { name: 'Aeon Mall Tân Phú', address: 'Quận Tân Phú' },
  { name: 'Crescent Mall', address: 'Quận 7' },
];

export function AutoGuaranteeBooking({ onComplete }: AutoGuaranteeBookingProps) {
  const [destination, setDestination] = useState('');
  const [arrivalTime, setArrivalTime] = useState('');
  const [vehicleType, setVehicleType] = useState<VehicleType>('Car');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<ParkingLotResult[]>([]);
  const [selectedLot, setSelectedLot] = useState<ParkingLotResult | null>(null);
  const [showAlmostFullWarning, setShowAlmostFullWarning] = useState(false);

  // Mock AI prediction for "almost full" notification
  useEffect(() => {
    if (searchResults.length > 0 && selectedLot?.almostFull) {
      const timer = setTimeout(() => {
        setShowAlmostFullWarning(true);
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [selectedLot, searchResults]);

  const handleSearch = async () => {
    if (!destination || !arrivalTime) return;

    setIsSearching(true);
    setSearchResults([]);
    setSelectedLot(null);
    setShowAlmostFullWarning(false);

    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1500));

    // Mock results with multiple parking lots
    const results: ParkingLotResult[] = [
      {
        id: '1',
        name: 'ParkSmart Quận 1',
        distance: '150m',
        availableSlots: 8,
        price: vehicleType === 'Car' ? 15000 : 5000,
        rating: 4.8,
        isBestMatch: true,
        almostFull: true,
        estimatedFillTime: '15 phút',
      },
      {
        id: '2',
        name: 'Bãi Vincom Center',
        distance: '200m',
        availableSlots: 45,
        price: vehicleType === 'Car' ? 20000 : 7000,
        rating: 4.5,
        isBestMatch: false,
        almostFull: false,
      },
      {
        id: '3',
        name: 'Parking Nguyễn Huệ',
        distance: '350m',
        availableSlots: 120,
        price: vehicleType === 'Car' ? 12000 : 4000,
        rating: 4.2,
        isBestMatch: false,
        almostFull: false,
      },
    ];

    setSearchResults(results);
    setSelectedLot(results[0]); // Auto-select best match
    setIsSearching(false);
  };

  const handleConfirm = () => {
    if (!selectedLot) return;
    onComplete({
      destination,
      arrivalTime,
      vehicleType,
      selectedLot,
    });
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Hero Banner */}
      <div className="relative overflow-hidden rounded-xl sm:rounded-2xl gradient-primary p-4 sm:p-6 text-primary-foreground">
        <div className="absolute right-0 top-0 h-full w-1/3 bg-white/5" />
        <div className="relative z-10">
          <Badge className="bg-white/20 text-white border-0 mb-2 sm:mb-3 text-[10px] sm:text-xs">
            <Sparkles className="h-2.5 w-2.5 sm:h-3 sm:w-3 mr-1" />
            Tính năng mới
          </Badge>
          <h2 className="text-lg sm:text-2xl font-bold mb-1 sm:mb-2">
            Đi đâu cũng có chỗ 🅿️
          </h2>
          <p className="text-xs sm:text-base text-primary-foreground/80 max-w-md">
            Chỉ cần nhập điểm đến và giờ tới, hệ thống sẽ tự động tìm và giữ chỗ cho bạn.
          </p>
        </div>
        <Shield className="absolute right-4 sm:right-6 bottom-4 sm:bottom-6 h-16 w-16 sm:h-24 sm:w-24 text-white/10" />
      </div>

      {/* Almost Full Warning */}
      {showAlmostFullWarning && selectedLot?.almostFull && (
        <div className="animate-fade-in rounded-xl border-2 border-yellow-500/50 bg-yellow-500/10 p-4">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-yellow-500/20">
              <AlertTriangle className="h-5 w-5 text-yellow-600" />
            </div>
            <div className="flex-1">
              <p className="font-semibold text-foreground">⚠️ {selectedLot.name} sắp đầy!</p>
              <p className="text-sm text-muted-foreground mt-1">
                Dự đoán hết chỗ trong <strong>{selectedLot.estimatedFillTime}</strong>. Giữ chỗ ngay để đảm bảo có vị trí khi bạn tới.
              </p>
              <div className="flex gap-2 mt-3">
                <Button size="sm" className="gradient-primary" onClick={handleConfirm}>
                  Giữ chỗ ngay
                </Button>
                <Button size="sm" variant="outline" onClick={() => setShowAlmostFullWarning(false)}>
                  Để sau
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Commitment Banner */}
      <div className="flex items-center gap-3 sm:gap-4 rounded-lg sm:rounded-xl border border-green-500/20 bg-green-500/10 p-3 sm:p-4">
        <div className="flex h-10 w-10 sm:h-12 sm:w-12 items-center justify-center rounded-lg sm:rounded-xl bg-green-500/20 shrink-0">
          <CheckCircle className="h-5 w-5 sm:h-6 sm:w-6 text-green-600" />
        </div>
        <div className="min-w-0">
          <p className="font-semibold text-foreground text-sm sm:text-base">Cam kết từ ParkSmart</p>
          <p className="text-xs sm:text-sm text-muted-foreground">
            ❝ Tới nơi là có chỗ ❞ - Nếu bãi đầy, tự động chuyển bãi khác
          </p>
        </div>
      </div>

      {/* Vehicle Type */}
      <div className="space-y-2 sm:space-y-3">
        <label className="text-xs sm:text-sm font-medium text-foreground">Loại xe</label>
        <div className="grid grid-cols-2 gap-2 sm:gap-3">
          <button
            onClick={() => setVehicleType('Car')}
            className={cn(
              "flex items-center justify-center gap-2 sm:gap-3 rounded-lg sm:rounded-xl border-2 p-3 sm:p-4 transition-all",
              vehicleType === 'Car'
                ? "border-primary bg-primary/5"
                : "border-border hover:border-primary/50"
            )}
          >
            <Car className={cn("h-5 w-5 sm:h-6 sm:w-6", vehicleType === 'Car' ? "text-primary" : "text-muted-foreground")} />
            <span className={cn("font-medium text-sm sm:text-base", vehicleType === 'Car' ? "text-primary" : "text-foreground")}>
              Ô tô
            </span>
          </button>
          <button
            onClick={() => setVehicleType('Motorbike')}
            className={cn(
              "flex items-center justify-center gap-2 sm:gap-3 rounded-lg sm:rounded-xl border-2 p-3 sm:p-4 transition-all",
              vehicleType === 'Motorbike'
                ? "border-primary bg-primary/5"
                : "border-border hover:border-primary/50"
            )}
          >
            <Bike className={cn("h-5 w-5 sm:h-6 sm:w-6", vehicleType === 'Motorbike' ? "text-primary" : "text-muted-foreground")} />
            <span className={cn("font-medium text-sm sm:text-base", vehicleType === 'Motorbike' ? "text-primary" : "text-foreground")}>
              Xe máy
            </span>
          </button>
        </div>
      </div>

      {/* Destination Input */}
      <div className="space-y-2 sm:space-y-3">
        <label className="text-xs sm:text-sm font-medium text-foreground">Điểm đến của bạn</label>
        <div className="relative">
          <MapPin className="absolute left-3 sm:left-4 top-1/2 -translate-y-1/2 h-4 w-4 sm:h-5 sm:w-5 text-muted-foreground" />
          <input
            type="text"
            placeholder="Nhập địa chỉ hoặc tên địa điểm..."
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            className="w-full rounded-lg sm:rounded-xl border border-border bg-background pl-10 sm:pl-12 pr-3 sm:pr-4 py-2.5 sm:py-3 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        
        {/* Popular Destinations */}
        <div className="flex flex-wrap gap-1.5 sm:gap-2">
          {popularDestinations.map((place) => (
            <button
              key={place.name}
              onClick={() => setDestination(place.name)}
              className="rounded-full border border-border bg-muted/50 px-2 sm:px-3 py-1 sm:py-1.5 text-[10px] sm:text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            >
              {place.name}
            </button>
          ))}
        </div>
      </div>

      {/* Arrival Time */}
      <div className="space-y-2 sm:space-y-3">
        <label className="text-xs sm:text-sm font-medium text-foreground">Giờ bạn sẽ tới</label>
        <div className="relative">
          <Clock className="absolute left-3 sm:left-4 top-1/2 -translate-y-1/2 h-4 w-4 sm:h-5 sm:w-5 text-muted-foreground pointer-events-none z-10" />
          <input
            type="datetime-local"
            value={arrivalTime}
            onChange={(e) => setArrivalTime(e.target.value)}
            min={new Date().toISOString().slice(0, 16)}
            className="w-full rounded-lg sm:rounded-xl border border-border bg-background pl-10 sm:pl-12 pr-3 sm:pr-4 py-2.5 sm:py-3 text-sm focus:border-primary focus:outline-none appearance-none cursor-pointer [&::-webkit-calendar-picker-indicator]:cursor-pointer [&::-webkit-calendar-picker-indicator]:opacity-100 [&::-webkit-calendar-picker-indicator]:absolute [&::-webkit-calendar-picker-indicator]:right-3 [&::-webkit-calendar-picker-indicator]:w-5 [&::-webkit-calendar-picker-indicator]:h-5"
            style={{ colorScheme: 'auto' }}
          />
        </div>
      </div>

      {/* Search Button */}
      <Button
        onClick={handleSearch}
        disabled={!destination || !arrivalTime || isSearching}
        className="w-full gradient-primary gap-2 h-10 sm:h-12 text-sm sm:text-base"
      >
        {isSearching ? (
          <>
            <Loader2 className="h-4 w-4 sm:h-5 sm:w-5 animate-spin" />
            Đang tìm bãi tốt nhất...
          </>
        ) : (
          <>
            <Navigation className="h-4 w-4 sm:h-5 sm:w-5" />
            Tìm chỗ đỗ xe
          </>
        )}
      </Button>

      {/* Search Results - Parking Lot List */}
      {searchResults.length > 0 && (
        <div className="animate-slide-up space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-foreground text-sm sm:text-base">
              Bãi đỗ xe phù hợp ({searchResults.length})
            </h3>
            <Badge variant="outline" className="text-xs">
              <TrendingDown className="h-3 w-3 mr-1" />
              Giá tốt nhất
            </Badge>
          </div>

          <div className="space-y-2">
            {searchResults.map((lot) => (
              <button
                key={lot.id}
                onClick={() => setSelectedLot(lot)}
                className={cn(
                  "w-full rounded-xl border p-3 sm:p-4 text-left transition-all",
                  selectedLot?.id === lot.id
                    ? "border-primary bg-primary/5 ring-2 ring-primary/20"
                    : "border-border hover:border-primary/50"
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h4 className="font-medium text-foreground text-sm sm:text-base truncate">{lot.name}</h4>
                      {lot.isBestMatch && (
                        <Badge className="bg-primary/10 text-primary border-primary/20 text-[10px]">
                          <Star className="h-2.5 w-2.5 mr-0.5" />
                          Đề xuất
                        </Badge>
                      )}
                      {lot.almostFull && (
                        <Badge className="bg-yellow-500/10 text-yellow-600 border-yellow-500/20 text-[10px]">
                          <AlertTriangle className="h-2.5 w-2.5 mr-0.5" />
                          Sắp đầy
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-3 mt-1 text-xs sm:text-sm text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <MapPin className="h-3 w-3" />
                        {lot.distance}
                      </span>
                      <span>•</span>
                      <span className={cn(
                        lot.availableSlots < 10 ? "text-yellow-600" : "text-green-600"
                      )}>
                        {lot.availableSlots} chỗ trống
                      </span>
                      <span>•</span>
                      <span>⭐ {lot.rating}</span>
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-base sm:text-lg font-bold text-primary">
                      {lot.price.toLocaleString('vi-VN')}đ
                    </p>
                    <p className="text-[10px] sm:text-xs text-muted-foreground">/giờ</p>
                  </div>
                </div>
              </button>
            ))}
          </div>

          {/* Confirm Button */}
          {selectedLot && (
            <div className="flex gap-2 sm:gap-3 pt-2">
              <Button variant="outline" className="flex-1 text-xs sm:text-sm h-10 sm:h-11">
                Xem trên bản đồ
              </Button>
              <Button onClick={handleConfirm} className="flex-1 gradient-primary gap-1 sm:gap-2 text-xs sm:text-sm h-10 sm:h-11">
                Giữ chỗ tại {selectedLot.name.split(' ')[0]}
                <ArrowRight className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
              </Button>
            </div>
          )}
        </div>
      )}

      {/* How it works */}
      <div className="rounded-lg sm:rounded-xl bg-muted/50 p-3 sm:p-4 space-y-2 sm:space-y-3">
        <p className="text-xs sm:text-sm font-medium text-foreground">Cách hoạt động:</p>
        <div className="space-y-1.5 sm:space-y-2 text-xs sm:text-sm text-muted-foreground">
          <div className="flex items-start gap-1.5 sm:gap-2">
            <span className="flex h-4 w-4 sm:h-5 sm:w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] sm:text-xs font-bold text-primary">1</span>
            <span>Bạn nhập điểm đến và giờ tới</span>
          </div>
          <div className="flex items-start gap-1.5 sm:gap-2">
            <span className="flex h-4 w-4 sm:h-5 sm:w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] sm:text-xs font-bold text-primary">2</span>
            <span>Hệ thống hiển thị danh sách bãi phù hợp để bạn chọn</span>
          </div>
          <div className="flex items-start gap-1.5 sm:gap-2">
            <span className="flex h-4 w-4 sm:h-5 sm:w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] sm:text-xs font-bold text-primary">3</span>
            <span>Chỗ được giữ tự động đến khi bạn tới</span>
          </div>
          <div className="flex items-start gap-1.5 sm:gap-2">
            <span className="flex h-4 w-4 sm:h-5 sm:w-5 shrink-0 items-center justify-center rounded-full bg-green-500/10 text-[10px] sm:text-xs font-bold text-green-600">✓</span>
            <span>Nếu bãi đầy, tự động chuyển sang bãi khác gần đó</span>
          </div>
        </div>
      </div>
    </div>
  );
}
