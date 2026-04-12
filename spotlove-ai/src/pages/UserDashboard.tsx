import { useEffect, useState } from "react";
import {
  Car,
  MapPin,
  Clock,
  Calendar,
  CreditCard,
  Bell,
  AlertTriangle,
  ArrowRight,
  Bike,
  Loader2,
} from "lucide-react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useNavigate } from "react-router-dom";
import { useAuth, useBooking, useNotifications } from "@/hooks";

export default function UserDashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();

  // Zone name → virtual camera ID mapping
  const ZONE_CAMERA_MAP: Record<string, string> = {
    South: "virtual-zone-south",
    south: "virtual-zone-south",
    North: "virtual-zone-north",
    north: "virtual-zone-north",
    A: "virtual-zone-south",
    B: "virtual-zone-north",
    "Zone A": "virtual-zone-south",
    "Zone B": "virtual-zone-north",
  };

  const {
    currentParking,
    upcoming,
    noShowCount,
    totalSpent,
    loadCurrentParking,
    loadBookings,
    isLoading: bookingLoading,
  } = useBooking();
  const {
    recentNotifications,
    loadNotifications,
    isLoading: notifLoading,
  } = useNotifications();

  const [vehicleCount, setVehicleCount] = useState(0);

  // Load data on mount
  useEffect(() => {
    loadCurrentParking();
    loadBookings();
    loadNotifications();

    // Fetch vehicle count
    const loadVehicles = async () => {
      try {
        const { vehicleApi } = await import("@/services");
        const response = await vehicleApi.getVehicles();
        setVehicleCount(response.results?.length ?? 0);
      } catch {
        setVehicleCount(0);
      }
    };
    loadVehicles();
  }, [loadCurrentParking, loadBookings, loadNotifications]);

  const calculateCurrentCost = () => {
    if (!currentParking) return 0;
    return currentParking.currentCost;
  };

  const formatDuration = () => {
    if (!currentParking) return "";
    const hours = Math.floor(currentParking.duration / 60);
    const minutes = currentParking.duration % 60;
    return `${hours}h ${minutes}m`;
  };

  // Map notification types to icons
  const getActivityIcon = (type: string) => {
    switch (type) {
      case "booking":
        return <Calendar className="h-4 w-4 text-primary" />;
      case "payment":
        return <CreditCard className="h-4 w-4 text-primary" />;
      case "incident":
        return <Bell className="h-4 w-4 text-destructive" />;
      case "system":
      case "marketing":
      default:
        return <Bell className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const isLoading = bookingLoading || notifLoading;

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Welcome Header */}
        <div className="animate-fade-in">
          <h1 className="text-xl font-bold text-foreground sm:text-2xl">
            Xin chào, {user?.username}! 👋
          </h1>
          <p className="mt-1 text-sm text-muted-foreground sm:text-base">
            Quản lý xe và đặt chỗ của bạn
          </p>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        )}

        {/* Current Parking Status */}
        {!isLoading && currentParking ? (
          <div className="rounded-2xl border-2 border-primary/50 bg-gradient-to-br from-primary/10 to-primary/5 p-4 sm:p-6 animate-fade-in">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3 sm:gap-4">
                <div className="flex h-12 w-12 sm:h-14 sm:w-14 items-center justify-center rounded-xl bg-primary/20 shrink-0">
                  {currentParking.booking.vehicleType === "Car" ? (
                    <Car className="h-6 w-6 sm:h-7 sm:w-7 text-primary" />
                  ) : (
                    <Bike className="h-6 w-6 sm:h-7 sm:w-7 text-primary" />
                  )}
                </div>
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <h2 className="text-lg sm:text-xl font-bold text-foreground">
                      {currentParking.booking.licensePlate}
                    </h2>
                    <Badge className="bg-success/10 text-success border-success/20">
                      <div className="h-1.5 w-1.5 rounded-full bg-success mr-1.5 animate-pulse" />
                      Đang đậu
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
                    <MapPin className="h-4 w-4" />
                    <span>
                      {currentParking.booking.zoneName} • Slot{" "}
                      {currentParking.booking.slotCode}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 mt-2 text-sm">
                    <div className="flex items-center gap-1">
                      <Clock className="h-4 w-4 text-primary" />
                      <span className="font-medium">{formatDuration()}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <CreditCard className="h-4 w-4 text-primary" />
                      <span className="font-medium">
                        {calculateCurrentCost().toLocaleString("vi-VN")}đ
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex gap-2 mt-4">
              <Button
                variant="outline"
                className="flex-1"
                size="sm"
                onClick={() => {
                  const zoneName = currentParking?.booking?.zoneName || "";
                  const cameraId =
                    ZONE_CAMERA_MAP[zoneName] || "virtual-f1-overview";
                  navigate(`/cameras?camera=${cameraId}`);
                }}
              >
                Xem camera
              </Button>
              <Button
                variant="outline"
                className="flex-1 text-destructive hover:bg-destructive/10"
                size="sm"
                onClick={() => navigate("/panic")}
              >
                <AlertTriangle className="h-4 w-4 mr-1" />
                Báo sự cố
              </Button>
            </div>
          </div>
        ) : (
          !isLoading && (
            <div className="rounded-2xl border border-dashed border-border bg-muted/30 p-6 text-center animate-fade-in">
              <Car className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
              <h3 className="font-semibold text-foreground">
                Không có xe đang đậu
              </h3>
              <p className="text-sm text-muted-foreground mt-1">
                Đặt chỗ ngay để giữ vị trí cho xe của bạn
              </p>
              <Button
                className="mt-4 gradient-primary"
                onClick={() => navigate("/booking")}
              >
                Đặt chỗ ngay
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </div>
          )
        )}

        {/* Quick Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div
            className="rounded-xl border border-border bg-card p-3 sm:p-4 cursor-pointer hover:border-primary/50 transition-colors"
            onClick={() => navigate("/history")}
          >
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <Calendar className="h-4 w-4" />
              <span className="text-xs">Sắp tới</span>
            </div>
            <p className="text-xl sm:text-2xl font-bold text-foreground">
              {upcoming.length}
            </p>
          </div>
          <div className="rounded-xl border border-border bg-card p-3 sm:p-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <CreditCard className="h-4 w-4" />
              <span className="text-xs">Chi tiêu</span>
            </div>
            <p className="text-xl sm:text-2xl font-bold text-foreground">
              {(totalSpent / 1000000).toFixed(1)}M
            </p>
          </div>
          <div className="rounded-xl border border-border bg-card p-3 sm:p-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <Car className="h-4 w-4" />
              <span className="text-xs">Xe đã lưu</span>
            </div>
            <p className="text-xl sm:text-2xl font-bold text-foreground">
              {vehicleCount}
            </p>
          </div>
          <div className="rounded-xl border border-border bg-card p-3 sm:p-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <AlertTriangle className="h-4 w-4" />
              <span className="text-xs">No-show</span>
            </div>
            <p
              className={cn(
                "text-xl sm:text-2xl font-bold",
                noShowCount > 0 ? "text-destructive" : "text-success",
              )}
            >
              {noShowCount}
            </p>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-2 gap-3">
          <Button
            variant="outline"
            className="h-auto py-4 flex flex-col gap-2"
            onClick={() => navigate("/booking")}
          >
            <Calendar className="h-6 w-6 text-primary" />
            <span>Đặt chỗ mới</span>
          </Button>
          <Button
            variant="outline"
            className="h-auto py-4 flex flex-col gap-2"
            onClick={() => navigate("/map")}
          >
            <MapPin className="h-6 w-6 text-primary" />
            <span>Xem bản đồ</span>
          </Button>
        </div>

        {/* Recent Activity */}
        <div className="rounded-2xl border border-border bg-card p-4 sm:p-6 animate-slide-up">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-foreground">
              Hoạt động gần đây
            </h3>
            <Bell className="h-5 w-5 text-muted-foreground" />
          </div>
          <div className="space-y-3">
            {recentNotifications.length > 0 ? (
              recentNotifications.map((notification) => (
                <div key={notification.id} className="flex items-start gap-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
                    {getActivityIcon(notification.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-foreground">
                      {notification.message}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {new Date(notification.createdAt).toLocaleDateString(
                        "vi-VN",
                      )}{" "}
                      {new Date(notification.createdAt).toLocaleTimeString(
                        "vi-VN",
                        { hour: "2-digit", minute: "2-digit" },
                      )}
                    </p>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground text-center py-4">
                Chưa có hoạt động nào
              </p>
            )}
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
