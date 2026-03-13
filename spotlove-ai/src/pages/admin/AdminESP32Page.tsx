import { useState, useEffect, useCallback, useRef } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Cpu,
  Wifi,
  WifiOff,
  WifiHigh,
  WifiLow,
  WifiZero,
  Activity,
  RefreshCcw,
  Terminal,
  Clock,
  Zap,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Signal,
  CircuitBoard,
  Filter,
  X,
  ServerOff,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import {
  aiApi,
  type ESP32DeviceInfo,
  type ESP32DeviceLog,
} from "@/services/api/ai.api";

// ── Helpers ──────────────────────────────────────────────────────────────

/** Classify WiFi signal strength from RSSI */
function getWifiQuality(rssi: number): {
  label: string;
  color: string;
  icon: typeof Wifi;
} {
  if (rssi >= -40)
    return { label: "Tuyệt vời", color: "text-green-500", icon: Wifi };
  if (rssi >= -55)
    return { label: "Tốt", color: "text-green-400", icon: WifiHigh };
  if (rssi >= -70)
    return { label: "Trung bình", color: "text-yellow-500", icon: WifiLow };
  return { label: "Yếu", color: "text-red-500", icon: WifiZero };
}

/** Format timestamp for Vietnamese locale */
function formatTimestamp(ts: string): string {
  return new Date(ts).toLocaleString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

/** Format relative time from now */
function timeAgo(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return `${seconds}s trước`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m trước`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h trước`;
  const days = Math.floor(hours / 24);
  return `${days}d trước`;
}

// ── Log Level Filter Type ────────────────────────────────────────────────

type LogLevel = "all" | "info" | "warning" | "error";

// ── Sub-components ──────────────────────────────────────────────────────

function StatusIndicator({ isOnline }: { isOnline: boolean }) {
  return (
    <span className="relative flex h-3 w-3">
      {isOnline && (
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
      )}
      <span
        className={cn(
          "relative inline-flex h-3 w-3 rounded-full",
          isOnline ? "bg-green-500" : "bg-red-500",
        )}
      />
    </span>
  );
}

function LogLevelBadge({ level }: { level: ESP32DeviceLog["level"] }) {
  const config = {
    info: {
      label: "INFO",
      className: "bg-blue-500/10 text-blue-600 border-blue-500/20",
    },
    warning: {
      label: "WARN",
      className: "bg-yellow-500/10 text-yellow-600 border-yellow-500/20",
    },
    error: {
      label: "ERROR",
      className: "bg-red-500/10 text-red-600 border-red-500/20",
    },
  };
  const c = config[level];
  return (
    <Badge
      variant="outline"
      className={cn("text-[10px] font-mono px-1.5 py-0", c.className)}
    >
      {c.label}
    </Badge>
  );
}

function WifiSignalDisplay({ rssi }: { rssi: number }) {
  const quality = getWifiQuality(rssi);
  const Icon = quality.icon;
  return (
    <div className="flex items-center gap-1.5">
      <Icon className={cn("h-4 w-4", quality.color)} />
      <span className={cn("text-xs font-medium", quality.color)}>
        {rssi} dBm
      </span>
      <span className="text-[10px] text-muted-foreground">
        ({quality.label})
      </span>
    </div>
  );
}

function GpioConfigDisplay({
  gpioConfig,
}: {
  gpioConfig: ESP32DeviceInfo["gpioConfig"];
}) {
  const entries = Object.entries(gpioConfig).filter(([, v]) => v !== undefined);
  if (entries.length === 0)
    return <span className="text-xs text-muted-foreground">N/A</span>;
  return (
    <div className="flex flex-wrap gap-1">
      {entries.map(([key, value]) => (
        <Badge
          key={key}
          variant="outline"
          className="text-[10px] px-1.5 py-0 font-mono"
        >
          <Zap className="h-2.5 w-2.5 mr-0.5" />
          {key}: GPIO {value}
        </Badge>
      ))}
    </div>
  );
}

// ── Device Card ──────────────────────────────────────────────────────────

function DeviceCard({
  device,
  isSelected,
  onSelect,
}: {
  device: ESP32DeviceInfo;
  isSelected: boolean;
  onSelect: () => void;
}) {
  return (
    <div
      data-testid={`device-card-${device.deviceId}`}
      onClick={onSelect}
      className={cn(
        "rounded-xl border bg-card text-card-foreground shadow-sm transition-all duration-200 cursor-pointer hover:shadow-md",
        isSelected && "ring-2 ring-primary border-primary",
        !device.isOnline && "opacity-70",
      )}
    >
      <div className="p-4 space-y-3">
        {/* Header row */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className={cn(
                "flex h-10 w-10 items-center justify-center rounded-lg",
                device.isOnline ? "bg-green-500/10" : "bg-red-500/10",
              )}
            >
              <CircuitBoard
                className={cn(
                  "h-5 w-5",
                  device.isOnline ? "text-green-600" : "text-red-600",
                )}
              />
            </div>
            <div>
              <h3 className="font-semibold text-sm flex items-center gap-2">
                {device.deviceId}
                <StatusIndicator isOnline={device.isOnline} />
              </h3>
              <p className="text-xs text-muted-foreground">{device.ip}</p>
            </div>
          </div>
          <Badge
            variant="outline"
            className={cn(
              device.isOnline
                ? "bg-green-500/10 text-green-600 border-green-500/20"
                : "bg-red-500/10 text-red-600 border-red-500/20",
            )}
          >
            {device.isOnline ? "Online" : "Offline"}
          </Badge>
        </div>

        {/* Info grid */}
        <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
          <div>
            <span className="text-muted-foreground">WiFi Signal:</span>
            <div className="mt-0.5">
              <WifiSignalDisplay rssi={device.wifiRssi} />
            </div>
          </div>
          <div>
            <span className="text-muted-foreground">Firmware:</span>
            <p className="font-medium mt-0.5">{device.firmware}</p>
          </div>
          <div className="col-span-2">
            <span className="text-muted-foreground">GPIO Config:</span>
            <div className="mt-0.5">
              <GpioConfigDisplay gpioConfig={device.gpioConfig} />
            </div>
          </div>
          <div>
            <span className="text-muted-foreground">Last Seen:</span>
            <p className="font-medium mt-0.5">{timeAgo(device.lastSeen)}</p>
          </div>
          <div>
            <span className="text-muted-foreground">Logs:</span>
            <p className="font-medium mt-0.5">{device.logCount} entries</p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Log Viewer Panel ─────────────────────────────────────────────────────

function LogViewerPanel({
  deviceId,
  onClose,
}: {
  deviceId: string;
  onClose: () => void;
}) {
  const [logs, setLogs] = useState<ESP32DeviceLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterLevel, setFilterLevel] = useState<LogLevel>("all");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchLogs = useCallback(async () => {
    try {
      const response = await aiApi.getESP32DeviceLogs(deviceId);
      setLogs(response.logs);
    } catch {
      toast.error(`Không thể tải logs cho ${deviceId}`);
    } finally {
      setLoading(false);
    }
  }, [deviceId]);

  useEffect(() => {
    setLoading(true);
    setFilterLevel("all");
    fetchLogs();

    // Auto-refresh logs every 5 seconds
    intervalRef.current = setInterval(fetchLogs, 5000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchLogs]);

  const filteredLogs =
    filterLevel === "all" ? logs : logs.filter((l) => l.level === filterLevel);

  const levelCounts = {
    info: logs.filter((l) => l.level === "info").length,
    warning: logs.filter((l) => l.level === "warning").length,
    error: logs.filter((l) => l.level === "error").length,
  };

  return (
    <div
      data-testid="log-viewer-panel"
      className="rounded-xl border bg-card shadow-sm"
    >
      {/* Panel header */}
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4 text-primary" />
          <h3 className="font-semibold text-sm">Logs — {deviceId}</h3>
          <Badge variant="outline" className="text-[10px] px-1.5 py-0">
            {logs.length} entries
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs"
            onClick={fetchLogs}
          >
            <RefreshCcw className="h-3 w-3 mr-1" />
            Refresh
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={onClose}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-2 px-4 py-2 border-b bg-muted/30">
        <Filter className="h-3 w-3 text-muted-foreground" />
        <span className="text-xs text-muted-foreground">Lọc:</span>
        {(["all", "info", "warning", "error"] as LogLevel[]).map((level) => (
          <Button
            key={level}
            variant={filterLevel === level ? "default" : "outline"}
            size="sm"
            className={cn(
              "h-6 text-[10px] px-2",
              filterLevel === level &&
                level === "info" &&
                "bg-blue-600 hover:bg-blue-700",
              filterLevel === level &&
                level === "warning" &&
                "bg-yellow-600 hover:bg-yellow-700",
              filterLevel === level &&
                level === "error" &&
                "bg-red-600 hover:bg-red-700",
            )}
            onClick={() => setFilterLevel(level)}
          >
            {level === "all"
              ? `Tất cả (${logs.length})`
              : `${level.toUpperCase()} (${levelCounts[level]})`}
          </Button>
        ))}
      </div>

      {/* Log table */}
      <div className="max-h-[420px] overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin h-6 w-6 border-4 border-primary border-t-transparent rounded-full" />
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <Activity className="h-8 w-8 mb-2" />
            <p className="text-sm">Không có log nào</p>
          </div>
        ) : (
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-muted/50 backdrop-blur-sm">
              <tr className="text-left">
                <th className="px-4 py-2 font-medium text-muted-foreground w-44">
                  Thời gian
                </th>
                <th className="px-4 py-2 font-medium text-muted-foreground w-20">
                  Level
                </th>
                <th className="px-4 py-2 font-medium text-muted-foreground">
                  Nội dung
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50">
              {filteredLogs.map((log, idx) => (
                <tr
                  key={`${log.timestamp}-${idx}`}
                  className="hover:bg-muted/30 transition-colors"
                >
                  <td className="px-4 py-2 font-mono text-muted-foreground whitespace-nowrap">
                    {formatTimestamp(log.timestamp)}
                  </td>
                  <td className="px-4 py-2">
                    <LogLevelBadge level={log.level} />
                  </td>
                  <td className="px-4 py-2 font-mono text-foreground">
                    {log.message}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Auto-refresh indicator */}
      <div className="flex items-center gap-1.5 px-4 py-2 border-t bg-muted/20 text-[10px] text-muted-foreground">
        <span className="relative flex h-1.5 w-1.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-green-500" />
        </span>
        Tự động cập nhật mỗi 5 giây
      </div>
    </div>
  );
}

// ── Empty State ──────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted mb-4">
        <ServerOff className="h-8 w-8 text-muted-foreground" />
      </div>
      <h3 className="text-lg font-semibold text-foreground mb-2">
        Không có thiết bị ESP32 nào được kết nối
      </h3>
      <p className="text-sm text-muted-foreground max-w-md">
        Hãy đảm bảo các thiết bị ESP32 Gate Controller đã được bật nguồn, kết
        nối WiFi, và đăng ký với hệ thống AI Service. Thiết bị sẽ tự động xuất
        hiện khi gửi heartbeat.
      </p>
      <div className="mt-4 rounded-lg border bg-muted/30 p-3 text-xs text-muted-foreground font-mono max-w-sm">
        <p className="mb-1">// Trên ESP32, gọi endpoint:</p>
        <p>POST /ai/parking/esp32/check-in/</p>
        <p>với header X-Gateway-Secret</p>
      </div>
    </div>
  );
}

// ── Main Page ───────────────────────────────────────────────────────────

export default function AdminESP32Page() {
  const [devices, setDevices] = useState<ESP32DeviceInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string | null>(null);

  const fetchDevices = useCallback(async () => {
    try {
      const response = await aiApi.getESP32Devices();
      setDevices(response.devices);
      // Auto-select first device if none is selected yet
      if (response.devices.length > 0) {
        setSelectedDeviceId((prev) => prev ?? response.devices[0].deviceId);
      }
    } catch {
      toast.error("Không thể tải danh sách thiết bị ESP32");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDevices();

    // Auto-refresh device list every 10 seconds
    const interval = setInterval(fetchDevices, 10000);
    return () => clearInterval(interval);
  }, [fetchDevices]);

  const onlineCount = devices.filter((d) => d.isOnline).length;
  const offlineCount = devices.filter((d) => !d.isOnline).length;

  return (
    <MainLayout>
      <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
              <Cpu className="h-6 w-6 text-primary" />
              Quản lý ESP32 Gate Controller
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Giám sát trạng thái và logs các thiết bị IoT cổng ra/vào
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setLoading(true);
              fetchDevices();
            }}
            disabled={loading}
            data-testid="refresh-devices-btn"
          >
            <RefreshCcw
              className={cn("h-4 w-4 mr-1", loading && "animate-spin")}
            />
            Làm mới
          </Button>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-xl border bg-card p-4">
            <div className="flex items-center gap-2 mb-1">
              <Cpu className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs font-medium text-muted-foreground">
                Tổng thiết bị
              </span>
            </div>
            <p className="text-2xl font-bold">{devices.length}</p>
          </div>
          <div className="rounded-xl border bg-card p-4">
            <div className="flex items-center gap-2 mb-1">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <span className="text-xs font-medium text-muted-foreground">
                Online
              </span>
            </div>
            <p className="text-2xl font-bold text-green-600">{onlineCount}</p>
          </div>
          <div className="rounded-xl border bg-card p-4">
            <div className="flex items-center gap-2 mb-1">
              <XCircle className="h-4 w-4 text-red-600" />
              <span className="text-xs font-medium text-muted-foreground">
                Offline
              </span>
            </div>
            <p className="text-2xl font-bold text-red-600">{offlineCount}</p>
          </div>
        </div>

        {/* Auto-refresh indicator */}
        <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-green-500" />
          </span>
          Danh sách thiết bị tự động cập nhật mỗi 10 giây
        </div>

        {/* Content: Device List + Log Viewer */}
        {loading && devices.length === 0 ? (
          <div className="flex items-center justify-center py-16">
            <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
          </div>
        ) : devices.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Device cards — left column */}
            <div className="lg:col-span-1 space-y-3">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Signal className="h-4 w-4 text-primary" />
                Danh sách thiết bị
              </h2>
              <div className="space-y-3">
                {devices.map((device) => (
                  <DeviceCard
                    key={device.deviceId}
                    device={device}
                    isSelected={selectedDeviceId === device.deviceId}
                    onSelect={() =>
                      setSelectedDeviceId((prev) =>
                        prev === device.deviceId ? null : device.deviceId,
                      )
                    }
                  />
                ))}
              </div>
            </div>

            {/* Log viewer panel — right column (always visible if selected) */}
            <div className="lg:col-span-2">
              {selectedDeviceId ? (
                <LogViewerPanel
                  deviceId={selectedDeviceId}
                  onClose={() => setSelectedDeviceId(null)}
                />
              ) : (
                <div className="rounded-xl border bg-card shadow-sm flex flex-col items-center justify-center py-16 text-muted-foreground">
                  <Terminal className="h-8 w-8 mb-2" />
                  <p className="text-sm">Chọn một thiết bị để xem logs</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
