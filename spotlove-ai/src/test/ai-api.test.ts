import { describe, it, expect, vi, beforeEach } from "vitest";
import type {
  BanknoteRecognitionResponse,
  BanknoteQualityInfo,
  BanknoteDetectionInfo,
  DetectionMode,
} from "@/services/api/ai.api";
import {
  DENOMINATION_LABELS,
  DENOMINATION_COLORS,
} from "@/services/api/ai.api";

// ── Mock axios client ──
vi.mock("@/services/api/axios.client", () => {
  const mockClient = {
    post: vi.fn(),
    get: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  };
  return { default: mockClient };
});

// ── Type contract tests ──
describe("AI API Types", () => {
  it("BanknoteRecognitionResponse has required fields", () => {
    const response: BanknoteRecognitionResponse = {
      decision: "accept",
      denomination: "100000",
      confidence: 0.95,
      method: "color",
      quality: {
        blurScore: 150.5,
        exposureScore: 128.0,
        status: "ok",
        message: "Image quality is acceptable",
      },
      detection: {
        found: true,
        confidence: 0.99,
        message: "Banknote detected",
      },
      allProbabilities: { "100000": 0.95, "200000": 0.03, "50000": 0.02 },
      stagesExecuted: ["preprocessing", "detection", "color_classification"],
      processingTimeMs: 45.2,
      processingTime: 0.045,
      message: "Accepted: 100000 VND with 95.0% confidence",
      pipelineVersion: "hybrid-mvp-v1",
    };

    expect(response.decision).toBe("accept");
    expect(response.denomination).toBe("100000");
    expect(response.confidence).toBeGreaterThan(0.9);
    expect(response.method).toBe("color");
    expect(response.quality).toBeDefined();
    expect(response.detection).toBeDefined();
    expect(response.allProbabilities).toBeDefined();
    expect(response.stagesExecuted).toHaveLength(3);
    expect(response.pipelineVersion).toBe("hybrid-mvp-v1");
  });

  it("supports all decision types", () => {
    const decisions: BanknoteRecognitionResponse["decision"][] = [
      "accept",
      "low_confidence",
      "no_banknote",
      "bad_quality",
      "error",
    ];
    decisions.forEach((d) => expect(typeof d).toBe("string"));
  });

  it("supports all method types", () => {
    const methods: BanknoteRecognitionResponse["method"][] = [
      "color",
      "ai_fallback",
      "none",
    ];
    methods.forEach((m) => expect(typeof m).toBe("string"));
  });

  it("BanknoteQualityInfo has correct shape", () => {
    const quality: BanknoteQualityInfo = {
      blurScore: 200.0,
      exposureScore: 130.5,
      status: "ok",
      message: "Good quality",
    };
    expect(quality.blurScore).toBeGreaterThan(0);
    expect(quality.exposureScore).toBeGreaterThan(0);
    expect(quality.status).toBe("ok");
  });

  it("BanknoteDetectionInfo has correct shape", () => {
    const detection: BanknoteDetectionInfo = {
      found: true,
      confidence: 0.98,
      message: "Found banknote",
    };
    expect(detection.found).toBe(true);
    expect(detection.confidence).toBeCloseTo(0.98, 2);
  });

  it("DetectionMode supports full and fast", () => {
    const modes: DetectionMode[] = ["full", "fast"];
    expect(modes).toContain("full");
    expect(modes).toContain("fast");
  });

  it("allows null quality and detection", () => {
    const response: BanknoteRecognitionResponse = {
      decision: "error",
      denomination: null,
      confidence: 0,
      method: "none",
      quality: null,
      detection: null,
      allProbabilities: null,
      stagesExecuted: [],
      processingTimeMs: 5.0,
      processingTime: 0.005,
      message: "Internal error",
      pipelineVersion: "hybrid-mvp-v1",
    };
    expect(response.quality).toBeNull();
    expect(response.detection).toBeNull();
    expect(response.allProbabilities).toBeNull();
  });
});

// ── Denomination constants ──
describe("Denomination Constants", () => {
  it("DENOMINATION_LABELS has all 9 denominations", () => {
    const expectedDenoms = [
      "1000",
      "2000",
      "5000",
      "10000",
      "20000",
      "50000",
      "100000",
      "200000",
      "500000",
    ];
    expectedDenoms.forEach((d) => {
      expect(DENOMINATION_LABELS).toHaveProperty(d);
      expect(DENOMINATION_LABELS[d]).toContain("VND");
    });
    expect(Object.keys(DENOMINATION_LABELS)).toHaveLength(9);
  });

  it("DENOMINATION_COLORS has all 9 denominations", () => {
    const expectedDenoms = [
      "1000",
      "2000",
      "5000",
      "10000",
      "20000",
      "50000",
      "100000",
      "200000",
      "500000",
    ];
    expectedDenoms.forEach((d) => {
      expect(DENOMINATION_COLORS).toHaveProperty(d);
      expect(DENOMINATION_COLORS[d]).toMatch(/^#[0-9A-Fa-f]{6}$/);
    });
    expect(Object.keys(DENOMINATION_COLORS)).toHaveLength(9);
  });

  it("labels are formatted correctly", () => {
    expect(DENOMINATION_LABELS["100000"]).toBe("100.000 VND");
    expect(DENOMINATION_LABELS["500000"]).toBe("500.000 VND");
    expect(DENOMINATION_LABELS["1000"]).toBe("1.000 VND");
  });
});

// ── API endpoint tests ──
describe("AI API Endpoints", () => {
  let apiClient: {
    post: ReturnType<typeof vi.fn>;
    get: ReturnType<typeof vi.fn>;
  };

  beforeEach(async () => {
    vi.clearAllMocks();
    const mod = await import("@/services/api/axios.client");
    apiClient = mod.default as unknown as typeof apiClient;
  });

  it("detectBanknote sends POST with FormData (full mode)", async () => {
    const mockResponse: BanknoteRecognitionResponse = {
      decision: "accept",
      denomination: "100000",
      confidence: 0.95,
      method: "color",
      quality: {
        blurScore: 150,
        exposureScore: 128,
        status: "ok",
        message: "OK",
      },
      detection: { found: true, confidence: 0.99, message: "Found" },
      allProbabilities: { "100000": 0.95 },
      stagesExecuted: ["preprocessing", "detection", "color_classification"],
      processingTimeMs: 30,
      processingTime: 0.03,
      message: "Accepted",
      pipelineVersion: "hybrid-mvp-v1",
    };

    apiClient.post.mockResolvedValue({ data: mockResponse });

    const { aiApi } = await import("@/services/api/ai.api");
    const file = new File(["test"], "banknote.jpg", { type: "image/jpeg" });
    const result = await aiApi.detectBanknote(file, "full");

    expect(apiClient.post).toHaveBeenCalledTimes(1);
    const [url, formData, config] = apiClient.post.mock.calls[0];
    expect(url).toBe("/ai/detect/banknote/?mode=full");
    expect(formData).toBeInstanceOf(FormData);
    expect(formData.get("image")).toBeTruthy();
    expect(config.headers["Content-Type"]).toBe("multipart/form-data");
    expect(result.decision).toBe("accept");
    expect(result.denomination).toBe("100000");
  });

  it("detectBanknote uses fast mode when specified", async () => {
    apiClient.post.mockResolvedValue({
      data: {
        decision: "accept",
        denomination: "50000",
        confidence: 0.88,
        method: "color",
        quality: null,
        detection: null,
        allProbabilities: {},
        stagesExecuted: ["color_classification"],
        processingTimeMs: 10,
        processingTime: 0.01,
        message: "Accepted fast",
        pipelineVersion: "hybrid-mvp-v1",
      },
    });

    const { aiApi } = await import("@/services/api/ai.api");
    const file = new File(["test"], "note.png", { type: "image/png" });
    const result = await aiApi.detectBanknote(file, "fast");

    const [url] = apiClient.post.mock.calls[0];
    expect(url).toBe("/ai/detect/banknote/?mode=fast");
    expect(result.denomination).toBe("50000");
  });

  it("detectBanknote defaults to full mode", async () => {
    apiClient.post.mockResolvedValue({
      data: {
        decision: "no_banknote",
        denomination: null,
        confidence: 0,
        method: "none",
        quality: {
          blurScore: 100,
          exposureScore: 128,
          status: "ok",
          message: "OK",
        },
        detection: { found: false, confidence: 0, message: "No banknote" },
        allProbabilities: null,
        stagesExecuted: ["preprocessing", "detection"],
        processingTimeMs: 20,
        processingTime: 0.02,
        message: "No banknote detected",
        pipelineVersion: "hybrid-mvp-v1",
      },
    });

    const { aiApi } = await import("@/services/api/ai.api");
    const file = new File(["test"], "photo.jpg", { type: "image/jpeg" });
    await aiApi.detectBanknote(file);

    const [url] = apiClient.post.mock.calls[0];
    expect(url).toBe("/ai/detect/banknote/?mode=full");
  });

  it("propagates API errors", async () => {
    apiClient.post.mockRejectedValue(new Error("Network Error"));

    const { aiApi } = await import("@/services/api/ai.api");
    const file = new File(["test"], "err.jpg", { type: "image/jpeg" });

    await expect(aiApi.detectBanknote(file)).rejects.toThrow("Network Error");
  });
});
