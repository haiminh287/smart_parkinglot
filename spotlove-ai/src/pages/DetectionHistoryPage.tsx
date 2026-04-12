import { useState, useEffect, useCallback } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import {
  Search,
  ScanSearch,
  ChevronLeft,
  ChevronRight,
  Image as ImageIcon,
  Loader2,
  Calendar,
  RefreshCw,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { aiApi, type DetectionRecord } from "@/services/api/ai.api";

const AI_BASE_URL =
  import.meta.env.VITE_AI_SERVICE_URL || "http://localhost:8009";

const ACTION_LABELS: Record<string, { label: string; className: string }> = {
  scan: { label: "Quét", className: "bg-blue-500/10 text-blue-500" },
  check_in: {
    label: "Check-in",
    className: "bg-green-500/10 text-green-500",
  },
  check_out: {
    label: "Check-out",
    className: "bg-orange-500/10 text-orange-500",
  },
};

function formatDate(dateStr: string): string {
  if (!dateStr) return "—";
  try {
    return new Date(dateStr).toLocaleString("vi-VN");
  } catch {
    return dateStr;
  }
}

function buildImageUrl(imageUrl: string | null): string | null {
  if (!imageUrl) return null;
  if (imageUrl.startsWith("http")) return imageUrl;
  return `${AI_BASE_URL}${imageUrl}`;
}

function ConfidenceBadge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const cls =
    pct >= 80
      ? "bg-green-500/10 text-green-600"
      : pct >= 60
        ? "bg-yellow-500/10 text-yellow-600"
        : "bg-red-500/10 text-red-600";
  return (
    <Badge variant="outline" className={cls}>
      {pct}%
    </Badge>
  );
}

function DecisionBadge({ decision }: { decision: string }) {
  const isSuccess = decision.includes("success");
  return (
    <Badge
      variant="outline"
      className={
        isSuccess
          ? "bg-green-500/10 text-green-600"
          : "bg-red-500/10 text-red-600"
      }
    >
      {isSuccess ? "Thành công" : "Thất bại"}
    </Badge>
  );
}

export default function DetectionHistoryPage() {
  const { toast } = useToast();
  const [data, setData] = useState<DetectionRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [isLoading, setIsLoading] = useState(true);
  const [plateSearch, setPlateSearch] = useState("");
  const [actionFilter, setActionFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    try {
      const params: Record<string, string | number> = {
        page,
        page_size: pageSize,
      };
      if (plateSearch.trim()) params.plate_text = plateSearch.trim();
      if (actionFilter) params.action = actionFilter;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;

      const response = await aiApi.getDetectionHistory(params);
      setData(response.results);
      setTotal(response.total);
    } catch {
      toast({
        title: "Lỗi",
        description: "Không thể tải lịch sử nhận diện",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  }, [page, pageSize, plateSearch, actionFilter, dateFrom, dateTo, toast]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const totalPages = Math.ceil(total / pageSize);

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between animate-fade-in">
          <div>
            <h1 className="text-2xl font-bold text-foreground">
              Lịch sử nhận diện
            </h1>
            <p className="mt-1 text-muted-foreground">
              {total} kết quả nhận diện biển số xe
            </p>
          </div>
          <Button variant="outline" className="gap-2" onClick={fetchData}>
            <RefreshCw className="h-4 w-4" />
            Làm mới
          </Button>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3 items-center">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Tìm biển số..."
              value={plateSearch}
              onChange={(e) => {
                setPlateSearch(e.target.value);
                setPage(1);
              }}
              className="pl-9 w-48"
            />
          </div>
          <select
            value={actionFilter}
            onChange={(e) => {
              setActionFilter(e.target.value);
              setPage(1);
            }}
            className="rounded-xl border border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none"
          >
            <option value="">Tất cả</option>
            <option value="scan">Quét</option>
            <option value="check_in">Check-in</option>
            <option value="check_out">Check-out</option>
          </select>
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            <Input
              type="date"
              value={dateFrom}
              onChange={(e) => {
                setDateFrom(e.target.value);
                setPage(1);
              }}
              className="w-36"
            />
            <span className="text-muted-foreground">—</span>
            <Input
              type="date"
              value={dateTo}
              onChange={(e) => {
                setDateTo(e.target.value);
                setPage(1);
              }}
              className="w-36"
            />
          </div>
        </div>

        {/* Loading */}
        {isLoading && (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="h-12 w-12 animate-spin text-primary" />
            <p className="mt-4 text-muted-foreground">Đang tải dữ liệu...</p>
          </div>
        )}

        {/* Empty state */}
        {!isLoading && data.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <ScanSearch className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-lg font-semibold text-foreground">
              Không có dữ liệu
            </p>
            <p className="text-muted-foreground">
              Thử thay đổi bộ lọc hoặc chờ dữ liệu mới
            </p>
          </div>
        )}

        {/* Table */}
        {!isLoading && data.length > 0 && (
          <div className="rounded-2xl border border-border bg-card overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10">#</TableHead>
                  <TableHead>Thời gian</TableHead>
                  <TableHead>Biển số</TableHead>
                  <TableHead>Confidence</TableHead>
                  <TableHead>Hành động</TableHead>
                  <TableHead>Kết quả</TableHead>
                  <TableHead>Ảnh</TableHead>
                  <TableHead className="text-right">Xử lý</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.map((record, idx) => {
                  const imgUrl = buildImageUrl(record.image_url);
                  const actionInfo = ACTION_LABELS[record.action] || {
                    label: record.action,
                    className: "bg-muted text-muted-foreground",
                  };
                  return (
                    <TableRow key={record.id}>
                      <TableCell className="text-muted-foreground">
                        {(page - 1) * pageSize + idx + 1}
                      </TableCell>
                      <TableCell className="text-sm whitespace-nowrap">
                        {formatDate(record.created_at)}
                      </TableCell>
                      <TableCell>
                        <span className="font-mono font-bold text-foreground">
                          {record.plate_text || "—"}
                        </span>
                      </TableCell>
                      <TableCell>
                        <ConfidenceBadge value={record.confidence} />
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={actionInfo.className}
                        >
                          {actionInfo.label}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <DecisionBadge decision={record.decision} />
                      </TableCell>
                      <TableCell>
                        {imgUrl ? (
                          <Dialog>
                            <DialogTrigger asChild>
                              <button className="rounded-lg overflow-hidden border border-border hover:border-primary transition-colors">
                                <img
                                  src={imgUrl}
                                  alt={record.plate_text}
                                  className="h-10 w-16 object-cover"
                                  loading="lazy"
                                />
                              </button>
                            </DialogTrigger>
                            <DialogContent className="sm:max-w-lg p-2">
                              <img
                                src={imgUrl}
                                alt={record.plate_text}
                                className="w-full rounded-lg"
                              />
                            </DialogContent>
                          </Dialog>
                        ) : (
                          <div className="flex h-10 w-16 items-center justify-center rounded-lg bg-muted">
                            <ImageIcon className="h-4 w-4 text-muted-foreground" />
                          </div>
                        )}
                      </TableCell>
                      <TableCell className="text-right text-sm text-muted-foreground">
                        {record.processing_time_ms != null
                          ? `${record.processing_time_ms}ms`
                          : "—"}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}

        {/* Pagination */}
        {!isLoading && totalPages > 1 && (
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Trang {page} / {totalPages} ({total} kết quả)
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
