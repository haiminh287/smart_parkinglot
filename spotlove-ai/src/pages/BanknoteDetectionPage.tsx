import { useState, useCallback, useRef } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";
import {
  Upload,
  Camera,
  RotateCcw,
  Zap,
  ScanLine,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Loader2,
  Info,
  ChevronDown,
  ChevronUp,
  Banknote,
  Eye,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  aiService,
  DENOMINATION_LABELS,
  DENOMINATION_COLORS,
} from "@/services/business/ai.service";
import type {
  BanknoteRecognitionResponse,
  DetectionMode,
} from "@/services/business/ai.service";

// ── Decision Display Config ──────────────────────

const DECISION_CONFIG: Record<
  string,
  { label: string; color: string; icon: React.ElementType; bgClass: string }
> = {
  accept: {
    label: "Nhận diện thành công",
    color: "text-green-600 dark:text-green-400",
    icon: CheckCircle,
    bgClass:
      "bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-800",
  },
  low_confidence: {
    label: "Độ tin cậy thấp",
    color: "text-yellow-600 dark:text-yellow-400",
    icon: AlertTriangle,
    bgClass:
      "bg-yellow-50 dark:bg-yellow-950/30 border-yellow-200 dark:border-yellow-800",
  },
  no_banknote: {
    label: "Không tìm thấy tiền",
    color: "text-red-600 dark:text-red-400",
    icon: XCircle,
    bgClass: "bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800",
  },
  bad_quality: {
    label: "Ảnh chất lượng kém",
    color: "text-orange-600 dark:text-orange-400",
    icon: AlertTriangle,
    bgClass:
      "bg-orange-50 dark:bg-orange-950/30 border-orange-200 dark:border-orange-800",
  },
  error: {
    label: "Lỗi xử lý",
    color: "text-red-600 dark:text-red-400",
    icon: XCircle,
    bgClass: "bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800",
  },
};

const METHOD_LABELS: Record<string, string> = {
  color: "Phân tích màu sắc (HSV)",
  ai_fallback: "AI MobileNetV3",
  none: "Không xác định",
};

// ── Component ────────────────────────────────────

export default function BanknoteDetectionPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [mode, setMode] = useState<DetectionMode>("full");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BanknoteRecognitionResponse | null>(
    null,
  );
  const [showDetails, setShowDetails] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── File handling ──

  const handleFile = useCallback((file: File) => {
    if (!file.type.startsWith("image/")) {
      toast.error("Vui lòng chọn file hình ảnh (JPEG, PNG, ...)");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      toast.error("File quá lớn. Giới hạn 10MB.");
      return;
    }
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setResult(null);
    setShowDetails(false);
  }, []);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);
      const file = e.dataTransfer.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  // ── Detection ──

  const handleDetect = async () => {
    if (!selectedFile) {
      toast.error("Vui lòng chọn ảnh trước");
      return;
    }
    setLoading(true);
    setResult(null);
    try {
      const response = await aiService.detectBanknote(selectedFile, mode);
      setResult(response);
      if (response.decision === "accept") {
        const label = response.denomination
          ? DENOMINATION_LABELS[response.denomination] ||
            `${response.denomination} VND`
          : "Không rõ";
        toast.success(
          `Nhận diện: ${label} (${(response.confidence * 100).toFixed(1)}%)`,
        );
      } else if (response.decision === "low_confidence") {
        toast.warning("Độ tin cậy thấp — thử chụp lại với ánh sáng tốt hơn");
      } else if (response.decision === "bad_quality") {
        toast.warning("Ảnh chất lượng kém — vui lòng chụp rõ nét hơn");
      } else if (response.decision === "error") {
        toast.error(response.message || "Đã xảy ra lỗi");
      }
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : "Không thể kết nối đến AI service";
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setResult(null);
    setShowDetails(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  // ── Render helpers ──

  const decisionConfig = result
    ? DECISION_CONFIG[result.decision] || DECISION_CONFIG.error
    : null;

  const denominationLabel = result?.denomination
    ? DENOMINATION_LABELS[result.denomination] || `${result.denomination} VND`
    : null;

  const denominationColor = result?.denomination
    ? DENOMINATION_COLORS[result.denomination] || "#6B7280"
    : "#6B7280";

  return (
    <MainLayout>
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 text-white">
            <Banknote className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-foreground">
              Nhận diện tiền Việt Nam
            </h1>
            <p className="text-sm text-muted-foreground">
              Hybrid AI: Phân tích màu sắc + MobileNetV3 Fallback
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Column — Upload + Controls */}
          <div className="space-y-4">
            {/* Upload Area */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Upload className="h-5 w-5" />
                  Tải ảnh lên
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div
                  data-testid="drop-zone"
                  className={cn(
                    "border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all duration-200",
                    dragActive
                      ? "border-primary bg-primary/5 scale-[1.02]"
                      : "border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/50",
                    previewUrl && "p-2",
                  )}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                >
                  {previewUrl ? (
                    <img
                      src={previewUrl}
                      alt="Preview"
                      className="w-full h-64 object-contain rounded-lg"
                    />
                  ) : (
                    <div className="py-8 space-y-3">
                      <Camera className="h-12 w-12 mx-auto text-muted-foreground/50" />
                      <div>
                        <p className="font-medium text-foreground">
                          Kéo thả ảnh vào đây
                        </p>
                        <p className="text-sm text-muted-foreground mt-1">
                          hoặc nhấn để chọn file (JPEG, PNG — tối đa 10MB)
                        </p>
                      </div>
                    </div>
                  )}
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={handleFileChange}
                    data-testid="file-input"
                  />
                </div>

                {selectedFile && (
                  <p className="text-xs text-muted-foreground mt-2 truncate">
                    📎 {selectedFile.name} (
                    {(selectedFile.size / 1024).toFixed(0)} KB)
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Mode Selection + Actions */}
            <Card>
              <CardContent className="pt-6 space-y-4">
                {/* Mode Toggle */}
                <div>
                  <label className="text-sm font-medium text-foreground mb-2 block">
                    Chế độ nhận diện
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    <Button
                      variant={mode === "full" ? "default" : "outline"}
                      size="sm"
                      onClick={() => setMode("full")}
                      className="w-full"
                      data-testid="mode-full"
                    >
                      <ScanLine className="h-4 w-4 mr-1" />
                      Đầy đủ
                    </Button>
                    <Button
                      variant={mode === "fast" ? "default" : "outline"}
                      size="sm"
                      onClick={() => setMode("fast")}
                      className="w-full"
                      data-testid="mode-fast"
                    >
                      <Zap className="h-4 w-4 mr-1" />
                      Nhanh
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {mode === "full"
                      ? "Chạy toàn bộ pipeline: Tiền xử lý → Phát hiện → Phân tích màu → AI Fallback"
                      : "Bỏ qua kiểm tra chất lượng, ưu tiên tốc độ"}
                  </p>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-2">
                  <Button
                    className="flex-1"
                    onClick={handleDetect}
                    disabled={!selectedFile || loading}
                    data-testid="detect-button"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Đang xử lý...
                      </>
                    ) : (
                      <>
                        <Eye className="h-4 w-4 mr-2" />
                        Nhận diện
                      </>
                    )}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={handleReset}
                    disabled={loading}
                    data-testid="reset-button"
                  >
                    <RotateCcw className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Right Column — Results */}
          <div className="space-y-4">
            {/* Result Card */}
            {result && decisionConfig && (
              <Card
                className={cn("border", decisionConfig.bgClass)}
                data-testid="result-card"
              >
                <CardContent className="pt-6 space-y-4">
                  {/* Decision Header */}
                  <div className="flex items-center gap-3">
                    <decisionConfig.icon
                      className={cn("h-8 w-8", decisionConfig.color)}
                    />
                    <div>
                      <p
                        className={cn(
                          "font-semibold text-lg",
                          decisionConfig.color,
                        )}
                      >
                        {decisionConfig.label}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {result.message}
                      </p>
                    </div>
                  </div>

                  {/* Denomination Display */}
                  {result.decision === "accept" && denominationLabel && (
                    <div className="text-center py-4">
                      <div
                        className="inline-block px-6 py-3 rounded-2xl text-white font-bold text-3xl shadow-lg"
                        style={{ backgroundColor: denominationColor }}
                        data-testid="denomination-display"
                      >
                        {denominationLabel}
                      </div>
                      <div className="mt-2 flex items-center justify-center gap-2">
                        <Badge variant="secondary">
                          Độ tin cậy: {(result.confidence * 100).toFixed(1)}%
                        </Badge>
                        <Badge variant="outline">
                          {METHOD_LABELS[result.method] || result.method}
                        </Badge>
                      </div>
                    </div>
                  )}

                  {/* Confidence Bar */}
                  {result.confidence > 0 && (
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-muted-foreground">
                          Độ tin cậy
                        </span>
                        <span className="font-medium">
                          {(result.confidence * 100).toFixed(1)}%
                        </span>
                      </div>
                      <Progress
                        value={result.confidence * 100}
                        className="h-2"
                      />
                    </div>
                  )}

                  {/* Quick Stats */}
                  <div className="grid grid-cols-3 gap-2 text-center text-xs">
                    <div className="p-2 rounded-lg bg-background/50">
                      <p className="text-muted-foreground">Thời gian</p>
                      <p className="font-medium">
                        {result.processingTimeMs?.toFixed(0) ||
                          result.processingTime?.toFixed(0) ||
                          "N/A"}{" "}
                        ms
                      </p>
                    </div>
                    <div className="p-2 rounded-lg bg-background/50">
                      <p className="text-muted-foreground">Pipeline</p>
                      <p className="font-medium">{result.pipelineVersion}</p>
                    </div>
                    <div className="p-2 rounded-lg bg-background/50">
                      <p className="text-muted-foreground">Stages</p>
                      <p className="font-medium">
                        {result.stagesExecuted?.length || 0}
                      </p>
                    </div>
                  </div>

                  {/* Toggle Details */}
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full"
                    onClick={() => setShowDetails(!showDetails)}
                    data-testid="toggle-details"
                  >
                    {showDetails ? (
                      <>
                        <ChevronUp className="h-4 w-4 mr-1" /> Ẩn chi tiết
                      </>
                    ) : (
                      <>
                        <ChevronDown className="h-4 w-4 mr-1" /> Xem chi tiết
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>
            )}

            {/* Detailed Info (collapsible) */}
            {result && showDetails && (
              <div className="space-y-4" data-testid="detail-section">
                {/* Quality Info */}
                {result.quality && (
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <Info className="h-4 w-4" />
                        Chất lượng ảnh
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">
                          Trạng thái
                        </span>
                        <Badge
                          variant={
                            result.quality.status === "ok"
                              ? "default"
                              : "destructive"
                          }
                        >
                          {result.quality.status === "ok"
                            ? "Tốt"
                            : result.quality.status}
                        </Badge>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">
                          Blur Score
                        </span>
                        <span>{result.quality.blurScore.toFixed(1)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">
                          Exposure Score
                        </span>
                        <span>{result.quality.exposureScore.toFixed(1)}</span>
                      </div>
                      <p className="text-xs text-muted-foreground italic">
                        {result.quality.message}
                      </p>
                    </CardContent>
                  </Card>
                )}

                {/* Detection Info */}
                {result.detection && (
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <ScanLine className="h-4 w-4" />
                        Phát hiện vùng tiền
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Phát hiện</span>
                        <Badge
                          variant={
                            result.detection.found ? "default" : "secondary"
                          }
                        >
                          {result.detection.found ? "Có" : "Không"}
                        </Badge>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">
                          Confidence
                        </span>
                        <span>
                          {(result.detection.confidence * 100).toFixed(1)}%
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground italic">
                        {result.detection.message}
                      </p>
                    </CardContent>
                  </Card>
                )}

                {/* Pipeline Stages */}
                {result.stagesExecuted && result.stagesExecuted.length > 0 && (
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <Zap className="h-4 w-4" />
                        Pipeline Stages
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex flex-wrap gap-1.5">
                        {result.stagesExecuted.map((stage, i) => (
                          <Badge key={i} variant="outline" className="text-xs">
                            {i + 1}. {stage}
                          </Badge>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Probability Breakdown */}
                {result.allProbabilities &&
                  Object.keys(result.allProbabilities).length > 0 && (
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm flex items-center gap-2">
                          <BarChartIcon className="h-4 w-4" />
                          Xác suất các mệnh giá
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-2">
                        {Object.entries(result.allProbabilities)
                          .sort(([, a], [, b]) => b - a)
                          .map(([denom, prob]) => (
                            <div
                              key={denom}
                              className="flex items-center gap-2"
                            >
                              <span className="text-xs w-24 text-right font-medium">
                                {DENOMINATION_LABELS[denom] || `${denom} VND`}
                              </span>
                              <div className="flex-1 h-4 bg-muted rounded-full overflow-hidden">
                                <div
                                  className="h-full rounded-full transition-all duration-500"
                                  style={{
                                    width: `${Math.max(prob * 100, 1)}%`,
                                    backgroundColor:
                                      DENOMINATION_COLORS[denom] || "#6B7280",
                                  }}
                                />
                              </div>
                              <span className="text-xs w-12 text-muted-foreground">
                                {(prob * 100).toFixed(1)}%
                              </span>
                            </div>
                          ))}
                      </CardContent>
                    </Card>
                  )}
              </div>
            )}

            {/* Empty State */}
            {!result && !loading && (
              <Card className="border-dashed" data-testid="empty-state">
                <CardContent className="pt-6 text-center py-12">
                  <Banknote className="h-16 w-16 mx-auto text-muted-foreground/30 mb-4" />
                  <p className="text-muted-foreground">
                    Chọn ảnh và nhấn <strong>Nhận diện</strong> để bắt đầu
                  </p>
                  <p className="text-xs text-muted-foreground/70 mt-2">
                    Hỗ trợ tất cả mệnh giá VND: 1k, 2k, 5k, 10k, 20k, 50k, 100k,
                    200k, 500k
                  </p>
                </CardContent>
              </Card>
            )}

            {/* Loading State */}
            {loading && (
              <Card data-testid="loading-state">
                <CardContent className="pt-6 text-center py-12">
                  <Loader2 className="h-12 w-12 mx-auto text-primary animate-spin mb-4" />
                  <p className="text-muted-foreground">Đang phân tích ảnh...</p>
                  <p className="text-xs text-muted-foreground/70 mt-1">
                    {mode === "full" ? "Pipeline đầy đủ" : "Chế độ nhanh"}
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </MainLayout>
  );
}

// Simple bar chart icon since lucide doesn't export BarChart directly with that name
function BarChartIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <line x1="12" y1="20" x2="12" y2="10" />
      <line x1="18" y1="20" x2="18" y2="4" />
      <line x1="6" y1="20" x2="6" y2="16" />
    </svg>
  );
}
