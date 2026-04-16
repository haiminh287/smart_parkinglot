import { useState, useEffect } from "react";
import {
  Car,
  DollarSign,
  TrendingUp,
  Calendar,
  Users,
  Loader2,
  Activity,
  Video,
  CheckCircle,
  AlertTriangle,
  Shield,
  Gauge,
} from "lucide-react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { StatsCard } from "@/components/dashboard/StatsCard";
import { SlotOverview } from "@/components/dashboard/SlotOverview";
import { RecentBookings } from "@/components/dashboard/RecentBookings";
import { adminService } from "@/services/business";
import { cn } from "@/lib/utils";
import { useNavigate } from "react-router-dom";

interface DashboardData {
  totalUsers: number;
  totalBookings: number;
  totalRevenue: number;
  activeParkings: number;
  occupancyRate: number;
  usersChange: number;
  bookingsChange: number;
  revenueChange: number;
  newUsersThisMonth?: number;
  bookingsThisMonth?: number;
  revenueThisMonth?: number;
}

interface RecentActivity {
  type: string;
  message: string;
  timestamp: string;
  user?: string;
}

export default function AdminDashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardData | null>(null);
  const [activities, setActivities] = useState<RecentActivity[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [statsData, activitiesData] = await Promise.all([
          adminService.getDashboardStats(),
          adminService.getRecentActivities(8),
        ]);
        setStats(statsData as unknown as DashboardData);
        setActivities(activitiesData);
      } catch (error) {
        console.error("Failed to fetch dashboard data:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const formatRevenue = (value: number) => {
    if (value >= 1000000000) return `${(value / 1000000000).toFixed(1)}B`;
    if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `${(value / 1000).toFixed(0)}K`;
    return String(value);
  };

  const getActivityIcon = (type: string) => {
    switch (type) {
      case "check_in":
        return <CheckCircle className="h-4 w-4 text-success" />;
      case "check_out":
        return <Car className="h-4 w-4 text-primary" />;
      case "booking":
        return <Calendar className="h-4 w-4 text-blue-500" />;
      case "payment":
        return <DollarSign className="h-4 w-4 text-success" />;
      case "incident":
        return <AlertTriangle className="h-4 w-4 text-destructive" />;
      default:
        return <Activity className="h-4 w-4 text-muted-foreground" />;
    }
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between animate-fade-in">
          <div>
            <h1 className="text-xl font-bold text-foreground sm:text-2xl md:text-3xl">
              Dashboard Admin 🅿️
            </h1>
            <p className="mt-1 text-sm text-muted-foreground sm:text-base">
              Quản lý và theo dõi toàn bộ hệ thống bãi giữ xe
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge
              variant="outline"
              className="bg-success/10 text-success border-success/20 gap-1.5"
            >
              <div className="h-2 w-2 rounded-full bg-success animate-pulse" />
              Hệ thống hoạt động
            </Badge>
          </div>
        </div>

        {/* Stats Grid */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : (
          <>
            <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
              <StatsCard
                title="Tổng người dùng"
                value={stats?.totalUsers ?? 0}
                subtitle={
                  stats?.newUsersThisMonth
                    ? `+${stats.newUsersThisMonth} tháng này`
                    : undefined
                }
                icon={Users}
                variant="primary"
                trend={
                  stats?.usersChange
                    ? {
                        value: Math.round(stats.usersChange),
                        positive: stats.usersChange >= 0,
                      }
                    : undefined
                }
              />
              <StatsCard
                title="Xe đang đậu"
                value={stats?.activeParkings ?? 0}
                subtitle={
                  stats?.occupancyRate
                    ? `Tỷ lệ lấp đầy ${stats.occupancyRate.toFixed(1)}%`
                    : undefined
                }
                icon={Car}
                trend={
                  stats?.bookingsChange
                    ? {
                        value: Math.round(stats.bookingsChange),
                        positive: stats.bookingsChange >= 0,
                      }
                    : undefined
                }
              />
              <StatsCard
                title="Doanh thu tháng"
                value={formatRevenue(stats?.revenueThisMonth ?? 0)}
                subtitle="VNĐ"
                icon={DollarSign}
                variant="success"
                trend={
                  stats?.revenueChange
                    ? {
                        value: Math.round(stats.revenueChange),
                        positive: stats.revenueChange >= 0,
                      }
                    : undefined
                }
              />
              <StatsCard
                title="Tổng booking"
                value={stats?.totalBookings ?? 0}
                subtitle={
                  stats?.bookingsThisMonth
                    ? `${stats.bookingsThisMonth} tháng này`
                    : undefined
                }
                icon={Calendar}
                variant="warning"
              />
            </div>

            {/* Occupancy Rate Bar */}
            <div className="rounded-2xl border border-border bg-card p-4 sm:p-6 animate-fade-in">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Gauge className="h-5 w-5 text-primary" />
                  <h3 className="font-semibold text-foreground">
                    Tỷ lệ lấp đầy tổng thể
                  </h3>
                </div>
                <span
                  className={cn(
                    "text-2xl font-bold",
                    (stats?.occupancyRate ?? 0) > 80
                      ? "text-destructive"
                      : (stats?.occupancyRate ?? 0) > 50
                        ? "text-warning"
                        : "text-success",
                  )}
                >
                  {(stats?.occupancyRate ?? 0).toFixed(1)}%
                </span>
              </div>
              <div className="h-3 overflow-hidden rounded-full bg-muted">
                <div
                  className={cn(
                    "h-full rounded-full transition-all duration-1000",
                    (stats?.occupancyRate ?? 0) > 80
                      ? "bg-destructive"
                      : (stats?.occupancyRate ?? 0) > 50
                        ? "bg-warning"
                        : "bg-success",
                  )}
                  style={{
                    width: `${Math.min(stats?.occupancyRate ?? 0, 100)}%`,
                  }}
                />
              </div>
              <div className="flex justify-between mt-2 text-xs text-muted-foreground">
                <span>0%</span>
                <span>Trống</span>
                <span>50%</span>
                <span>Gần đầy</span>
                <span>100%</span>
              </div>
            </div>

            {/* Main Content Grid */}
            <div className="grid gap-6 lg:grid-cols-3">
              {/* Left Column - Slot Overview + Recent Bookings */}
              <div className="lg:col-span-2 space-y-6">
                <SlotOverview />
                <RecentBookings />
              </div>

              {/* Right Column - Quick Actions + Recent Activity + System Info */}
              <div className="space-y-6">
                {/* Quick Admin Actions */}
                <div className="rounded-2xl border border-border bg-card p-4 sm:p-6 animate-slide-up">
                  <h3 className="text-lg font-semibold text-foreground mb-4">
                    Truy cập nhanh
                  </h3>
                  <div className="grid grid-cols-2 gap-2">
                    <Button
                      variant="outline"
                      className="h-auto py-3 flex flex-col gap-1.5 text-xs"
                      onClick={() => navigate("/admin/users")}
                    >
                      <Users className="h-5 w-5 text-primary" />
                      Người dùng
                    </Button>
                    <Button
                      variant="outline"
                      className="h-auto py-3 flex flex-col gap-1.5 text-xs"
                      onClick={() => navigate("/admin/cameras")}
                    >
                      <Video className="h-5 w-5 text-primary" />
                      Camera
                    </Button>
                    <Button
                      variant="outline"
                      className="h-auto py-3 flex flex-col gap-1.5 text-xs"
                      onClick={() => navigate("/cameras")}
                    >
                      <Shield className="h-5 w-5 text-primary" />
                      Giám sát live
                    </Button>
                    <Button
                      variant="outline"
                      className="h-auto py-3 flex flex-col gap-1.5 text-xs"
                      onClick={() => navigate("/admin/reports")}
                    >
                      <TrendingUp className="h-5 w-5 text-primary" />
                      Báo cáo
                    </Button>
                  </div>
                </div>

                {/* System Status */}
                <div className="rounded-2xl border border-border bg-card p-4 sm:p-6 animate-slide-up">
                  <h3 className="text-lg font-semibold text-foreground mb-4">
                    Trạng thái hệ thống
                  </h3>
                  <div className="space-y-3">
                    {[
                      { name: "API Gateway", status: "online" },
                      { name: "Auth Service", status: "online" },
                      { name: "Booking Service", status: "online" },
                      { name: "AI Service", status: "online" },
                      { name: "Camera EZVIZ", status: "online" },
                    ].map((service) => (
                      <div
                        key={service.name}
                        className="flex items-center justify-between"
                      >
                        <span className="text-sm text-foreground">
                          {service.name}
                        </span>
                        <Badge
                          variant="outline"
                          className={cn(
                            "text-xs",
                            service.status === "online"
                              ? "bg-success/10 text-success border-success/20"
                              : "bg-destructive/10 text-destructive border-destructive/20",
                          )}
                        >
                          <div
                            className={cn(
                              "h-1.5 w-1.5 rounded-full mr-1.5",
                              service.status === "online"
                                ? "bg-success"
                                : "bg-destructive",
                            )}
                          />
                          {service.status === "online" ? "Online" : "Offline"}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Recent Activity */}
                <div className="rounded-2xl border border-border bg-card p-4 sm:p-6 animate-slide-up">
                  <h3 className="text-lg font-semibold text-foreground mb-4">
                    Hoạt động gần đây
                  </h3>
                  <div className="space-y-3">
                    {activities.length > 0 ? (
                      activities.slice(0, 6).map((activity, index) => (
                        <div key={index} className="flex items-start gap-3">
                          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted">
                            {getActivityIcon(activity.type)}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-foreground line-clamp-2">
                              {activity.message}
                            </p>
                            <p className="text-xs text-muted-foreground mt-0.5">
                              {new Date(activity.timestamp).toLocaleString(
                                "vi-VN",
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
            </div>
          </>
        )}
      </div>
    </MainLayout>
  );
}
