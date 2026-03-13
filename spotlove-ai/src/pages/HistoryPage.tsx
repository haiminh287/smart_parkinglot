import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { MainLayout } from "@/components/layout/MainLayout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Car,
  Bike,
  Clock,
  MapPin,
  CheckCircle,
  XCircle,
  AlertCircle,
  Search,
  Calendar,
  Navigation,
  X,
  QrCode,
  BarChart3,
  TrendingUp,
  TrendingDown,
  Camera,
  CreditCard,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { BookingQRCode } from "@/components/booking/BookingQRCode";
import { useToast } from "@/hooks/use-toast";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useBooking } from "@/hooks";
import type { Booking, BookingStatus } from "@/store/slices/bookingSlice";

const statusConfig = {
  pending: {
    label: "Chờ xác nhận",
    color: "bg-warning/10 text-warning",
    icon: AlertCircle,
  },
  confirmed: {
    label: "Đã xác nhận",
    color: "bg-primary/10 text-primary",
    icon: CheckCircle,
  },
  checked_in: {
    label: "Đã check-in",
    color: "bg-primary/10 text-primary",
    icon: CheckCircle,
  },
  parked: {
    label: "Đang đậu",
    color: "bg-success/10 text-success",
    icon: CheckCircle,
  },
  checked_out: {
    label: "Đã lấy xe",
    color: "bg-muted text-muted-foreground",
    icon: XCircle,
  },
  completed: {
    label: "Hoàn thành",
    color: "bg-muted text-muted-foreground",
    icon: CheckCircle,
  },
  cancelled: {
    label: "Đã hủy",
    color: "bg-destructive/10 text-destructive",
    icon: XCircle,
  },
  no_show: {
    label: "Không đến",
    color: "bg-destructive/10 text-destructive",
    icon: XCircle,
  },
};

export default function HistoryPage() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [searchQuery, setSearchQuery] = useState("");
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [selectedBooking, setSelectedBooking] = useState<Booking | null>(null);
  const [showQRDialog, setShowQRDialog] = useState(false);
  const [showCancelDialog, setShowCancelDialog] = useState(false);
  const [bookingToCancel, setBookingToCancel] = useState<Booking | null>(null);
  const [monthlyExpenseData, setMonthlyExpenseData] = useState<
    Array<{ month: string; amount: number }>
  >([
    { month: "T8", amount: 0 },
    { month: "T9", amount: 0 },
    { month: "T10", amount: 0 },
    { month: "T11", amount: 0 },
    { month: "T12", amount: 0 },
    { month: "T1", amount: 0 },
  ]);

  const {
    bookings,
    noShowCount,
    totalSpent,
    forceOnlinePayment,
    loadBookings,
    getBookingStats,
    cancel,
    isLoading,
  } = useBooking();

  // Load bookings on mount and when filters change
  useEffect(() => {
    loadBookings({
      status:
        filterStatus !== "all" ? (filterStatus as BookingStatus) : undefined,
    });
  }, [filterStatus, loadBookings]);

  // Load stats for monthly chart
  useEffect(() => {
    const loadStats = async () => {
      try {
        const stats = await getBookingStats();
        if (stats) {
          // Use real monthlyExpenses from API if available
          if (
            stats.monthlyExpenses &&
            Array.isArray(stats.monthlyExpenses) &&
            stats.monthlyExpenses.length > 0
          ) {
            setMonthlyExpenseData(
              stats.monthlyExpenses.map(
                (item: { month: string; amount: number }) => ({
                  month: item.month,
                  amount: Number(item.amount || 0),
                }),
              ),
            );
          } else if (stats.totalSpent) {
            // Fallback: distribute total across months
            const total = Number(stats.totalSpent);
            setMonthlyExpenseData([
              { month: "T8", amount: total * 0.1 },
              { month: "T9", amount: total * 0.15 },
              { month: "T10", amount: total * 0.12 },
              { month: "T11", amount: total * 0.18 },
              { month: "T12", amount: total * 0.2 },
              { month: "T1", amount: total * 0.25 },
            ]);
          }
        }
      } catch (error) {
        console.error("Failed to load stats:", error);
      }
    };

    loadStats();
  }, [getBookingStats]);

  const filteredHistory = bookings.filter((booking) => {
    const matchesSearch = booking.licensePlate
      .toLowerCase()
      .includes(searchQuery.toLowerCase());
    const matchesFilter =
      filterStatus === "all" || booking.status === filterStatus;
    return matchesSearch && matchesFilter;
  });

  // Calculate stats
  console.log("Monthly Expense Data:", monthlyExpenseData);
  const thisMonthSpent =
    monthlyExpenseData[monthlyExpenseData.length - 1].amount;
  // const lastMonthSpent =
  //   monthlyExpenseData[monthlyExpenseData.length - 2].amount;
  const lastMonthSpent = 1000000; // Placeholder until real data available
  const monthlyChange = (
    ((thisMonthSpent - lastMonthSpent) / lastMonthSpent) *
    100
  ).toFixed(1);

  const handleCancel = (booking: Booking) => {
    setBookingToCancel(booking);
    setShowCancelDialog(true);
  };

  const confirmCancel = async () => {
    if (bookingToCancel) {
      await cancel(bookingToCancel.id);
      toast({
        title: "Đã hủy đặt chỗ",
        description: `Booking ${bookingToCancel.id} đã được hủy thành công.`,
      });
      setShowCancelDialog(false);
      setBookingToCancel(null);
    }
  };

  const handleViewQR = (booking: Booking) => {
    setSelectedBooking(booking);
    setShowQRDialog(true);
  };

  // Check if booking can be cancelled
  const canCancel = (booking: Booking) => {
    return ["pending", "confirmed"].includes(booking.status);
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="animate-fade-in">
          <h1 className="text-2xl font-bold text-foreground">
            Lịch sử & Thống kê
          </h1>
          <p className="mt-1 text-muted-foreground">
            Xem lịch sử đặt chỗ và thống kê chi tiêu
          </p>
        </div>

        {/* No-Show Warning Banner */}
        {noShowCount > 0 && (
          <div
            className={cn(
              "flex items-start gap-3 rounded-2xl border p-4 animate-fade-in",
              forceOnlinePayment
                ? "border-destructive/50 bg-destructive/10"
                : "border-warning/50 bg-warning/10",
            )}
          >
            <AlertCircle
              className={cn(
                "h-6 w-6 shrink-0",
                forceOnlinePayment ? "text-destructive" : "text-warning",
              )}
            />
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <p
                  className={cn(
                    "font-semibold",
                    forceOnlinePayment ? "text-destructive" : "text-warning",
                  )}
                >
                  {forceOnlinePayment
                    ? "Tài khoản bị hạn chế"
                    : "Cảnh báo vi phạm"}
                </p>
                <Badge
                  variant={forceOnlinePayment ? "destructive" : "secondary"}
                >
                  {noShowCount} lần vi phạm
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground mt-1">
                {forceOnlinePayment
                  ? "Bạn đã có 2 lần không đến sau khi đặt chỗ. Từ bây giờ, bạn phải thanh toán online trước khi đặt."
                  : `Bạn đã có ${noShowCount} lần không đến sau khi đặt chỗ. Nếu vi phạm thêm ${2 - noShowCount} lần nữa, bạn sẽ bị bắt buộc thanh toán online.`}
              </p>
            </div>
          </div>
        )}

        {/* Stats Cards */}
        <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl sm:rounded-2xl border border-border bg-card p-3 sm:p-6">
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0">
                <p className="text-xs sm:text-sm text-muted-foreground truncate">
                  Tổng chi tiêu
                </p>
                <p className="text-lg sm:text-2xl font-bold text-foreground mt-1">
                  {(totalSpent / 1000000).toFixed(1)}M
                </p>
              </div>
              <div className="flex h-8 w-8 sm:h-12 sm:w-12 items-center justify-center rounded-lg sm:rounded-xl bg-primary/10 shrink-0">
                <BarChart3 className="h-4 w-4 sm:h-6 sm:w-6 text-primary" />
              </div>
            </div>
          </div>

          <div className="rounded-xl sm:rounded-2xl border border-border bg-card p-3 sm:p-6">
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0">
                <p className="text-xs sm:text-sm text-muted-foreground truncate">
                  Tháng này
                </p>
                <p className="text-lg sm:text-2xl font-bold text-foreground mt-1">
                  {(thisMonthSpent / 1000000).toFixed(1)}M
                </p>
                <div
                  className={cn(
                    "flex items-center gap-1 mt-1 text-[10px] sm:text-xs",
                    Number(monthlyChange) > 0
                      ? "text-destructive"
                      : "text-success",
                  )}
                >
                  {Number(monthlyChange) > 0 ? (
                    <TrendingUp className="h-2.5 w-2.5 sm:h-3 sm:w-3" />
                  ) : (
                    <TrendingDown className="h-2.5 w-2.5 sm:h-3 sm:w-3" />
                  )}
                  <span className="truncate">{monthlyChange}%</span>
                </div>
              </div>
              <div className="flex h-8 w-8 sm:h-12 sm:w-12 items-center justify-center rounded-lg sm:rounded-xl bg-accent/10 shrink-0">
                <Calendar className="h-4 w-4 sm:h-6 sm:w-6 text-accent" />
              </div>
            </div>
          </div>

          <div className="rounded-xl sm:rounded-2xl border border-border bg-card p-3 sm:p-6">
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0">
                <p className="text-xs sm:text-sm text-muted-foreground truncate">
                  Số lần đặt
                </p>
                <p className="text-lg sm:text-2xl font-bold text-foreground mt-1">
                  {bookings.length}
                </p>
                <p className="text-[10px] sm:text-xs text-muted-foreground mt-1 truncate">
                  {bookings.filter((b) => b.status === "parked").length} đang
                  đậu
                </p>
              </div>
              <div className="flex h-8 w-8 sm:h-12 sm:w-12 items-center justify-center rounded-lg sm:rounded-xl bg-success/10 shrink-0">
                <Car className="h-4 w-4 sm:h-6 sm:w-6 text-success" />
              </div>
            </div>
          </div>

          {/* Violation Stats Card */}
          <div
            className={cn(
              "rounded-xl sm:rounded-2xl border p-3 sm:p-6",
              forceOnlinePayment
                ? "border-destructive/50 bg-destructive/5"
                : noShowCount > 0
                  ? "border-warning/50 bg-warning/5"
                  : "border-border bg-card",
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0">
                <p className="text-xs sm:text-sm text-muted-foreground truncate">
                  Vi phạm
                </p>
                <p
                  className={cn(
                    "text-lg sm:text-2xl font-bold mt-1",
                    forceOnlinePayment
                      ? "text-destructive"
                      : noShowCount > 0
                        ? "text-warning"
                        : "text-success",
                  )}
                >
                  {noShowCount}
                </p>
                <p className="text-[10px] sm:text-xs text-muted-foreground mt-1 truncate">
                  {noShowCount === 0
                    ? "Không vi phạm"
                    : forceOnlinePayment
                      ? "Bị hạn chế"
                      : "Cảnh báo"}
                </p>
              </div>
              <div
                className={cn(
                  "flex h-8 w-8 sm:h-12 sm:w-12 items-center justify-center rounded-lg sm:rounded-xl shrink-0",
                  forceOnlinePayment
                    ? "bg-destructive/10"
                    : noShowCount > 0
                      ? "bg-warning/10"
                      : "bg-success/10",
                )}
              >
                <XCircle
                  className={cn(
                    "h-4 w-4 sm:h-6 sm:w-6",
                    forceOnlinePayment
                      ? "text-destructive"
                      : noShowCount > 0
                        ? "text-warning"
                        : "text-success",
                  )}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Monthly Expense Chart */}
        <div className="rounded-xl sm:rounded-2xl border border-border bg-card p-3 sm:p-6">
          <h3 className="text-base sm:text-lg font-semibold text-foreground mb-3 sm:mb-4">
            Chi tiêu theo tháng
          </h3>
          <div className="h-48 sm:h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={monthlyExpenseData}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="hsl(var(--border))"
                />
                <XAxis
                  dataKey="month"
                  stroke="hsl(var(--muted-foreground))"
                  fontSize={10}
                />
                <YAxis
                  stroke="hsl(var(--muted-foreground))"
                  fontSize={10}
                  tickFormatter={(value) => `${(value / 1000000).toFixed(1)}M`}
                  width={40}
                />
                <Tooltip
                  formatter={(value: number) => [
                    `${value.toLocaleString("vi-VN")}đ`,
                    "Chi tiêu",
                  ]}
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "8px",
                    fontSize: "12px",
                  }}
                />
                <Bar
                  dataKey="amount"
                  fill="hsl(var(--primary))"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Search & Filter */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Tìm theo biển số..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-xl border border-border bg-card pl-10 pr-4 py-2 text-sm sm:py-2.5 sm:text-base text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
          <div className="flex gap-1.5 sm:gap-2 flex-wrap">
            {["all", "parked", "confirmed", "completed"].map((status) => (
              <Button
                key={status}
                variant={filterStatus === status ? "default" : "outline"}
                size="sm"
                onClick={() => setFilterStatus(status)}
                className="text-xs sm:text-sm px-2 sm:px-3"
              >
                {status === "all"
                  ? "Tất cả"
                  : statusConfig[status as keyof typeof statusConfig]?.label}
              </Button>
            ))}
          </div>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        )}

        {/* Booking List */}
        {!isLoading && (
          <div className="space-y-4">
            {filteredHistory.map((booking) => {
              const status = statusConfig[booking.status];
              const StatusIcon = status?.icon || AlertCircle;

              return (
                <div
                  key={booking.id}
                  className="group rounded-xl sm:rounded-2xl border border-border bg-card p-3 sm:p-4 md:p-6 transition-all duration-200 hover:border-primary/30 hover:shadow-lg animate-slide-up"
                >
                  <div className="flex flex-col gap-3 sm:gap-4">
                    {/* Top: Vehicle Info */}
                    <div className="flex gap-3 sm:gap-4">
                      <div
                        className={cn(
                          "flex h-10 w-10 sm:h-12 sm:w-12 md:h-14 md:w-14 items-center justify-center rounded-lg sm:rounded-xl shrink-0",
                          booking.vehicleType === "Car"
                            ? "bg-primary/10 text-primary"
                            : "bg-accent/10 text-accent",
                        )}
                      >
                        {booking.vehicleType === "Car" ? (
                          <Car className="h-5 w-5 sm:h-6 sm:w-6 md:h-7 md:w-7" />
                        ) : (
                          <Bike className="h-5 w-5 sm:h-6 sm:w-6 md:h-7 md:w-7" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className="text-sm sm:text-base md:text-lg font-bold text-foreground font-mono truncate">
                            {booking.licensePlate}
                          </p>
                          <Badge
                            variant="outline"
                            className={cn(
                              "text-[10px] sm:text-xs",
                              status?.color,
                            )}
                          >
                            <StatusIcon className="mr-1 h-2.5 w-2.5 sm:h-3 sm:w-3" />
                            <span className="hidden xs:inline">
                              {status?.label}
                            </span>
                          </Badge>
                        </div>
                        <p className="text-[10px] sm:text-xs text-muted-foreground font-mono mt-0.5">
                          #{booking.id}
                        </p>
                        <div className="mt-1 sm:mt-2 flex flex-col xs:flex-row xs:flex-wrap xs:items-center gap-1 xs:gap-2 sm:gap-4 text-xs sm:text-sm text-muted-foreground">
                          <span className="flex items-center gap-1 truncate">
                            <MapPin className="h-3 w-3 sm:h-4 sm:w-4 shrink-0" />
                            <span className="truncate">
                              {booking.zoneName} - {booking.slotCode}
                            </span>
                          </span>
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3 w-3 sm:h-4 sm:w-4 shrink-0" />
                            <span className="text-[10px] sm:text-xs">
                              {new Date(booking.startTime).toLocaleDateString(
                                "vi-VN",
                              )}
                            </span>
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Bottom: Price & Actions */}
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pt-3 border-t border-border sm:border-t-0 sm:pt-0">
                      <div className="flex items-center gap-2">
                        <p className="text-lg sm:text-xl md:text-2xl font-bold text-foreground">
                          {booking.totalAmount.toLocaleString("vi-VN")}đ
                        </p>
                        <Badge
                          className={cn(
                            "text-[10px] sm:text-xs",
                            booking.paymentStatus === "completed"
                              ? "bg-success/10 text-success"
                              : "bg-warning/10 text-warning",
                          )}
                        >
                          {booking.paymentStatus === "completed"
                            ? "Đã TT"
                            : "Chờ TT"}
                        </Badge>
                      </div>
                      <div className="flex flex-wrap gap-1.5 sm:gap-2">
                        {/* Pay Now - for unpaid bookings */}
                        {booking.paymentStatus === "pending" && (
                          <Button
                            variant="default"
                            size="sm"
                            className="gap-1 sm:gap-2 gradient-primary text-xs sm:text-sm h-8 px-2 sm:px-3"
                            onClick={() =>
                              navigate(`/payment?bookingId=${booking.id}`)
                            }
                          >
                            <CreditCard className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
                            <span className="hidden xs:inline">Thanh toán</span>
                            <span className="xs:hidden">TT</span>
                          </Button>
                        )}

                        {/* View QR */}
                        <Button
                          variant="outline"
                          size="sm"
                          className="gap-1 sm:gap-2 text-xs sm:text-sm h-8 px-2 sm:px-3"
                          onClick={() => handleViewQR(booking)}
                        >
                          <QrCode className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
                          <span className="hidden sm:inline">Xem QR</span>
                          <span className="sm:hidden">QR</span>
                        </Button>

                        {/* View Camera - only for parked vehicles */}
                        {booking.status === "parked" && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="gap-1 sm:gap-2 text-xs sm:text-sm h-8 px-2 sm:px-3"
                          >
                            <Camera className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
                            <span className="hidden sm:inline">Xem xe</span>
                          </Button>
                        )}

                        {/* Navigation */}
                        {["parked", "checked_in", "confirmed"].includes(
                          booking.status,
                        ) && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="gap-1 sm:gap-2 text-xs sm:text-sm h-8 px-2 sm:px-3"
                            onClick={() => navigate("/map")}
                          >
                            <Navigation className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
                            <span className="hidden sm:inline">Chỉ đường</span>
                          </Button>
                        )}

                        {/* Cancel - only for pending/confirmed bookings */}
                        {canCancel(booking) && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="gap-1 sm:gap-2 text-destructive hover:bg-destructive/10 text-xs sm:text-sm h-8 px-2 sm:px-3"
                            onClick={() => handleCancel(booking)}
                          >
                            <X className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
                            <span className="hidden sm:inline">Hủy</span>
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {!isLoading && filteredHistory.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-muted">
              <Clock className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold text-foreground">
              Không tìm thấy
            </h3>
            <p className="mt-1 text-muted-foreground">
              Không có lịch sử đặt chỗ phù hợp với tìm kiếm
            </p>
          </div>
        )}
      </div>

      {/* QR Code Dialog */}
      <Dialog open={showQRDialog} onOpenChange={setShowQRDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Mã QR Đặt Chỗ</DialogTitle>
          </DialogHeader>
          {selectedBooking && (
            <BookingQRCode
              bookingId={selectedBooking.id}
              vehicleType={selectedBooking.vehicleType}
              licensePlate={selectedBooking.licensePlate}
              zone={selectedBooking.zoneName}
              slot={selectedBooking.slotCode}
              dates={[new Date(selectedBooking.startTime)]}
              status={
                selectedBooking.paymentStatus === "completed"
                  ? "confirmed"
                  : "pending"
              }
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Cancel Confirmation Dialog */}
      <Dialog open={showCancelDialog} onOpenChange={setShowCancelDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Xác nhận hủy đặt chỗ</DialogTitle>
            <DialogDescription>
              Bạn có chắc chắn muốn hủy đặt chỗ này? Hành động này không thể
              hoàn tác.
            </DialogDescription>
          </DialogHeader>
          {bookingToCancel && (
            <div className="rounded-xl bg-muted/50 p-4 space-y-2">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Mã đặt chỗ</span>
                <span className="font-mono font-medium">
                  {bookingToCancel.id}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Biển số</span>
                <span className="font-mono font-medium">
                  {bookingToCancel.licensePlate}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Vị trí</span>
                <span className="font-medium">
                  {bookingToCancel.zoneName} - {bookingToCancel.slotCode}
                </span>
              </div>
            </div>
          )}
          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={() => setShowCancelDialog(false)}
            >
              Không, giữ lại
            </Button>
            <Button variant="destructive" onClick={confirmCancel}>
              Xác nhận hủy
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </MainLayout>
  );
}
