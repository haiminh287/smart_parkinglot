/**
 * AdminViolationsPage — Admin view for parking violations / incidents.
 *
 * Features:
 *   - List all incidents with filters (type, status, date)
 *   - Resolve / cancel incidents
 *   - View incident details with camera evidence
 *   - Stats overview (total, pending, resolved)
 */

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
  AlertTriangle,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  Clock,
  MapPin,
  Car,
  Camera,
  RefreshCw,
  Loader2,
  Eye,
  Filter,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { incidentApi } from "@/services/api/incident.api";
import { useToast } from "@/hooks/use-toast";

interface Incident {
  id: string;
  type: string;
  description: string;
  status: "pending" | "resolved" | "cancelled";
  reportedBy: string;
  bookingId: string | null;
  slotCode: string | null;
  zoneName: string | null;
  cameraId: string | null;
  evidenceUrl: string | null;
  createdAt: string;
  resolvedAt: string | null;
  resolvedBy: string | null;
  resolution: string | null;
}

const INCIDENT_TYPE_LABELS: Record<string, string> = {
  wrong_slot: "Đỗ sai chỗ",
  no_booking: "Không có booking",
  overstay: "Quá giờ",
  unauthorized: "Truy cập trái phép",
  damage: "Hư hỏng tài sản",
  other: "Khác",
};

const STATUS_CONFIG: Record<
  string,
  { label: string; variant: "default" | "secondary" | "destructive" }
> = {
  pending: { label: "Chờ xử lý", variant: "destructive" },
  resolved: { label: "Đã xử lý", variant: "default" },
  cancelled: { label: "Đã hủy", variant: "secondary" },
};

export default function AdminViolationsPage() {
  const { toast } = useToast();
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(
    null,
  );
  const [showDetailDialog, setShowDetailDialog] = useState(false);
  const [showResolveDialog, setShowResolveDialog] = useState(false);
  const [resolution, setResolution] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchIncidents = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await incidentApi.getIncidents();
      const rawResults = (response.results || []) as unknown as Array<
        Record<string, unknown>
      >;
      const mapped: Incident[] = rawResults.map((inc) => ({
        id: String(inc.id ?? ""),
        type: String(inc.type ?? inc.incident_type ?? "other"),
        description: String(inc.description ?? ""),
        status: String(inc.status ?? "pending") as Incident["status"],
        reportedBy: String(inc.reported_by ?? inc.reportedBy ?? "Hệ thống"),
        bookingId: inc.booking_id
          ? String(inc.booking_id)
          : inc.bookingId
            ? String(inc.bookingId)
            : null,
        slotCode: inc.slot_code
          ? String(inc.slot_code)
          : inc.slotCode
            ? String(inc.slotCode)
            : null,
        zoneName: inc.zone_name
          ? String(inc.zone_name)
          : inc.zoneName
            ? String(inc.zoneName)
            : null,
        cameraId: inc.camera_id ? String(inc.camera_id) : null,
        evidenceUrl: inc.evidence_url ? String(inc.evidence_url) : null,
        createdAt: String(inc.created_at ?? inc.createdAt ?? ""),
        resolvedAt: inc.resolved_at ? String(inc.resolved_at) : null,
        resolvedBy: inc.resolved_by ? String(inc.resolved_by) : null,
        resolution: inc.resolution ? String(inc.resolution) : null,
      }));
      setIncidents(mapped);
    } catch (error) {
      console.error("Failed to fetch incidents:", error);
      toast({
        title: "Lỗi",
        description: "Không thể tải danh sách vi phạm",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    fetchIncidents();
  }, [fetchIncidents]);

  const filteredIncidents = incidents.filter((inc) => {
    if (statusFilter !== "all" && inc.status !== statusFilter) return false;
    if (typeFilter !== "all" && inc.type !== typeFilter) return false;
    return true;
  });

  const stats = {
    total: incidents.length,
    pending: incidents.filter((i) => i.status === "pending").length,
    resolved: incidents.filter((i) => i.status === "resolved").length,
    cancelled: incidents.filter((i) => i.status === "cancelled").length,
  };

  const handleResolve = async () => {
    if (!selectedIncident || !resolution.trim()) return;
    setIsSubmitting(true);
    try {
      await incidentApi.resolveIncident(selectedIncident.id, { resolution });
      toast({ title: "Thành công", description: "Đã xử lý vi phạm" });
      setShowResolveDialog(false);
      setResolution("");
      await fetchIncidents();
    } catch (error) {
      console.error("Failed to resolve incident:", error);
      toast({
        title: "Lỗi",
        description: "Không thể xử lý vi phạm",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = async (incident: Incident) => {
    try {
      await incidentApi.cancelIncident(incident.id);
      toast({ title: "Thành công", description: "Đã hủy vi phạm" });
      await fetchIncidents();
    } catch (error) {
      console.error("Failed to cancel incident:", error);
      toast({
        title: "Lỗi",
        description: "Không thể hủy vi phạm",
        variant: "destructive",
      });
    }
  };

  const formatDate = (dateStr: string): string => {
    if (!dateStr) return "—";
    try {
      return new Date(dateStr).toLocaleString("vi-VN");
    } catch {
      return dateStr;
    }
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between animate-fade-in">
          <div>
            <h1 className="text-2xl font-bold text-foreground">
              Quản lý vi phạm
            </h1>
            <p className="mt-1 text-muted-foreground">
              {stats.total} vi phạm | {stats.pending} chờ xử lý
            </p>
          </div>
          <Button variant="outline" className="gap-2" onClick={fetchIncidents}>
            <RefreshCw className="h-4 w-4" />
            Làm mới
          </Button>
        </div>

        {/* Stats Cards */}
        <div className="grid gap-4 sm:grid-cols-4">
          <div className="rounded-xl border border-border bg-card p-4 flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-destructive/10">
              <ShieldAlert className="h-6 w-6 text-destructive" />
            </div>
            <div>
              <p className="text-2xl font-bold text-foreground">
                {stats.total}
              </p>
              <p className="text-sm text-muted-foreground">Tổng vi phạm</p>
            </div>
          </div>
          <div className="rounded-xl border border-border bg-card p-4 flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-warning/10">
              <Clock className="h-6 w-6 text-warning" />
            </div>
            <div>
              <p className="text-2xl font-bold text-foreground">
                {stats.pending}
              </p>
              <p className="text-sm text-muted-foreground">Chờ xử lý</p>
            </div>
          </div>
          <div className="rounded-xl border border-border bg-card p-4 flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-success/10">
              <CheckCircle2 className="h-6 w-6 text-success" />
            </div>
            <div>
              <p className="text-2xl font-bold text-foreground">
                {stats.resolved}
              </p>
              <p className="text-sm text-muted-foreground">Đã xử lý</p>
            </div>
          </div>
          <div className="rounded-xl border border-border bg-card p-4 flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-muted">
              <XCircle className="h-6 w-6 text-muted-foreground" />
            </div>
            <div>
              <p className="text-2xl font-bold text-foreground">
                {stats.cancelled}
              </p>
              <p className="text-sm text-muted-foreground">Đã hủy</p>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3 items-center">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-xl border border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none"
          >
            <option value="all">Tất cả trạng thái</option>
            <option value="pending">Chờ xử lý</option>
            <option value="resolved">Đã xử lý</option>
            <option value="cancelled">Đã hủy</option>
          </select>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="rounded-xl border border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none"
          >
            <option value="all">Tất cả loại</option>
            <option value="wrong_slot">Đỗ sai chỗ</option>
            <option value="no_booking">Không có booking</option>
            <option value="overstay">Quá giờ</option>
            <option value="unauthorized">Truy cập trái phép</option>
            <option value="damage">Hư hỏng</option>
            <option value="other">Khác</option>
          </select>
          <span className="text-sm text-muted-foreground ml-auto">
            {filteredIncidents.length} kết quả
          </span>
        </div>

        {/* Loading */}
        {isLoading && (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="h-12 w-12 animate-spin text-primary" />
            <p className="mt-4 text-muted-foreground">Đang tải vi phạm...</p>
          </div>
        )}

        {/* Incidents List */}
        {!isLoading && (
          <div className="space-y-3">
            {filteredIncidents.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <ShieldAlert className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-lg font-semibold text-foreground">
                  Không có vi phạm nào
                </p>
                <p className="text-muted-foreground">
                  {statusFilter !== "all" || typeFilter !== "all"
                    ? "Thử thay đổi bộ lọc"
                    : "Hệ thống đang hoạt động tốt"}
                </p>
              </div>
            ) : (
              filteredIncidents.map((incident) => (
                <div
                  key={incident.id}
                  className={cn(
                    "rounded-2xl border bg-card p-4 transition-all hover:shadow-md animate-slide-up",
                    incident.status === "pending"
                      ? "border-destructive/20"
                      : "border-border",
                  )}
                >
                  <div className="flex items-start gap-4">
                    <div
                      className={cn(
                        "flex h-10 w-10 items-center justify-center rounded-xl shrink-0",
                        incident.status === "pending"
                          ? "bg-destructive/10"
                          : incident.status === "resolved"
                            ? "bg-success/10"
                            : "bg-muted",
                      )}
                    >
                      <AlertTriangle
                        className={cn(
                          "h-5 w-5",
                          incident.status === "pending"
                            ? "text-destructive"
                            : incident.status === "resolved"
                              ? "text-success"
                              : "text-muted-foreground",
                        )}
                      />
                    </div>

                    <div className="flex-1 min-w-0 space-y-2">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <p className="font-semibold text-foreground">
                            {INCIDENT_TYPE_LABELS[incident.type] ||
                              incident.type}
                          </p>
                          <p className="text-sm text-muted-foreground line-clamp-2">
                            {incident.description}
                          </p>
                        </div>
                        <Badge
                          variant={
                            STATUS_CONFIG[incident.status]?.variant ??
                            "secondary"
                          }
                        >
                          {STATUS_CONFIG[incident.status]?.label ??
                            incident.status}
                        </Badge>
                      </div>

                      <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {formatDate(incident.createdAt)}
                        </span>
                        {incident.slotCode && (
                          <span className="flex items-center gap-1">
                            <Car className="h-3 w-3" />
                            Slot {incident.slotCode}
                          </span>
                        )}
                        {incident.zoneName && (
                          <span className="flex items-center gap-1">
                            <MapPin className="h-3 w-3" />
                            {incident.zoneName}
                          </span>
                        )}
                        {incident.cameraId && (
                          <span className="flex items-center gap-1">
                            <Camera className="h-3 w-3" />
                            Camera
                          </span>
                        )}
                      </div>

                      <div className="flex gap-2 pt-1">
                        <Button
                          variant="outline"
                          size="sm"
                          className="gap-1"
                          onClick={() => {
                            setSelectedIncident(incident);
                            setShowDetailDialog(true);
                          }}
                        >
                          <Eye className="h-3 w-3" />
                          Chi tiết
                        </Button>
                        {incident.status === "pending" && (
                          <>
                            <Button
                              size="sm"
                              className="gap-1 bg-success hover:bg-success/90"
                              onClick={() => {
                                setSelectedIncident(incident);
                                setResolution("");
                                setShowResolveDialog(true);
                              }}
                            >
                              <CheckCircle2 className="h-3 w-3" />
                              Xử lý
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              className="gap-1 text-destructive hover:text-destructive"
                              onClick={() => handleCancel(incident)}
                            >
                              <XCircle className="h-3 w-3" />
                              Hủy
                            </Button>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Detail Dialog */}
      <Dialog open={showDetailDialog} onOpenChange={setShowDetailDialog}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>
              Chi tiết vi phạm #{selectedIncident?.id.slice(0, 8)}
            </DialogTitle>
          </DialogHeader>
          {selectedIncident && (
            <div className="space-y-4">
              <div className="grid gap-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Loại</span>
                  <span className="font-medium">
                    {INCIDENT_TYPE_LABELS[selectedIncident.type] ||
                      selectedIncident.type}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Trạng thái</span>
                  <Badge
                    variant={
                      STATUS_CONFIG[selectedIncident.status]?.variant ??
                      "secondary"
                    }
                  >
                    {STATUS_CONFIG[selectedIncident.status]?.label ??
                      selectedIncident.status}
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Báo cáo bởi</span>
                  <span className="font-medium">
                    {selectedIncident.reportedBy}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Thời gian</span>
                  <span className="font-medium">
                    {formatDate(selectedIncident.createdAt)}
                  </span>
                </div>
                {selectedIncident.slotCode && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Slot</span>
                    <span className="font-mono font-medium">
                      {selectedIncident.slotCode}
                    </span>
                  </div>
                )}
                {selectedIncident.bookingId && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Booking</span>
                    <span className="font-mono text-xs">
                      {selectedIncident.bookingId}
                    </span>
                  </div>
                )}
              </div>

              <div className="rounded-xl bg-muted/50 p-3">
                <p className="text-sm font-medium text-foreground mb-1">
                  Mô tả:
                </p>
                <p className="text-sm text-muted-foreground">
                  {selectedIncident.description}
                </p>
              </div>

              {selectedIncident.evidenceUrl && (
                <div className="rounded-xl overflow-hidden border border-border">
                  <img
                    src={selectedIncident.evidenceUrl}
                    alt="Bằng chứng"
                    className="w-full object-cover max-h-64"
                    onError={(e) => {
                      e.currentTarget.style.display = "none";
                    }}
                  />
                </div>
              )}

              {selectedIncident.resolvedAt && (
                <div className="rounded-xl bg-success/10 border border-success/20 p-3 text-sm space-y-1">
                  <p className="font-medium text-success">Đã xử lý</p>
                  <p className="text-muted-foreground">
                    Bởi: {selectedIncident.resolvedBy || "Hệ thống"}
                  </p>
                  <p className="text-muted-foreground">
                    Lúc: {formatDate(selectedIncident.resolvedAt)}
                  </p>
                  {selectedIncident.resolution && (
                    <p className="text-muted-foreground">
                      Ghi chú: {selectedIncident.resolution}
                    </p>
                  )}
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Resolve Dialog */}
      <Dialog open={showResolveDialog} onOpenChange={setShowResolveDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Xử lý vi phạm</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Vi phạm:{" "}
              <strong>
                {INCIDENT_TYPE_LABELS[selectedIncident?.type ?? "other"]}
              </strong>
            </p>
            <div>
              <label className="block text-sm font-medium mb-1.5">
                Ghi chú xử lý <span className="text-destructive">*</span>
              </label>
              <textarea
                value={resolution}
                onChange={(e) => setResolution(e.target.value)}
                placeholder="Mô tả cách xử lý vi phạm..."
                rows={4}
                className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none resize-none"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowResolveDialog(false)}
            >
              Hủy
            </Button>
            <Button
              className="bg-success hover:bg-success/90"
              onClick={handleResolve}
              disabled={isSubmitting || !resolution.trim()}
            >
              {isSubmitting ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <CheckCircle2 className="h-4 w-4 mr-2" />
              )}
              Xác nhận xử lý
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </MainLayout>
  );
}
