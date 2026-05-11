import { useState, useEffect, useCallback } from "react";
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
  MapPin,
  Plus,
  Edit2,
  Trash2,
  Car,
  Bike,
  Building2,
  Layers,
  ParkingCircle,
  RefreshCw,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { parkingService, adminService, type Floor } from "@/services/business";
import { useToast } from "@/hooks/use-toast";
import type { ParkingLot } from "@/types/parking";

interface ZoneRow {
  id: string;
  name: string;
  floor: string; // floor UUID
  floorLevel: number;
  vehicleType: "Car" | "Motorbike";
  capacity: number;
  availableSlots: number;
}

const defaultAddForm = {
  name: "",
  floorId: "",
  vehicleType: "Car" as "Car" | "Motorbike",
  capacity: 50,
};

export default function AdminZonesPage() {
  const { toast } = useToast();

  // ---- Data ----
  const [lots, setLots] = useState<ParkingLot[]>([]);
  const [selectedLotId, setSelectedLotId] = useState<string>("");
  const [floors, setFloors] = useState<Floor[]>([]);
  const [zones, setZones] = useState<ZoneRow[]>([]);
  const [selectedFloor, setSelectedFloor] = useState<string>("all");

  // ---- UI ----
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [selectedZone, setSelectedZone] = useState<ZoneRow | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [addForm, setAddForm] = useState(defaultAddForm);
  const [editForm, setEditForm] = useState({
    name: "",
    floorId: "",
    vehicleType: "Car" as "Car" | "Motorbike",
    capacity: 50,
  });

  // ---- Load parking lots on mount ----
  useEffect(() => {
    const fetchLots = async () => {
      try {
        const resp = await parkingService.getLots({ pageSize: 100 });
        const items = resp.results ?? [];
        setLots(items);
        if (items.length > 0) setSelectedLotId(items[0].id);
      } catch (err) {
        console.error("Failed to fetch lots:", err);
      }
    };
    fetchLots();
  }, []);

  // ---- When lot changes → load floors ----
  useEffect(() => {
    if (!selectedLotId) return;
    const fetchFloors = async () => {
      try {
        const resp = await parkingService.getFloors(selectedLotId);
        setFloors(resp.results ?? []);
      } catch (err) {
        console.error("Failed to fetch floors:", err);
        setFloors([]);
      }
    };
    fetchFloors();
    setSelectedFloor("all");
  }, [selectedLotId]);

  // ---- Fetch zones for current lot ----
  const fetchZones = useCallback(async () => {
    if (!selectedLotId) return;
    try {
      setIsLoading(true);
      setError(null);
      const resp = await parkingService.getZones({
        lotId: selectedLotId,
        pageSize: 200,
      });
      const mapped: ZoneRow[] = (resp.results ?? []).map((z) => ({
        id: z.id,
        name: z.name,
        floor: z.floor ?? z.floorId ?? "",
        floorLevel: z.floorLevel ?? 1,
        vehicleType: z.vehicleType,
        capacity: z.capacity,
        availableSlots: z.availableSlots ?? 0,
      }));
      setZones(mapped);
    } catch (err) {
      console.error("Failed to fetch zones:", err);
      setError("Không thể tải danh sách zone");
      toast({
        title: "Lỗi",
        description: "Không thể tải danh sách zone",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  }, [selectedLotId, toast]);

  useEffect(() => {
    fetchZones();
  }, [fetchZones]);

  // ---- CRUD: Create ----
  const handleCreateZone = async () => {
    if (!addForm.name || !addForm.floorId) {
      toast({
        title: "Lỗi",
        description: "Vui lòng điền đầy đủ thông tin",
        variant: "destructive",
      });
      return;
    }
    try {
      setIsSubmitting(true);
      await adminService.createZone({
        floor: addForm.floorId,
        name: addForm.name,
        vehicleType: addForm.vehicleType,
        capacity: addForm.capacity,
      });
      toast({ title: "Thành công", description: "Đã tạo zone mới" });
      await fetchZones();
      setShowAddDialog(false);
      setAddForm(defaultAddForm);
    } catch (err) {
      console.error("Failed to create zone:", err);
      toast({
        title: "Lỗi",
        description: "Không thể tạo zone",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  // ---- CRUD: Update ----
  const handleUpdateZone = async () => {
    if (!selectedZone) return;
    try {
      setIsSubmitting(true);
      await adminService.updateZone(selectedZone.id, {
        name: editForm.name,
        floor: editForm.floorId,
        vehicleType: editForm.vehicleType,
        capacity: editForm.capacity,
      });
      toast({ title: "Thành công", description: "Đã cập nhật zone" });
      await fetchZones();
      setShowEditDialog(false);
    } catch (err) {
      console.error("Failed to update zone:", err);
      toast({
        title: "Lỗi",
        description: "Không thể cập nhật zone",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  // ---- CRUD: Delete ----
  const handleDeleteZone = async () => {
    if (!selectedZone) return;
    try {
      setIsSubmitting(true);
      await adminService.deleteZone(selectedZone.id);
      toast({ title: "Thành công", description: "Đã xóa zone" });
      await fetchZones();
      setShowDeleteDialog(false);
      setSelectedZone(null);
    } catch (err) {
      console.error("Failed to delete zone:", err);
      toast({
        title: "Lỗi",
        description: "Không thể xóa zone. Zone có thể vẫn còn slot.",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  // ---- Filtered list ----
  const filteredZones =
    selectedFloor === "all"
      ? zones
      : zones.filter((z) => z.floor === selectedFloor);

  // ---- Helpers ----
  const floorName = (floorUUID: string) => {
    const f = floors.find((fl) => fl.id === floorUUID);
    return f ? f.name || `Tầng ${f.level}` : "—";
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between animate-fade-in">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Quản lý Zone</h1>
            <p className="mt-1 text-muted-foreground">
              {zones.length} zone · {floors.length} tầng
            </p>
          </div>
          <div className="flex gap-3">
            <Button
              variant="outline"
              size="sm"
              className="gap-2"
              onClick={fetchZones}
            >
              <RefreshCw className="h-4 w-4" />
              Làm mới
            </Button>
            <Button
              className="gradient-primary gap-2"
              onClick={() => {
                setAddForm({
                  ...defaultAddForm,
                  floorId: floors[0]?.id ?? "",
                });
                setShowAddDialog(true);
              }}
            >
              <Plus className="h-4 w-4" />
              Thêm Zone
            </Button>
          </div>
        </div>

        {/* Parking Lot selector */}
        {lots.length > 1 && (
          <div className="flex items-center gap-3">
            <Building2 className="h-4 w-4 text-muted-foreground" />
            <select
              value={selectedLotId}
              onChange={(e) => setSelectedLotId(e.target.value)}
              className="rounded-xl border border-border bg-card px-4 py-2 text-sm focus:border-primary focus:outline-none"
            >
              {lots.map((lot) => (
                <option key={lot.id} value={lot.id}>
                  {lot.name}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Floor filter pills */}
        {!isLoading && !error && floors.length > 0 && (
          <div className="flex gap-2 flex-wrap">
            <Button
              variant={selectedFloor === "all" ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedFloor("all")}
              className="gap-2"
            >
              <Layers className="h-4 w-4" />
              Tất cả tầng
            </Button>
            {floors.map((f) => (
              <Button
                key={f.id}
                variant={selectedFloor === f.id ? "default" : "outline"}
                size="sm"
                onClick={() => setSelectedFloor(f.id)}
              >
                {f.name || `Tầng ${f.level}`}
              </Button>
            ))}
          </div>
        )}

        {/* Loading */}
        {isLoading && (
          <div className="flex flex-col items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
            <p className="mt-4 text-muted-foreground">Đang tải zones…</p>
          </div>
        )}

        {/* Error */}
        {error && !isLoading && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <MapPin className="h-12 w-12 text-destructive mb-4" />
            <p className="text-lg font-semibold">{error}</p>
            <Button className="mt-4" onClick={fetchZones}>
              Thử lại
            </Button>
          </div>
        )}

        {/* Grid */}
        {!isLoading && !error && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filteredZones.map((zone) => (
              <div
                key={zone.id}
                className="rounded-2xl border border-border bg-card p-5 transition-all hover:shadow-lg animate-slide-up"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div
                      className={cn(
                        "flex h-12 w-12 items-center justify-center rounded-xl",
                        zone.vehicleType === "Car"
                          ? "bg-primary/10 text-primary"
                          : "bg-accent/10 text-accent",
                      )}
                    >
                      {zone.vehicleType === "Car" ? (
                        <Car className="h-6 w-6" />
                      ) : (
                        <Bike className="h-6 w-6" />
                      )}
                    </div>
                    <div>
                      <h3 className="font-semibold text-foreground">
                        {zone.name}
                      </h3>
                      <p className="text-sm text-muted-foreground">
                        {floorName(zone.floor)}
                      </p>
                    </div>
                  </div>
                  <Badge className="bg-success/10 text-success">
                    Hoạt động
                  </Badge>
                </div>

                {/* Slots bar */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <ParkingCircle className="h-4 w-4" />
                      <span>Chỗ trống</span>
                    </div>
                    <span className="font-semibold text-foreground">
                      {zone.availableSlots}/{zone.capacity}
                    </span>
                  </div>

                  <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className={cn(
                        "h-full rounded-full transition-all",
                        zone.capacity > 0 &&
                          zone.availableSlots / zone.capacity > 0.3
                          ? "bg-success"
                          : zone.capacity > 0 &&
                              zone.availableSlots / zone.capacity > 0.1
                            ? "bg-warning"
                            : "bg-destructive",
                      )}
                      style={{
                        width: `${zone.capacity > 0 ? (zone.availableSlots / zone.capacity) * 100 : 0}%`,
                      }}
                    />
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-2 mt-4 pt-4 border-t border-border">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1 gap-1"
                    onClick={() => {
                      setSelectedZone(zone);
                      setEditForm({
                        name: zone.name,
                        floorId: zone.floor,
                        vehicleType: zone.vehicleType,
                        capacity: zone.capacity,
                      });
                      setShowEditDialog(true);
                    }}
                  >
                    <Edit2 className="h-3 w-3" />
                    Sửa
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1 gap-1 text-destructive hover:text-destructive"
                    onClick={() => {
                      setSelectedZone(zone);
                      setShowDeleteDialog(true);
                    }}
                  >
                    <Trash2 className="h-3 w-3" />
                    Xóa
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Empty */}
        {!isLoading && !error && filteredZones.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <MapPin className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-lg font-semibold">Không có zone nào</p>
            <p className="text-muted-foreground">
              Chọn tầng khác hoặc thêm zone mới
            </p>
          </div>
        )}
      </div>

      {/* ============ Add Zone Dialog ============ */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Thêm Zone mới</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1.5">
                Tên Zone
              </label>
              <input
                type="text"
                placeholder="VD: Zone A"
                value={addForm.name}
                onChange={(e) =>
                  setAddForm({ ...addForm, name: e.target.value })
                }
                className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5">Tầng</label>
              <select
                value={addForm.floorId}
                onChange={(e) =>
                  setAddForm({ ...addForm, floorId: e.target.value })
                }
                className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
              >
                <option value="">Chọn tầng</option>
                {floors.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.name || `Tầng ${f.level}`}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5">
                Loại xe
              </label>
              <select
                value={addForm.vehicleType}
                onChange={(e) =>
                  setAddForm({
                    ...addForm,
                    vehicleType: e.target.value as "Car" | "Motorbike",
                  })
                }
                className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
              >
                <option value="Car">Ô tô</option>
                <option value="Motorbike">Xe máy</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5">
                Sức chứa
              </label>
              <input
                type="number"
                placeholder="50"
                value={addForm.capacity}
                onChange={(e) =>
                  setAddForm({ ...addForm, capacity: Number(e.target.value) })
                }
                className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddDialog(false)}>
              Hủy
            </Button>
            <Button
              className="gradient-primary"
              onClick={handleCreateZone}
              disabled={isSubmitting}
            >
              {isSubmitting ? "Đang tạo…" : "Thêm Zone"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ============ Edit Zone Dialog ============ */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Chỉnh sửa {selectedZone?.name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1.5">
                Tên Zone
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
            <div>
              <label className="block text-sm font-medium mb-1.5">Tầng</label>
              <select
                value={editForm.floorId}
                onChange={(e) =>
                  setEditForm({ ...editForm, floorId: e.target.value })
                }
                className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
              >
                {floors.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.name || `Tầng ${f.level}`}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5">
                Loại xe
              </label>
              <select
                value={editForm.vehicleType}
                onChange={(e) =>
                  setEditForm({
                    ...editForm,
                    vehicleType: e.target.value as "Car" | "Motorbike",
                  })
                }
                className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
              >
                <option value="Car">Ô tô</option>
                <option value="Motorbike">Xe máy</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5">
                Sức chứa
              </label>
              <input
                type="number"
                value={editForm.capacity}
                onChange={(e) =>
                  setEditForm({
                    ...editForm,
                    capacity: Number(e.target.value),
                  })
                }
                className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEditDialog(false)}>
              Hủy
            </Button>
            <Button
              className="gradient-primary"
              onClick={handleUpdateZone}
              disabled={isSubmitting}
            >
              {isSubmitting ? "Đang lưu…" : "Lưu thay đổi"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ============ Delete Dialog ============ */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Xác nhận xóa</DialogTitle>
          </DialogHeader>
          <p className="text-muted-foreground">
            Bạn có chắc chắn muốn xóa <strong>{selectedZone?.name}</strong>? Tất
            cả slot trong zone này cũng sẽ bị xóa.
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
              onClick={handleDeleteZone}
              disabled={isSubmitting}
            >
              {isSubmitting ? "Đang xóa…" : "Xóa Zone"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </MainLayout>
  );
}
