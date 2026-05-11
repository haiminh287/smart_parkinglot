/**
 * KioskPage — Self-service Kiosk UI for parking entrance/exit gates.
 *
 * Features:
 *   - QR code scanning via camera stream
 *   - License plate display from AI recognition
 *   - Barrier status indicator
 *   - Cash payment integration with banknote detection
 *   - Real-time gate event feed
 */

import { useState, useEffect, useCallback, useRef } from "react";
import {
  QrCode,
  Camera,
  DollarSign,
  ShieldCheck,
  AlertTriangle,
  Loader2,
  ArrowRight,
  CheckCircle2,
  XCircle,
  Banknote,
  Car,
  LogIn,
  LogOut,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  aiService,
  type ESP32Response,
  type GateEvent,
  type BarrierAction,
} from "@/services/business";

type KioskMode = "idle" | "check-in" | "check-out" | "cash-payment" | "result";

interface GateLog {
  id: string;
  timestamp: Date;
  event: GateEvent;
  message: string;
  plateText: string | null;
  success: boolean;
}

const EVENT_LABELS: Record<GateEvent, string> = {
  check_in_success: "Check-in thành công",
  check_in_failed: "Check-in thất bại",
  check_out_success: "Check-out thành công",
  check_out_awaiting_payment: "Chờ thanh toán",
  check_out_failed: "Check-out thất bại",
  verify_slot_success: "Xác minh slot OK",
  verify_slot_failed: "Xác minh slot lỗi",
};

const BARRIER_LABELS: Record<BarrierAction, string> = {
  open: "🟢 MỞ BARRIER",
  close: "🔴 ĐÓNG BARRIER",
  no_action: "⚪ KHÔNG THAY ĐỔI",
};

export default function KioskPage() {
  const [mode, setMode] = useState<KioskMode>("idle");
  const [gateId] = useState("GATE-01");
  const [isProcessing, setIsProcessing] = useState(false);
  const [lastResult, setLastResult] = useState<ESP32Response | null>(null);
  const [gateLogs, setGateLogs] = useState<GateLog[]>([]);
  const [cashTotal, setCashTotal] = useState(0);
  const [currentTime, setCurrentTime] = useState(new Date());
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Clock
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const addLog = useCallback((response: ESP32Response) => {
    const log: GateLog = {
      id: crypto.randomUUID(),
      timestamp: new Date(),
      event: response.event,
      message: response.message,
      plateText: response.plateText,
      success: response.success,
    };
    setGateLogs((prev) => [log, ...prev].slice(0, 20));
  }, []);

  const handleCheckIn = async () => {
    setMode("check-in");
    setIsProcessing(true);
    try {
      const response = await aiService.esp32CheckIn({ gateId });
      setLastResult(response);
      addLog(response);
      setMode("result");
    } catch (error) {
      const errorResponse: ESP32Response = {
        success: false,
        event: "check_in_failed",
        barrierAction: "close",
        message: error instanceof Error ? error.message : "Lỗi hệ thống",
        gateId,
        bookingId: null,
        plateText: null,
        amountDue: null,
        amountPaid: null,
        processingTimeMs: 0,
        details: null,
      };
      setLastResult(errorResponse);
      addLog(errorResponse);
      setMode("result");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleCheckOut = async () => {
    setMode("check-out");
    setIsProcessing(true);
    try {
      const response = await aiService.esp32CheckOut({ gateId });
      setLastResult(response);
      addLog(response);

      // If awaiting payment, switch to cash mode
      if (response.event === "check_out_awaiting_payment") {
        setMode("cash-payment");
        setCashTotal(0);
      } else {
        setMode("result");
      }
    } catch (error) {
      const errorResponse: ESP32Response = {
        success: false,
        event: "check_out_failed",
        barrierAction: "close",
        message: error instanceof Error ? error.message : "Lỗi hệ thống",
        gateId,
        bookingId: null,
        plateText: null,
        amountDue: null,
        amountPaid: null,
        processingTimeMs: 0,
        details: null,
      };
      setLastResult(errorResponse);
      addLog(errorResponse);
      setMode("result");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleCashInsert = async () => {
    if (!lastResult?.bookingId || !fileInputRef.current) return;
    fileInputRef.current.click();
  };

  const handleCashImage = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !lastResult?.bookingId) return;

    setIsProcessing(true);
    try {
      // First detect banknote denomination
      const banknoteResult = await aiService.detectBanknote(file);
      if (banknoteResult.decision === "accept" && banknoteResult.denomination) {
        const insertedAmount = parseInt(banknoteResult.denomination, 10);
        setCashTotal((prev) => prev + insertedAmount);

        // Send cash payment to ESP32 endpoint
        const reader = new FileReader();
        reader.onloadend = async () => {
          const base64 = (reader.result as string).split(",")[1];
          try {
            const cashResponse = await aiService.esp32CashPayment({
              bookingId: lastResult.bookingId!,
              imageBase64: base64,
              gateId,
            });
            setLastResult(cashResponse);
            addLog(cashResponse);
            if (cashResponse.success) {
              setMode("result");
            }
          } catch (err) {
            console.error("Cash payment error:", err);
          }
        };
        reader.readAsDataURL(file);
      }
    } catch (error) {
      console.error("Banknote detection error:", error);
    } finally {
      setIsProcessing(false);
      // Reset input
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const resetKiosk = () => {
    setMode("idle");
    setLastResult(null);
    setCashTotal(0);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/30 flex flex-col">
      {/* Kiosk Header */}
      <header className="border-b border-border bg-card/80 backdrop-blur-sm px-6 py-4">
        <div className="flex items-center justify-between max-w-6xl mx-auto">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl gradient-primary">
              <Car className="h-6 w-6 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-foreground">
                ParkSmart Kiosk
              </h1>
              <p className="text-sm text-muted-foreground">
                Cổng {gateId} — Hệ thống tự động
              </p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-2xl font-mono font-bold text-foreground">
              {currentTime.toLocaleTimeString("vi-VN")}
            </p>
            <p className="text-sm text-muted-foreground">
              {currentTime.toLocaleDateString("vi-VN", {
                weekday: "long",
                year: "numeric",
                month: "long",
                day: "numeric",
              })}
            </p>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex items-center justify-center p-6">
        <div className="max-w-4xl w-full grid gap-6 lg:grid-cols-3">
          {/* Left Panel — Actions */}
          <div className="lg:col-span-2 space-y-6">
            {mode === "idle" && (
              <div className="space-y-6 animate-fade-in">
                <div className="text-center space-y-2">
                  <QrCode className="h-16 w-16 mx-auto text-primary" />
                  <h2 className="text-3xl font-bold text-foreground">
                    Chào mừng đến ParkSmart
                  </h2>
                  <p className="text-lg text-muted-foreground">
                    Vui lòng chọn hành động bên dưới
                  </p>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <button
                    onClick={handleCheckIn}
                    className="flex flex-col items-center gap-4 rounded-3xl border-2 border-success/30 bg-success/5 p-8 transition-all hover:border-success hover:shadow-lg hover:shadow-success/20 active:scale-[0.98]"
                  >
                    <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-success/20">
                      <LogIn className="h-10 w-10 text-success" />
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-bold text-foreground">
                        VÀO BÃI
                      </p>
                      <p className="text-sm text-muted-foreground mt-1">
                        Quét QR + Nhận diện biển số
                      </p>
                    </div>
                  </button>

                  <button
                    onClick={handleCheckOut}
                    className="flex flex-col items-center gap-4 rounded-3xl border-2 border-primary/30 bg-primary/5 p-8 transition-all hover:border-primary hover:shadow-lg hover:shadow-primary/20 active:scale-[0.98]"
                  >
                    <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-primary/20">
                      <LogOut className="h-10 w-10 text-primary" />
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-bold text-foreground">
                        RA BÃI
                      </p>
                      <p className="text-sm text-muted-foreground mt-1">
                        Quét QR + Thanh toán
                      </p>
                    </div>
                  </button>
                </div>
              </div>
            )}

            {(mode === "check-in" || mode === "check-out") && isProcessing && (
              <div className="flex flex-col items-center justify-center py-16 animate-fade-in space-y-6">
                <div className="relative">
                  <div className="h-24 w-24 rounded-full border-4 border-primary/20 animate-pulse" />
                  <Camera className="absolute inset-0 m-auto h-12 w-12 text-primary animate-bounce" />
                </div>
                <div className="text-center space-y-2">
                  <p className="text-2xl font-bold text-foreground">
                    {mode === "check-in"
                      ? "Đang quét QR vào bãi..."
                      : "Đang quét QR ra bãi..."}
                  </p>
                  <p className="text-muted-foreground">
                    Vui lòng đưa mã QR trước camera
                  </p>
                  <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary mt-4" />
                </div>
              </div>
            )}

            {mode === "cash-payment" && (
              <div className="space-y-6 animate-fade-in">
                <div className="text-center space-y-2">
                  <DollarSign className="h-16 w-16 mx-auto text-warning" />
                  <h2 className="text-2xl font-bold text-foreground">
                    Thanh toán tiền mặt
                  </h2>
                  <p className="text-muted-foreground">
                    Đưa tiền trước camera để thanh toán
                  </p>
                </div>

                <div className="rounded-2xl border-2 border-warning/30 bg-warning/5 p-6 space-y-4">
                  <div className="flex justify-between items-center text-lg">
                    <span className="text-muted-foreground">
                      Cần thanh toán:
                    </span>
                    <span className="text-2xl font-bold text-foreground">
                      {(lastResult?.amountDue ?? 0).toLocaleString("vi-VN")} VNĐ
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-lg">
                    <span className="text-muted-foreground">Đã nạp:</span>
                    <span className="text-2xl font-bold text-success">
                      {cashTotal.toLocaleString("vi-VN")} VNĐ
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-lg border-t border-border pt-3">
                    <span className="text-muted-foreground">Còn thiếu:</span>
                    <span className="text-2xl font-bold text-destructive">
                      {Math.max(
                        0,
                        (lastResult?.amountDue ?? 0) - cashTotal,
                      ).toLocaleString("vi-VN")}{" "}
                      VNĐ
                    </span>
                  </div>
                </div>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  capture="environment"
                  className="hidden"
                  onChange={handleCashImage}
                />

                <Button
                  size="lg"
                  className="w-full h-16 text-lg gap-3"
                  onClick={handleCashInsert}
                  disabled={isProcessing}
                >
                  {isProcessing ? (
                    <Loader2 className="h-6 w-6 animate-spin" />
                  ) : (
                    <Banknote className="h-6 w-6" />
                  )}
                  {isProcessing
                    ? "Đang nhận diện tiền..."
                    : "Đưa tiền vào / Chụp ảnh tiền"}
                </Button>

                <Button
                  variant="outline"
                  className="w-full"
                  onClick={resetKiosk}
                >
                  Hủy giao dịch
                </Button>
              </div>
            )}

            {mode === "result" && lastResult && (
              <div className="space-y-6 animate-fade-in">
                <div
                  className={cn(
                    "rounded-3xl border-2 p-8 text-center space-y-4",
                    lastResult.success
                      ? "border-success/30 bg-success/5"
                      : "border-destructive/30 bg-destructive/5",
                  )}
                >
                  {lastResult.success ? (
                    <CheckCircle2 className="h-20 w-20 mx-auto text-success" />
                  ) : (
                    <XCircle className="h-20 w-20 mx-auto text-destructive" />
                  )}
                  <h2 className="text-3xl font-bold text-foreground">
                    {EVENT_LABELS[lastResult.event]}
                  </h2>
                  <p className="text-lg text-muted-foreground">
                    {lastResult.message}
                  </p>

                  {lastResult.plateText && (
                    <div className="inline-flex items-center gap-2 rounded-xl bg-card border border-border px-6 py-3">
                      <Car className="h-5 w-5 text-primary" />
                      <span className="text-xl font-mono font-bold text-foreground">
                        {lastResult.plateText}
                      </span>
                    </div>
                  )}

                  <div className="text-lg font-bold">
                    {BARRIER_LABELS[lastResult.barrierAction]}
                  </div>
                </div>

                <Button
                  size="lg"
                  className="w-full h-14 text-lg gradient-primary"
                  onClick={resetKiosk}
                >
                  <ArrowRight className="h-5 w-5 mr-2" />
                  Tiếp tục
                </Button>
              </div>
            )}
          </div>

          {/* Right Panel — Event Log */}
          <div className="space-y-4">
            <div className="rounded-2xl border border-border bg-card p-4">
              <h3 className="font-semibold text-foreground mb-3 flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-primary" />
                Nhật ký cổng
              </h3>
              <div className="space-y-2 max-h-[400px] overflow-y-auto">
                {gateLogs.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    Chưa có hoạt động
                  </p>
                ) : (
                  gateLogs.map((log) => (
                    <div
                      key={log.id}
                      className={cn(
                        "flex items-start gap-2 rounded-lg p-2 text-sm border",
                        log.success
                          ? "bg-success/5 border-success/20"
                          : "bg-destructive/5 border-destructive/20",
                      )}
                    >
                      {log.success ? (
                        <CheckCircle2 className="h-4 w-4 text-success shrink-0 mt-0.5" />
                      ) : (
                        <AlertTriangle className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
                      )}
                      <div className="min-w-0 flex-1">
                        <p className="font-medium text-foreground truncate">
                          {EVENT_LABELS[log.event]}
                        </p>
                        {log.plateText && (
                          <p className="font-mono text-xs text-muted-foreground">
                            {log.plateText}
                          </p>
                        )}
                        <p className="text-xs text-muted-foreground">
                          {log.timestamp.toLocaleTimeString("vi-VN")}
                        </p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Gate Status Card */}
            <div className="rounded-2xl border border-border bg-card p-4 space-y-3">
              <h3 className="font-semibold text-foreground flex items-center gap-2">
                <Camera className="h-4 w-4 text-primary" />
                Trạng thái cổng
              </h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Gate ID</span>
                  <Badge variant="outline" className="font-mono">
                    {gateId}
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Chế độ</span>
                  <Badge
                    className={cn(
                      mode === "idle"
                        ? "bg-muted text-muted-foreground"
                        : "bg-primary text-primary-foreground",
                    )}
                  >
                    {mode === "idle"
                      ? "Sẵn sàng"
                      : mode === "cash-payment"
                        ? "Thanh toán"
                        : "Xử lý"}
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Hôm nay</span>
                  <span className="font-semibold text-foreground">
                    {gateLogs.filter((l) => l.success).length} lượt
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
