/**
 * Tests for chatbot.api.ts — verifies types, endpoint paths, and API contract.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import type {
  ChatResponse,
  ChatMessage,
  Conversation,
  QuickAction,
} from "@/services/api/chatbot.api";

// Mock axios client
vi.mock("@/services/api/axios.client", () => {
  const mockClient = {
    post: vi.fn(),
    get: vi.fn(),
    put: vi.fn(),
  };
  return { default: mockClient };
});

describe("Chatbot API Types", () => {
  it("ChatResponse includes v3.0 fields", () => {
    const response: ChatResponse = {
      response: "Test response",
      intent: "check_slots",
      entities: { vehicleType: "car" },
      suggestions: ["Đặt chỗ"],
      conversationId: "conv-1",
      messageId: "msg-1",
      confidence: 0.85,
      processingTimeMs: 150,
      showMap: true,
      showQrCode: false,
      clarificationNeeded: false,
      confirmationNeeded: true,
      confidenceBreakdown: {
        llm: 0.9,
        entityCompleteness: 0.8,
        contextMatch: 0.7,
      },
      safetyCode: "SAFE",
      safetyHint: null,
    };
    expect(response.confidence).toBe(0.85);
    expect(response.confidenceBreakdown?.llm).toBe(0.9);
    expect(response.safetyCode).toBe("SAFE");
    expect(response.confirmationNeeded).toBe(true);
    expect(response.showMap).toBe(true);
  });

  it("ChatMessage includes extended fields", () => {
    const msg: ChatMessage = {
      id: "msg-1",
      conversationId: "conv-1",
      role: "assistant",
      content: "Hello",
      intent: "greeting",
      entities: {},
      confidence: 0.9,
      decisionData: { showMap: true },
      processingTimeMs: 100,
      createdAt: "2026-01-01T00:00:00Z",
    };
    expect(msg.confidence).toBe(0.9);
    expect(msg.decisionData).toEqual({ showMap: true });
  });

  it("Conversation includes v3.0 fields", () => {
    const conv: Conversation = {
      id: "conv-1",
      userId: "user-1",
      currentState: "idle",
      totalTurns: 5,
      clarificationCount: 1,
      handoffRequested: false,
      satisfactionScore: 4.5,
      context: {},
      createdAt: "2026-01-01T00:00:00Z",
      updatedAt: "2026-01-01T00:00:00Z",
    };
    expect(conv.totalTurns).toBe(5);
    expect(conv.clarificationCount).toBe(1);
    expect(conv.handoffRequested).toBe(false);
  });

  it("QuickAction has required fields", () => {
    const action: QuickAction = {
      id: "check_slots",
      label: "Xem chỗ trống",
      icon: "mapPin",
      prompt: "Còn chỗ trống không?",
    };
    expect(action.id).toBe("check_slots");
    expect(action.prompt).toBeTruthy();
  });
});

describe("Chatbot API Endpoints", () => {
  let apiClient: {
    post: ReturnType<typeof vi.fn>;
    get: ReturnType<typeof vi.fn>;
    put: ReturnType<typeof vi.fn>;
  };

  beforeEach(async () => {
    vi.clearAllMocks();
    const mod = await import("@/services/api/axios.client");
    apiClient = mod.default as typeof apiClient;
  });

  it("sendMessage calls POST /chatbot/chat/", async () => {
    const mockResponse = {
      data: {
        response: "OK",
        intent: "greeting",
        entities: {},
        suggestions: [],
        conversationId: "conv-1",
        messageId: "msg-1",
      },
    };
    apiClient.post.mockResolvedValue(mockResponse);

    const { chatbotApi } = await import("@/services/api/chatbot.api");
    const result = await chatbotApi.sendMessage("hello", "conv-1");

    expect(apiClient.post).toHaveBeenCalledWith("/chatbot/chat/", {
      message: "hello",
      conversationId: "conv-1",
    });
    expect(result.response).toBe("OK");
  });

  it("getQuickActions calls GET /chatbot/quick-actions/", async () => {
    apiClient.get.mockResolvedValue({
      data: {
        quickActions: [
          { id: "test", label: "Test", icon: "star", prompt: "Test" },
        ],
      },
    });

    const { chatbotApi } = await import("@/services/api/chatbot.api");
    const result = await chatbotApi.getQuickActions();

    expect(apiClient.get).toHaveBeenCalledWith("/chatbot/quick-actions/");
    expect(result.quickActions).toHaveLength(1);
  });

  it("getChatHistory calls GET /chatbot/conversations/history/latest/", async () => {
    apiClient.get.mockResolvedValue({
      data: { messages: [], conversationId: null },
    });

    const { chatbotApi } = await import("@/services/api/chatbot.api");
    await chatbotApi.getChatHistory();

    expect(apiClient.get).toHaveBeenCalledWith(
      "/chatbot/conversations/history/latest/",
    );
  });

  it("getChatMessages calls GET /chatbot/conversations/{id}/messages/", async () => {
    apiClient.get.mockResolvedValue({
      data: { messages: [], conversationId: "conv-123" },
    });

    const { chatbotApi } = await import("@/services/api/chatbot.api");
    await chatbotApi.getChatMessages("conv-123");

    expect(apiClient.get).toHaveBeenCalledWith(
      "/chatbot/conversations/conv-123/messages/",
    );
  });

  it("getActiveConversation calls GET /chatbot/conversations/active/", async () => {
    apiClient.get.mockResolvedValue({
      data: {
        conversation: { id: "conv-1" },
        messages: [],
      },
    });

    const { chatbotApi } = await import("@/services/api/chatbot.api");
    await chatbotApi.getActiveConversation();

    expect(apiClient.get).toHaveBeenCalledWith(
      "/chatbot/conversations/active/",
    );
  });

  it("createConversation calls POST /chatbot/conversations/", async () => {
    apiClient.post.mockResolvedValue({
      data: { id: "conv-new", userId: "user-1" },
    });

    const { chatbotApi } = await import("@/services/api/chatbot.api");
    await chatbotApi.createConversation();

    expect(apiClient.post).toHaveBeenCalledWith("/chatbot/conversations/");
  });

  it("submitFeedback calls POST /chatbot/feedback/", async () => {
    apiClient.post.mockResolvedValue({
      data: { message: "Thanks", rating: 5 },
    });

    const { chatbotApi } = await import("@/services/api/chatbot.api");
    await chatbotApi.submitFeedback({
      conversationId: "conv-1",
      rating: 5,
      comment: "Great!",
    });

    expect(apiClient.post).toHaveBeenCalledWith("/chatbot/feedback/", {
      conversationId: "conv-1",
      rating: 5,
      comment: "Great!",
    });
  });

  it("getPreferences calls GET /chatbot/preferences/", async () => {
    apiClient.get.mockResolvedValue({ data: {} });

    const { chatbotApi } = await import("@/services/api/chatbot.api");
    await chatbotApi.getPreferences();

    expect(apiClient.get).toHaveBeenCalledWith("/chatbot/preferences/");
  });

  it("getNotifications calls GET /chatbot/notifications/", async () => {
    apiClient.get.mockResolvedValue({
      data: { notifications: [], count: 0 },
    });

    const { chatbotApi } = await import("@/services/api/chatbot.api");
    await chatbotApi.getNotifications();

    expect(apiClient.get).toHaveBeenCalledWith("/chatbot/notifications/");
  });
});
