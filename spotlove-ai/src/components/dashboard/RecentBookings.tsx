import { useState, useEffect } from "react";
import {
  Car,
  Bike,
  Clock,
  MapPin,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { bookingService } from "@/services/business";
import { mapBookingResponse, type Booking } from "@/store/slices/bookingSlice";

const statusConfig: Record<
  string,
  { label: string; color: string; icon: React.ElementType }
> = {
  checked_in: {
    label: "Đã check-in",
    color: "bg-primary/10 text-primary",
    icon: CheckCircle,
  },
  not_checked_in: {
    label: "Chưa check-in",
    color: "bg-warning/10 text-warning",
    icon: AlertCircle,
  },
  checked_out: {
    label: "Đã lấy xe",
    color: "bg-muted text-muted-foreground",
    icon: XCircle,
  },
  parked: {
    label: "Đang đậu",
    color: "bg-success/10 text-success",
    icon: CheckCircle,
  },
  confirmed: {
    label: "Đã xác nhận",
    color: "bg-primary/10 text-primary",
    icon: CheckCircle,
  },
  pending: {
    label: "Chờ xác nhận",
    color: "bg-warning/10 text-warning",
    icon: AlertCircle,
  },
  cancelled: {
    label: "Đã hủy",
    color: "bg-destructive/10 text-destructive",
    icon: XCircle,
  },
  completed: {
    label: "Hoàn thành",
    color: "bg-success/10 text-success",
    icon: CheckCircle,
  },
};

export function RecentBookings() {
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchRecentBookings = async () => {
      try {
        const response = await bookingService.getHistory({ page: 1, pageSize: 5 });
        const mapped = (response.results || []).map((item) =>
          mapBookingResponse(item),
        );
        setBookings(mapped);
      } catch (error) {
        console.error("Failed to fetch recent bookings:", error);
        setBookings([]);
      } finally {
        setLoading(false);
      }
    };
    fetchRecentBookings();
  }, []);

  return (
    <div className="rounded-2xl border border-border bg-card p-6 animate-slide-up">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-foreground">
            Lịch sử gần đây
          </h3>
          <p className="text-sm text-muted-foreground">Các booking mới nhất</p>
        </div>
        <button className="text-sm font-medium text-primary hover:underline">
          Xem tất cả
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : bookings.length === 0 ? (
        <div className="text-center py-8">
          <Car className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Chưa có booking nào</p>
        </div>
      ) : (
        <div className="space-y-4">
          {bookings.map((booking) => {
            const status =
              statusConfig[booking.status] || statusConfig["pending"];
            const StatusIcon = status.icon;

            return (
              <div
                key={booking.id}
                className="group flex items-center gap-4 rounded-xl border border-border bg-background/50 p-4 transition-all duration-200 hover:border-primary/30 hover:shadow-sm"
              >
                {/* Vehicle Icon */}
                <div
                  className={cn(
                    "flex h-12 w-12 items-center justify-center rounded-xl",
                    booking.vehicleType === "Car"
                      ? "bg-primary/10 text-primary"
                      : "bg-accent/10 text-accent",
                  )}
                >
                  {booking.vehicleType === "Car" ? (
                    <Car className="h-6 w-6" />
                  ) : (
                    <Bike className="h-6 w-6" />
                  )}
                </div>

                {/* Booking Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-semibold text-foreground">
                      {booking.licensePlate}
                    </p>
                    <Badge
                      variant="outline"
                      className={cn("text-xs", status.color)}
                    >
                      <StatusIcon className="mr-1 h-3 w-3" />
                      {status.label}
                    </Badge>
                  </div>
                  <div className="mt-1 flex items-center gap-4 text-sm text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <MapPin className="h-3 w-3" />
                      {booking.zoneName} - {booking.slotCode}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {new Date(booking.startTime).toLocaleDateString("vi-VN")}
                    </span>
                  </div>
                </div>

                {/* Payment Status */}
                <div className="text-right">
                  <Badge
                    variant={
                      booking.paymentStatus === "completed"
                        ? "default"
                        : "secondary"
                    }
                    className={cn(
                      booking.paymentStatus === "completed"
                        ? "bg-success text-success-foreground"
                        : "bg-warning/10 text-warning",
                    )}
                  >
                    {booking.paymentStatus === "completed"
                      ? "Đã thanh toán"
                      : "Chờ thanh toán"}
                  </Badge>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
