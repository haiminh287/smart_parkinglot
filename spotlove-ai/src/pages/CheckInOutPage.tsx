/**
 * CheckInOutPage — User-facing check-in / check-out flow.
 *
 * Features:
 *   - Show current active booking
 *   - Display QR code for gate scanning
 *   - Upload plate image for manual check-in/out
 *   - Show real-time booking status
 *   - Payment status indicator
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { MainLayout } from "@/components/layout/MainLayout";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  QrCode,
  Camera,
  LogIn,
  LogOut,
  Clock,
  MapPin,
  Car,
  CreditCard,
  CheckCircle2,
  XCircle,
  Loader2,
  Upload,
  ArrowRight,
  AlertTriangle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useBooking } from "@/hooks";
import { BookingQRCode } from "@/components/booking/BookingQRCode";
import { aiApi } from "@/services/api/ai.api";
import type { CheckInResponse, CheckOutResponse } from "@/services/api/ai.api";

type ActiveTab = "check-in" | "check-out";

interface ManualResult {
  success: boolean;
  message: string;
  plateText?: string;
  bookingId?: string;
}

export default function CheckInOutPage() {
  const navigate = useNavigate();
  const { currentParking, loadCurrentParking, isLoading } = useBooking();
  const [activeTab, setActiveTab] = useState<ActiveTab>("check-in");
  const [isProcessing, setIsProcessing] = useState(false);
  const [manualResult, setManualResult] = useState<ManualResult | null>(null);
  const [showResultDialog, setShowResultDialog] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  // QR scan modal state
  const [isQrModalOpen, setIsQrModalOpen] = useState(false);
  const [qrScanStatus, setQrScanStatus] = useState<
    "idle" | "scanning" | "found" | "error"
  >("idle");
  const [scannedQrData, setScannedQrData] = useState<string | null>(null);
  const [qrCheckInLoading, setQrCheckInLoading] = useState(false);
  const [qrCheckInResult, setQrCheckInResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);

  const qrPollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    loadCurrentParking();
  }, [loadCurrentParking]);

  // Cleanup QR poll interval on unmount
  useEffect(() => {
    return () => {
      if (qrPollIntervalRef.current) clearInterval(qrPollIntervalRef.current);
    };
  }, []);

  // Auto-switch to check-out if currently parked
  useEffect(() => {
    if (currentParking) {
      setActiveTab("check-out");
    }
  }, [currentParking]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
    }
  };

  const handleManualCheckIn = useCallback(async () => {
    if (!selectedFile || !currentParking) return;
    setIsProcessing(true);
    setManualResult(null);
    try {
      const response: CheckInResponse = await aiApi.checkIn(selectedFile, {
        bookingId: currentParking.booking.id,
        userId: currentParking.booking.userId,
      });
      setManualResult({
        success: response.success,
        message: response.message,
        plateText: response.plateText,
        bookingId: response.bookingId,
      });
      setShowResultDialog(true);
      if (response.success) {
        loadCurrentParking();
      }
    } catch (error) {
      setManualResult({
        success: false,
        message: error instanceof Error ? error.message : "Lỗi check-in",
      });
      setShowResultDialog(true);
    } finally {
      setIsProcessing(false);
    }
  }, [selectedFile, currentParking, loadCurrentParking]);

  const handleManualCheckOut = useCallback(async () => {
    if (!selectedFile || !currentParking) return;
    setIsProcessing(true);
    setManualResult(null);
    try {
      const response: CheckOutResponse = await aiApi.checkOut(selectedFile, {
        bookingId: currentParking.booking.id,
        userId: currentParking.booking.userId,
      });
      setManualResult({
        success: response.success,
        message: response.message,
        plateText: response.plateText,
        bookingId: response.bookingId,
      });
      setShowResultDialog(true);
      if (response.success) {
        loadCurrentParking();
      }
    } catch (error) {
      setManualResult({
        success: false,
        message: error instanceof Error ? error.message : "Lỗi check-out",
      });
      setShowResultDialog(true);
    } finally {
      setIsProcessing(false);
    }
  }, [selectedFile, currentParking, loadCurrentParking]);

  const resetForm = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setManualResult(null);
  };

  const startQrScan = () => {
    setIsQrModalOpen(true);
    setQrScanStatus("scanning");
    setScannedQrData(null);
    setQrCheckInResult(null);

    qrPollIntervalRef.current = setInterval(async () => {
      try {
        const resp = await fetch(
          "/ai/cameras/scan-qr?camera_id=qr-camera-droidcam",
        );
        const data = await resp.json();
        if (data.found && data.qr_data) {
          clearInterval(qrPollIntervalRef.current!);
          qrPollIntervalRef.current = null;
          setScannedQrData(data.qr_data);
          setQrScanStatus("found");
        }
      } catch {
        // network blip — keep polling
      }
    }, 1500);
  };

  const stopQrScan = () => {
    if (qrPollIntervalRef.current) {
      clearInterval(qrPollIntervalRef.current);
      qrPollIntervalRef.current = null;
    }
    setIsQrModalOpen(false);
    setQrScanStatus("idle");
    setScannedQrData(null);
  };

  const confirmQrCheckIn = async () => {
    if (!scannedQrData) return;
    setQrCheckInLoading(true);
    try {
      const resp = await fetch("/ai/parking/esp32/check-in/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          gate_id: "GATE-IN-01",
          qr_data: scannedQrData,
        }),
      });
      const result = await resp.json();
      setQrCheckInResult({
        success: result.success ?? resp.ok,
        message:
          result.message || (resp.ok ? "Check-in thành công!" : "Thất bại"),
      });
    } catch (err) {
      setQrCheckInResult({ success: false, message: "Lỗi kết nối server" });
    } finally {
      setQrCheckInLoading(false);
    }
  };

  const formatDuration = (minutes: number): string => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours > 0) return `${hours}h ${mins}m`;
    return `${mins} phút`;
  };

  return (
    <MainLayout>
      <div className="mx-auto max-w-3xl space-y-6">
        {/* Header */}
        <div className="animate-fade-in">
          <h1 className="text-2xl font-bold text-foreground">
            Check-in / Check-out
          </h1>
          <p className="mt-1 text-muted-foreground">
            Quét QR tại cổng hoặc upload ảnh biển số
          </p>
        </div>

        {/* Current Parking Status */}
        {currentParking && (
          <div className="rounded-2xl border-2 border-success/30 bg-success/5 p-5 space-y-3 animate-fade-in">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-success/20">
                <Car className="h-6 w-6 text-success" />
              </div>
              <div className="flex-1">
                <p className="font-semibold text-foreground">Đang đỗ xe</p>
                <p className="text-sm text-muted-foreground">
                  Biển số:{" "}
                  <span className="font-mono font-bold">
                    {currentParking.booking.licensePlate}
                  </span>
                </p>
              </div>
              <Badge className="bg-success text-success-foreground">
                ACTIVE
              </Badge>
            </div>
            <div className="grid grid-cols-3 gap-3 text-sm">
              <div className="rounded-lg bg-card border border-border p-3 text-center">
                <MapPin className="h-4 w-4 mx-auto text-muted-foreground mb-1" />
                <p className="font-medium">
                  {currentParking.booking.zoneName || "—"}
                </p>
                <p className="text-xs text-muted-foreground">Vị trí</p>
              </div>
              <div className="rounded-lg bg-card border border-border p-3 text-center">
                <Clock className="h-4 w-4 mx-auto text-muted-foreground mb-1" />
                <p className="font-medium">
                  {formatDuration(currentParking.duration)}
                </p>
                <p className="text-xs text-muted-foreground">Thời gian</p>
              </div>
              <div className="rounded-lg bg-card border border-border p-3 text-center">
                <CreditCard className="h-4 w-4 mx-auto text-muted-foreground mb-1" />
                <p className="font-medium">
                  {(currentParking.currentCost ?? 0).toLocaleString("vi-VN")}đ
                </p>
                <p className="text-xs text-muted-foreground">Chi phí</p>
              </div>
            </div>
          </div>
        )}

        {/* Tab Selector */}
        <div className="flex gap-2 rounded-2xl border border-border bg-muted/50 p-1.5">
          <button
            onClick={() => {
              setActiveTab("check-in");
              resetForm();
            }}
            className={cn(
              "flex-1 flex items-center justify-center gap-2 rounded-xl py-3 font-medium transition-all",
              activeTab === "check-in"
                ? "bg-success text-success-foreground shadow-md"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            <LogIn className="h-4 w-4" />
            Check-in
          </button>
          <button
            onClick={() => {
              setActiveTab("check-out");
              resetForm();
            }}
            className={cn(
              "flex-1 flex items-center justify-center gap-2 rounded-xl py-3 font-medium transition-all",
              activeTab === "check-out"
                ? "bg-primary text-primary-foreground shadow-md"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            <LogOut className="h-4 w-4" />
            Check-out
          </button>
        </div>

        {/* QR Code Section */}
        <div className="rounded-2xl border border-border bg-card p-6 space-y-4">
          <div className="text-center space-y-2">
            <QrCode className="h-10 w-10 mx-auto text-primary" />
            <h2 className="text-lg font-semibold text-foreground">
              {activeTab === "check-in"
                ? "Quét QR để vào bãi"
                : "Quét QR để ra bãi"}
            </h2>
            <p className="text-sm text-muted-foreground">
              Đưa mã QR booking trước camera tại cổng. Hệ thống sẽ tự động nhận
              diện.
            </p>
          </div>

          {/* Show QR for current/upcoming booking */}
          {currentParking && activeTab === "check-out" && (
            <div className="flex justify-center">
              <BookingQRCode
                bookingId={currentParking.booking.id}
                vehicleType={
                  (currentParking.booking.vehicleType as "Car" | "Motorbike") ??
                  "Car"
                }
                licensePlate={currentParking.booking.licensePlate}
                zone={currentParking.booking.zoneName || ""}
                slot={currentParking.booking.slotCode || ""}
                dates={[new Date()]}
                status="confirmed"
              />
            </div>
          )}
        </div>

        {/* Manual Upload Section */}
        <div className="rounded-2xl border border-border bg-card p-6 space-y-4">
          <div className="text-center space-y-2">
            <Camera className="h-10 w-10 mx-auto text-primary" />
            <h2 className="text-lg font-semibold text-foreground">
              {activeTab === "check-in"
                ? "Check-in thủ công"
                : "Check-out thủ công"}
            </h2>
            <p className="text-sm text-muted-foreground">
              Upload ảnh biển số xe để xác minh
            </p>
          </div>

          {/* File Upload */}
          <div className="space-y-3">
            <label
              htmlFor="plate-image"
              className={cn(
                "flex flex-col items-center justify-center rounded-2xl border-2 border-dashed p-8 cursor-pointer transition-all",
                previewUrl
                  ? "border-primary bg-primary/5"
                  : "border-border hover:border-primary/50 hover:bg-muted/50",
              )}
            >
              {previewUrl ? (
                <img
                  src={previewUrl}
                  alt="Ảnh biển số"
                  className="max-h-48 rounded-xl object-contain"
                />
              ) : (
                <>
                  <Upload className="h-10 w-10 text-muted-foreground mb-2" />
                  <p className="text-sm font-medium text-foreground">
                    Chọn ảnh biển số xe
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    JPG, PNG — tối đa 5MB
                  </p>
                </>
              )}
              <input
                id="plate-image"
                type="file"
                accept="image/*"
                capture="environment"
                className="hidden"
                onChange={handleFileSelect}
              />
            </label>

            {selectedFile && (
              <div className="flex gap-3">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={resetForm}
                  disabled={isProcessing}
                >
                  Chọn lại
                </Button>
                <Button
                  className={cn(
                    "flex-1 gap-2",
                    activeTab === "check-in"
                      ? "bg-success hover:bg-success/90"
                      : "gradient-primary",
                  )}
                  onClick={
                    activeTab === "check-in"
                      ? handleManualCheckIn
                      : handleManualCheckOut
                  }
                  disabled={isProcessing}
                >
                  {isProcessing ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : activeTab === "check-in" ? (
                    <LogIn className="h-4 w-4" />
                  ) : (
                    <LogOut className="h-4 w-4" />
                  )}
                  {isProcessing
                    ? "Đang xử lý..."
                    : activeTab === "check-in"
                      ? "Check-in"
                      : "Check-out"}
                </Button>
              </div>
            )}

            {activeTab === "check-in" && (
              <Button
                type="button"
                variant="outline"
                className="w-full gap-2"
                onClick={startQrScan}
              >
                <Camera className="h-4 w-4" />
                Quét QR tự động (DroidCam)
              </Button>
            )}
          </div>
        </div>

        {/* Helpful Tips */}
        <div className="rounded-2xl border border-border bg-muted/30 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-warning shrink-0 mt-0.5" />
            <div className="text-sm space-y-1">
              <p className="font-medium text-foreground">Lưu ý:</p>
              <ul className="text-muted-foreground space-y-1">
                <li>
                  • Hệ thống sẽ tự động nhận diện biển số khi quét QR tại cổng
                </li>
                <li>• Đảm bảo biển số xe rõ ràng, không bị che khuất</li>
                <li>
                  • Nếu check-in thất bại, liên hệ bảo vệ hoặc gọi hotline
                </li>
                {activeTab === "check-out" && (
                  <li>
                    • Thanh toán cần hoàn tất trước khi check-out (trừ gói
                    &ldquo;thanh toán khi ra&rdquo;)
                  </li>
                )}
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* Result Dialog */}
      <Dialog open={showResultDialog} onOpenChange={setShowResultDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {manualResult?.success
                ? activeTab === "check-in"
                  ? "Check-in thành công!"
                  : "Check-out thành công!"
                : "Thao tác thất bại"}
            </DialogTitle>
          </DialogHeader>
          <div className="text-center space-y-4 py-4">
            {manualResult?.success ? (
              <CheckCircle2 className="h-16 w-16 mx-auto text-success" />
            ) : (
              <XCircle className="h-16 w-16 mx-auto text-destructive" />
            )}
            <p className="text-muted-foreground">{manualResult?.message}</p>
            {manualResult?.plateText && (
              <div className="inline-flex items-center gap-2 rounded-xl bg-muted border border-border px-4 py-2">
                <Car className="h-4 w-4 text-primary" />
                <span className="font-mono font-bold text-foreground">
                  {manualResult.plateText}
                </span>
              </div>
            )}
          </div>
          <div className="flex gap-3">
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => {
                setShowResultDialog(false);
                resetForm();
              }}
            >
              Đóng
            </Button>
            {manualResult?.success && (
              <Button
                className="flex-1 gradient-primary"
                onClick={() => {
                  setShowResultDialog(false);
                  navigate(activeTab === "check-in" ? "/" : "/history");
                }}
              >
                <ArrowRight className="h-4 w-4 mr-2" />
                {activeTab === "check-in" ? "Về trang chủ" : "Xem lịch sử"}
              </Button>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* QR Scan Modal */}
      {isQrModalOpen && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(0,0,0,0.7)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget) stopQrScan();
          }}
        >
          <div
            style={{
              background: "#1e1e2e",
              borderRadius: "12px",
              padding: "24px",
              maxWidth: "480px",
              width: "90%",
              color: "#fff",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "16px",
              }}
            >
              <h3 style={{ margin: 0 }}>📷 Quét mã QR Booking</h3>
              <button
                onClick={stopQrScan}
                style={{
                  background: "none",
                  border: "none",
                  color: "#fff",
                  fontSize: "20px",
                  cursor: "pointer",
                }}
              >
                ✕
              </button>
            </div>

            {/* DroidCam live stream */}
            <div
              style={{
                position: "relative",
                borderRadius: "8px",
                overflow: "hidden",
                marginBottom: "16px",
              }}
            >
              <img
                src="/ai/cameras/stream?camera_id=qr-camera-droidcam&fps=5"
                alt="DroidCam Stream"
                style={{ width: "100%", display: "block" }}
                onError={(e) => {
                  (e.target as HTMLImageElement).alt =
                    "⚠️ Không kết nối được camera";
                }}
              />
              {qrScanStatus === "scanning" && (
                <div
                  style={{
                    position: "absolute",
                    bottom: "8px",
                    left: "50%",
                    transform: "translateX(-50%)",
                    background: "rgba(0,0,0,0.6)",
                    color: "#fff",
                    padding: "4px 12px",
                    borderRadius: "16px",
                    fontSize: "13px",
                  }}
                >
                  🔍 Đang quét QR...
                </div>
              )}
            </div>

            {qrScanStatus === "found" && scannedQrData && (
              <div
                style={{
                  background: "#2a2a3e",
                  borderRadius: "8px",
                  padding: "12px",
                  marginBottom: "16px",
                }}
              >
                <p
                  style={{
                    margin: "0 0 4px",
                    fontSize: "13px",
                    color: "#a0a0b0",
                  }}
                >
                  QR đã nhận diện:
                </p>
                <p
                  style={{
                    margin: 0,
                    fontSize: "12px",
                    wordBreak: "break-all",
                    color: "#4ade80",
                  }}
                >
                  {scannedQrData.length > 120
                    ? scannedQrData.slice(0, 120) + "..."
                    : scannedQrData}
                </p>
              </div>
            )}

            {qrCheckInResult && (
              <div
                style={{
                  background: qrCheckInResult.success ? "#14532d" : "#7f1d1d",
                  borderRadius: "8px",
                  padding: "12px",
                  marginBottom: "16px",
                  color: qrCheckInResult.success ? "#4ade80" : "#fca5a5",
                }}
              >
                {qrCheckInResult.success ? "✅ " : "❌ "}
                {qrCheckInResult.message}
                {qrCheckInResult.success && (
                  <p
                    style={{
                      margin: "4px 0 0",
                      fontSize: "12px",
                      opacity: 0.8,
                    }}
                  >
                    Xe sẽ xuất hiện tự động trong Unity Simulation
                  </p>
                )}
              </div>
            )}

            <div
              style={{
                display: "flex",
                gap: "8px",
                justifyContent: "flex-end",
              }}
            >
              {qrScanStatus === "found" && !qrCheckInResult && (
                <button
                  onClick={confirmQrCheckIn}
                  disabled={qrCheckInLoading}
                  style={{
                    background: "#4f46e5",
                    color: "#fff",
                    border: "none",
                    borderRadius: "6px",
                    padding: "8px 20px",
                    cursor: "pointer",
                    fontWeight: 600,
                  }}
                >
                  {qrCheckInLoading
                    ? "⏳ Đang xử lý..."
                    : "✅ Xác nhận Check-in"}
                </button>
              )}
              <button
                onClick={stopQrScan}
                style={{
                  background: "#374151",
                  color: "#fff",
                  border: "none",
                  borderRadius: "6px",
                  padding: "8px 20px",
                  cursor: "pointer",
                }}
              >
                Đóng
              </button>
            </div>
          </div>
        </div>
      )}
    </MainLayout>
  );
}
