/**
 * Chatbot API Service
 * API calls for chatbot interactions — fully aligned with chatbot-service-fastapi v3.0
 */

import apiClient from "./axios.client";

// =====================
// Types
// =====================

export interface ChatMessage {
  id: string;
  conversationId: string;
  role: "user" | "assistant";
  content: string;
  intent?: string;
  entities?: Record<string, unknown>;
  confidence?: number | null;
  decisionData?: Record<string, unknown>;
  actionTaken?: string;
  actionResult?: Record<string, unknown>;
  processingTimeMs?: number | null;
  createdAt: string;
}

export interface ChatResponse {
  response: string;
  intent: string | null;
  entities: Record<string, unknown>;
  suggestions: string[];
  data?: Record<string, unknown>;
  conversationId: string;
  messageId: string;
  // 🔥 v3.0 fields
  confidence?: number | null;
  processingTimeMs?: number | null;
  showMap?: boolean;
  showQrCode?: boolean;
  clarificationNeeded?: boolean;
  confirmationNeeded?: boolean;
  // 🔥 2.2: Hybrid confidence breakdown
  confidenceBreakdown?: {
    llm?: number;
    entityCompleteness?: number;
    contextMatch?: number;
  };
  // 🔥 2.3: Safety codes
  safetyCode?: string | null;
  safetyHint?: string | null;
}

export interface QuickAction {
  id: string;
  label: string;
  icon: string;
  prompt: string;
}

export interface Conversation {
  id: string;
  userId: string;
  currentState: string;
  totalTurns: number;
  clarificationCount: number;
  handoffRequested: boolean;
  satisfactionScore?: number | null;
  context: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface ActiveConversationResponse {
  conversation: Conversation;
  messages: ChatMessage[];
}

export interface FeedbackRequest {
  conversationId: string;
  rating: number; // 1-5
  comment?: string;
}

// =====================
// API Endpoints
// =====================

export const chatbotApi = {
  /**
   * Send a chat message and get AI response
   * POST /chatbot/chat/
   */
  sendMessage: async (
    message: string,
    conversationId?: string,
  ): Promise<ChatResponse> => {
    const response = await apiClient.post<ChatResponse>("/chatbot/chat/", {
      message,
      conversationId,
    });
    return response.data;
  },

  /**
   * Get quick action buttons
   * GET /chatbot/quick-actions/
   */
  getQuickActions: async (): Promise<{ quickActions: QuickAction[] }> => {
    const response = await apiClient.get("/chatbot/quick-actions/");
    return response.data;
  },

  /**
   * Get chat history for a specific conversation
   * GET /chatbot/conversations/{conversationId}/messages/
   */
  getChatMessages: async (
    conversationId: string,
  ): Promise<{ messages: ChatMessage[]; conversationId: string }> => {
    const response = await apiClient.get(
      `/chatbot/conversations/${conversationId}/messages/`,
    );
    return response.data;
  },

  /**
   * Get latest conversation history (no conversationId needed)
   * GET /chatbot/conversations/history/latest/
   */
  getChatHistory: async (): Promise<{
    messages: ChatMessage[];
    conversationId: string | null;
  }> => {
    const response = await apiClient.get(
      "/chatbot/conversations/history/latest/",
    );
    return response.data;
  },

  /**
   * Get or create active conversation with recent messages
   * GET /chatbot/conversations/active/
   */
  getActiveConversation: async (): Promise<ActiveConversationResponse> => {
    const response = await apiClient.get<ActiveConversationResponse>(
      "/chatbot/conversations/active/",
    );
    return response.data;
  },

  /**
   * List all conversations for current user
   * GET /chatbot/conversations/
   */
  listConversations: async (): Promise<Conversation[]> => {
    const response = await apiClient.get<Conversation[]>(
      "/chatbot/conversations/",
    );
    return response.data;
  },

  /**
   * Create new conversation
   * POST /chatbot/conversations/
   */
  createConversation: async (): Promise<Conversation> => {
    const response = await apiClient.post<Conversation>(
      "/chatbot/conversations/",
    );
    return response.data;
  },

  /**
   * Submit feedback / satisfaction rating
   * POST /chatbot/feedback/
   */
  submitFeedback: async (
    feedback: FeedbackRequest,
  ): Promise<{ message: string; rating: number }> => {
    const response = await apiClient.post("/chatbot/feedback/", feedback);
    return response.data;
  },

  /**
   * Get user preferences
   * GET /chatbot/preferences/
   */
  getPreferences: async (): Promise<Record<string, unknown>> => {
    const response = await apiClient.get("/chatbot/preferences/");
    return response.data;
  },

  /**
   * Update user preferences
   * PUT /chatbot/preferences/
   */
  updatePreferences: async (
    prefs: Record<string, unknown>,
  ): Promise<Record<string, unknown>> => {
    const response = await apiClient.put("/chatbot/preferences/", prefs);
    return response.data;
  },

  /**
   * Get proactive notifications
   * GET /chatbot/notifications/
   */
  getNotifications: async (): Promise<{
    notifications: Record<string, unknown>[];
    count: number;
  }> => {
    const response = await apiClient.get("/chatbot/notifications/");
    return response.data;
  },
};
