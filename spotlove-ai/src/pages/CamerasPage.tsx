import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { MainLayout } from "@/components/layout/MainLayout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Camera,
  Video,
  VideoOff,
  Maximize2,
  Grid3X3,
  LayoutGrid,
  ChevronDown,
  Circle,
  Car,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Lock,
  AlertCircle,
  Loader2,
  Wifi,
  WifiOff,
  Radio,
  Globe,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/use-auth";
import { adminApi, bookingApi, parkingApi } from "@/services";
import { useToast } from "@/hooks/use-toast";
import { mapBookingResponse } from "@/store/slices/bookingSlice";

interface CameraFeed {
  id: string;
  name: string;
  zone: string;
  floor: number;
  isOnline: boolean;
  vehicleCount: number;
  streamUrl?: string;
  /** Raw stream URL from backend (before proxy resolution) */
  rawStreamUrl?: string;
  ipAddress?: string;
  port?: number;
}

interface UserVehicle {
  id: string;
  licensePlate: string;
  zone: string;
  slot: string;
  cameraId: string;
}

type ViewMode = "grid" | "single";
type StreamType = "rtsp" | "http" | "proxy";

// ── Stream URL helpers ─────────────────────────────────────────────────── //

/** Check whether a URL is an RTSP stream */
const isRtspUrl = (url: string): boolean => url.startsWith("rtsp://");

/** Check whether a URL is already proxied through the AI service */
const isProxiedUrl = (url: string): boolean => url.startsWith("/ai/cameras/");

/**
 * Resolve the display-ready stream URL.
 * - Already proxied (`/ai/cameras/…`): use as-is
 * - RTSP: proxy through AI service MJPEG endpoint
 * - HTTP: use directly (MJPEG / DroidCam streams work in `<img>`)
 */
const getDisplayStreamUrl = (streamUrl: string | undefined): string | null => {
  if (!streamUrl) return null;
  if (isProxiedUrl(streamUrl)) return streamUrl;
  if (isRtspUrl(streamUrl)) {
    return `/ai/cameras/stream?url=${encodeURIComponent(streamUrl)}&fps=3`;
  }
  return streamUrl;
};

/** Determine stream type for badge / UI logic */
const getStreamType = (streamUrl: string | undefined): StreamType => {
  if (!streamUrl) return "http";
  if (isProxiedUrl(streamUrl)) return "proxy";
  if (isRtspUrl(streamUrl)) return "rtsp";
  return "http";
};

// ── Hardcoded monitoring cameras from AI service ─────────────────────────── //
const MONITORING_CAMERAS: CameraFeed[] = [
  {
    id: "plate-camera-ezviz",
    name: "Camera Biển Số (EZVIZ)",
    zone: "Cổng vào",
    floor: 1,
    isOnline: true,
    vehicleCount: 0,
    streamUrl: "/ai/cameras/stream?camera_id=plate-camera-ezviz&fps=3",
  },
  {
    id: "qr-camera-droidcam",
    name: "Camera QR Code (DroidCam)",
    zone: "Cổng vào",
    floor: 1,
    isOnline: true,
    vehicleCount: 0,
    streamUrl: "/ai/cameras/stream?camera_id=qr-camera-droidcam&fps=3",
  },
];

export default function CamerasPage() {
  const { user } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const isAdmin = user?.role === "admin";

  const [cameras, setCameras] = useState<CameraFeed[]>([]);
  const [userVehicles, setUserVehicles] = useState<UserVehicle[]>([]);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [selectedCamera, setSelectedCamera] = useState<CameraFeed | null>(null);
  const [selectedFloor, setSelectedFloor] = useState<number | "all">("all");
  const [showFullscreen, setShowFullscreen] = useState(false);
  const [trackingVehicle, setTrackingVehicle] = useState<UserVehicle | null>(
    null,
  );
  /** Track cameras whose stream failed to load */
  const [streamErrors, setStreamErrors] = useState<Set<string>>(new Set());

  /** Mark a camera stream as errored */
  const handleStreamError = useCallback((cameraId: string) => {
    setStreamErrors((prev) => {
      if (prev.has(cameraId)) return prev;
      const next = new Set(prev);
      next.add(cameraId);
      return next;
    });
  }, []);

  // Fetch cameras (admin) or user parking (regular user)
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        if (isAdmin) {
          // Admin: Fetch all cameras from backend + merge monitoring cameras
          let backendCameras: CameraFeed[] = [];
          try {
            const response = await adminApi.getCameras();
            backendCameras = response.results.map((cam) => ({
              id: cam.id,
              name: cam.name,
              zone: cam.zone || "",
              floor: 1,
              isOnline: cam.isActive !== false,
              vehicleCount: 0,
              rawStreamUrl: cam.streamUrl,
              streamUrl: cam.streamUrl,
              ipAddress: cam.ipAddress,
              port: cam.port,
            }));
          } catch {
            // Backend cameras API might fail, that's OK
          }
          // Merge: monitoring cameras first, then backend ones (dedup by id)
          const existingIds = new Set(MONITORING_CAMERAS.map((c) => c.id));
          const merged = [
            ...MONITORING_CAMERAS,
            ...backendCameras.filter((c) => !existingIds.has(c.id)),
          ];
          setCameras(merged);
        } else {
          // Regular user: Fetch current parking + show monitoring cameras
          let parkingCameras: CameraFeed[] = [];
          let vehicles: UserVehicle[] = [];

          try {
            const parking = await bookingApi.getCurrentParking();
            if (parking && parking.booking) {
              const mapped = mapBookingResponse(parking.booking as never);
              const slotId = mapped.slotId;
              const zoneName = mapped.zoneName || "";
              const slotCode = mapped.slotCode || "";
              const licensePlate = mapped.licensePlate || "";

              let cameraId = "";
              let cameraName = `Camera ${zoneName}`;
              const floorLevel = 1;
              let streamUrl: string | undefined;
              const isOnline = true;

              if (slotId) {
                try {
                  const slotData = await parkingApi.getSlot(slotId);
                  if (slotData.cameraId) {
                    cameraId = slotData.cameraId;
                    cameraName = `Camera Slot ${slotCode}`;
                  }
                } catch (e) {
                  console.warn("Could not fetch slot camera:", e);
                }
              }

              if (!cameraId) {
                cameraId = `camera-zone-${mapped.zoneId || "unknown"}`;
                cameraName = `Camera ${zoneName}`;
              }

              vehicles = [
                {
                  id: mapped.id,
                  licensePlate,
                  zone: zoneName,
                  slot: slotCode,
                  cameraId,
                },
              ];

              parkingCameras = [
                {
                  id: cameraId,
                  name: cameraName,
                  zone: zoneName,
                  floor: floorLevel,
                  isOnline,
                  vehicleCount: 1,
                  streamUrl,
                },
              ];
            }
          } catch {
            // No active parking, that's fine
          }

          setUserVehicles(vehicles);
          // User sees: their parking camera + monitoring cameras
          const existingIds = new Set(parkingCameras.map((c) => c.id));
          const merged = [
            ...parkingCameras,
            ...MONITORING_CAMERAS.filter((c) => !existingIds.has(c.id)),
          ];
          setCameras(merged);
        }
      } catch (error) {
        console.error("Failed to fetch camera data:", error);
        setCameras(MONITORING_CAMERAS); // Fallback to monitoring cameras
        setUserVehicles([]);
        toast({
          title: "Lỗi",
          description: "Không thể tải dữ liệu camera. Vui lòng thử lại sau.",
          variant: "destructive",
        });
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [isAdmin, toast]);

  // Filter cameras based on role and floor
  const monitoringCameraIds = new Set(MONITORING_CAMERAS.map((c) => c.id));
  const userCameraIds = userVehicles.map((v) => v.cameraId);
  const accessibleCameras = isAdmin
    ? cameras
    : cameras.filter(
        (c) => userCameraIds.includes(c.id) || monitoringCameraIds.has(c.id),
      );

  const filteredCameras = accessibleCameras.filter(
    (camera) => selectedFloor === "all" || camera.floor === selectedFloor,
  );

  const handleTrackVehicle = (vehicle: UserVehicle) => {
    const camera = cameras.find((c) => c.id === vehicle.cameraId);
    if (camera) {
      setTrackingVehicle(vehicle);
      setSelectedCamera(camera);
      setShowFullscreen(true);
    }
  };

  // Loading state
  if (loading) {
    return (
      <MainLayout>
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-3" />
            <p className="text-muted-foreground">Đang tải camera...</p>
          </div>
        </div>
      </MainLayout>
    );
  }

  // If user has no parked vehicles AND no monitoring cameras, show empty state
  if (!isAdmin && userVehicles.length === 0 && cameras.length === 0) {
    return (
      <MainLayout>
        <div className="space-y-6">
          <div className="animate-fade-in">
            <h1 className="text-2xl font-bold text-foreground">
              Camera Tracking
            </h1>
            <p className="mt-1 text-muted-foreground">
              Theo dõi trực tiếp xe của bạn
            </p>
          </div>

          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-muted">
              <Lock className="h-10 w-10 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold text-foreground">
              Không có xe đang đậu
            </h3>
            <p className="mt-2 max-w-sm text-muted-foreground">
              Bạn chỉ có thể xem camera khi có xe đang đậu tại bãi. Hãy đặt chỗ
              để bắt đầu theo dõi xe của bạn.
            </p>
            <Button
              className="mt-6 gradient-primary"
              onClick={() => (window.location.href = "/booking")}
            >
              <Car className="h-4 w-4 mr-2" />
              Đặt chỗ ngay
            </Button>
          </div>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between animate-fade-in">
          <div>
            <h1 className="text-2xl font-bold text-foreground">
              Camera Tracking
            </h1>
            <p className="mt-1 text-muted-foreground">
              {isAdmin
                ? "Theo dõi trực tiếp tất cả các zone đậu xe"
                : "Theo dõi trực tiếp xe của bạn"}
            </p>
          </div>

          {isAdmin && (
            <div className="flex items-center gap-3">
              {/* Camera Management Link */}
              <Button
                variant="outline"
                size="sm"
                className="gap-2"
                onClick={() => navigate("/admin/cameras")}
              >
                <Settings className="h-4 w-4" />
                Quản lý
              </Button>

              {/* Floor Filter - Only for Admin */}
              <div className="relative">
                <select
                  value={selectedFloor}
                  onChange={(e) =>
                    setSelectedFloor(
                      e.target.value === "all" ? "all" : Number(e.target.value),
                    )
                  }
                  className="appearance-none rounded-xl border border-border bg-card px-4 py-2 pr-10 text-sm font-medium focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                >
                  <option value="all">Tất cả tầng</option>
                  <option value="1">Tầng 1</option>
                  <option value="2">Tầng 2</option>
                  <option value="3">Tầng 3</option>
                </select>
                <ChevronDown className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground pointer-events-none" />
              </div>

              {/* View Mode Toggle */}
              <div className="flex rounded-xl border border-border bg-card p-1">
                <Button
                  variant={viewMode === "grid" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setViewMode("grid")}
                  className="px-3"
                >
                  <Grid3X3 className="h-4 w-4" />
                </Button>
                <Button
                  variant={viewMode === "single" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setViewMode("single")}
                  className="px-3"
                >
                  <LayoutGrid className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* User's Parked Vehicles - Quick Access */}
        {userVehicles.length > 0 && (
          <div className="rounded-2xl border-2 border-primary/20 bg-primary/5 p-3 sm:p-4">
            <div className="flex items-center gap-2 mb-3">
              <Car className="h-5 w-5 text-primary shrink-0" />
              <h3 className="font-semibold text-foreground text-sm sm:text-base">
                {isAdmin ? "Xe đang đậu" : "Xe của bạn đang đậu"}
              </h3>
            </div>
            <div className="flex flex-wrap gap-2 sm:gap-3">
              {userVehicles.map((vehicle) => (
                <Button
                  key={vehicle.id}
                  variant="outline"
                  size="sm"
                  className="gap-2 bg-background text-xs sm:text-sm"
                  onClick={() => handleTrackVehicle(vehicle)}
                >
                  <Video className="h-3 w-3 sm:h-4 sm:w-4 text-primary" />
                  <span className="font-mono font-bold">
                    {vehicle.licensePlate}
                  </span>
                  <Badge
                    variant="secondary"
                    className="text-[10px] sm:text-xs hidden sm:inline-flex"
                  >
                    {vehicle.zone} - {vehicle.slot}
                  </Badge>
                </Button>
              ))}
            </div>
          </div>
        )}

        {/* Stats - Only for Admin */}
        {isAdmin && (
          <div className="grid gap-3 grid-cols-1 sm:grid-cols-3">
            <div className="rounded-xl border border-border bg-card p-3 sm:p-4 flex items-center gap-3 sm:gap-4">
              <div className="flex h-10 w-10 sm:h-12 sm:w-12 items-center justify-center rounded-xl bg-success/10 shrink-0">
                <Video className="h-5 w-5 sm:h-6 sm:w-6 text-success" />
              </div>
              <div className="min-w-0">
                <p className="text-xl sm:text-2xl font-bold text-foreground">
                  {cameras.filter((c) => c.isOnline).length}
                </p>
                <p className="text-xs sm:text-sm text-muted-foreground truncate">
                  Camera online
                </p>
              </div>
            </div>
            <div className="rounded-xl border border-border bg-card p-3 sm:p-4 flex items-center gap-3 sm:gap-4">
              <div className="flex h-10 w-10 sm:h-12 sm:w-12 items-center justify-center rounded-xl bg-destructive/10 shrink-0">
                <VideoOff className="h-5 w-5 sm:h-6 sm:w-6 text-destructive" />
              </div>
              <div className="min-w-0">
                <p className="text-xl sm:text-2xl font-bold text-foreground">
                  {cameras.filter((c) => !c.isOnline).length}
                </p>
                <p className="text-xs sm:text-sm text-muted-foreground truncate">
                  Camera offline
                </p>
              </div>
            </div>
            <div className="rounded-xl border border-border bg-card p-3 sm:p-4 flex items-center gap-3 sm:gap-4">
              <div className="flex h-10 w-10 sm:h-12 sm:w-12 items-center justify-center rounded-xl bg-primary/10 shrink-0">
                <Camera className="h-5 w-5 sm:h-6 sm:w-6 text-primary" />
              </div>
              <div className="min-w-0">
                <p className="text-xl sm:text-2xl font-bold text-foreground">
                  {cameras.reduce((sum, c) => sum + c.vehicleCount, 0)}
                </p>
                <p className="text-xs sm:text-sm text-muted-foreground truncate">
                  Xe đang tracking
                </p>
              </div>
            </div>
          </div>
        )}

        {/* User-specific info banner */}
        {!isAdmin && (
          <div className="flex items-start gap-3 rounded-xl bg-muted/50 border border-border p-4">
            <AlertCircle className="h-5 w-5 text-muted-foreground shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-muted-foreground">
                Bạn chỉ có thể xem camera tại vị trí xe của bạn đang đậu. Để xem
                toàn bộ hệ thống camera, vui lòng liên hệ quản trị viên.
              </p>
            </div>
          </div>
        )}

        {/* Camera Grid */}
        <div
          className={cn(
            "grid gap-4",
            viewMode === "grid"
              ? "sm:grid-cols-2 lg:grid-cols-3"
              : "grid-cols-1",
          )}
        >
          {filteredCameras.map((camera) => {
            const streamType = getStreamType(camera.streamUrl);
            const displayUrl = getDisplayStreamUrl(camera.streamUrl);
            const hasError = streamErrors.has(camera.id);

            return (
              <div
                key={camera.id}
                className={cn(
                  "group relative overflow-hidden rounded-2xl border border-border bg-card transition-all duration-300 hover:border-primary/50 hover:shadow-lg animate-slide-up",
                  selectedCamera?.id === camera.id && "ring-2 ring-primary",
                )}
              >
                {/* Camera Feed — Live stream or placeholder */}
                <div className="relative aspect-video bg-gradient-to-br from-muted to-muted/50">
                  {camera.isOnline ? (
                    <>
                      {displayUrl && !hasError ? (
                        <img
                          src={displayUrl}
                          alt={`Live feed: ${camera.name}`}
                          className="absolute inset-0 w-full h-full object-cover"
                          data-testid={`camera-stream-${camera.id}`}
                          onError={() => handleStreamError(camera.id)}
                        />
                      ) : hasError ? (
                        /* Stream load failed — show error placeholder */
                        <div className="absolute inset-0 flex items-center justify-center">
                          <div className="text-center px-4">
                            <WifiOff className="mx-auto h-10 w-10 text-amber-500/70" />
                            <p className="mt-2 text-sm font-medium text-amber-600 dark:text-amber-400">
                              Không thể tải luồng video
                            </p>
                            <p className="mt-1 text-xs text-muted-foreground">
                              Camera có thể đang offline hoặc không khả dụng
                            </p>
                            <Button
                              variant="outline"
                              size="sm"
                              className="mt-3 text-xs"
                              onClick={() => {
                                setStreamErrors((prev) => {
                                  const next = new Set(prev);
                                  next.delete(camera.id);
                                  return next;
                                });
                              }}
                            >
                              <RotateCcw className="h-3 w-3 mr-1" />
                              Thử lại
                            </Button>
                          </div>
                        </div>
                      ) : (
                        /* No stream URL available */
                        <div className="absolute inset-0 flex items-center justify-center">
                          <div className="text-center">
                            <Video className="mx-auto h-12 w-12 text-muted-foreground/50" />
                            <p className="mt-2 text-sm text-muted-foreground">
                              Chưa có luồng video
                            </p>
                          </div>
                        </div>
                      )}

                      {/* Stream type badge — top-left alongside REC indicator */}
                      <div className="absolute left-3 top-3 flex items-center gap-2">
                        <div className="flex items-center gap-2 rounded-full bg-destructive/90 px-2 py-1">
                          <Circle className="h-2 w-2 fill-current animate-pulse" />
                          <span className="text-xs font-medium text-destructive-foreground">
                            REC
                          </span>
                        </div>
                        {streamType === "rtsp" || streamType === "proxy" ? (
                          <Badge className="bg-violet-600/90 hover:bg-violet-600 text-white text-[10px] px-1.5 py-0.5">
                            <Radio className="h-3 w-3 mr-1" />
                            RTSP
                          </Badge>
                        ) : (
                          <Badge className="bg-emerald-600/90 hover:bg-emerald-600 text-white text-[10px] px-1.5 py-0.5">
                            <Globe className="h-3 w-3 mr-1" />
                            Trực tiếp
                          </Badge>
                        )}
                      </div>

                      {/* Fullscreen button */}
                      <Button
                        variant="ghost"
                        size="icon"
                        className="absolute right-3 top-3 h-8 w-8 bg-background/80 opacity-0 transition-opacity group-hover:opacity-100"
                        onClick={() => {
                          setSelectedCamera(camera);
                          setTrackingVehicle(
                            userVehicles.find(
                              (v) => v.cameraId === camera.id,
                            ) || null,
                          );
                          setShowFullscreen(true);
                        }}
                      >
                        <Maximize2 className="h-4 w-4" />
                      </Button>
                    </>
                  ) : (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="text-center">
                        <VideoOff className="mx-auto h-12 w-12 text-destructive/50" />
                        <p className="mt-2 text-sm text-destructive">Offline</p>
                      </div>
                    </div>
                  )}
                </div>

                {/* Camera Info */}
                <div className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="min-w-0">
                      <p className="font-semibold text-foreground truncate">
                        {camera.name}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        Tầng {camera.floor} - {camera.zone}
                      </p>
                    </div>
                    <Badge
                      variant={camera.isOnline ? "default" : "destructive"}
                      className={cn(
                        "shrink-0 ml-2",
                        camera.isOnline ? "bg-success/10 text-success" : "",
                      )}
                    >
                      {camera.isOnline ? (
                        <>
                          <Wifi className="h-3 w-3 mr-1" />
                          Online
                        </>
                      ) : (
                        <>
                          <WifiOff className="h-3 w-3 mr-1" />
                          Offline
                        </>
                      )}
                    </Badge>
                  </div>

                  {/* Camera metadata (admin) */}
                  {isAdmin && (
                    <div className="mt-3 space-y-1.5 text-xs text-muted-foreground">
                      {camera.ipAddress && (
                        <div className="flex items-center gap-1.5">
                          <span className="font-medium text-foreground/70">
                            IP:
                          </span>
                          <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px]">
                            {camera.ipAddress}
                            {camera.port ? `:${camera.port}` : ""}
                          </code>
                        </div>
                      )}
                      {camera.rawStreamUrl && (
                        <div className="flex items-center gap-1.5 min-w-0">
                          <span className="font-medium text-foreground/70 shrink-0">
                            URL:
                          </span>
                          <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px] truncate">
                            {isRtspUrl(camera.rawStreamUrl)
                              ? camera.rawStreamUrl.replace(
                                  /\/\/[^@]+@/,
                                  "//***@",
                                )
                              : camera.rawStreamUrl}
                          </code>
                        </div>
                      )}
                    </div>
                  )}

                  {camera.isOnline && isAdmin && (
                    <div className="mt-3 flex items-center gap-2 text-sm">
                      <span className="text-muted-foreground">
                        Đang tracking:
                      </span>
                      <span className="font-semibold text-primary">
                        {camera.vehicleCount} xe
                      </span>
                    </div>
                  )}
                  {!isAdmin && (
                    <div className="mt-3">
                      <Badge
                        className={cn(
                          monitoringCameraIds.has(camera.id)
                            ? "bg-blue-500/10 text-blue-600"
                            : "bg-primary/10 text-primary",
                        )}
                      >
                        {monitoringCameraIds.has(camera.id)
                          ? "📹 Camera giám sát"
                          : "Vị trí xe của bạn"}
                      </Badge>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Empty State */}
        {filteredCameras.length === 0 && isAdmin && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-muted">
              <Camera className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold text-foreground">
              Không có camera
            </h3>
            <p className="mt-1 text-muted-foreground">
              Không tìm thấy camera cho tầng đã chọn
            </p>
          </div>
        )}
      </div>

      {/* Fullscreen Camera Dialog */}
      <Dialog open={showFullscreen} onOpenChange={setShowFullscreen}>
        <DialogContent className="max-w-4xl w-[95vw] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-2 flex-wrap">
                <Video className="h-5 w-5 text-primary shrink-0" />
                <span className="truncate">{selectedCamera?.name}</span>
                {trackingVehicle && (
                  <Badge className="bg-primary/10 text-primary">
                    Tracking: {trackingVehicle.licensePlate}
                  </Badge>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <ZoomIn className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <ZoomOut className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <RotateCcw className="h-4 w-4" />
                </Button>
              </div>
            </DialogTitle>
          </DialogHeader>

          <div className="relative aspect-video rounded-xl overflow-hidden bg-gradient-to-br from-muted to-muted/50">
            {selectedCamera?.isOnline ? (
              <>
                {(() => {
                  const fullscreenUrl = getDisplayStreamUrl(
                    selectedCamera.streamUrl,
                  );
                  const fullscreenHasError = streamErrors.has(
                    selectedCamera.id,
                  );

                  if (fullscreenUrl && !fullscreenHasError) {
                    return (
                      <img
                        src={fullscreenUrl}
                        alt={`Live feed: ${selectedCamera.name}`}
                        className="absolute inset-0 w-full h-full object-cover"
                        data-testid={`fullscreen-stream-${selectedCamera.id}`}
                        onError={() => handleStreamError(selectedCamera.id)}
                      />
                    );
                  }
                  if (fullscreenHasError) {
                    return (
                      <div className="absolute inset-0 flex items-center justify-center">
                        <div className="text-center p-4">
                          <WifiOff className="mx-auto h-14 w-14 text-amber-500/70" />
                          <p className="mt-3 text-base font-medium text-amber-600 dark:text-amber-400">
                            Không thể tải luồng video
                          </p>
                          <p className="mt-1 text-sm text-muted-foreground">
                            Camera có thể đang offline hoặc không khả dụng
                          </p>
                          <Button
                            variant="outline"
                            size="sm"
                            className="mt-4"
                            onClick={() => {
                              setStreamErrors((prev) => {
                                const next = new Set(prev);
                                next.delete(selectedCamera.id);
                                return next;
                              });
                            }}
                          >
                            <RotateCcw className="h-4 w-4 mr-2" />
                            Thử lại
                          </Button>
                        </div>
                      </div>
                    );
                  }
                  return (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="text-center p-4">
                        <Video className="mx-auto h-12 w-12 sm:h-20 sm:w-20 text-muted-foreground/50" />
                        <p className="mt-2 sm:mt-4 text-sm sm:text-lg text-muted-foreground">
                          Live Feed - {selectedCamera.zone}
                        </p>
                      </div>
                    </div>
                  );
                })()}
                {trackingVehicle && (
                  <div className="absolute bottom-4 left-4 p-3 sm:p-4 rounded-xl bg-background/80 inline-block">
                    <p className="text-xs sm:text-sm text-muted-foreground">
                      Đang theo dõi xe
                    </p>
                    <p className="text-lg sm:text-2xl font-mono font-bold text-primary">
                      {trackingVehicle.licensePlate}
                    </p>
                    <p className="text-xs sm:text-sm text-muted-foreground">
                      Vị trí: {trackingVehicle.slot}
                    </p>
                  </div>
                )}
                <div className="absolute left-2 sm:left-4 top-2 sm:top-4 flex items-center gap-1.5 sm:gap-2 rounded-full bg-destructive/90 px-2 sm:px-3 py-1 sm:py-1.5">
                  <Circle className="h-1.5 w-1.5 sm:h-2 sm:w-2 fill-current animate-pulse" />
                  <span className="text-xs sm:text-sm font-medium text-destructive-foreground">
                    LIVE
                  </span>
                </div>
              </>
            ) : (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-center p-4">
                  <VideoOff className="mx-auto h-12 w-12 sm:h-20 sm:w-20 text-destructive/50" />
                  <p className="mt-2 sm:mt-4 text-sm sm:text-lg text-destructive">
                    Camera Offline
                  </p>
                </div>
              </div>
            )}
          </div>

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between p-3 sm:p-4 bg-muted/50 rounded-xl">
            <div>
              <p className="text-xs sm:text-sm text-muted-foreground">
                Tầng {selectedCamera?.floor} - {selectedCamera?.zone}
              </p>
              {isAdmin && (
                <p className="text-sm sm:text-base font-semibold">
                  Đang tracking: {selectedCamera?.vehicleCount} xe
                </p>
              )}
              {!isAdmin && trackingVehicle && (
                <p className="text-sm sm:text-base font-semibold">
                  Vị trí: {trackingVehicle.slot}
                </p>
              )}
            </div>
            <Badge
              variant="outline"
              className="bg-success/10 text-success w-fit"
            >
              <Circle className="h-2 w-2 fill-current mr-2" />
              Online
            </Badge>
          </div>
        </DialogContent>
      </Dialog>
    </MainLayout>
  );
}
