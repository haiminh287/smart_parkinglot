import { useEffect, useState } from "react";
import { Activity, Camera, Loader2, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { aiService } from "@/services/business";
import type { LiveOccupancyResponse } from "@/services/business";

const POLL_INTERVAL_MS = 5000;

/**
 * AI Live Occupancy Card — hiển thị realtime số xe YOLO detect được
 * trên frame camera tổng (virtual-f1-overview) mà Unity simulator stream.
 * Poll 5s/lần. Dùng cho admin dashboard.
 */
export function AILiveOccupancyCard({
  totalSlots,
}: {
  totalSlots?: number;
}) {
  const [data, setData] = useState<LiveOccupancyResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const fetchOccupancy = async () => {
    try {
      setLoading(true);
      setError(null);
      const resp = await aiService.detectOverviewLive();
      setData(resp);
      setLastUpdate(new Date());
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Lỗi không xác định";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOccupancy();
    const id = setInterval(fetchOccupancy, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, []);

  const occupied = data?.total_vehicles ?? 0;
  const available =
    totalSlots !== undefined ? Math.max(totalSlots - occupied, 0) : null;
  const occupancyRate =
    totalSlots && totalSlots > 0 ? (occupied / totalSlots) * 100 : null;

  return (
    <div className="rounded-2xl border border-border bg-card p-4 sm:p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
            <Camera className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h3 className="font-semibold text-foreground text-sm sm:text-base">
              AI Slot Occupancy (Live)
            </h3>
            <p className="text-xs text-muted-foreground">
              Camera tổng · YOLO11n realtime
            </p>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={fetchOccupancy}
          disabled={loading}
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="h-4 w-4" />
          )}
        </Button>
      </div>

      {error && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
          Không lấy được dữ liệu AI: {error}
        </div>
      )}

      {data && !error && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <StatBox
              label="Xe đang đỗ (AI)"
              value={occupied}
              color="text-primary"
            />
            <StatBox
              label="Chỗ còn trống"
              value={available ?? "—"}
              color="text-success"
            />
            <StatBox
              label="Tỉ lệ lấp"
              value={
                occupancyRate !== null ? `${occupancyRate.toFixed(0)}%` : "—"
              }
              color="text-warning"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="outline" className="gap-1">
              <Activity className="h-3 w-3" />
              {data.detection_method}
            </Badge>
            <Badge variant="outline">
              Frame age {data.frame_age_seconds.toFixed(1)}s
            </Badge>
            <Badge variant="outline">
              AI {data.processing_time_ms.toFixed(0)}ms
            </Badge>
            {lastUpdate && (
              <span
                className={cn(
                  "ml-auto",
                  loading && "animate-pulse",
                )}
              >
                Cập nhật: {lastUpdate.toLocaleTimeString("vi-VN")}
              </span>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function StatBox({
  label,
  value,
  color,
}: {
  label: string;
  value: number | string;
  color: string;
}) {
  return (
    <div className="rounded-xl bg-muted/40 p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={cn("text-2xl font-bold", color)}>{value}</p>
    </div>
  );
}
