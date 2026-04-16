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
  ParkingCircle,
  Plus,
  Edit2,
  Trash2,
  Car,
  Search,
  Camera,
  Check,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { parkingService, adminService } from "@/services/business";
import { useToast } from "@/hooks/use-toast";

interface Slot {
  id: string;
  code: string;
  zoneId: string;
  zoneName: string;
  floorLevel: number;
  vehicleType: "Car" | "Motorbike";
  status: "available" | "occupied" | "reserved" | "maintenance";
  cameraId?: string;
}

interface ZoneOption {
  id: string;
  name: string;
}

export default function AdminSlotsPage() {
  const { toast } = useToast();
  const [slots, setSlots] = useState<Slot[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [zones, setZones] = useState<ZoneOption[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterZone, setFilterZone] = useState<string>("all");
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [selectedSlot, setSelectedSlot] = useState<Slot | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const pageSize = 20;

  // Form state
  const [addForm, setAddForm] = useState({
    code: "",
    zoneId: "",
    status: "available" as string,
  });
  const [editForm, setEditForm] = useState({
    code: "",
    zoneId: "",
    status: "available" as string,
  });

  // Fetch zones first
  useEffect(() => {
    const fetchZonesData = async () => {
      try {
        const lotsResponse = await parkingService.getLots();
        if (lotsResponse.results.length > 0) {
          const zonesResponse = await parkingService.getZones({
            lot_id: lotsResponse.results[0].id,
          });
          const zoneOptions = zonesResponse.results.map((z) => ({
            id: z.id,
            name: z.name,
          }));
          setZones(zoneOptions);
        }
      } catch (error) {
        console.error("Failed to fetch zones:", error);
      }
    };
    fetchZonesData();
  }, []);

  // Fetch slots
  const fetchSlots = async () => {
    if (zones.length === 0) return;
    try {
      setIsLoading(true);
      setError(null);

      const zoneId = filterZone !== "all" ? filterZone : undefined;

      const response = await parkingService.getSlots({
        ...(zoneId ? { zone_id: zoneId } : {}),
        page: currentPage,
        pageSize: pageSize,
        status:
          filterStatus !== "all"
            ? (filterStatus as
                | "available"
                | "occupied"
                | "reserved"
                | "maintenance")
            : undefined,
      });

      setTotalCount(response.count ?? 0);

      const mappedSlots: Slot[] = response.results.map((s) => ({
        id: s.id,
        code: s.code,
        zoneId: s.zone || s.zoneId || "",
        zoneName:
          zones.find((z) => z.id === (s.zone || s.zoneId))?.name || "Unknown",
        floorLevel: s.floor || 1,
        vehicleType: s.vehicleType || "Car",
        status: s.status,
        cameraId: s.camera || s.cameraId,
      }));

      setSlots(mappedSlots);
    } catch (err) {
      console.error("Failed to fetch slots:", err);
      setError("Không thể tải danh sách slot");
      toast({
        title: "Lỗi",
        description: "Không thể tải danh sách slot",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Create slot
  const handleCreateSlot = async () => {
    if (!addForm.code || !addForm.zoneId) {
      toast({
        title: "Lỗi",
        description: "Vui lòng điền đầy đủ thông tin",
        variant: "destructive",
      });
      return;
    }
    try {
      setIsSubmitting(true);
      await adminService.createSlot({
        zone: addForm.zoneId,
        code: addForm.code,
        status: addForm.status,
      });
      toast({ title: "Thành công", description: "Đã tạo slot mới" });
      await fetchSlots();
      setShowAddDialog(false);
      setAddForm({ code: "", zoneId: zones[0]?.id || "", status: "available" });
    } catch (error) {
      console.error("Failed to create slot:", error);
      toast({
        title: "Lỗi",
        description: "Không thể tạo slot",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Update slot
  const handleUpdateSlot = async () => {
    if (!selectedSlot) return;
    try {
      setIsSubmitting(true);
      await adminService.updateSlot(selectedSlot.id, {
        code: editForm.code,
        zone: editForm.zoneId,
        status: editForm.status,
      });
      toast({ title: "Thành công", description: "Đã cập nhật slot" });
      await fetchSlots();
      setShowEditDialog(false);
    } catch (error) {
      console.error("Failed to update slot:", error);
      toast({
        title: "Lỗi",
        description: "Không thể cập nhật slot",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Delete slot
  const handleDeleteSlot = async () => {
    if (!selectedSlot) return;
    try {
      setIsSubmitting(true);
      await adminService.deleteSlot(selectedSlot.id);
      toast({ title: "Thành công", description: "Đã xóa slot" });
      await fetchSlots();
      setShowDeleteDialog(false);
      setSelectedSlot(null);
    } catch (error) {
      console.error("Failed to delete slot:", error);
      toast({
        title: "Lỗi",
        description: "Không thể xóa slot",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Fetch slots when zones loaded or filters change
  useEffect(() => {
    if (zones.length > 0) fetchSlots();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [zones, filterZone, filterStatus, currentPage]);

  // Reset page when filter changes
  useEffect(() => {
    setCurrentPage(1);
  }, [filterZone, filterStatus]);

  const totalPages = Math.ceil(totalCount / pageSize);

  const filteredSlots = slots.filter((slot) => {
    const matchesSearch = slot.code
      .toLowerCase()
      .includes(searchQuery.toLowerCase());
    return matchesSearch;
  });

  const getStatusBadge = (status: Slot["status"]) => {
    switch (status) {
      case "available":
        return <Badge className="bg-success/10 text-success">Trống</Badge>;
      case "occupied":
        return <Badge className="bg-primary/10 text-primary">Đang đậu</Badge>;
      case "reserved":
        return <Badge className="bg-warning/10 text-warning">Đã đặt</Badge>;
      case "maintenance":
        return <Badge variant="destructive">Bảo trì</Badge>;
    }
  };

  const stats = {
    total: totalCount,
    available: slots.filter((s) => s.status === "available").length,
    occupied: slots.filter((s) => s.status === "occupied").length,
    reserved: slots.filter((s) => s.status === "reserved").length,
    maintenance: slots.filter((s) => s.status === "maintenance").length,
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between animate-fade-in">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Quản lý Slot</h1>
            <p className="mt-1 text-muted-foreground">
              {stats.total} slot | {stats.available} trống | {stats.occupied}{" "}
              đang đậu
            </p>
          </div>
          <Button
            className="gradient-primary gap-2"
            onClick={() => {
              setAddForm({
                code: "",
                zoneId: zones[0]?.id || "",
                status: "available",
              });
              setShowAddDialog(true);
            }}
          >
            <Plus className="h-4 w-4" />
            Thêm Slot
          </Button>
        </div>

        {/* Stats */}
        <div className="grid gap-3 grid-cols-2 sm:grid-cols-4">
          <div className="rounded-xl border border-border bg-card p-3 sm:p-4 flex items-center gap-3 sm:gap-4">
            <div className="flex h-8 w-8 sm:h-10 sm:w-10 items-center justify-center rounded-lg bg-success/10">
              <Check className="h-4 w-4 sm:h-5 sm:w-5 text-success" />
            </div>
            <div>
              <p className="text-xl sm:text-2xl font-bold text-foreground">
                {stats.available}
              </p>
              <p className="text-xs sm:text-sm text-muted-foreground">
                Slot trống
              </p>
            </div>
          </div>
          <div className="rounded-xl border border-border bg-card p-3 sm:p-4 flex items-center gap-3 sm:gap-4">
            <div className="flex h-8 w-8 sm:h-10 sm:w-10 items-center justify-center rounded-lg bg-primary/10">
              <Car className="h-4 w-4 sm:h-5 sm:w-5 text-primary" />
            </div>
            <div>
              <p className="text-xl sm:text-2xl font-bold text-foreground">
                {stats.occupied}
              </p>
              <p className="text-xs sm:text-sm text-muted-foreground">
                Đang đậu
              </p>
            </div>
          </div>
          <div className="rounded-xl border border-border bg-card p-3 sm:p-4 flex items-center gap-3 sm:gap-4">
            <div className="flex h-8 w-8 sm:h-10 sm:w-10 items-center justify-center rounded-lg bg-warning/10">
              <ParkingCircle className="h-4 w-4 sm:h-5 sm:w-5 text-warning" />
            </div>
            <div>
              <p className="text-xl sm:text-2xl font-bold text-foreground">
                {stats.reserved}
              </p>
              <p className="text-xs sm:text-sm text-muted-foreground">
                Đã đặt trước
              </p>
            </div>
          </div>
          <div className="rounded-xl border border-border bg-card p-3 sm:p-4 flex items-center gap-3 sm:gap-4">
            <div className="flex h-8 w-8 sm:h-10 sm:w-10 items-center justify-center rounded-lg bg-destructive/10">
              <X className="h-4 w-4 sm:h-5 sm:w-5 text-destructive" />
            </div>
            <div>
              <p className="text-xl sm:text-2xl font-bold text-foreground">
                {stats.maintenance}
              </p>
              <p className="text-xs sm:text-sm text-muted-foreground">
                Bảo trì
              </p>
            </div>
          </div>
        </div>

        {/* Filters */}
        {!isLoading && !error && (
          <div className="flex flex-col gap-4 sm:flex-row">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                placeholder="Tìm theo mã slot..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-xl border border-border bg-card pl-10 pr-4 py-2.5 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>
            <select
              value={filterZone}
              onChange={(e) => setFilterZone(e.target.value)}
              className="rounded-xl border border-border bg-card px-4 py-2.5 focus:border-primary focus:outline-none"
            >
              <option value="all">Tất cả Zone</option>
              {zones.map((zone) => (
                <option key={zone.id} value={zone.id}>
                  {zone.name}
                </option>
              ))}
            </select>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="rounded-xl border border-border bg-card px-4 py-2.5 focus:border-primary focus:outline-none"
            >
              <option value="all">Tất cả trạng thái</option>
              <option value="available">Trống</option>
              <option value="occupied">Đang đậu</option>
              <option value="reserved">Đã đặt</option>
              <option value="maintenance">Bảo trì</option>
            </select>
          </div>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className="flex flex-col items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            <p className="mt-4 text-muted-foreground">Đang tải slots...</p>
          </div>
        )}

        {/* Error State */}
        {error && !isLoading && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <ParkingCircle className="h-12 w-12 text-destructive mb-4" />
            <p className="text-lg font-semibold text-foreground">
              Có lỗi xảy ra
            </p>
            <p className="text-muted-foreground mb-4">{error}</p>
            <Button onClick={fetchSlots}>Thử lại</Button>
          </div>
        )}

        {/* Slots Grid */}
        {!isLoading && !error && (
          <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
            {filteredSlots.map((slot) => (
              <div
                key={slot.id}
                className={cn(
                  "rounded-xl border-2 p-4 transition-all hover:shadow-md animate-slide-up",
                  slot.status === "available" &&
                    "border-success/50 bg-success/5",
                  slot.status === "occupied" &&
                    "border-primary/50 bg-primary/5",
                  slot.status === "reserved" &&
                    "border-warning/50 bg-warning/5",
                  slot.status === "maintenance" &&
                    "border-destructive/50 bg-destructive/5",
                )}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div
                      className={cn(
                        "flex h-8 w-8 items-center justify-center rounded-lg",
                        slot.vehicleType === "Car"
                          ? "bg-primary/20"
                          : "bg-accent/20",
                      )}
                    >
                      <Car
                        className={cn(
                          "h-4 w-4",
                          slot.vehicleType === "Car"
                            ? "text-primary"
                            : "text-accent",
                        )}
                      />
                    </div>
                    <span className="font-mono font-bold text-foreground">
                      {slot.code}
                    </span>
                  </div>
                  {getStatusBadge(slot.status)}
                </div>

                <div className="text-sm text-muted-foreground mb-3">
                  <p>{slot.zoneName}</p>
                  {slot.cameraId && (
                    <div className="flex items-center gap-1 mt-1 text-xs">
                      <Camera className="h-3 w-3" />
                      <span>Camera gắn</span>
                    </div>
                  )}
                </div>

                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => {
                      setSelectedSlot(slot);
                      setEditForm({
                        code: slot.code,
                        zoneId: slot.zoneId,
                        status: slot.status,
                      });
                      setShowEditDialog(true);
                    }}
                  >
                    <Edit2 className="h-3 w-3" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1 text-destructive hover:text-destructive"
                    onClick={() => {
                      setSelectedSlot(slot);
                      setShowDeleteDialog(true);
                    }}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}

        {!isLoading && !error && filteredSlots.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <ParkingCircle className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-lg font-semibold text-foreground">
              Không tìm thấy slot
            </p>
            <p className="text-muted-foreground">
              Thử thay đổi bộ lọc hoặc từ khóa tìm kiếm
            </p>
          </div>
        )}

        {/* Pagination Controls */}
        {!isLoading && !error && totalPages > 1 && (
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-border">
            <p className="text-sm text-muted-foreground">
              Hiển thị {(currentPage - 1) * pageSize + 1}–
              {Math.min(currentPage * pageSize, totalCount)} / {totalCount} slot
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={currentPage <= 1}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              >
                ← Trước
              </Button>
              {Array.from({ length: totalPages }, (_, i) => i + 1)
                .filter(
                  (p) =>
                    p === 1 ||
                    p === totalPages ||
                    Math.abs(p - currentPage) <= 2,
                )
                .reduce<(number | string)[]>((acc, p, idx, arr) => {
                  if (idx > 0 && p - (arr[idx - 1] as number) > 1) {
                    acc.push("...");
                  }
                  acc.push(p);
                  return acc;
                }, [])
                .map((item, idx) =>
                  typeof item === "string" ? (
                    <span
                      key={`ellipsis-${idx}`}
                      className="px-1 text-muted-foreground"
                    >
                      …
                    </span>
                  ) : (
                    <Button
                      key={item}
                      variant={item === currentPage ? "default" : "outline"}
                      size="sm"
                      className="min-w-[36px]"
                      onClick={() => setCurrentPage(item)}
                    >
                      {item}
                    </Button>
                  ),
                )}
              <Button
                variant="outline"
                size="sm"
                disabled={currentPage >= totalPages}
                onClick={() =>
                  setCurrentPage((p) => Math.min(totalPages, p + 1))
                }
              >
                Tiếp →
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Add Slot Dialog */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Thêm Slot mới</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1.5">
                Mã Slot
              </label>
              <input
                type="text"
                placeholder="VD: A-10"
                value={addForm.code}
                onChange={(e) =>
                  setAddForm({ ...addForm, code: e.target.value })
                }
                className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
              />
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
                <option value="">Chọn Zone</option>
                {zones.map((zone) => (
                  <option key={zone.id} value={zone.id}>
                    {zone.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5">
                Trạng thái
              </label>
              <select
                value={addForm.status}
                onChange={(e) =>
                  setAddForm({ ...addForm, status: e.target.value })
                }
                className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
              >
                <option value="available">Trống</option>
                <option value="maintenance">Bảo trì</option>
              </select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddDialog(false)}>
              Hủy
            </Button>
            <Button
              className="gradient-primary"
              onClick={handleCreateSlot}
              disabled={isSubmitting}
            >
              {isSubmitting ? "Đang tạo..." : "Thêm Slot"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Slot Dialog */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Chỉnh sửa Slot {selectedSlot?.code}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1.5">
                Mã Slot
              </label>
              <input
                type="text"
                value={editForm.code}
                onChange={(e) =>
                  setEditForm({ ...editForm, code: e.target.value })
                }
                className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
              />
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
                {zones.map((zone) => (
                  <option key={zone.id} value={zone.id}>
                    {zone.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5">
                Trạng thái
              </label>
              <select
                value={editForm.status}
                onChange={(e) =>
                  setEditForm({ ...editForm, status: e.target.value })
                }
                className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
              >
                <option value="available">Trống</option>
                <option value="occupied">Đang đậu</option>
                <option value="reserved">Đã đặt</option>
                <option value="maintenance">Bảo trì</option>
              </select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEditDialog(false)}>
              Hủy
            </Button>
            <Button
              className="gradient-primary"
              onClick={handleUpdateSlot}
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
            Bạn có chắc chắn muốn xóa slot <strong>{selectedSlot?.code}</strong>
            ? Hành động này không thể hoàn tác.
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
              onClick={handleDeleteSlot}
              disabled={isSubmitting}
            >
              {isSubmitting ? "Đang xóa..." : "Xóa Slot"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </MainLayout>
  );
}
