import { describe, it, expect, vi, beforeEach, beforeAll } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import BanknoteDetectionPage from "@/pages/BanknoteDetectionPage";

// ── Polyfills ──
beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
  // URL.createObjectURL mock
  if (!globalThis.URL.createObjectURL) {
    globalThis.URL.createObjectURL = vi.fn(() => "blob:mock-url");
  }
  if (!globalThis.URL.revokeObjectURL) {
    globalThis.URL.revokeObjectURL = vi.fn();
  }
});

// ── Mocks ──
vi.mock("@/components/layout/MainLayout", () => ({
  MainLayout: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="main-layout">{children}</div>
  ),
}));

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
    warning: vi.fn(),
  },
}));

const mockDetectBanknote = vi.fn();

vi.mock("@/services/api/ai.api", () => ({
  aiApi: {
    detectBanknote: (...args: unknown[]) => mockDetectBanknote(...args),
  },
  DENOMINATION_LABELS: {
    "1000": "1.000 VND",
    "2000": "2.000 VND",
    "5000": "5.000 VND",
    "10000": "10.000 VND",
    "20000": "20.000 VND",
    "50000": "50.000 VND",
    "100000": "100.000 VND",
    "200000": "200.000 VND",
    "500000": "500.000 VND",
  },
  DENOMINATION_COLORS: {
    "1000": "#8B7355",
    "2000": "#6B8E23",
    "5000": "#4682B4",
    "10000": "#DAA520",
    "20000": "#4169E1",
    "50000": "#DB7093",
    "100000": "#228B22",
    "200000": "#CD5C5C",
    "500000": "#00CED1",
  },
}));

// ── Helpers ──
const createMockFile = (
  name = "banknote.jpg",
  type = "image/jpeg",
  size = 1024,
) => {
  const content = new Uint8Array(size);
  return new File([content], name, { type });
};

const acceptResponse = {
  decision: "accept" as const,
  denomination: "100000",
  confidence: 0.95,
  method: "color" as const,
  quality: {
    blurScore: 150.0,
    exposureScore: 128.0,
    status: "ok",
    message: "Quality OK",
  },
  detection: { found: true, confidence: 0.99, message: "Banknote detected" },
  allProbabilities: { "100000": 0.95, "200000": 0.03, "50000": 0.02 },
  stagesExecuted: ["preprocessing", "detection", "color_classification"],
  processingTimeMs: 45.2,
  processingTime: 0.045,
  message: "Accepted: 100000 VND with 95.0% confidence",
  pipelineVersion: "hybrid-mvp-v1",
};

describe("BanknoteDetectionPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── Rendering ──

  it("renders within MainLayout", () => {
    render(<BanknoteDetectionPage />);
    expect(screen.getByTestId("main-layout")).toBeInTheDocument();
  });

  it("renders page title", () => {
    render(<BanknoteDetectionPage />);
    expect(screen.getByText("Nhận diện tiền Việt Nam")).toBeInTheDocument();
  });

  it("renders subtitle with pipeline description", () => {
    render(<BanknoteDetectionPage />);
    expect(
      screen.getByText(/Hybrid AI.*Phân tích màu sắc.*MobileNetV3/i),
    ).toBeInTheDocument();
  });

  it("renders upload area", () => {
    render(<BanknoteDetectionPage />);
    expect(screen.getByText("Kéo thả ảnh vào đây")).toBeInTheDocument();
    expect(screen.getByText(/hoặc nhấn để chọn file/)).toBeInTheDocument();
  });

  it("renders mode selection buttons", () => {
    render(<BanknoteDetectionPage />);
    expect(screen.getByTestId("mode-full")).toBeInTheDocument();
    expect(screen.getByTestId("mode-fast")).toBeInTheDocument();
  });

  it("renders detect button (disabled without image)", () => {
    render(<BanknoteDetectionPage />);
    const btn = screen.getByTestId("detect-button");
    expect(btn).toBeInTheDocument();
    expect(btn).toBeDisabled();
  });

  it("renders empty state when no result", () => {
    render(<BanknoteDetectionPage />);
    expect(screen.getByTestId("empty-state")).toBeInTheDocument();
    expect(screen.getByText(/Chọn ảnh và nhấn/)).toBeInTheDocument();
  });

  // ── File Upload ──

  it("shows preview and enables detect after file selection", async () => {
    render(<BanknoteDetectionPage />);
    const file = createMockFile();
    const input = screen.getByTestId("file-input");

    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByAltText("Preview")).toBeInTheDocument();
      expect(screen.getByTestId("detect-button")).not.toBeDisabled();
    });

    // File info shown
    expect(screen.getByText(/banknote\.jpg/)).toBeInTheDocument();
  });

  it("rejects non-image files", async () => {
    const { toast } = await import("sonner");
    render(<BanknoteDetectionPage />);
    const file = new File(["text"], "doc.txt", { type: "text/plain" });
    const input = screen.getByTestId("file-input");

    fireEvent.change(input, { target: { files: [file] } });

    expect(toast.error).toHaveBeenCalledWith(
      "Vui lòng chọn file hình ảnh (JPEG, PNG, ...)",
    );
  });

  it("handles drag and drop", async () => {
    render(<BanknoteDetectionPage />);
    const dropZone = screen.getByTestId("drop-zone");
    const file = createMockFile();

    // Drag over
    fireEvent.dragOver(dropZone, { dataTransfer: { files: [] } });

    // Drop
    fireEvent.drop(dropZone, { dataTransfer: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByAltText("Preview")).toBeInTheDocument();
    });
  });

  // ── Mode Toggle ──

  it("toggles between full and fast mode", () => {
    render(<BanknoteDetectionPage />);

    // Full mode is default — check description
    expect(screen.getByText(/Chạy toàn bộ pipeline/)).toBeInTheDocument();

    // Switch to fast
    fireEvent.click(screen.getByTestId("mode-fast"));
    expect(screen.getByText(/Bỏ qua kiểm tra chất lượng/)).toBeInTheDocument();

    // Switch back to full
    fireEvent.click(screen.getByTestId("mode-full"));
    expect(screen.getByText(/Chạy toàn bộ pipeline/)).toBeInTheDocument();
  });

  // ── Detection Flow ──

  it("shows loading state during detection", async () => {
    // Make detectBanknote hang
    mockDetectBanknote.mockReturnValue(new Promise(() => {}));

    render(<BanknoteDetectionPage />);
    const input = screen.getByTestId("file-input");
    fireEvent.change(input, { target: { files: [createMockFile()] } });

    await waitFor(() => {
      expect(screen.getByTestId("detect-button")).not.toBeDisabled();
    });

    fireEvent.click(screen.getByTestId("detect-button"));

    await waitFor(() => {
      expect(screen.getByTestId("loading-state")).toBeInTheDocument();
      expect(screen.getByText("Đang phân tích ảnh...")).toBeInTheDocument();
    });
  });

  it("displays successful detection result", async () => {
    mockDetectBanknote.mockResolvedValue(acceptResponse);

    render(<BanknoteDetectionPage />);
    const input = screen.getByTestId("file-input");
    fireEvent.change(input, { target: { files: [createMockFile()] } });

    await waitFor(() => {
      expect(screen.getByTestId("detect-button")).not.toBeDisabled();
    });

    fireEvent.click(screen.getByTestId("detect-button"));

    await waitFor(() => {
      expect(screen.getByTestId("result-card")).toBeInTheDocument();
    });

    // Decision label
    expect(screen.getByText("Nhận diện thành công")).toBeInTheDocument();

    // Denomination display
    expect(screen.getByTestId("denomination-display")).toHaveTextContent(
      "100.000 VND",
    );

    // Confidence badge
    expect(screen.getByText("Độ tin cậy: 95.0%")).toBeInTheDocument();

    // Method badge
    expect(screen.getByText("Phân tích màu sắc (HSV)")).toBeInTheDocument();
  });

  it("shows toast for successful detection", async () => {
    const { toast } = await import("sonner");
    mockDetectBanknote.mockResolvedValue(acceptResponse);

    render(<BanknoteDetectionPage />);
    const input = screen.getByTestId("file-input");
    fireEvent.change(input, { target: { files: [createMockFile()] } });

    await waitFor(() => {
      expect(screen.getByTestId("detect-button")).not.toBeDisabled();
    });

    fireEvent.click(screen.getByTestId("detect-button"));

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith(
        expect.stringContaining("100.000 VND"),
      );
    });
  });

  it("shows warning toast for low confidence", async () => {
    const { toast } = await import("sonner");
    mockDetectBanknote.mockResolvedValue({
      ...acceptResponse,
      decision: "low_confidence",
      confidence: 0.5,
    });

    render(<BanknoteDetectionPage />);
    const input = screen.getByTestId("file-input");
    fireEvent.change(input, { target: { files: [createMockFile()] } });

    await waitFor(() => {
      expect(screen.getByTestId("detect-button")).not.toBeDisabled();
    });
    fireEvent.click(screen.getByTestId("detect-button"));

    await waitFor(() => {
      expect(toast.warning).toHaveBeenCalledWith(
        expect.stringContaining("Độ tin cậy thấp"),
      );
    });
  });

  it("handles API error gracefully", async () => {
    const { toast } = await import("sonner");
    mockDetectBanknote.mockRejectedValue(new Error("Service unavailable"));

    render(<BanknoteDetectionPage />);
    const input = screen.getByTestId("file-input");
    fireEvent.change(input, { target: { files: [createMockFile()] } });

    await waitFor(() => {
      expect(screen.getByTestId("detect-button")).not.toBeDisabled();
    });
    fireEvent.click(screen.getByTestId("detect-button"));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("Service unavailable");
    });
  });

  // ── Details Panel ──

  it("toggles detail section", async () => {
    mockDetectBanknote.mockResolvedValue(acceptResponse);

    render(<BanknoteDetectionPage />);
    const input = screen.getByTestId("file-input");
    fireEvent.change(input, { target: { files: [createMockFile()] } });

    await waitFor(() => {
      expect(screen.getByTestId("detect-button")).not.toBeDisabled();
    });
    fireEvent.click(screen.getByTestId("detect-button"));

    await waitFor(() => {
      expect(screen.getByTestId("result-card")).toBeInTheDocument();
    });

    // Details initially hidden
    expect(screen.queryByTestId("detail-section")).not.toBeInTheDocument();

    // Open details
    fireEvent.click(screen.getByTestId("toggle-details"));
    expect(screen.getByTestId("detail-section")).toBeInTheDocument();

    // Quality info shown
    expect(screen.getByText("Chất lượng ảnh")).toBeInTheDocument();
    expect(screen.getByText("Blur Score")).toBeInTheDocument();
    expect(screen.getByText("Exposure Score")).toBeInTheDocument();

    // Detection info shown
    expect(screen.getByText("Phát hiện vùng tiền")).toBeInTheDocument();

    // Pipeline stages shown
    expect(screen.getByText("Pipeline Stages")).toBeInTheDocument();

    // Probability breakdown shown
    expect(screen.getByText("Xác suất các mệnh giá")).toBeInTheDocument();

    // Close details
    fireEvent.click(screen.getByTestId("toggle-details"));
    expect(screen.queryByTestId("detail-section")).not.toBeInTheDocument();
  });

  // ── Reset ──

  it("resets all state on reset button click", async () => {
    mockDetectBanknote.mockResolvedValue(acceptResponse);

    render(<BanknoteDetectionPage />);
    const input = screen.getByTestId("file-input");
    fireEvent.change(input, { target: { files: [createMockFile()] } });

    await waitFor(() => {
      expect(screen.getByTestId("detect-button")).not.toBeDisabled();
    });
    fireEvent.click(screen.getByTestId("detect-button"));

    await waitFor(() => {
      expect(screen.getByTestId("result-card")).toBeInTheDocument();
    });

    // Click reset
    fireEvent.click(screen.getByTestId("reset-button"));

    // Back to empty state
    await waitFor(() => {
      expect(screen.getByTestId("empty-state")).toBeInTheDocument();
      expect(screen.queryByTestId("result-card")).not.toBeInTheDocument();
      expect(screen.getByText("Kéo thả ảnh vào đây")).toBeInTheDocument();
      expect(screen.getByTestId("detect-button")).toBeDisabled();
    });
  });

  // ── Processing time display ──

  it("displays processing stats", async () => {
    mockDetectBanknote.mockResolvedValue(acceptResponse);

    render(<BanknoteDetectionPage />);
    const input = screen.getByTestId("file-input");
    fireEvent.change(input, { target: { files: [createMockFile()] } });

    await waitFor(() => {
      expect(screen.getByTestId("detect-button")).not.toBeDisabled();
    });
    fireEvent.click(screen.getByTestId("detect-button"));

    await waitFor(() => {
      expect(screen.getByTestId("result-card")).toBeInTheDocument();
    });

    // Processing time
    expect(screen.getByText("45 ms")).toBeInTheDocument();
    // Pipeline version
    expect(screen.getByText("hybrid-mvp-v1")).toBeInTheDocument();
    // Stages count
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  // ── Calls API with correct mode ──

  it("sends correct mode to API", async () => {
    mockDetectBanknote.mockResolvedValue(acceptResponse);

    render(<BanknoteDetectionPage />);
    const input = screen.getByTestId("file-input");
    fireEvent.change(input, { target: { files: [createMockFile()] } });

    // Switch to fast mode
    fireEvent.click(screen.getByTestId("mode-fast"));

    await waitFor(() => {
      expect(screen.getByTestId("detect-button")).not.toBeDisabled();
    });
    fireEvent.click(screen.getByTestId("detect-button"));

    await waitFor(() => {
      expect(mockDetectBanknote).toHaveBeenCalledWith(expect.any(File), "fast");
    });
  });
});
