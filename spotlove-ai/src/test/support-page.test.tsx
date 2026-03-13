/**
 * Tests for SupportPage — verifies rendering, chat flow, v3.0 features.
 */

import { describe, it, expect, vi, beforeEach, beforeAll } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import SupportPage from "@/pages/SupportPage";

// jsdom doesn't implement scrollIntoView
beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

// Mock dependencies
vi.mock("@/components/layout/MainLayout", () => ({
  MainLayout: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="main-layout">{children}</div>
  ),
}));

vi.mock("sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

// Mock chatbot API
const mockSendMessage = vi.fn();
const mockGetChatHistory = vi.fn();
const mockGetQuickActions = vi.fn();
const mockSubmitFeedback = vi.fn();

vi.mock("@/services/api/chatbot.api", () => ({
  chatbotApi: {
    sendMessage: (...args: unknown[]) => mockSendMessage(...args),
    getChatHistory: (...args: unknown[]) => mockGetChatHistory(...args),
    getQuickActions: (...args: unknown[]) => mockGetQuickActions(...args),
    submitFeedback: (...args: unknown[]) => mockSubmitFeedback(...args),
    getActiveConversation: vi.fn(),
    createConversation: vi.fn(),
    getChatMessages: vi.fn(),
    listConversations: vi.fn(),
    getPreferences: vi.fn(),
    updatePreferences: vi.fn(),
    getNotifications: vi.fn(),
  },
}));

describe("SupportPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetChatHistory.mockResolvedValue({
      messages: [],
      conversationId: null,
    });
  });

  it("renders welcome message", () => {
    render(<SupportPage />);
    expect(screen.getByText(/Xin chào!/)).toBeTruthy();
    expect(screen.getByText(/ParkSmart AI Assistant/)).toBeTruthy();
  });

  it("renders quick action buttons", () => {
    render(<SupportPage />);
    // "Đặt chỗ ô tô" appears in both quick actions and welcome suggestions
    expect(screen.getAllByText("Đặt chỗ ô tô").length).toBeGreaterThanOrEqual(
      1,
    );
    expect(screen.getByText("Đặt chỗ xe máy")).toBeTruthy();
    expect(screen.getByText("Xem lịch đặt")).toBeTruthy();
    expect(screen.getByText("Tìm chỗ trống")).toBeTruthy();
  });

  it("renders input field and send button", () => {
    render(<SupportPage />);
    const input = screen.getByPlaceholderText(/Nhập tin nhắn/);
    expect(input).toBeTruthy();
  });

  it("shows AI v3.0 badge", () => {
    render(<SupportPage />);
    expect(screen.getByText("AI v3.0")).toBeTruthy();
  });

  it("shows suggestions from welcome message", () => {
    render(<SupportPage />);
    // "Xem chỗ trống" and "Đặt chỗ ô tô" appear in both suggestions and quick actions
    expect(screen.getAllByText("Xem chỗ trống").length).toBeGreaterThanOrEqual(
      1,
    );
    expect(screen.getAllByText("Đặt chỗ ô tô").length).toBeGreaterThanOrEqual(
      1,
    );
    expect(screen.getByText("Xem giá")).toBeTruthy();
  });

  it("disables send button when input is empty", () => {
    render(<SupportPage />);
    const buttons = screen.getAllByRole("button");
    const sendButton = buttons.find((b) =>
      b.className.includes("gradient-primary"),
    );
    expect(sendButton).toBeTruthy();
    expect(sendButton!.hasAttribute("disabled")).toBe(true);
  });

  it("sends message and displays response", async () => {
    mockSendMessage.mockResolvedValue({
      response: "Hiện có 10 chỗ trống",
      intent: "check_slots",
      entities: {},
      suggestions: ["Đặt chỗ ngay"],
      conversationId: "conv-1",
      messageId: "msg-1",
      confidence: 0.9,
      processingTimeMs: 120,
      showMap: false,
      showQrCode: false,
      clarificationNeeded: false,
      confirmationNeeded: false,
      confidenceBreakdown: {
        llm: 0.9,
        entityCompleteness: 0.85,
        contextMatch: 0.95,
      },
      safetyCode: "SAFE",
      safetyHint: null,
    });

    render(<SupportPage />);

    const input = screen.getByPlaceholderText(/Nhập tin nhắn/);
    fireEvent.change(input, { target: { value: "Còn chỗ trống không?" } });
    fireEvent.keyPress(input, { key: "Enter", charCode: 13 });

    await waitFor(() => {
      expect(mockSendMessage).toHaveBeenCalledWith(
        "Còn chỗ trống không?",
        undefined,
      );
    });

    await waitFor(() => {
      expect(screen.getByText(/Hiện có 10 chỗ trống/)).toBeTruthy();
    });
  });

  it("displays confidence bar for assistant messages", async () => {
    mockSendMessage.mockResolvedValue({
      response: "Test response",
      intent: "test",
      entities: {},
      suggestions: [],
      conversationId: "conv-1",
      messageId: "msg-1",
      confidence: 0.85,
      processingTimeMs: 100,
      showMap: false,
      showQrCode: false,
      clarificationNeeded: false,
      confirmationNeeded: false,
    });

    render(<SupportPage />);

    const input = screen.getByPlaceholderText(/Nhập tin nhắn/);
    fireEvent.change(input, { target: { value: "Test" } });
    fireEvent.keyPress(input, { key: "Enter", charCode: 13 });

    await waitFor(() => {
      expect(screen.getByText("85%")).toBeTruthy();
      expect(screen.getByText(/100ms/)).toBeTruthy();
    });
  });

  it("shows confirmation buttons when confirmationNeeded is true", async () => {
    mockSendMessage.mockResolvedValue({
      response: "Bạn muốn đặt chỗ ô tô tại Zone A?",
      intent: "book_slot",
      entities: { zone: "A" },
      suggestions: [],
      conversationId: "conv-1",
      messageId: "msg-1",
      confidence: 0.8,
      confirmationNeeded: true,
      clarificationNeeded: false,
      showMap: false,
      showQrCode: false,
    });

    render(<SupportPage />);

    const input = screen.getByPlaceholderText(/Nhập tin nhắn/);
    fireEvent.change(input, { target: { value: "Đặt chỗ ô tô Zone A" } });
    fireEvent.keyPress(input, { key: "Enter", charCode: 13 });

    await waitFor(() => {
      expect(screen.getByText("Xác nhận")).toBeTruthy();
      expect(screen.getByText("Hủy bỏ")).toBeTruthy();
    });
  });

  it("shows clarification indicator when clarificationNeeded", async () => {
    mockSendMessage.mockResolvedValue({
      response: "Bạn muốn đặt chỗ cho loại xe nào?",
      intent: "book_slot",
      entities: {},
      suggestions: ["Ô tô", "Xe máy"],
      conversationId: "conv-1",
      messageId: "msg-1",
      confidence: 0.4,
      clarificationNeeded: true,
      confirmationNeeded: false,
      showMap: false,
      showQrCode: false,
    });

    render(<SupportPage />);

    const input = screen.getByPlaceholderText(/Nhập tin nhắn/);
    fireEvent.change(input, { target: { value: "Đặt chỗ" } });
    fireEvent.keyPress(input, { key: "Enter", charCode: 13 });

    await waitFor(() => {
      expect(screen.getByText(/Cần thêm thông tin/)).toBeTruthy();
    });
  });

  it("shows safety hint for blocked messages", async () => {
    mockSendMessage.mockResolvedValue({
      response: "Xin lỗi, tôi không thể xử lý yêu cầu này.",
      intent: null,
      entities: {},
      suggestions: [],
      conversationId: "conv-1",
      messageId: "msg-1",
      confidence: 0,
      safetyCode: "BLOCKED_PROFANITY",
      safetyHint: "Nội dung không phù hợp. Vui lòng thử lại.",
      clarificationNeeded: false,
      confirmationNeeded: false,
      showMap: false,
      showQrCode: false,
    });

    render(<SupportPage />);

    const input = screen.getByPlaceholderText(/Nhập tin nhắn/);
    fireEvent.change(input, { target: { value: "bad content" } });
    fireEvent.keyPress(input, { key: "Enter", charCode: 13 });

    await waitFor(() => {
      expect(screen.getByText(/Nội dung không phù hợp/)).toBeTruthy();
    });
  });

  it("shows map and QR code indicators", async () => {
    mockSendMessage.mockResolvedValue({
      response: "Xe bạn đang ở Zone A, slot A-12",
      intent: "current_parking",
      entities: {},
      suggestions: [],
      conversationId: "conv-1",
      messageId: "msg-1",
      showMap: true,
      showQrCode: true,
      clarificationNeeded: false,
      confirmationNeeded: false,
    });

    render(<SupportPage />);

    const input = screen.getByPlaceholderText(/Nhập tin nhắn/);
    fireEvent.change(input, { target: { value: "Xe đang đậu ở đâu?" } });
    fireEvent.keyPress(input, { key: "Enter", charCode: 13 });

    await waitFor(() => {
      expect(screen.getByText("Xem bản đồ")).toBeTruthy();
      expect(screen.getByText("Mã QR")).toBeTruthy();
    });
  });

  it("shows degraded-safe fallback on API error without fabricated booking data", async () => {
    mockSendMessage.mockRejectedValue(new Error("Network error"));

    render(<SupportPage />);

    const input = screen.getByPlaceholderText(/Nhập tin nhắn/);
    fireEvent.change(input, { target: { value: "Giá bao nhiêu?" } });
    fireEvent.keyPress(input, { key: "Enter", charCode: 13 });

    await waitFor(() => {
      expect(
        screen.getByText(/chatbot đang tạm thời không khả dụng/i),
      ).toBeTruthy();
      expect(screen.getByText(/liên hệ hỗ trợ trực tiếp/i)).toBeTruthy();
    });

    expect(screen.queryByText(/Bảng giá dịch vụ/i)).toBeNull();
    expect(screen.queryByText(/Zone A, slot A-12/i)).toBeNull();
    expect(screen.queryByText(/V1-16|A-12/i)).toBeNull();
    expect(screen.queryByText(/\d+[.,]?\d*\s*(đ|vnd|vnđ)/i)).toBeNull();
    expect(screen.queryByText(/Xe bạn đang ở Zone/i)).toBeNull();
    expect(mockSendMessage).toHaveBeenCalledWith("Giá bao nhiêu?", undefined);
  });

  it("loads chat history on mount", async () => {
    mockGetChatHistory.mockResolvedValue({
      messages: [
        {
          id: "msg-1",
          content: "Hello",
          role: "user",
          createdAt: "2026-01-01T00:00:00Z",
        },
        {
          id: "msg-2",
          content: "Hi there!",
          role: "assistant",
          createdAt: "2026-01-01T00:00:01Z",
        },
      ],
      conversationId: "conv-1",
    });

    render(<SupportPage />);

    await waitFor(() => {
      expect(mockGetChatHistory).toHaveBeenCalled();
    });
  });

  it("renders feedback button when conversation exists", async () => {
    mockSendMessage.mockResolvedValue({
      response: "OK",
      intent: "greeting",
      entities: {},
      suggestions: [],
      conversationId: "conv-1",
      messageId: "msg-1",
      clarificationNeeded: false,
      confirmationNeeded: false,
      showMap: false,
      showQrCode: false,
    });

    render(<SupportPage />);

    const input = screen.getByPlaceholderText(/Nhập tin nhắn/);
    fireEvent.change(input, { target: { value: "Hello" } });
    fireEvent.keyPress(input, { key: "Enter", charCode: 13 });

    await waitFor(() => {
      expect(screen.getByText("Đánh giá")).toBeTruthy();
    });
  });

  it("renders sidebar sections", () => {
    render(<SupportPage />);
    expect(screen.getByText("AI Assistant v3.0")).toBeTruthy();
    expect(screen.getByText("Email hỗ trợ")).toBeTruthy();
    expect(screen.getByText("Giờ làm việc")).toBeTruthy();
    expect(screen.getByText("AI hoạt động 24/7")).toBeTruthy();
  });
});
