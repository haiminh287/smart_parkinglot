import { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { MainLayout } from "@/components/layout/MainLayout";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  CreditCard,
  Copy,
  Check,
  Clock,
  Car,
  Bike,
  MapPin,
  Calendar,
  AlertTriangle,
  ArrowLeft,
  Building2,
  CheckCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useToast } from "@/hooks/use-toast";
import { QRCodeSVG } from "qrcode.react";
import { bookingApi } from "@/services";
import {
  mapBookingResponse,
  type Booking as MappedBooking,
} from "@/store/slices/bookingSlice";

// Bank info for QR payment
// TODO: Move these values to environment variables or a backend config endpoint
// e.g. VITE_BANK_CODE, VITE_BANK_ACCOUNT_NUMBER, VITE_BANK_ACCOUNT_NAME
const bankInfo = {
  bankName: import.meta.env.VITE_BANK_NAME ?? "Vietcombank",
  bankCode: import.meta.env.VITE_BANK_CODE ?? "VCB",
  accountNumber: import.meta.env.VITE_BANK_ACCOUNT_NUMBER ?? "1234567890123",
  accountName: import.meta.env.VITE_BANK_ACCOUNT_NAME ?? "CONG TY PARKSMART",
  branch: import.meta.env.VITE_BANK_BRANCH ?? "Chi nhánh Hồ Chí Minh",
};

// Generate VietQR content
const generateVietQR = (amount: number, bookingId: string) => {
  // VietQR format: bank code + account + amount + memo
  return `https://img.vietqr.io/image/${bankInfo.bankCode}-${bankInfo.accountNumber}-compact.png?amount=${amount}&addInfo=${bookingId}&accountName=${encodeURIComponent(bankInfo.accountName)}`;
};

export default function PaymentPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { toast } = useToast();
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [timeLeft, setTimeLeft] = useState<string>("");
  const [isExpired, setIsExpired] = useState(false);
  const [paymentConfirmed, setPaymentConfirmed] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [booking, setBooking] = useState<MappedBooking | null>(null);
  const [loading, setLoading] = useState(true);

  const bookingId = searchParams.get("bookingId");

  // Fetch booking details
  useEffect(() => {
    const fetchBooking = async () => {
      if (!bookingId) {
        toast({
          title: "Lỗi",
          description: "Không tìm thấy mã booking",
          variant: "destructive",
        });
        navigate("/history");
        return;
      }

      try {
        setLoading(true);
        const data = await bookingApi.getBooking(bookingId);
        // Map API response (which may have nested objects) to flat MappedBooking
        const mapped = mapBookingResponse(data);
        setBooking(mapped);
      } catch (error) {
        console.error("Failed to fetch booking:", error);
        toast({
          title: "Lỗi",
          description: "Không thể tải thông tin booking",
          variant: "destructive",
        });
        navigate("/history");
      } finally {
        setLoading(false);
      }
    };

    fetchBooking();
  }, [bookingId, navigate, toast]);

  // Countdown timer
  useEffect(() => {
    if (!booking) return;

    const updateTimer = () => {
      const now = new Date();
      // Payment deadline: 15 minutes after booking creation
      const paymentDeadline = new Date(
        new Date(booking.createdAt).getTime() + 15 * 60 * 1000,
      );
      const diff = paymentDeadline.getTime() - now.getTime();

      if (diff <= 0) {
        setIsExpired(true);
        setTimeLeft("Đã hết hạn");
        return;
      }

      const hours = Math.floor(diff / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((diff % (1000 * 60)) / 1000);

      setTimeLeft(
        `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`,
      );
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);
    return () => clearInterval(interval);
  }, [booking]);

  const handleCopy = (text: string, field: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    toast({
      title: "Đã sao chép",
      description: `${field} đã được sao chép vào clipboard`,
    });
    setTimeout(() => setCopiedField(null), 2000);
  };

  const handleConfirmPayment = () => {
    setIsVerifying(true);
    toast({
      title: "Đang xác minh thanh toán...",
      description:
        "Hệ thống đang kiểm tra giao dịch. Vui lòng đợi trong giây lát.",
    });
  };

  // Auto-poll payment status: every 10s normally, every 3s after user confirms
  useEffect(() => {
    if (!bookingId || !booking || paymentConfirmed) return;

    const interval = isVerifying ? 3000 : 10000;

    const pollInterval = setInterval(async () => {
      try {
        const result = await bookingApi.pollPaymentStatus(bookingId);
        if (result.paymentStatus === "completed") {
          clearInterval(pollInterval);
          setPaymentConfirmed(true);
          toast({
            title: "✅ Thanh toán thành công!",
            description: "Booking đã được xác nhận thanh toán.",
          });
          setTimeout(() => navigate("/history"), 2000);
        }
      } catch (error) {
        // Silently retry
      }
    }, interval);

    return () => clearInterval(pollInterval);
  }, [bookingId, booking, paymentConfirmed, isVerifying, toast, navigate]);

  if (paymentConfirmed) {
    return (
      <MainLayout>
        <div className="mx-auto max-w-lg py-16 text-center animate-fade-in">
          <div className="mb-6 flex justify-center">
            <div className="flex h-20 w-20 items-center justify-center rounded-full bg-success/10">
              <CheckCircle className="h-10 w-10 text-success" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-foreground mb-2">
            ✅ Thanh toán thành công!
          </h1>
          <p className="text-muted-foreground mb-6">
            Booking đã được xác nhận. Đang chuyển hướng...
          </p>
          <Button onClick={() => navigate("/history")}>
            Xem lịch sử đặt chỗ
          </Button>
        </div>
      </MainLayout>
    );
  }

  if (isVerifying) {
    return (
      <MainLayout>
        <div className="mx-auto max-w-lg py-16 text-center animate-fade-in">
          <div className="mb-6 flex justify-center">
            <div className="animate-spin h-16 w-16 border-4 border-primary border-t-transparent rounded-full" />
          </div>
          <h1 className="text-2xl font-bold text-foreground mb-2">
            Đang xác minh thanh toán...
          </h1>
          <p className="text-muted-foreground mb-4">
            Hệ thống đang kiểm tra giao dịch mỗi 3 giây. Vui lòng đợi.
          </p>
          <p className="text-xs text-muted-foreground mb-6">
            Thông thường mất 1-3 phút để ngân hàng xác nhận.
          </p>
          <Button variant="outline" onClick={() => navigate("/history")}>
            Xem lịch sử đặt chỗ
          </Button>
        </div>
      </MainLayout>
    );
  }

  if (loading || !booking) {
    return (
      <MainLayout>
        <div className="mx-auto max-w-4xl py-16 text-center">
          <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-muted-foreground">Đang tải thông tin booking...</p>
        </div>
      </MainLayout>
    );
  }

  // Map flat Booking fields to display fields
  const displayData = {
    id: booking.id,
    licensePlate: booking.licensePlate || "N/A",
    vehicleType: booking.vehicleType || "Car",
    parkingLot: booking.lotName || "N/A",
    floor: 1,
    zone: booking.zoneName || "N/A",
    slot: booking.slotCode,
    startDate: booking.startTime,
    endDate: booking.endTime || booking.startTime,
    packageType:
      booking.packageType === "monthly"
        ? "Theo tháng"
        : booking.packageType === "weekly"
          ? "Theo tuần"
          : booking.packageType === "daily"
            ? "Theo ngày"
            : "Theo giờ",
    price: booking.totalAmount || 0,
  };

  return (
    <MainLayout>
      <div className="mx-auto max-w-4xl space-y-4 sm:space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3 sm:gap-4 animate-fade-in">
          <Button
            variant="ghost"
            size="icon"
            className="shrink-0 h-9 w-9 sm:h-10 sm:w-10"
            onClick={() => navigate(-1)}
          >
            <ArrowLeft className="h-4 w-4 sm:h-5 sm:w-5" />
          </Button>
          <div className="min-w-0">
            <h1 className="text-lg sm:text-2xl font-bold text-foreground truncate">
              Thanh toán đặt chỗ
            </h1>
            <p className="text-xs sm:text-base text-muted-foreground truncate">
              Quét mã QR hoặc chuyển khoản
            </p>
          </div>
        </div>

        {/* Deadline Warning */}
        <div
          className={cn(
            "flex flex-col sm:flex-row items-start sm:items-center gap-2 sm:gap-3 rounded-xl sm:rounded-2xl border p-3 sm:p-4 animate-slide-up",
            isExpired
              ? "border-destructive/50 bg-destructive/10"
              : "border-warning/50 bg-warning/10",
          )}
        >
          <div className="flex items-center gap-2 sm:gap-3 flex-1">
            {isExpired ? (
              <AlertTriangle className="h-5 w-5 sm:h-6 sm:w-6 text-destructive shrink-0" />
            ) : (
              <Clock className="h-5 w-5 sm:h-6 sm:w-6 text-warning shrink-0" />
            )}
            <div className="flex-1 min-w-0">
              <p
                className={cn(
                  "text-sm sm:text-base font-medium",
                  isExpired ? "text-destructive" : "text-warning",
                )}
              >
                {isExpired ? "Đã hết hạn thanh toán" : "Thời gian còn lại"}
              </p>
              <p className="text-xs sm:text-sm text-muted-foreground hidden sm:block">
                {isExpired
                  ? "Vui lòng đặt chỗ mới nếu bạn vẫn muốn sử dụng dịch vụ."
                  : "Sau thời gian này, chỗ đặt sẽ tự động hủy."}
              </p>
            </div>
          </div>
          <div
            className={cn(
              "text-lg sm:text-2xl font-mono font-bold",
              isExpired ? "text-destructive" : "text-warning",
            )}
          >
            {timeLeft}
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          {/* QR Code Section */}
          <div className="rounded-2xl border border-border bg-card p-6 animate-slide-up">
            <h2 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
              <CreditCard className="h-5 w-5 text-primary" />
              Quét mã QR để thanh toán
            </h2>

            <div className="flex flex-col items-center">
              {/* QR Code */}
              <div className="mb-4 rounded-xl bg-white p-4 shadow-lg">
                <QRCodeSVG
                  value={`${bankInfo.bankCode}|${bankInfo.accountNumber}|${displayData.price}|${displayData.id}`}
                  size={200}
                  level="H"
                  includeMargin
                />
              </div>

              {/* Amount */}
              <div className="text-center mb-4">
                <p className="text-sm text-muted-foreground">
                  Số tiền thanh toán
                </p>
                <p className="text-3xl font-bold text-primary">
                  {displayData.price.toLocaleString("vi-VN")}đ
                </p>
              </div>

              {/* Bank Info */}
              <div className="w-full space-y-3 rounded-xl bg-muted/50 p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">
                    Ngân hàng
                  </span>
                  <span className="font-medium">{bankInfo.bankName}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">
                    Số tài khoản
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-medium">
                      {bankInfo.accountNumber}
                    </span>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={() =>
                        handleCopy(bankInfo.accountNumber, "Số tài khoản")
                      }
                    >
                      {copiedField === "Số tài khoản" ? (
                        <Check className="h-3 w-3 text-success" />
                      ) : (
                        <Copy className="h-3 w-3" />
                      )}
                    </Button>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Tên TK</span>
                  <span className="font-medium">{bankInfo.accountName}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">
                    Nội dung CK
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-medium text-primary">
                      {displayData.id}
                    </span>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={() => handleCopy(displayData.id, "Mã đặt chỗ")}
                    >
                      {copiedField === "Mã đặt chỗ" ? (
                        <Check className="h-3 w-3 text-success" />
                      ) : (
                        <Copy className="h-3 w-3" />
                      )}
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Booking Details */}
          <div className="space-y-4">
            <div className="rounded-2xl border border-border bg-card p-6 animate-slide-up">
              <h2 className="text-lg font-semibold text-foreground mb-4">
                Thông tin đặt chỗ
              </h2>

              <div className="space-y-4">
                {/* Vehicle */}
                <div className="flex items-center gap-4">
                  <div
                    className={cn(
                      "flex h-12 w-12 items-center justify-center rounded-xl",
                      displayData.vehicleType === "Car"
                        ? "bg-primary/10 text-primary"
                        : "bg-accent/10 text-accent",
                    )}
                  >
                    {displayData.vehicleType === "Car" ? (
                      <Car className="h-6 w-6" />
                    ) : (
                      <Bike className="h-6 w-6" />
                    )}
                  </div>
                  <div>
                    <p className="font-mono text-lg font-bold">
                      {displayData.licensePlate}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {displayData.vehicleType === "Car" ? "Ô tô" : "Xe máy"}
                    </p>
                  </div>
                </div>

                {/* Parking Lot */}
                <div className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-success/10">
                    <Building2 className="h-6 w-6 text-success" />
                  </div>
                  <div>
                    <p className="font-medium">{displayData.parkingLot}</p>
                    <p className="text-sm text-muted-foreground">Bãi giữ xe</p>
                  </div>
                </div>

                {/* Location */}
                <div className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-accent/10">
                    <MapPin className="h-6 w-6 text-accent" />
                  </div>
                  <div>
                    <p className="font-medium">
                      Tầng {displayData.floor} - {displayData.zone}
                      {displayData.slot && ` - ${displayData.slot}`}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Vị trí đậu xe
                    </p>
                  </div>
                </div>

                {/* Duration */}
                <div className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-warning/10">
                    <Calendar className="h-6 w-6 text-warning" />
                  </div>
                  <div>
                    <p className="font-medium">{displayData.packageType}</p>
                    <p className="text-sm text-muted-foreground">
                      {new Date(displayData.startDate).toLocaleDateString(
                        "vi-VN",
                      )}{" "}
                      -{" "}
                      {new Date(displayData.endDate).toLocaleDateString(
                        "vi-VN",
                      )}
                    </p>
                  </div>
                </div>
              </div>

              {/* Price Summary */}
              <div className="mt-6 border-t border-border pt-4">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Tổng tiền</span>
                  <span className="text-2xl font-bold text-foreground">
                    {displayData.price.toLocaleString("vi-VN")}đ
                  </span>
                </div>
              </div>
            </div>

            {/* Confirm Button */}
            <Button
              className="w-full gradient-primary"
              size="lg"
              onClick={handleConfirmPayment}
              disabled={isExpired}
            >
              <CheckCircle className="h-5 w-5 mr-2" />
              Tôi đã thanh toán
            </Button>

            <p className="text-center text-sm text-muted-foreground">
              Sau khi chuyển khoản, nhấn nút trên để hệ thống xác nhận.
              <br />
              Thường mất 1-5 phút để xác minh.
            </p>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
