import { useState, useEffect } from "react";
import { Car, Bike, ParkingCircle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { parkingService } from "@/services/business";

interface ZoneData {
  id: string;
  name: string;
  vehicleType: "Car" | "Motorbike";
  total: number;
  available: number;
  floor: number;
}

export function SlotOverview() {
  const [zones, setZones] = useState<ZoneData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchZones = async () => {
      try {
        // Get lots first, then zones for the first lot
        const lotsResponse = await parkingService.getLots();
        const lots = lotsResponse.results || [];
        if (lots.length > 0) {
          const zonesResponse = await parkingService.getZones({
            lotId: lots[0].id,
          });
          const zonesData: ZoneData[] = (zonesResponse.results || []).map(
            (z: {
              id: string;
              name: string;
              vehicleType?: string;
              vehicle_type?: string;
              capacity?: number;
              totalSlots?: number;
              total_slots?: number;
              availableSlots?: number;
              available_slots?: number;
              floorLevel?: number;
              floor?: number;
            }) => ({
              id: z.id,
              name: z.name,
              vehicleType: (z.vehicleType || z.vehicle_type || "Car") as
                | "Car"
                | "Motorbike",
              total: z.capacity || z.totalSlots || z.total_slots || 0,
              available: z.availableSlots || z.available_slots || 0,
              floor: z.floorLevel || z.floor || 1,
            }),
          );
          setZones(zonesData);
        }
      } catch (error) {
        console.error("Failed to fetch zone data:", error);
        setZones([]);
      } finally {
        setLoading(false);
      }
    };
    fetchZones();
  }, []);

  return (
    <div className="rounded-2xl border border-border bg-card p-6 animate-slide-up">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-foreground">
            Tổng quan chỗ đậu
          </h3>
          <p className="text-sm text-muted-foreground">
            Trạng thái theo từng zone
          </p>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-success" />
            <span className="text-muted-foreground">Còn trống</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-destructive" />
            <span className="text-muted-foreground">Đã đầy</span>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : zones.length === 0 ? (
        <div className="text-center py-8">
          <ParkingCircle className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Chưa có dữ liệu zone</p>
        </div>
      ) : (
        <div className="space-y-4">
          {zones.map((zone) => {
            const occupancyPercent =
              ((zone.total - zone.available) / zone.total) * 100;
            const isFull = zone.available === 0;
            const isNearFull = zone.available <= zone.total * 0.1;

            return (
              <div
                key={zone.id}
                className="group rounded-xl border border-border bg-background/50 p-4 transition-all duration-200 hover:border-primary/50 hover:shadow-md"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className={cn(
                        "flex h-10 w-10 items-center justify-center rounded-lg",
                        zone.vehicleType === "Car"
                          ? "bg-primary/10 text-primary"
                          : "bg-accent/10 text-accent",
                      )}
                    >
                      {zone.vehicleType === "Car" ? (
                        <Car className="h-5 w-5" />
                      ) : (
                        <Bike className="h-5 w-5" />
                      )}
                    </div>
                    <div>
                      <p className="font-medium text-foreground">{zone.name}</p>
                      <p className="text-xs text-muted-foreground">
                        Tầng {zone.floor} •{" "}
                        {zone.vehicleType === "Car" ? "Ô tô" : "Xe máy"}
                      </p>
                    </div>
                  </div>

                  <div className="text-right">
                    <p
                      className={cn(
                        "text-lg font-bold",
                        isFull
                          ? "text-destructive"
                          : isNearFull
                            ? "text-warning"
                            : "text-success",
                      )}
                    >
                      {zone.available}/{zone.total}
                    </p>
                    <p className="text-xs text-muted-foreground">còn trống</p>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-muted">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all duration-500",
                      isFull
                        ? "bg-destructive"
                        : isNearFull
                          ? "bg-warning"
                          : "bg-success",
                    )}
                    style={{ width: `${occupancyPercent}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
