import { useState, useEffect } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Car,
  Bike,
  Users,
  Calendar,
  ArrowUpRight,
  ArrowDownRight,
  Loader2,
  RefreshCcw,
  Download,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { adminApi } from "@/services";
import { toast } from "sonner";

interface StatsCard {
  title: string;
  value: string;
  change: string;
  positive: boolean;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
}

interface RevenueDataItem {
  month: string;
  revenue: number;
  bookings: number;
}

interface VehicleTypeItem {
  name: string;
  value: number;
  color: string;
}

interface DailyStatsItem {
  day: string;
  cars: number;
  bikes: number;
}

// Default/fallback data
const defaultRevenueData: RevenueDataItem[] = [
  { month: "T1", revenue: 0, bookings: 0 },
  { month: "T2", revenue: 0, bookings: 0 },
  { month: "T3", revenue: 0, bookings: 0 },
  { month: "T4", revenue: 0, bookings: 0 },
  { month: "T5", revenue: 0, bookings: 0 },
  { month: "T6", revenue: 0, bookings: 0 },
  { month: "T7", revenue: 0, bookings: 0 },
  { month: "T8", revenue: 0, bookings: 0 },
  { month: "T9", revenue: 0, bookings: 0 },
  { month: "T10", revenue: 0, bookings: 0 },
  { month: "T11", revenue: 0, bookings: 0 },
  { month: "T12", revenue: 0, bookings: 0 },
];

const defaultVehicleTypeData: VehicleTypeItem[] = [
  { name: "Ô tô", value: 50, color: "hsl(var(--primary))" },
  { name: "Xe máy", value: 50, color: "hsl(var(--accent))" },
];

const defaultDailyStats: DailyStatsItem[] = [
  { day: "T2", cars: 0, bikes: 0 },
  { day: "T3", cars: 0, bikes: 0 },
  { day: "T4", cars: 0, bikes: 0 },
  { day: "T5", cars: 0, bikes: 0 },
  { day: "T6", cars: 0, bikes: 0 },
  { day: "T7", cars: 0, bikes: 0 },
  { day: "CN", cars: 0, bikes: 0 },
];

const defaultStatsCards: StatsCard[] = [
  {
    title: "Doanh thu tháng này",
    value: "0đ",
    change: "0%",
    positive: true,
    icon: DollarSign,
    color: "success",
  },
  {
    title: "Tổng booking",
    value: "0",
    change: "0%",
    positive: true,
    icon: Calendar,
    color: "primary",
  },
  {
    title: "Người dùng mới",
    value: "0",
    change: "0%",
    positive: true,
    icon: Users,
    color: "accent",
  },
  {
    title: "Tỷ lệ lấp đầy",
    value: "0%",
    change: "0%",
    positive: true,
    icon: BarChart3,
    color: "warning",
  },
];

export default function AdminStatsPage() {
  const [isLoading, setIsLoading] = useState(true);
  const [isExporting, setIsExporting] = useState(false);
  const [statsCards, setStatsCards] = useState<StatsCard[]>(defaultStatsCards);
  const [revenueData, setRevenueData] =
    useState<RevenueDataItem[]>(defaultRevenueData);
  const [vehicleTypeData, setVehicleTypeData] = useState<VehicleTypeItem[]>(
    defaultVehicleTypeData,
  );
  const [dailyStats, setDailyStats] =
    useState<DailyStatsItem[]>(defaultDailyStats);
  const [yearlyGrowth, setYearlyGrowth] = useState("+0%");

  // Format currency
  const formatCurrency = (value: number): string => {
    if (value >= 1000000) {
      return `${(value / 1000000).toFixed(1)}M đ`;
    }
    return new Intl.NumberFormat("vi-VN").format(value) + "đ";
  };

  // Load dashboard stats
  const loadDashboardStats = async () => {
    try {
      const stats = await adminApi.getDashboardStats();

      setStatsCards([
        {
          title: "Doanh thu tháng này",
          value: formatCurrency(stats.totalRevenue),
          change: `${stats.revenueChange >= 0 ? "+" : ""}${stats.revenueChange.toFixed(1)}%`,
          positive: stats.revenueChange >= 0,
          icon: DollarSign,
          color: "success",
        },
        {
          title: "Tổng booking",
          value: stats.totalBookings.toLocaleString(),
          change: `${stats.bookingsChange >= 0 ? "+" : ""}${stats.bookingsChange.toFixed(1)}%`,
          positive: stats.bookingsChange >= 0,
          icon: Calendar,
          color: "primary",
        },
        {
          title: "Người dùng",
          value: stats.totalUsers.toLocaleString(),
          change: `${stats.usersChange >= 0 ? "+" : ""}${stats.usersChange.toFixed(1)}%`,
          positive: stats.usersChange >= 0,
          icon: Users,
          color: "accent",
        },
        {
          title: "Tỷ lệ lấp đầy",
          value: `${stats.occupancyRate.toFixed(1)}%`,
          change:
            stats.activeParkings > 0
              ? `${stats.activeParkings} xe đang đỗ`
              : "0 xe",
          positive: true,
          icon: BarChart3,
          color: "warning",
        },
      ]);
    } catch (error) {
      console.error("Failed to load dashboard stats:", error);
    }
  };

  // Load revenue report
  const loadRevenueReport = async () => {
    try {
      const now = new Date();
      const startDate = new Date(now.getFullYear(), 0, 1)
        .toISOString()
        .split("T")[0];
      const endDate = now.toISOString().split("T")[0];

      const reports = await adminApi.getRevenueReport({
        startDate,
        endDate,
        groupBy: "month",
      });

      if (reports && reports.length > 0) {
        const mappedData = reports.map((r) => ({
          month: `T${new Date(r.period).getMonth() + 1}`,
          revenue: r.revenue,
          bookings: r.bookings,
        }));
        setRevenueData(mappedData);

        // Calculate year-over-year growth
        // Year-over-year growth — requires historical data from backend
        // Currently not available, so we show N/A
        setYearlyGrowth("N/A");
      }
    } catch (error) {
      console.error("Failed to load revenue report:", error);
    }
  };

  // Load all data
  const loadAllData = async () => {
    setIsLoading(true);
    try {
      await Promise.all([loadDashboardStats(), loadRevenueReport()]);
    } catch (error) {
      console.error("Failed to load data:", error);
      toast.error("Không thể tải dữ liệu thống kê");
    } finally {
      setIsLoading(false);
    }
  };

  // Refresh data
  const handleRefresh = async () => {
    await loadAllData();
    toast.success("Đã cập nhật dữ liệu thống kê");
  };

  // Export report
  const handleExportReport = async (type: "csv" | "pdf") => {
    setIsExporting(true);
    try {
      // For now, create a simple CSV from the current data
      if (type === "csv") {
        const csvContent = [
          ["Tháng", "Doanh thu", "Số booking"],
          ...revenueData.map((r) => [r.month, r.revenue, r.bookings]),
        ]
          .map((row) => row.join(","))
          .join("\n");

        const blob = new Blob([csvContent], {
          type: "text/csv;charset=utf-8;",
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `baocao-${new Date().toISOString().split("T")[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        toast.success("Đã xuất báo cáo CSV");
      } else {
        toast.info("Tính năng xuất PDF đang được phát triển");
      }
    } catch (error) {
      console.error("Failed to export report:", error);
      toast.error("Không thể xuất báo cáo");
    } finally {
      setIsExporting(false);
    }
  };

  // Load data on mount
  useEffect(() => {
    loadAllData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between animate-fade-in">
          <div>
            <h1 className="text-2xl font-bold text-foreground">
              Thống kê & Báo cáo
            </h1>
            <p className="mt-1 text-muted-foreground">
              Phân tích chi tiết hoạt động kinh doanh
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={isLoading}
              className="gap-2"
            >
              <RefreshCcw
                className={cn("h-4 w-4", isLoading && "animate-spin")}
              />
              Làm mới
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExportReport("csv")}
              disabled={isExporting}
              className="gap-2"
            >
              <Download className="h-4 w-4" />
              Xuất CSV
            </Button>
          </div>
        </div>

        {/* Loading State */}
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <>
            {/* Stats Cards */}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {statsCards.map((stat) => (
                <div
                  key={stat.title}
                  className="rounded-2xl border border-border bg-card p-5 animate-slide-up"
                >
                  <div className="flex items-center justify-between">
                    <div
                      className={cn(
                        "flex h-10 w-10 items-center justify-center rounded-xl",
                        stat.color === "success" && "bg-success/10",
                        stat.color === "primary" && "bg-primary/10",
                        stat.color === "accent" && "bg-accent/10",
                        stat.color === "warning" && "bg-warning/10",
                      )}
                    >
                      <stat.icon
                        className={cn(
                          "h-5 w-5",
                          stat.color === "success" && "text-success",
                          stat.color === "primary" && "text-primary",
                          stat.color === "accent" && "text-accent",
                          stat.color === "warning" && "text-warning",
                        )}
                      />
                    </div>
                    <Badge
                      variant="outline"
                      className={cn(
                        "gap-1",
                        stat.positive
                          ? "bg-success/10 text-success border-success/20"
                          : "bg-destructive/10 text-destructive border-destructive/20",
                      )}
                    >
                      {stat.positive ? (
                        <ArrowUpRight className="h-3 w-3" />
                      ) : (
                        <ArrowDownRight className="h-3 w-3" />
                      )}
                      {stat.change}
                    </Badge>
                  </div>
                  <div className="mt-4">
                    <p className="text-2xl font-bold text-foreground">
                      {stat.value}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {stat.title}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            <div className="grid gap-6 lg:grid-cols-3">
              {/* Revenue Chart */}
              <div className="lg:col-span-2 rounded-2xl border border-border bg-card p-6">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h3 className="font-semibold text-foreground">
                      Doanh thu theo tháng
                    </h3>
                    <p className="text-sm text-muted-foreground">
                      Năm {new Date().getFullYear()}
                    </p>
                  </div>
                  <Badge className="bg-success/10 text-success">
                    <TrendingUp className="h-3 w-3 mr-1" />
                    {yearlyGrowth} YoY
                  </Badge>
                </div>
                <div className="h-[200px] sm:h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={revenueData}>
                      <CartesianGrid
                        strokeDasharray="3 3"
                        className="stroke-border"
                      />
                      <XAxis dataKey="month" className="text-xs" />
                      <YAxis
                        className="text-xs"
                        tickFormatter={(value) =>
                          `${(value / 1000000).toFixed(0)}M`
                        }
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "12px",
                        }}
                        formatter={(value: number) => [
                          new Intl.NumberFormat("vi-VN", {
                            style: "currency",
                            currency: "VND",
                          }).format(value),
                          "Doanh thu",
                        ]}
                      />
                      <Bar
                        dataKey="revenue"
                        fill="hsl(var(--primary))"
                        radius={[4, 4, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Vehicle Type Pie Chart */}
              <div className="rounded-2xl border border-border bg-card p-6">
                <h3 className="font-semibold text-foreground mb-6">
                  Phân bổ loại xe
                </h3>
                <div className="h-[200px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={vehicleTypeData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={80}
                        paddingAngle={5}
                        dataKey="value"
                      >
                        {vehicleTypeData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="mt-4 space-y-2">
                  {vehicleTypeData.map((item) => (
                    <div
                      key={item.name}
                      className="flex items-center justify-between"
                    >
                      <div className="flex items-center gap-2">
                        <div
                          className="h-3 w-3 rounded-full"
                          style={{ backgroundColor: item.color }}
                        />
                        <span className="text-sm text-muted-foreground">
                          {item.name}
                        </span>
                      </div>
                      <span className="font-semibold text-foreground">
                        {item.value}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Daily Stats */}
            <div className="rounded-2xl border border-border bg-card p-6">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-6">
                <div>
                  <h3 className="font-semibold text-foreground">
                    Lượt đậu xe theo ngày
                  </h3>
                  <p className="text-sm text-muted-foreground">Tuần này</p>
                </div>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <Car className="h-4 w-4 text-primary" />
                    <span className="text-xs sm:text-sm text-muted-foreground">
                      Ô tô
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Bike className="h-4 w-4 text-accent" />
                    <span className="text-xs sm:text-sm text-muted-foreground">
                      Xe máy
                    </span>
                  </div>
                </div>
              </div>
              <div className="h-[200px] sm:h-[250px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={dailyStats}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      className="stroke-border"
                    />
                    <XAxis dataKey="day" className="text-xs" />
                    <YAxis className="text-xs" />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "hsl(var(--card))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "12px",
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="cars"
                      stroke="hsl(var(--primary))"
                      strokeWidth={2}
                      dot={{ fill: "hsl(var(--primary))" }}
                    />
                    <Line
                      type="monotone"
                      dataKey="bikes"
                      stroke="hsl(var(--accent))"
                      strokeWidth={2}
                      dot={{ fill: "hsl(var(--accent))" }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </>
        )}
      </div>
    </MainLayout>
  );
}
