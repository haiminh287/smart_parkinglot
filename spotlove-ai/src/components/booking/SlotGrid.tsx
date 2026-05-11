import { useState, useEffect, useCallback, useRef } from "react";
import { Car, Bike, Check, Loader2, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ParkingSlot } from "@/store/slices/parkingSlice";

interface SlotData {
  id: string;
  code: string;
  isAvailable: boolean;
  isSelected: boolean;
}

interface SlotGridProps {
  zoneId: string;
  vehicleType: "Car" | "Motorbike";
  onSlotSelect: (slot: SlotData) => void;
  selectedSlot?: SlotData | null;
}

export function SlotGrid({
  zoneId,
  vehicleType,
  onSlotSelect,
  selectedSlot,
}: SlotGridProps) {
  const [slots, setSlots] = useState<SlotData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const refreshTimerRef = useRef<NodeJS.Timeout | null>(null);
  const REFRESH_INTERVAL = 15_000; // 15 seconds

  const fetchSlots = useCallback(
    async (showLoader = false) => {
      if (!zoneId) return;

      if (showLoader) setLoading(true);
      setError(null);

      try {
        const { parkingService } = await import("@/services/business");
        const response = await parkingService.getSlots({ zoneId });

        const transformedSlots = response.results.map(
          (apiSlot: ParkingSlot) => ({
            id: apiSlot.id,
            code: apiSlot.code,
            isAvailable: apiSlot.status === "available",
            isSelected: false,
          }),
        );

        setSlots(transformedSlots);
      } catch (err) {
        console.error("Failed to fetch slots:", err);
        if (showLoader) setError("Không thể tải danh sách chỗ đậu xe");
      } finally {
        if (showLoader) setLoading(false);
      }
    },
    [zoneId],
  );

  // Initial fetch + auto-refresh polling
  useEffect(() => {
    fetchSlots(true);

    refreshTimerRef.current = setInterval(() => {
      fetchSlots(false); // Silent refresh — no spinner
    }, REFRESH_INTERVAL);

    return () => {
      if (refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current);
      }
    };
  }, [fetchSlots]);

  const gridCols =
    vehicleType === "Car"
      ? "grid-cols-3 sm:grid-cols-4 md:grid-cols-6"
      : "grid-cols-4 sm:grid-cols-6 md:grid-cols-8";
  const slotSize =
    vehicleType === "Car"
      ? "h-14 w-14 sm:h-16 sm:w-16"
      : "h-10 w-10 sm:h-12 sm:w-12";

  // Calculate availability stats
  const availableCount = slots.filter((s) => s.isAvailable).length;
  const totalCount = slots.length;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-center text-destructive">
        {error}
      </div>
    );
  }

  if (slots.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-muted p-8 text-center text-muted-foreground">
        Không có chỗ đậu xe trong khu vực này
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Availability Stats */}
      <div className="flex items-center justify-between rounded-lg bg-muted/50 p-3 text-sm">
        <span className="font-medium">
          Còn trống: <span className="text-success">{availableCount}</span> /{" "}
          {totalCount}
        </span>
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">
            {Math.round((availableCount / totalCount) * 100)}% available
          </span>
          <button
            onClick={() => fetchSlots(false)}
            className="ml-2 rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            title="Làm mới"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-6 text-sm">
        <div className="flex items-center gap-2">
          <div className="h-4 w-4 rounded bg-success/20 border border-success" />
          <span className="text-muted-foreground">Còn trống</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-4 w-4 rounded bg-muted border border-border" />
          <span className="text-muted-foreground">Đã đặt</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-4 w-4 rounded bg-primary border border-primary" />
          <span className="text-muted-foreground">Đang chọn</span>
        </div>
      </div>

      {/* Slot Grid */}
      <div className={cn("grid gap-2", gridCols)}>
        {slots.map((slot) => {
          const isSelected = selectedSlot?.id === slot.id;

          return (
            <button
              key={slot.id}
              onClick={() => slot.isAvailable && onSlotSelect(slot)}
              disabled={!slot.isAvailable}
              className={cn(
                "relative flex flex-col items-center justify-center rounded-lg border-2 transition-all duration-200",
                slotSize,
                slot.isAvailable
                  ? isSelected
                    ? "border-primary bg-primary text-primary-foreground shadow-md"
                    : "border-success/50 bg-success/10 hover:border-success hover:bg-success/20 cursor-pointer"
                  : "border-border bg-muted cursor-not-allowed opacity-50",
              )}
            >
              {vehicleType === "Car" ? (
                <Car
                  className={cn(
                    "h-5 w-5",
                    isSelected
                      ? "text-primary-foreground"
                      : slot.isAvailable
                        ? "text-success"
                        : "text-muted-foreground",
                  )}
                />
              ) : (
                <Bike
                  className={cn(
                    "h-4 w-4",
                    isSelected
                      ? "text-primary-foreground"
                      : slot.isAvailable
                        ? "text-success"
                        : "text-muted-foreground",
                  )}
                />
              )}
              <span
                className={cn(
                  "text-xs font-medium mt-1",
                  isSelected
                    ? "text-primary-foreground"
                    : slot.isAvailable
                      ? "text-foreground"
                      : "text-muted-foreground",
                )}
              >
                {slot.code}
              </span>

              {isSelected && (
                <div className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-success text-success-foreground">
                  <Check className="h-3 w-3" />
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
