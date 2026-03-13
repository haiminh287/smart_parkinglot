import { useState, useEffect, useCallback, useRef } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DollarSign,
  TrendingUp,
  Calendar,
  Download,
  RefreshCcw,
  CreditCard,
  Banknote,
  Wallet,
  ArrowUpRight,
  Clock,
  CheckCircle2,
  XCircle,
  Activity,
  Users,
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
  PieChart,
  Pie,
  Cell,
  Area,
  AreaChart,
} from "recharts";
import { toast } from "sonner";
import { bookingApi } from "@/services/api/booking.api";
import type {
  RevenueSummary,
  DailyRevenueItem,
  HourlyRevenueItem,
} from "@/services/api/booking.api";

// ── Types ────────────────────────────────────────────────────────────────

type DailyDays = 7 | 30 | 90;

interface PaymentMethodDisplay {
  name: string;
  value: number;
  color: string;
  count: number;
}

interface FormattedHourlyItem {
  hour: string;
  revenue: number;
  bookings: number;
}

// ── Constants ────────────────────────────────────────────────────────────

const AUTO_REFRESH_INTERVAL = 60_000; // 60 seconds

const DAILY_RANGE_OPTIONS: { label: string; value: DailyDays }[] = [
  { label: "7 ngày", value: 7 },
  { label: "30 ngày", value: 30 },
  { label: "90 ngày", value: 90 },
];

const PAYMENT_COLORS = {
  online: "#3b82f6",
  onExit: "#10b981",
};

// ── Helpers ──────────────────────────────────────────────────────────────

function formatVND(amount: number): string {
  if (amount >= 1_000_000_000) {
    return `${(amount / 1_000_000_000).toFixed(1)}B`;
  }
  if (amount >= 1_000_000) {
    return `${(amount / 1_000_000).toFixed(1)}M`;
  }
  if (amount >= 1_000) {
    return `${(amount / 1_000).toFixed(0)}K`;
  }
  return amount.toLocaleString("vi-VN");
}

function formatFullVND(amount: number): string {
  return amount.toLocaleString("vi-VN") + "₫";
}

function formatDateLabel(dateStr: string): string {
  // dateStr is "YYYY-MM-DD", convert to "DD/MM"
  const parts = dateStr.split("-");
  if (parts.length === 3) {
    return `${parts[2]}/${parts[1]}`;
  }
  return dateStr;
}

function pct(part: number, total: number): string {
  if (total === 0) return "0";
  return ((part / total) * 100).toFixed(1);
}

// ── Sub-components ──────────────────────────────────────────────────────

function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  color,
}: {
  title: string;
  value: string;
  subtitle?: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
}) {
  return (
    <div
      className="rounded-xl border bg-card p-4 shadow-sm"
      data-testid="stat-card"
    >
      <div className="flex items-center justify-between mb-2">
        <div
          className={cn(
            "flex h-9 w-9 items-center justify-center rounded-lg",
            color,
          )}
        >
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <p className="text-xl font-bold">{value}</p>
      <p className="text-xs text-muted-foreground">{title}</p>
      {subtitle && (
        <p className="text-[10px] text-muted-foreground mt-0.5">{subtitle}</p>
      )}
    </div>
  );
}

function BookingStatBadge({
  label,
  count,
  total,
  icon: Icon,
  colorClass,
}: {
  label: string;
  count: number;
  total: number;
  icon: React.ComponentType<{ className?: string }>;
  colorClass: string;
}) {
  return (
    <div className="flex items-center justify-between rounded-lg border bg-card p-3">
      <div className="flex items-center gap-2">
        <div
          className={cn(
            "flex h-8 w-8 items-center justify-center rounded-lg",
            colorClass,
          )}
        >
          <Icon className="h-4 w-4" />
        </div>
        <div>
          <p className="text-sm font-semibold">
            {count.toLocaleString("vi-VN")}
          </p>
          <p className="text-xs text-muted-foreground">{label}</p>
        </div>
      </div>
      <Badge variant="secondary" className="text-[10px]">
        {pct(count, total)}%
      </Badge>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <MainLayout>
      <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
        {/* Header skeleton */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-2">
            <div className="h-7 w-56 rounded bg-muted animate-pulse" />
            <div className="h-4 w-72 rounded bg-muted animate-pulse" />
          </div>
        </div>
        {/* Cards skeleton */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="rounded-xl border bg-card p-4 shadow-sm space-y-3"
            >
              <div className="h-9 w-9 rounded-lg bg-muted animate-pulse" />
              <div className="h-6 w-24 rounded bg-muted animate-pulse" />
              <div className="h-3 w-16 rounded bg-muted animate-pulse" />
            </div>
          ))}
        </div>
        {/* Chart skeleton */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 rounded-xl border p-4 shadow-sm h-80 animate-pulse bg-muted/20" />
          <div className="rounded-xl border p-4 shadow-sm h-80 animate-pulse bg-muted/20" />
        </div>
      </div>
    </MainLayout>
  );
}

// ── Main Page ───────────────────────────────────────────────────────────

export default function AdminRevenuePage() {
  const [summary, setSummary] = useState<RevenueSummary | null>(null);
  const [dailyData, setDailyData] = useState<DailyRevenueItem[]>([]);
  const [hourlyData, setHourlyData] = useState<HourlyRevenueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [dailyDays, setDailyDays] = useState<DailyDays>(30);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Fetch summary + hourly (independent of dailyDays)
  const fetchCore = useCallback(async () => {
    const [summaryRes, hourlyRes] = await Promise.all([
      bookingApi.getRevenueSummary(),
      bookingApi.getHourlyRevenue(), // today by default
    ]);
    setSummary(summaryRes);
    setHourlyData(hourlyRes);
  }, []);

  // Fetch daily data (depends on dailyDays)
  const fetchDaily = useCallback(async (days: DailyDays) => {
    const dailyRes = await bookingApi.getDailyRevenue(days);
    setDailyData(dailyRes);
  }, []);

  // Full fetch
  const fetchAll = useCallback(
    async (isBackground = false) => {
      if (!isBackground) setLoading(true);
      else setRefreshing(true);
      try {
        await Promise.all([fetchCore(), fetchDaily(dailyDays)]);
      } catch {
        toast.error("Không thể tải dữ liệu doanh thu");
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [fetchCore, fetchDaily, dailyDays],
  );

  // Initial load
  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // Auto-refresh every 60s
  useEffect(() => {
    timerRef.current = setInterval(() => {
      fetchAll(true);
    }, AUTO_REFRESH_INTERVAL);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [fetchAll]);

  // Re-fetch daily when range changes
  const handleDailyRangeChange = useCallback(
    async (days: DailyDays) => {
      setDailyDays(days);
      try {
        await fetchDaily(days);
      } catch {
        toast.error("Không thể tải dữ liệu doanh thu theo ngày");
      }
    },
    [fetchDaily],
  );

  const handleRefresh = useCallback(() => {
    fetchAll();
  }, [fetchAll]);

  const handleExport = () => {
    toast.success("Đang xuất báo cáo doanh thu...");
  };

  // ── Derived data ──────────────────────────────────────────────────────

  const paymentMethods: PaymentMethodDisplay[] = summary
    ? [
        {
          name: "Chuyển khoản",
          value: summary.paymentMethods?.online?.amount ?? 0,
          color: PAYMENT_COLORS.online,
          count: summary.paymentMethods?.online?.count ?? 0,
        },
        {
          name: "Tiền mặt (khi ra)",
          value: summary.paymentMethods?.onExit?.amount ?? 0,
          color: PAYMENT_COLORS.onExit,
          count: summary.paymentMethods?.onExit?.count ?? 0,
        },
      ]
    : [];

  const formattedDaily: (DailyRevenueItem & { label: string })[] =
    dailyData.map((d) => ({
      ...d,
      label: formatDateLabel(d.date),
    }));

  const formattedHourly: FormattedHourlyItem[] = hourlyData.map((h) => ({
    hour: `${String(h.hour).padStart(2, "0")}:00`,
    revenue: h.revenue,
    bookings: h.bookings,
  }));

  // ── Loading state ─────────────────────────────────────────────────────

  if (loading && !summary) {
    return <LoadingSkeleton />;
  }

  return (
    <MainLayout>
      <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
              <DollarSign className="h-6 w-6 text-primary" />
              Báo cáo Doanh thu
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Phân tích doanh thu và giao dịch thanh toán
              {refreshing && (
                <span className="ml-2 text-xs text-primary">
                  (đang cập nhật...)
                </span>
              )}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={loading}
              data-testid="refresh-btn"
            >
              <RefreshCcw
                className={cn("h-4 w-4 mr-1", loading && "animate-spin")}
              />
              Làm mới
            </Button>
            <Button variant="outline" size="sm" onClick={handleExport}>
              <Download className="h-4 w-4 mr-1" />
              Xuất báo cáo
            </Button>
          </div>
        </div>

        {/* Revenue KPI Cards */}
        {summary && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard
              title="Tổng doanh thu"
              value={formatFullVND(summary.totalRevenue)}
              icon={DollarSign}
              color="bg-blue-500/10 text-blue-600"
            />
            <StatCard
              title="Doanh thu hôm nay"
              value={formatFullVND(summary.todayRevenue)}
              icon={Calendar}
              color="bg-green-500/10 text-green-600"
            />
            <StatCard
              title="Doanh thu tuần này"
              value={formatFullVND(summary.thisWeekRevenue)}
              icon={TrendingUp}
              color="bg-cyan-500/10 text-cyan-600"
            />
            <StatCard
              title="Doanh thu tháng này"
              value={formatFullVND(summary.thisMonthRevenue)}
              icon={Wallet}
              color="bg-purple-500/10 text-purple-600"
            />
          </div>
        )}

        {/* Booking Stats + Average */}
        {summary && (
          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            <BookingStatBadge
              label="Tổng booking"
              count={summary.totalBookings}
              total={summary.totalBookings}
              icon={Users}
              colorClass="bg-blue-500/10 text-blue-600"
            />
            <BookingStatBadge
              label="Hoàn thành"
              count={summary.completedBookings}
              total={summary.totalBookings}
              icon={CheckCircle2}
              colorClass="bg-green-500/10 text-green-600"
            />
            <BookingStatBadge
              label="Đang hoạt động"
              count={summary.activeBookings}
              total={summary.totalBookings}
              icon={Activity}
              colorClass="bg-amber-500/10 text-amber-600"
            />
            <BookingStatBadge
              label="Đã huỷ"
              count={summary.cancelledBookings}
              total={summary.totalBookings}
              icon={XCircle}
              colorClass="bg-red-500/10 text-red-600"
            />
            <div className="flex items-center justify-between rounded-lg border bg-card p-3">
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-500/10 text-violet-600">
                  <ArrowUpRight className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-sm font-semibold">
                    {formatFullVND(summary.averageBookingValue)}
                  </p>
                  <p className="text-xs text-muted-foreground">TB/booking</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Charts row 1: Daily Revenue + Payment Methods */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Daily revenue area chart */}
          <div className="lg:col-span-2 rounded-xl border bg-card p-4 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-primary" />
                Doanh thu theo ngày
              </h3>
              <div className="flex items-center gap-1">
                {DAILY_RANGE_OPTIONS.map((opt) => (
                  <Button
                    key={opt.value}
                    size="sm"
                    variant={dailyDays === opt.value ? "default" : "ghost"}
                    className="h-7 text-[11px] px-2"
                    onClick={() => handleDailyRangeChange(opt.value)}
                  >
                    {opt.label}
                  </Button>
                ))}
              </div>
            </div>
            <div className="h-64">
              {formattedDaily.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={formattedDaily}>
                    <defs>
                      <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop
                          offset="5%"
                          stopColor="#3b82f6"
                          stopOpacity={0.3}
                        />
                        <stop
                          offset="95%"
                          stopColor="#3b82f6"
                          stopOpacity={0}
                        />
                      </linearGradient>
                    </defs>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      className="stroke-border"
                    />
                    <XAxis
                      dataKey="label"
                      tick={{ fontSize: 10 }}
                      interval={dailyDays <= 7 ? 0 : dailyDays <= 30 ? 2 : 6}
                    />
                    <YAxis tick={{ fontSize: 10 }} tickFormatter={formatVND} />
                    <Tooltip
                      formatter={(val: number) => formatFullVND(val)}
                      labelFormatter={(label: string) => `Ngày ${label}`}
                      labelStyle={{ color: "var(--foreground)" }}
                      contentStyle={{
                        backgroundColor: "var(--card)",
                        border: "1px solid var(--border)",
                        borderRadius: "8px",
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="revenue"
                      stroke="#3b82f6"
                      fill="url(#revGrad)"
                      strokeWidth={2}
                      name="Doanh thu"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
                  Chưa có dữ liệu
                </div>
              )}
            </div>
          </div>

          {/* Payment methods pie chart */}
          <div className="rounded-xl border bg-card p-4 shadow-sm">
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
              <CreditCard className="h-4 w-4 text-primary" />
              Phương thức thanh toán
            </h3>
            {paymentMethods.some((m) => m.value > 0) ? (
              <>
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={paymentMethods}
                        cx="50%"
                        cy="50%"
                        innerRadius={40}
                        outerRadius={70}
                        dataKey="value"
                        label={({ name, percent }) =>
                          `${name} ${(percent * 100).toFixed(0)}%`
                        }
                        labelLine={false}
                      >
                        {paymentMethods.map((entry) => (
                          <Cell key={entry.name} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        formatter={(val: number) => formatFullVND(val)}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="space-y-1.5 mt-2">
                  {paymentMethods.map((m) => (
                    <div
                      key={m.name}
                      className="flex items-center justify-between text-xs"
                    >
                      <div className="flex items-center gap-1.5">
                        <div
                          className="h-2.5 w-2.5 rounded-full"
                          style={{ backgroundColor: m.color }}
                        />
                        <span>{m.name}</span>
                      </div>
                      <div className="text-right">
                        <span className="font-medium">
                          {formatVND(m.value)}
                        </span>
                        <span className="text-muted-foreground ml-1">
                          ({m.count.toLocaleString("vi-VN")} giao dịch)
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="flex items-center justify-center h-48 text-sm text-muted-foreground">
                Chưa có dữ liệu
              </div>
            )}
          </div>
        </div>

        {/* Charts row 2: Daily bookings bar + Hourly distribution */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Daily bookings bar chart */}
          <div className="rounded-xl border bg-card p-4 shadow-sm">
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
              <Banknote className="h-4 w-4 text-primary" />
              Số booking theo ngày ({dailyDays} ngày gần nhất)
            </h3>
            <div className="h-56">
              {formattedDaily.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={formattedDaily}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      className="stroke-border"
                    />
                    <XAxis
                      dataKey="label"
                      tick={{ fontSize: 10 }}
                      interval={dailyDays <= 7 ? 0 : dailyDays <= 30 ? 2 : 6}
                    />
                    <YAxis tick={{ fontSize: 10 }} />
                    <Tooltip
                      formatter={(val: number) => [val, "Bookings"]}
                      labelFormatter={(label: string) => `Ngày ${label}`}
                      contentStyle={{
                        backgroundColor: "var(--card)",
                        border: "1px solid var(--border)",
                        borderRadius: "8px",
                      }}
                    />
                    <Bar
                      dataKey="bookings"
                      name="Bookings"
                      fill="#10b981"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
                  Chưa có dữ liệu
                </div>
              )}
            </div>
          </div>

          {/* Hourly distribution */}
          <div className="rounded-xl border bg-card p-4 shadow-sm">
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
              <Clock className="h-4 w-4 text-primary" />
              Phân bố theo giờ (hôm nay)
            </h3>
            <div className="h-56">
              {formattedHourly.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={formattedHourly}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      className="stroke-border"
                    />
                    <XAxis dataKey="hour" tick={{ fontSize: 9 }} interval={2} />
                    <YAxis tick={{ fontSize: 10 }} tickFormatter={formatVND} />
                    <Tooltip
                      formatter={(val: number, name: string) =>
                        name === "Doanh thu" ? formatFullVND(val) : val
                      }
                      contentStyle={{
                        backgroundColor: "var(--card)",
                        border: "1px solid var(--border)",
                        borderRadius: "8px",
                      }}
                    />
                    <Bar
                      dataKey="revenue"
                      name="Doanh thu"
                      fill="#8b5cf6"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
                  Chưa có dữ liệu
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Auto-refresh footer note */}
        <div className="text-center text-xs text-muted-foreground pb-2">
          Tự động cập nhật mỗi 60 giây
        </div>
      </div>
    </MainLayout>
  );
}
