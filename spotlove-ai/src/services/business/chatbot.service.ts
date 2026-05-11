/**
 * Chatbot Business Service
 * Business logic layer - handles chatbot interactions
 *
 * Pattern: service.ts = Business Logic layer
 *          api.ts = Pure HTTP calls only
 */

import { chatbotApi } from "@/services/api/chatbot.api";
import type {
  ChatMessage,
  ChatResponse,
  QuickAction,
  Conversation,
  ActiveConversationResponse,
  FeedbackRequest,
} from "@/services/api/chatbot.api";

// =====================
// Re-export Types for consumers
// =====================

export type {
  ChatMessage,
  ChatResponse,
  QuickAction,
  Conversation,
  ActiveConversationResponse,
  FeedbackRequest,
};

// =====================
// Business Service Types
// =====================

export interface SendMessageResult {
  success: boolean;
  response?: ChatResponse;
  message: string;
}

export interface ConversationResult {
  success: boolean;
  conversation?: Conversation;
  messages?: ChatMessage[];
  message: string;
}

interface ApiErrorPayload {
  response?: {
    data?: {
      message?: string;
    };
  };
}

const getApiErrorMessage = (
  error: unknown,
  fallbackMessage: string,
): string => {
  const apiError = error as ApiErrorPayload;
  return apiError.response?.data?.message || fallbackMessage;
};

// =====================
// Chatbot Business Service
// =====================

export const chatbotService = {
  /**
   * Send a chat message and get AI response
   */
  async sendMessage(
    message: string,
    conversationId?: string,
  ): Promise<ChatResponse> {
    return chatbotApi.sendMessage(message, conversationId);
  },

  /**
   * Send message with error handling wrapper
   */
  async sendMessageSafe(
    message: string,
    conversationId?: string,
  ): Promise<SendMessageResult> {
    try {
      const response = await chatbotApi.sendMessage(message, conversationId);
      return {
        success: true,
        response,
        message: "Đã gửi tin nhắn",
      };
    } catch (error: unknown) {
      return {
        success: false,
        message: getApiErrorMessage(error, "Không thể gửi tin nhắn"),
      };
    }
  },

  /**
   * Get quick action buttons
   */
  async getQuickActions(): Promise<{ quickActions: QuickAction[] }> {
    return chatbotApi.getQuickActions();
  },

  /**
   * Get chat messages for a specific conversation
   */
  async getChatMessages(
    conversationId: string,
  ): Promise<{ messages: ChatMessage[]; conversationId: string }> {
    return chatbotApi.getChatMessages(conversationId);
  },

  /**
   * Get latest conversation history (no conversationId needed)
   */
  async getChatHistory(): Promise<{
    messages: ChatMessage[];
    conversationId: string | null;
  }> {
    return chatbotApi.getChatHistory();
  },

  /**
   * Get or create active conversation with recent messages
   */
  async getActiveConversation(): Promise<ActiveConversationResponse> {
    return chatbotApi.getActiveConversation();
  },

  /**
   * List all conversations for current user
   */
  async listConversations(): Promise<Conversation[]> {
    return chatbotApi.listConversations();
  },

  /**
   * Create a new conversation
   */
  async createConversation(): Promise<Conversation> {
    return chatbotApi.createConversation();
  },

  /**
   * Submit feedback / satisfaction rating
   */
  async submitFeedback(
    feedback: FeedbackRequest,
  ): Promise<{ message: string; rating: number }> {
    return chatbotApi.submitFeedback(feedback);
  },

  /**
   * Get user preferences
   */
  async getPreferences(): Promise<Record<string, unknown>> {
    return chatbotApi.getPreferences();
  },

  /**
   * Update user preferences
   */
  async updatePreferences(
    prefs: Record<string, unknown>,
  ): Promise<Record<string, unknown>> {
    return chatbotApi.updatePreferences(prefs);
  },
};
