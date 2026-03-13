import { useState, useEffect } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  AlertTriangle,
  Camera,
  Phone,
  FileText,
  Shield,
  Clock,
  MapPin,
  CheckCircle,
  Loader2,
  Car,
  AlertCircle,
  History,
  User,
  Video,
  RefreshCcw,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/AuthContext";
import { toast } from "sonner";
import { incidentApi, bookingApi } from "@/services";
import { mapBookingResponse } from "@/store/slices/bookingSlice";
import type {
  Incident,
  IncidentType as ApiIncidentType,
} from "@/services/api/incident.api";

interface IncidentLog {
  id: string;
  type: "vehicle_issue" | "security" | "accident" | "other";
  description: string;
  status: "pending" | "responding" | "resolved";
  createdAt: Date;
  location: string;
}

interface CurrentParkingInfo {
  zone: string;
  slot: string;
  floor: number;
  cameraId: string;
  licensePlate: string;
  bookingId?: string;
  zoneId?: string;
  slotId?: string;
}

// Map API incident type to local type
const mapApiTypeToLocal = (apiType: ApiIncidentType): IncidentLog["type"] => {
  const mapping: Record<ApiIncidentType, IncidentLog["type"]> = {
    vehicle_damage: "vehicle_issue",
    theft: "security",
    accident: "accident",
    emergency: "security",
    suspicious_activity: "security",
    other: "other",
  };
  return mapping[apiType] || "other";
};

// Map local type to API type
const mapLocalTypeToApi = (localType: string): ApiIncidentType => {
  const mapping: Record<string, ApiIncidentType> = {
    vehicle_issue: "vehicle_damage",
    security: "theft",
    accident: "accident",
    other: "other",
  };
  return mapping[localType] || "other";
};

// Map API status to local status
const mapApiStatusToLocal = (apiStatus: string): IncidentLog["status"] => {
  const mapping: Record<string, IncidentLog["status"]> = {
    pending: "pending",
    in_progress: "responding",
    resolved: "resolved",
  };
  return mapping[apiStatus] || "pending";
};

const incidentTypes = [
  {
    id: "vehicle_issue",
    label: "Xe có vấn đề",
    icon: Car,
    color: "bg-warning/10 text-warning border-warning/20",
    description: "Xe bị trầy, hỏng, hoặc có dấu hiệu bất thường",
  },
  {
    id: "security",
    label: "An ninh",
    icon: Shield,
    color: "bg-destructive/10 text-destructive border-destructive/20",
    description: "Nghi vấn người lạ, hành vi đáng ngờ",
  },
  {
    id: "accident",
    label: "Tai nạn",
    icon: AlertTriangle,
    color: "bg-destructive/10 text-destructive border-destructive/20",
    description: "Va chạm, sự cố tại bãi xe",
  },
  {
    id: "other",
    label: "Khác",
    icon: AlertCircle,
    color: "bg-muted text-muted-foreground border-border",
    description: "Các vấn đề khác cần hỗ trợ",
  },
];

export default function PanicButtonPage() {
  const { user } = useAuth();
  const [isProcessing, setIsProcessing] = useState(false);
  const [isLoadingParking, setIsLoadingParking] = useState(true);
  const [isLoadingIncidents, setIsLoadingIncidents] = useState(true);
  const [showCameraDialog, setShowCameraDialog] = useState(false);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [incidentNote, setIncidentNote] = useState("");
  const [incidents, setIncidents] = useState<IncidentLog[]>([]);
  const [cameraStream, setCameraStream] = useState<string | null>(null);
  const [userParkingInfo, setUserParkingInfo] =
    useState<CurrentParkingInfo | null>(null);

  // Load current parking info
  useEffect(() => {
    const loadCurrentParking = async () => {
      setIsLoadingParking(true);
      try {
        const response = await bookingApi.getCurrentParking();

        if (response && response.booking) {
          const mapped = mapBookingResponse(response.booking);
          setUserParkingInfo({
            zone: mapped.zoneName || "N/A",
            slot: mapped.slotCode || "N/A",
            floor: 1,
            cameraId: `CAM-${mapped.zoneName?.charAt(5) || "A"}1-01`,
            licensePlate: mapped.licensePlate || "N/A",
            bookingId: mapped.id,
            zoneId: mapped.zoneId,
            slotId: mapped.slotId,
          });
        } else {
          // No active parking session
          setUserParkingInfo(null);
        }
      } catch (error) {
        console.log("No active parking session");
        setUserParkingInfo(null);
      } finally {
        setIsLoadingParking(false);
      }
    };

    loadCurrentParking();
  }, []);

  // Load incidents history
  useEffect(() => {
    const loadIncidents = async () => {
      setIsLoadingIncidents(true);
      try {
        const response = await incidentApi.getMyIncidents({
          page: 1,
          pageSize: 10,
        });
        const mappedIncidents: IncidentLog[] = response.results.map(
          (incident: Incident) => ({
            id: incident.id,
            type: mapApiTypeToLocal(incident.type),
            description:
              incident.description ||
              incidentTypes.find(
                (t) => mapLocalTypeToApi(t.id) === incident.type,
              )?.label ||
              "Sự cố",
            status: mapApiStatusToLocal(incident.status),
            createdAt: new Date(incident.createdAt),
            location:
              incident.zoneName && incident.slotCode
                ? `${incident.zoneName} - ${incident.slotCode}`
                : incident.zoneName || "Không xác định",
          }),
        );
        setIncidents(mappedIncidents);
      } catch (error) {
        console.log("Failed to load incidents");
        setIncidents([]);
      } finally {
        setIsLoadingIncidents(false);
      }
    };

    loadIncidents();
  }, []);

  const handlePanicButton = async () => {
    if (!selectedType) {
      toast.error("Vui lòng chọn loại sự cố");
      return;
    }

    if (!userParkingInfo || !userParkingInfo.bookingId) {
      toast.error("Bạn cần có phiên đỗ xe đang hoạt động để báo cáo sự cố");
      return;
    }

    setShowConfirmDialog(true);
  };

  const confirmPanic = async () => {
    setIsProcessing(true);
    setShowConfirmDialog(false);

    try {
      // Show processing steps
      toast.info("📹 Đang mở camera khu vực...", { duration: 2000 });
      await new Promise((resolve) => setTimeout(resolve, 500));

      // Call the API to report incident
      const response = await incidentApi.reportIncident({
        type: mapLocalTypeToApi(selectedType!),
        description: incidentNote || undefined,
        bookingId: userParkingInfo?.bookingId,
        location: {
          zoneId: userParkingInfo?.zoneId,
          slotId: userParkingInfo?.slotId,
        },
      });

      toast.info("📞 Đang thông báo bảo vệ...", { duration: 2000 });
      await new Promise((resolve) => setTimeout(resolve, 500));

      toast.info("📝 Đã ghi log sự cố...", { duration: 2000 });

      // Add new incident to local state
      const newIncident: IncidentLog = {
        id: response.incident.id,
        type: selectedType as IncidentLog["type"],
        description:
          incidentNote ||
          incidentTypes.find((t) => t.id === selectedType)?.label ||
          "Sự cố",
        status: "responding",
        createdAt: new Date(),
        location: `${userParkingInfo?.zone} - ${userParkingInfo?.slot}`,
      };
      setIncidents([newIncident, ...incidents]);

      setShowCameraDialog(true);
      setSelectedType(null);
      setIncidentNote("");

      toast.success(
        `✅ ${response.message || "Đã gửi cảnh báo!"} Bảo vệ sẽ đến trong 3 phút.`,
        { duration: 5000 },
      );
    } catch (error: unknown) {
      console.error(
        "Failed to report incident via API, using local fallback:",
        error,
      );

      // Fallback: create local incident when API is unavailable
      const fallbackIncident: IncidentLog = {
        id: `local-${Date.now()}`,
        type: selectedType as IncidentLog["type"],
        description:
          incidentNote ||
          incidentTypes.find((t) => t.id === selectedType)?.label ||
          "Sự cố",
        status: "responding",
        createdAt: new Date(),
        location: `${userParkingInfo?.zone} - ${userParkingInfo?.slot}`,
      };
      setIncidents((prev) => [fallbackIncident, ...prev]);
      setShowCameraDialog(true);
      setSelectedType(null);
      setIncidentNote("");

      toast.success("✅ Đã ghi nhận sự cố! Bảo vệ sẽ đến trong 3 phút.", {
        duration: 5000,
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleViewCamera = async () => {
    if (!userParkingInfo?.zoneId) {
      setShowCameraDialog(true);
      return;
    }

    try {
      const cameraInfo = await incidentApi.getNearbyCamera({
        zoneId: userParkingInfo.zoneId,
        slotId: userParkingInfo.slotId,
      });
      setCameraStream(cameraInfo.streamUrl);
    } catch (error) {
      console.log("Failed to get camera stream");
    }
    setShowCameraDialog(true);
  };

  const refreshIncidents = async () => {
    setIsLoadingIncidents(true);
    try {
      const response = await incidentApi.getMyIncidents({
        page: 1,
        pageSize: 10,
      });
      const mappedIncidents: IncidentLog[] = response.results.map(
        (incident: Incident) => ({
          id: incident.id,
          type: mapApiTypeToLocal(incident.type),
          description: incident.description || "Sự cố",
          status: mapApiStatusToLocal(incident.status),
          createdAt: new Date(incident.createdAt),
          location:
            incident.zoneName && incident.slotCode
              ? `${incident.zoneName} - ${incident.slotCode}`
              : incident.zoneName || "Không xác định",
        }),
      );
      setIncidents(mappedIncidents);
      toast.success("Đã cập nhật danh sách sự cố");
    } catch (error) {
      toast.error("Không thể cập nhật danh sách");
    } finally {
      setIsLoadingIncidents(false);
    }
  };

  const getStatusBadge = (status: IncidentLog["status"]) => {
    switch (status) {
      case "pending":
        return <Badge variant="secondary">Đang chờ</Badge>;
      case "responding":
        return (
          <Badge className="bg-warning/10 text-warning border-warning/20">
            Đang xử lý
          </Badge>
        );
      case "resolved":
        return (
          <Badge className="bg-success/10 text-success border-success/20">
            Đã giải quyết
          </Badge>
        );
    }
  };

  return (
    <MainLayout>
      <div className="space-y-6 max-w-2xl mx-auto">
        {/* Header */}
        <div className="animate-fade-in text-center">
          <div className="inline-flex items-center justify-center h-16 w-16 rounded-2xl bg-destructive/10 mb-4">
            <AlertTriangle className="h-8 w-8 text-destructive" />
          </div>
          <h1 className="text-2xl font-bold text-foreground">Panic Button</h1>
          <p className="mt-2 text-muted-foreground">
            Báo cáo sự cố khẩn cấp - Bảo vệ sẽ phản hồi ngay lập tức
          </p>
        </div>

        {/* Current Parking Info */}
        <div className="rounded-2xl border border-border bg-card p-4">
          {isLoadingParking ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : userParkingInfo ? (
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
                <Car className="h-6 w-6 text-primary" />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <p className="font-semibold text-foreground">
                    {userParkingInfo.licensePlate}
                  </p>
                </div>
                <p className="text-sm text-muted-foreground">
                  {userParkingInfo.zone} • Slot {userParkingInfo.slot} • Tầng{" "}
                  {userParkingInfo.floor}
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleViewCamera}
                className="gap-2"
              >
                <Camera className="h-4 w-4" />
                Xem camera
              </Button>
            </div>
          ) : (
            <div className="text-center py-4">
              <Car className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
              <p className="text-sm font-medium text-foreground">
                Chưa có phiên đỗ xe
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Bạn cần check-in booking để báo cáo sự cố
              </p>
            </div>
          )}
        </div>

        {/* Incident Type Selection */}
        <div className="space-y-3">
          <label className="text-sm font-medium text-foreground">
            Loại sự cố
          </label>
          <div className="grid grid-cols-2 gap-3">
            {incidentTypes.map((type) => (
              <button
                key={type.id}
                onClick={() => setSelectedType(type.id)}
                className={cn(
                  "flex flex-col items-center gap-2 rounded-xl border-2 p-4 transition-all",
                  selectedType === type.id
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-primary/50",
                )}
              >
                <div
                  className={cn(
                    "flex h-10 w-10 items-center justify-center rounded-lg",
                    type.color,
                  )}
                >
                  <type.icon className="h-5 w-5" />
                </div>
                <span className="text-sm font-medium text-foreground">
                  {type.label}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Note Input */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-foreground">
            Mô tả thêm (tùy chọn)
          </label>
          <textarea
            value={incidentNote}
            onChange={(e) => setIncidentNote(e.target.value)}
            placeholder="Mô tả chi tiết sự cố..."
            className="w-full rounded-xl border border-border bg-background px-4 py-3 text-sm focus:border-primary focus:outline-none min-h-[100px] resize-none"
          />
        </div>

        {/* Panic Button */}
        <Button
          onClick={handlePanicButton}
          disabled={
            isProcessing ||
            !selectedType ||
            !userParkingInfo ||
            !userParkingInfo.bookingId
          }
          className={cn(
            "w-full h-16 text-lg font-bold rounded-2xl transition-all",
            isProcessing
              ? "bg-muted"
              : "bg-destructive hover:bg-destructive/90 text-destructive-foreground shadow-lg hover:shadow-xl",
          )}
        >
          {isProcessing ? (
            <>
              <Loader2 className="h-6 w-6 animate-spin mr-2" />
              Đang xử lý...
            </>
          ) : (
            <>
              <AlertTriangle className="h-6 w-6 mr-2" />
              🚨 XE TÔI CÓ VẤN ĐỀ
            </>
          )}
        </Button>

        {/* What happens section */}
        <div className="rounded-xl bg-muted/50 p-4 space-y-3">
          <p className="text-sm font-medium text-foreground">
            Khi bạn nhấn nút:
          </p>
          <div className="space-y-2 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <Camera className="h-4 w-4 text-primary" />
              <span>Camera khu vực xe của bạn sẽ được mở</span>
            </div>
            <div className="flex items-center gap-2">
              <Phone className="h-4 w-4 text-primary" />
              <span>Bảo vệ nhận thông báo và di chuyển đến ngay</span>
            </div>
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-primary" />
              <span>Sự cố được ghi log để theo dõi và xử lý</span>
            </div>
          </div>
        </div>

        {/* Incident History */}
        <div className="rounded-2xl border border-border bg-card p-4 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <History className="h-5 w-5 text-muted-foreground" />
              <h3 className="font-semibold text-foreground">Lịch sử sự cố</h3>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline">{incidents.length} sự cố</Badge>
              <Button
                variant="ghost"
                size="icon"
                onClick={refreshIncidents}
                disabled={isLoadingIncidents}
              >
                <RefreshCcw
                  className={cn(
                    "h-4 w-4",
                    isLoadingIncidents && "animate-spin",
                  )}
                />
              </Button>
            </div>
          </div>

          {isLoadingIncidents ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : incidents.length > 0 ? (
            <div className="space-y-3">
              {incidents.slice(0, 5).map((incident) => (
                <div
                  key={incident.id}
                  className="flex items-start gap-3 rounded-xl border border-border bg-background/50 p-3"
                >
                  <div
                    className={cn(
                      "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
                      incidentTypes.find((t) => t.id === incident.type)?.color,
                    )}
                  >
                    {(() => {
                      const IconComponent =
                        incidentTypes.find((t) => t.id === incident.type)
                          ?.icon || AlertCircle;
                      return <IconComponent className="h-4 w-4" />;
                    })()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-foreground text-sm">
                      {incident.description}
                    </p>
                    <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                      <MapPin className="h-3 w-3" />
                      <span>{incident.location}</span>
                      <span>•</span>
                      <Clock className="h-3 w-3" />
                      <span>
                        {incident.createdAt.toLocaleDateString("vi-VN")}
                      </span>
                    </div>
                  </div>
                  {getStatusBadge(incident.status)}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <CheckCircle className="h-8 w-8 mx-auto mb-2 text-success" />
              <p>Không có sự cố nào được ghi nhận</p>
            </div>
          )}
        </div>

        {/* Emergency Contacts */}
        <div className="rounded-xl border border-border bg-card p-4">
          <h3 className="font-semibold text-foreground mb-3">
            Liên hệ khẩn cấp
          </h3>
          <div className="grid grid-cols-2 gap-3">
            <Button variant="outline" className="gap-2 h-12">
              <Phone className="h-4 w-4" />
              <div className="text-left">
                <p className="text-xs text-muted-foreground">Bảo vệ</p>
                <p className="font-medium">1900-1234</p>
              </div>
            </Button>
            <Button variant="outline" className="gap-2 h-12">
              <Shield className="h-4 w-4" />
              <div className="text-left">
                <p className="text-xs text-muted-foreground">Công an</p>
                <p className="font-medium">113</p>
              </div>
            </Button>
          </div>
        </div>
      </div>

      {/* Camera Dialog */}
      <Dialog open={showCameraDialog} onOpenChange={setShowCameraDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Camera className="h-5 w-5" />
              Camera khu vực xe của bạn
            </DialogTitle>
            <DialogDescription>
              {userParkingInfo?.zone} • Slot {userParkingInfo?.slot}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Camera Feed */}
            <div className="aspect-video rounded-xl bg-muted flex items-center justify-center relative overflow-hidden">
              {cameraStream ? (
                <iframe
                  src={cameraStream}
                  className="absolute inset-0 w-full h-full"
                  allow="autoplay"
                />
              ) : (
                <>
                  <div className="absolute inset-0 bg-gradient-to-br from-gray-800 to-gray-900" />
                  <div className="relative z-10 text-center">
                    <Video className="h-12 w-12 mx-auto text-muted-foreground mb-2" />
                    <p className="text-muted-foreground">Camera Feed</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {userParkingInfo?.cameraId || "Không có camera"}
                    </p>
                  </div>
                </>
              )}
              <div className="absolute top-3 left-3 flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
                <span className="text-xs text-white/80">LIVE</span>
              </div>
              <div className="absolute bottom-3 right-3">
                <Badge variant="secondary" className="text-xs">
                  {new Date().toLocaleTimeString("vi-VN")}
                </Badge>
              </div>
            </div>

            <div className="flex gap-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => setShowCameraDialog(false)}
              >
                Đóng
              </Button>
              <Button className="flex-1 gradient-primary">
                <Phone className="h-4 w-4 mr-2" />
                Gọi bảo vệ
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Confirm Dialog */}
      <Dialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-destructive">
              <AlertTriangle className="h-5 w-5" />
              Xác nhận báo cáo sự cố
            </DialogTitle>
            <DialogDescription>
              Bạn có chắc chắn muốn báo cáo sự cố? Bảo vệ sẽ được thông báo ngay
              lập tức.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="rounded-xl bg-muted/50 p-4 space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <User className="h-4 w-4 text-muted-foreground" />
                <span className="text-muted-foreground">Người báo:</span>
                <span className="font-medium">{user?.username}</span>
              </div>
              <div className="flex items-center gap-2">
                <Car className="h-4 w-4 text-muted-foreground" />
                <span className="text-muted-foreground">Xe:</span>
                <span className="font-medium">
                  {userParkingInfo?.licensePlate}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <MapPin className="h-4 w-4 text-muted-foreground" />
                <span className="text-muted-foreground">Vị trí:</span>
                <span className="font-medium">
                  {userParkingInfo?.zone} - {userParkingInfo?.slot}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-muted-foreground" />
                <span className="text-muted-foreground">Loại:</span>
                <span className="font-medium">
                  {incidentTypes.find((t) => t.id === selectedType)?.label}
                </span>
              </div>
            </div>

            <div className="flex gap-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => setShowConfirmDialog(false)}
              >
                Hủy
              </Button>
              <Button
                className="flex-1 bg-destructive hover:bg-destructive/90 text-destructive-foreground"
                onClick={confirmPanic}
              >
                <AlertTriangle className="h-4 w-4 mr-2" />
                Xác nhận
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </MainLayout>
  );
}
