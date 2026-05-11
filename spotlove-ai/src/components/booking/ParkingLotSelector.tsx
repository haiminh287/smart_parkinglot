import { useState, useEffect } from "react";
import { MapPin, Navigation, Building2, Car, Star, Clock } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { ParkingLot } from "@/types/parking";
import { parkingService } from "@/services/business/parking.service";

interface ParkingLotSelectorProps {
  onSelect: (parkingLot: ParkingLot) => void;
  selectedLot?: ParkingLot | null;
}

const calculateDistance = (
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number,
): number => {
  const R = 6371; // Earth's radius in km
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
};

export function ParkingLotSelector({
  onSelect,
  selectedLot,
}: ParkingLotSelectorProps) {
  const [userLocation, setUserLocation] = useState<{
    lat: number;
    lng: number;
  } | null>(null);
  const [isLocating, setIsLocating] = useState(false);
  const [sortedLots, setSortedLots] = useState<ParkingLot[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch real parking lots from API
  useEffect(() => {
    const fetchParkingLots = async () => {
      try {
        setIsLoading(true);
        const response = await parkingService.getLots();
        const lots = response.results || [];
        setSortedLots(lots);
      } catch {
        return;
      } finally {
        setIsLoading(false);
      }
    };

    fetchParkingLots();
  }, []);

  const handleGetLocation = () => {
    setIsLocating(true);

    // Check if geolocation is available
    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        async (position) => {
          const { latitude, longitude } = position.coords;
          setUserLocation({ lat: latitude, lng: longitude });

          // Use nearest lots API for more accurate results
          try {
            const nearestData = await parkingService.getNearestLots({
              lat: latitude,
              lng: longitude,
              vehicleType: "Car",
              limit: 10,
            });
            setSortedLots(nearestData.results || []);
            setIsLocating(false);
          } catch {
            // Fallback to manual distance calculation
            const lotsWithDistance = sortedLots.map((lot) => ({
              ...lot,
              distance: calculateDistance(
                latitude,
                longitude,
                lot.latitude,
                lot.longitude,
              ),
            }));
            lotsWithDistance.sort(
              (a, b) => (a.distance || 0) - (b.distance || 0),
            );
            setSortedLots(lotsWithDistance);
            setIsLocating(false);
          }
        },
        () => {
          setIsLocating(false);
          // Fallback to HCM city center when GPS unavailable
          const defaultLat = 10.7756;
          const defaultLng = 106.7019;
          setUserLocation({ lat: defaultLat, lng: defaultLng });

          // Try to fetch nearest lots using API
          (async () => {
            try {
              const nearestData = await parkingService.getNearestLots({
                lat: defaultLat,
                lng: defaultLng,
                vehicleType: "Car",
                limit: 10,
              });
              setSortedLots(nearestData.results || []);
            } catch {
              // Fallback to manual distance calculation
              const lotsWithDistance = sortedLots.map((lot) => ({
                ...lot,
                distance: calculateDistance(
                  defaultLat,
                  defaultLng,
                  lot.latitude,
                  lot.longitude,
                ),
              }));
              lotsWithDistance.sort(
                (a, b) => (a.distance || 0) - (b.distance || 0),
              );
              setSortedLots(lotsWithDistance);
            }
          })();
        },
        { enableHighAccuracy: true, timeout: 10000 },
      );
    } else {
      setIsLocating(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Location Button */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <h3 className="text-base sm:text-lg font-semibold text-foreground">
          Chọn bãi giữ xe
        </h3>
        <Button
          variant="outline"
          size="sm"
          className="gap-2 text-xs sm:text-sm w-full sm:w-auto"
          onClick={handleGetLocation}
          disabled={isLocating}
        >
          <Navigation
            className={cn(
              "h-3.5 w-3.5 sm:h-4 sm:w-4",
              isLocating && "animate-pulse",
            )}
          />
          {isLocating
            ? "Đang định vị..."
            : userLocation
              ? "Đã định vị"
              : "Tìm gần nhất"}
        </Button>
      </div>

      {userLocation && (
        <div className="flex items-center gap-2 rounded-lg bg-success/10 px-3 py-2 text-xs sm:text-sm text-success">
          <MapPin className="h-3.5 w-3.5 sm:h-4 sm:w-4 shrink-0" />
          <span>Đã xác định vị trí - Hiển thị bãi xe gần nhất</span>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="text-center py-8 text-sm text-muted-foreground">
          Đang tải danh sách bãi xe...
        </div>
      )}

      {/* Parking Lots List */}
      {!isLoading && (
        <div className="space-y-3">
          {sortedLots.map((lot, index) => {
            const isRecommended = userLocation && index === 0;
            const availabilityPercent =
              (lot.availableSlots / lot.totalSlots) * 100;

            return (
              <button
                key={lot.id}
                onClick={() => onSelect(lot)}
                className={cn(
                  "relative w-full rounded-xl border-2 p-3 sm:p-4 text-left transition-all",
                  selectedLot?.id === lot.id
                    ? "border-primary bg-primary/5 shadow-lg shadow-primary/20"
                    : "border-border hover:border-primary/50",
                )}
              >
                {isRecommended && (
                  <Badge className="absolute -top-2 right-2 sm:right-4 bg-success text-success-foreground gap-1 text-[10px] sm:text-xs">
                    <Star className="h-2.5 w-2.5 sm:h-3 sm:w-3" />
                    Gần nhất
                  </Badge>
                )}

                <div className="flex gap-3 sm:gap-4">
                  <div
                    className={cn(
                      "flex h-10 w-10 sm:h-12 sm:w-12 md:h-14 md:w-14 shrink-0 items-center justify-center rounded-lg sm:rounded-xl",
                      selectedLot?.id === lot.id
                        ? "gradient-primary"
                        : "bg-muted",
                    )}
                  >
                    <Building2
                      className={cn(
                        "h-5 w-5 sm:h-6 sm:w-6 md:h-7 md:w-7",
                        selectedLot?.id === lot.id
                          ? "text-primary-foreground"
                          : "text-muted-foreground",
                      )}
                    />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h4 className="font-semibold text-foreground text-sm sm:text-base truncate">
                        {lot.name}
                      </h4>
                      {lot.distance !== undefined && (
                        <Badge
                          variant="outline"
                          className="text-[10px] sm:text-xs shrink-0"
                        >
                          {lot.distance < 1
                            ? `${Math.round(lot.distance * 1000)}m`
                            : `${lot.distance.toFixed(1)}km`}
                        </Badge>
                      )}
                    </div>
                    <p className="mt-0.5 sm:mt-1 text-xs sm:text-sm text-muted-foreground truncate">
                      <MapPin className="inline h-3 w-3 mr-1" />
                      {lot.address}
                    </p>
                    <div className="mt-1.5 sm:mt-2 flex flex-wrap items-center gap-2 sm:gap-4 text-xs sm:text-sm">
                      <span className="flex items-center gap-1">
                        <Car className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-muted-foreground" />
                        <span
                          className={cn(
                            "font-medium",
                            availabilityPercent > 30
                              ? "text-success"
                              : availabilityPercent > 10
                                ? "text-warning"
                                : "text-destructive",
                          )}
                        >
                          {lot.availableSlots}
                        </span>
                        <span className="text-muted-foreground hidden xs:inline">
                          / {lot.totalSlots} chỗ
                        </span>
                      </span>
                      {lot.distance !== undefined && (
                        <span className="flex items-center gap-1 text-muted-foreground">
                          <Clock className="h-3.5 w-3.5 sm:h-4 sm:w-4" />~
                          {Math.ceil(lot.distance * 3)}p
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Availability bar */}
                <div className="mt-2 sm:mt-3 h-1 sm:h-1.5 rounded-full bg-muted overflow-hidden">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all",
                      availabilityPercent > 30
                        ? "bg-success"
                        : availabilityPercent > 10
                          ? "bg-warning"
                          : "bg-destructive",
                    )}
                    style={{ width: `${availabilityPercent}%` }}
                  />
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
