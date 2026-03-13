import { useState, useEffect } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Camera,
  Plus,
  Trash2,
  Video,
  VideoOff,
  Wifi,
  WifiOff,
  Settings,
  RefreshCw,
  MapPin,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { adminApi } from "@/services/api/admin.api";
import { parkingApi } from "@/services/api/parking.api";
import { useToast } from "@/hooks/use-toast";

interface CameraDevice {
  id: string;
  name: string;
  ipAddress: string;
  port: number;
  zoneId: string;
  zoneName: string;
  status: "online" | "offline" | "error";
  streamUrl: string;
  isActive: boolean;
  /** System cameras (from AI service config) cannot be edited/deleted */
  isSystem?: boolean;
}

// ── Hardcoded monitoring cameras (AI service) ─────────────────────────── //
const SYSTEM_CAMERAS: CameraDevice[] = [
  {
    id: "plate-camera-ezviz",
    name: "Camera Biển Số (EZVIZ)",
    ipAddress: "192.168.100.23",
    port: 554,
    zoneId: "",
    zoneName: "Cổng vào",
    status: "online",
    streamUrl: "/ai/cameras/stream?camera_id=plate-camera-ezviz&fps=3",
    isActive: true,
    isSystem: true,
  },
  {
    id: "qr-camera-droidcam",
    name: "Camera QR Code (DroidCam)",
    ipAddress: "192.168.100.130",
    port: 4747,
    zoneId: "",
    zoneName: "Cổng vào",
    status: "online",
    streamUrl: "/ai/cameras/stream?camera_id=qr-camera-droidcam&fps=3",
    isActive: true,
    isSystem: true,
  },
];

interface ZoneOption {
  id: string;
  name: string;
}

export default function AdminCamerasPage() {
  const { toast } = useToast();
  const [cameras, setCameras] = useState<CameraDevice[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [zones, setZones] = useState<ZoneOption[]>([]);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [selectedCamera, setSelectedCamera] = useState<CameraDevice | null>(
    null,
  );
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form state
  const [addForm, setAddForm] = useState({
    name: "",
    ipAddress: "",
    port: 554,
    zoneId: "",
  });
  const [editForm, setEditForm] = useState({
    name: "",
    ipAddress: "",
    port: 554,
    zoneId: "",
  });

  // Fetch zones for dropdown
  useEffect(() => {
    const fetchZones = async () => {
      try {
        const lotsResponse = await parkingApi.getLots();
        if (lotsResponse.results.length > 0) {
          const zonesResponse = await parkingApi.getZones({
            lot_id: lotsResponse.results[0].id,
          });
          setZones(
            zonesResponse.results.map((z) => ({ id: z.id, name: z.name })),
          );
        }
      } catch (error) {
        console.error("Failed to fetch zones:", error);
      }
    };
    fetchZones();
  }, []);

  // Fetch cameras
  const fetchCameras = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await adminApi.getCameras();

      const mappedCameras: CameraDevice[] = response.results.map((cam) => ({
        id: cam.id,
        name: cam.name,
        ipAddress: cam.ipAddress || "",
        port: cam.port || 554,
        zoneId: cam.zone || "",
        zoneName: zones.find((z) => z.id === cam.zone)?.name || "Chưa gán",
        status: cam.isActive ? "online" : "offline",
        streamUrl: cam.streamUrl || "",
        isActive: cam.isActive !== false,
        isSystem: false,
      }));

      // Merge system cameras (EZVIZ, DroidCam) — shown first, dedup by id
      const dbIds = new Set(mappedCameras.map((c) => c.id));
      const merged = [
        ...SYSTEM_CAMERAS.filter((sc) => !dbIds.has(sc.id)),
        ...mappedCameras,
      ];
      setCameras(merged);
    } catch (err) {
      console.error("Failed to fetch cameras:", err);
      setError("Không thể tải danh sách camera");
      toast({
        title: "Lỗi",
        description: "Không thể tải danh sách camera",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Create camera
  const handleCreateCamera = async () => {
    if (!addForm.name || !addForm.ipAddress) {
      toast({
        title: "Lỗi",
        description: "Vui lòng điền tên và IP address",
        variant: "destructive",
      });
      return;
    }
    try {
      setIsSubmitting(true);
      await adminApi.createCamera({
        name: addForm.name,
        ipAddress: addForm.ipAddress,
        port: addForm.port,
        zone: addForm.zoneId || undefined,
        streamUrl: `rtsp://${addForm.ipAddress}:${addForm.port}/stream`,
      });
      toast({ title: "Thành công", description: "Đã thêm camera mới" });
      await fetchCameras();
      setShowAddDialog(false);
      setAddForm({ name: "", ipAddress: "", port: 554, zoneId: "" });
    } catch (error) {
      console.error("Failed to create camera:", error);
      toast({
        title: "Lỗi",
        description: "Không thể thêm camera",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Update camera
  const handleUpdateCamera = async () => {
    if (!selectedCamera) return;
    try {
      setIsSubmitting(true);
      await adminApi.updateCamera(selectedCamera.id, {
        name: editForm.name,
        ipAddress: editForm.ipAddress,
        port: editForm.port,
        zone: editForm.zoneId || null,
        streamUrl: `rtsp://${editForm.ipAddress}:${editForm.port}/stream`,
      });
      toast({ title: "Thành công", description: "Đã cập nhật camera" });
      await fetchCameras();
      setShowEditDialog(false);
    } catch (error) {
      console.error("Failed to update camera:", error);
      toast({
        title: "Lỗi",
        description: "Không thể cập nhật camera",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Delete camera
  const handleDeleteCamera = async () => {
    if (!selectedCamera) return;
    try {
      setIsSubmitting(true);
      await adminApi.deleteCamera(selectedCamera.id);
      toast({ title: "Thành công", description: "Đã xóa camera" });
      await fetchCameras();
      setShowDeleteDialog(false);
      setSelectedCamera(null);
    } catch (error) {
      console.error("Failed to delete camera:", error);
      toast({
        title: "Lỗi",
        description: "Không thể xóa camera",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Refresh camera status
  const handleRefreshStatus = async () => {
    await fetchCameras();
    toast({
      title: "Đã cập nhật",
      description: "Trạng thái camera đã được làm mới",
    });
  };

  useEffect(() => {
    fetchCameras();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [zones]);

  const stats = {
    total: cameras.length,
    online: cameras.filter((c) => c.status === "online").length,
    offline: cameras.filter((c) => c.status === "offline").length,
    error: cameras.filter((c) => c.status === "error").length,
  };

  const getStatusBadge = (status: CameraDevice["status"]) => {
    switch (status) {
      case "online":
        return (
          <Badge className="bg-success/10 text-success gap-1">
            <Wifi className="h-3 w-3" />
            Online
          </Badge>
        );
      case "offline":
        return (
          <Badge variant="secondary" className="gap-1">
            <WifiOff className="h-3 w-3" />
            Offline
          </Badge>
        );
      case "error":
        return (
          <Badge variant="destructive" className="gap-1">
            <WifiOff className="h-3 w-3" />
            Lỗi
          </Badge>
        );
    }
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between animate-fade-in">
          <div>
            <h1 className="text-2xl font-bold text-foreground">
              Quản lý Camera
            </h1>
            <p className="mt-1 text-muted-foreground">
              {stats.total} camera | {stats.online} online |{" "}
              {stats.offline + stats.error} có vấn đề
            </p>
          </div>
          <div className="flex gap-3">
            <Button
              variant="outline"
              className="gap-2"
              onClick={handleRefreshStatus}
            >
              <RefreshCw className="h-4 w-4" />
              Làm mới
            </Button>
            <Button
              className="gradient-primary gap-2"
              onClick={() => {
                setAddForm({
                  name: "",
                  ipAddress: "",
                  port: 554,
                  zoneId: zones[0]?.id || "",
                });
                setShowAddDialog(true);
              }}
            >
              <Plus className="h-4 w-4" />
              Thêm Camera
            </Button>
          </div>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="flex flex-col items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            <p className="mt-4 text-muted-foreground">Đang tải cameras...</p>
          </div>
        )}

        {/* Error State */}
        {error && !isLoading && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Camera className="h-12 w-12 text-destructive mb-4" />
            <p className="text-lg font-semibold text-foreground">
              Có lỗi xảy ra
            </p>
            <p className="text-muted-foreground mb-4">{error}</p>
            <Button onClick={fetchCameras}>Thử lại</Button>
          </div>
        )}

        {/* Stats */}
        {!isLoading && !error && (
          <div className="grid gap-4 sm:grid-cols-4">
            <div className="rounded-xl border border-border bg-card p-4 flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
                <Camera className="h-6 w-6 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold text-foreground">
                  {stats.total}
                </p>
                <p className="text-sm text-muted-foreground">Tổng camera</p>
              </div>
            </div>
            <div className="rounded-xl border border-border bg-card p-4 flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-success/10">
                <Video className="h-6 w-6 text-success" />
              </div>
              <div>
                <p className="text-2xl font-bold text-foreground">
                  {stats.online}
                </p>
                <p className="text-sm text-muted-foreground">Đang hoạt động</p>
              </div>
            </div>
            <div className="rounded-xl border border-border bg-card p-4 flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-muted">
                <VideoOff className="h-6 w-6 text-muted-foreground" />
              </div>
              <div>
                <p className="text-2xl font-bold text-foreground">
                  {stats.offline}
                </p>
                <p className="text-sm text-muted-foreground">Offline</p>
              </div>
            </div>
            <div className="rounded-xl border border-border bg-card p-4 flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-destructive/10">
                <WifiOff className="h-6 w-6 text-destructive" />
              </div>
              <div>
                <p className="text-2xl font-bold text-foreground">
                  {stats.error}
                </p>
                <p className="text-sm text-muted-foreground">Có lỗi</p>
              </div>
            </div>
          </div>
        )}

        {/* Cameras Grid */}
        {!isLoading && !error && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {cameras.map((camera) => (
              <div
                key={camera.id}
                className="rounded-2xl border border-border bg-card overflow-hidden transition-all hover:shadow-lg animate-slide-up"
              >
                {/* Camera Preview */}
                <div className="relative aspect-video bg-gradient-to-br from-muted to-muted/50">
                  {camera.status === "online" && camera.streamUrl ? (
                    <>
                      <img
                        src={camera.streamUrl}
                        alt={camera.name}
                        className="absolute inset-0 h-full w-full object-cover"
                        onError={(e) => {
                          const target = e.currentTarget;
                          target.style.display = "none";
                          const fallback =
                            target.nextElementSibling as HTMLElement | null;
                          if (fallback) fallback.style.display = "flex";
                        }}
                      />
                      <div className="absolute inset-0 hidden items-center justify-center">
                        <Video className="h-12 w-12 text-muted-foreground/50" />
                      </div>
                      <div className="absolute left-3 top-3 flex items-center gap-2 rounded-full bg-destructive/90 px-2 py-1">
                        <div className="h-2 w-2 rounded-full bg-white animate-pulse" />
                        <span className="text-xs font-medium text-white">
                          LIVE
                        </span>
                      </div>
                    </>
                  ) : (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <VideoOff
                        className={cn(
                          "h-12 w-12",
                          camera.status === "error"
                            ? "text-destructive/50"
                            : "text-muted-foreground/50",
                        )}
                      />
                    </div>
                  )}
                </div>

                {/* Camera Info */}
                <div className="p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-semibold text-foreground">
                        {camera.name}
                      </h3>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <MapPin className="h-3 w-3" />
                        <span>{camera.zoneName}</span>
                      </div>
                    </div>
                    {getStatusBadge(camera.status)}
                  </div>

                  <div className="rounded-lg bg-muted/50 p-3 space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">IP Address</span>
                      <span className="font-mono text-foreground">
                        {camera.ipAddress}:{camera.port}
                      </span>
                    </div>
                  </div>

                  <div className="flex gap-2 pt-2">
                    {camera.isSystem ? (
                      <Badge
                        variant="secondary"
                        className="w-full justify-center py-1.5"
                      >
                        Camera hệ thống (AI Service)
                      </Badge>
                    ) : (
                      <>
                        <Button
                          variant="outline"
                          size="sm"
                          className="flex-1 gap-1"
                          onClick={() => {
                            setSelectedCamera(camera);
                            setEditForm({
                              name: camera.name,
                              ipAddress: camera.ipAddress,
                              port: camera.port,
                              zoneId: camera.zoneId,
                            });
                            setShowEditDialog(true);
                          }}
                        >
                          <Settings className="h-3 w-3" />
                          Cấu hình
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="flex-1 gap-1 text-destructive hover:text-destructive"
                          onClick={() => {
                            setSelectedCamera(camera);
                            setShowDeleteDialog(true);
                          }}
                        >
                          <Trash2 className="h-3 w-3" />
                          Xóa
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {!isLoading && !error && cameras.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Camera className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-lg font-semibold text-foreground">
              Chưa có camera nào
            </p>
            <p className="text-muted-foreground">
              Thêm camera mới để bắt đầu giám sát
            </p>
          </div>
        )}
      </div>

      {/* Add Camera Dialog */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Thêm Camera mới</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1.5">
                Tên Camera
              </label>
              <input
                type="text"
                placeholder="VD: Camera E-01"
                value={addForm.name}
                onChange={(e) =>
                  setAddForm({ ...addForm, name: e.target.value })
                }
                className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  IP Address
                </label>
                <input
                  type="text"
                  placeholder="192.168.1.xxx"
                  value={addForm.ipAddress}
                  onChange={(e) =>
                    setAddForm({ ...addForm, ipAddress: e.target.value })
                  }
                  className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">Port</label>
                <input
                  type="number"
                  value={addForm.port}
                  onChange={(e) =>
                    setAddForm({ ...addForm, port: Number(e.target.value) })
                  }
                  className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5">Zone</label>
              <select
                value={addForm.zoneId}
                onChange={(e) =>
                  setAddForm({ ...addForm, zoneId: e.target.value })
                }
                className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
              >
                <option value="">Không gán zone</option>
                {zones.map((zone) => (
                  <option key={zone.id} value={zone.id}>
                    {zone.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddDialog(false)}>
              Hủy
            </Button>
            <Button
              className="gradient-primary"
              onClick={handleCreateCamera}
              disabled={isSubmitting}
            >
              {isSubmitting ? "Đang thêm..." : "Thêm Camera"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Camera Dialog */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cấu hình {selectedCamera?.name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1.5">
                Tên Camera
              </label>
              <input
                type="text"
                value={editForm.name}
                onChange={(e) =>
                  setEditForm({ ...editForm, name: e.target.value })
                }
                className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  IP Address
                </label>
                <input
                  type="text"
                  value={editForm.ipAddress}
                  onChange={(e) =>
                    setEditForm({ ...editForm, ipAddress: e.target.value })
                  }
                  className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">Port</label>
                <input
                  type="number"
                  value={editForm.port}
                  onChange={(e) =>
                    setEditForm({ ...editForm, port: Number(e.target.value) })
                  }
                  className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5">Zone</label>
              <select
                value={editForm.zoneId}
                onChange={(e) =>
                  setEditForm({ ...editForm, zoneId: e.target.value })
                }
                className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
              >
                <option value="">Không gán zone</option>
                {zones.map((zone) => (
                  <option key={zone.id} value={zone.id}>
                    {zone.name}
                  </option>
                ))}
              </select>
            </div>
            {selectedCamera && (
              <div className="p-3 rounded-xl bg-muted/50">
                <p className="text-sm text-muted-foreground">
                  Trạng thái:{" "}
                  {selectedCamera.status === "online" ? (
                    <span className="text-success font-medium">
                      Đang hoạt động
                    </span>
                  ) : (
                    <span className="text-muted-foreground font-medium">
                      Offline
                    </span>
                  )}
                </p>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEditDialog(false)}>
              Hủy
            </Button>
            <Button
              className="gradient-primary"
              onClick={handleUpdateCamera}
              disabled={isSubmitting}
            >
              {isSubmitting ? "Đang lưu..." : "Lưu thay đổi"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Xác nhận xóa</DialogTitle>
          </DialogHeader>
          <p className="text-muted-foreground">
            Bạn có chắc chắn muốn xóa camera{" "}
            <strong>{selectedCamera?.name}</strong>? Hành động này không thể
            hoàn tác.
          </p>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowDeleteDialog(false)}
            >
              Hủy
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteCamera}
              disabled={isSubmitting}
            >
              {isSubmitting ? "Đang xóa..." : "Xóa Camera"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </MainLayout>
  );
}
