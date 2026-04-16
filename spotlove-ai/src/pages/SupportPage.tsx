import { useState, useRef, useEffect, useCallback } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Send,
  Mail,
  Clock,
  User,
  Bot,
  Paperclip,
  Image,
  Loader2,
  Car,
  Calendar,
  MapPin,
  Sparkles,
  MessageSquare,
  CheckCircle2,
  XCircle,
  QrCode,
  Map,
  Star,
  ShieldCheck,
  HelpCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { chatbotService, type ChatResponse } from "@/services/business";
import { toast } from "sonner";

interface Message {
  id: string;
  content: string;
  sender: "user" | "assistant";
  timestamp: string;
  isLoading?: boolean;
  suggestions?: string[];
  // v3.0 fields
  confidence?: number | null;
  processingTimeMs?: number | null;
  showMap?: boolean;
  showQrCode?: boolean;
  clarificationNeeded?: boolean;
  confirmationNeeded?: boolean;
  confidenceBreakdown?: {
    llm?: number;
    entityCompleteness?: number;
    contextMatch?: number;
  };
  safetyCode?: string | null;
  safetyHint?: string | null;
  intent?: string | null;
}

interface QuickAction {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  prompt: string;
}

const defaultQuickActions: QuickAction[] = [
  { label: "Đặt chỗ ô tô", icon: Car, prompt: "Tôi muốn đặt chỗ đậu ô tô" },
  { label: "Đặt chỗ xe máy", icon: Car, prompt: "Tôi muốn đặt chỗ đậu xe máy" },
  {
    label: "Xem lịch đặt",
    icon: Calendar,
    prompt: "Cho tôi xem lịch đặt chỗ của tôi",
  },
  {
    label: "Tìm chỗ trống",
    icon: MapPin,
    prompt: "Còn chỗ trống ở đâu không?",
  },
];

const welcomeMessage: Message = {
  id: "welcome",
  content: `Xin chào! 👋 Tôi là trợ lý AI của ParkSmart. Tôi có thể giúp bạn:

• **Đặt chỗ đậu xe** - Chỉ cần nói loại xe và thời gian
• **Xem chỗ trống** - Tìm vị trí đậu xe phù hợp
• **Quản lý booking** - Xem, hủy hoặc thay đổi đặt chỗ
• **Hỗ trợ khác** - Giải đáp mọi thắc mắc

Bạn cần tôi giúp gì hôm nay?`,
  sender: "assistant",
  timestamp: new Date().toISOString(),
  suggestions: ["Xem chỗ trống", "Đặt chỗ ô tô", "Xem giá"],
};

// Safety code display helpers
const safetyCodeLabels: Record<string, { label: string; color: string }> = {
  SAFE: { label: "An toàn", color: "text-green-600" },
  BLOCKED_PII: { label: "Chặn dữ liệu nhạy cảm", color: "text-red-500" },
  BLOCKED_PROFANITY: { label: "Nội dung không phù hợp", color: "text-red-500" },
  BLOCKED_INJECTION: { label: "Phát hiện injection", color: "text-red-500" },
  RATE_LIMITED: { label: "Giới hạn tần suất", color: "text-yellow-600" },
  BLOCKED_SPAM: { label: "Phát hiện spam", color: "text-yellow-600" },
  HUMAN_HANDOFF: { label: "Chuyển nhân viên", color: "text-blue-500" },
};

export default function SupportPage() {
  const [messages, setMessages] = useState<Message[]>([welcomeMessage]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [quickActions] = useState<QuickAction[]>(defaultQuickActions);
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackRating, setFeedbackRating] = useState(0);
  const [feedbackComment, setFeedbackComment] = useState("");
  const [pendingConfirmation, setPendingConfirmation] = useState<string | null>(
    null,
  );
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Load chat history on mount
  useEffect(() => {
    const loadChatHistory = async () => {
      try {
        const history = await chatbotService.getChatHistory();
        if (history.messages && history.messages.length > 0) {
          setMessages([
            welcomeMessage,
            ...history.messages.map((msg) => {
              const decisionData = (msg.decisionData || {}) as Record<
                string,
                unknown
              >;
              const confidenceBreakdown = decisionData.confidenceBreakdown as
                | {
                    llm?: number;
                    entityCompleteness?: number;
                    contextMatch?: number;
                  }
                | undefined;

              return {
                id: msg.id,
                content: msg.content,
                sender: msg.role as "user" | "assistant",
                timestamp: msg.createdAt,
                // Restore bot message metadata from decisionData
                suggestions:
                  (decisionData.suggestions as string[]) || undefined,
                confidence: msg.confidence ?? undefined,
                processingTimeMs: msg.processingTimeMs ?? undefined,
                showMap: (decisionData.showMap as boolean) || undefined,
                showQrCode: (decisionData.showQrCode as boolean) || undefined,
                intent: msg.intent || undefined,
                confidenceBreakdown: confidenceBreakdown || undefined,
                safetyCode: (decisionData.safetyCode as string) || undefined,
                safetyHint: (decisionData.safetyHint as string) || undefined,
              };
            }),
          ]);
          setConversationId(history.conversationId);
        }
      } catch {
        // No history, use welcome message
      }
    };

    loadChatHistory();
  }, []);

  const handleSend = async (content?: string) => {
    const messageContent = content || inputValue.trim();
    if (!messageContent || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: messageContent,
      sender: "user",
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);
    setPendingConfirmation(null);

    // Add loading message
    const loadingMessage: Message = {
      id: "loading",
      content: "",
      sender: "assistant",
      timestamp: new Date().toISOString(),
      isLoading: true,
    };
    setMessages((prev) => [...prev, loadingMessage]);

    try {
      // Call the chatbot API
      const response: ChatResponse = await chatbotService.sendMessage(
        messageContent,
        conversationId || undefined,
      );

      // Remove loading message and add real response
      setMessages((prev) => prev.filter((m) => m.id !== "loading"));

      const assistantMessage: Message = {
        id: response.messageId,
        content: response.response,
        sender: "assistant",
        timestamp: new Date().toISOString(),
        suggestions: response.suggestions,
        confidence: response.confidence,
        processingTimeMs: response.processingTimeMs,
        showMap: response.showMap,
        showQrCode: response.showQrCode,
        clarificationNeeded: response.clarificationNeeded,
        confirmationNeeded: response.confirmationNeeded,
        confidenceBreakdown: response.confidenceBreakdown,
        safetyCode: response.safetyCode,
        safetyHint: response.safetyHint,
        intent: response.intent,
      };

      setMessages((prev) => [...prev, assistantMessage]);
      setConversationId(response.conversationId);

      // If confirmation needed, track it
      if (response.confirmationNeeded) {
        setPendingConfirmation(response.intent || "action");
      }
    } catch {
      // Remove loading message
      setMessages((prev) => prev.filter((m) => m.id !== "loading"));

      const fallbackResponse =
        "Hiện chatbot đang tạm thời không khả dụng. Vui lòng thử lại sau ít phút hoặc liên hệ hỗ trợ trực tiếp qua nút Liên hệ ở góc phải.";
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: fallbackResponse,
        sender: "assistant",
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);

      toast.error(
        "Chatbot đang tạm thời không khả dụng. Vui lòng thử lại sau.",
      );
    } finally {
      setIsLoading(false);
    }
  };

  // Handle confirmation actions
  const handleConfirm = () => {
    handleSend("Xác nhận");
  };

  const handleCancel = () => {
    setPendingConfirmation(null);
    handleSend("Hủy bỏ");
  };

  // Handle feedback submission
  const handleSubmitFeedback = async () => {
    if (!conversationId || feedbackRating === 0) return;

    try {
      await chatbotService.submitFeedback({
        conversationId,
        rating: feedbackRating,
        comment: feedbackComment || undefined,
      });
      toast.success("Cảm ơn bạn đã phản hồi! 🎉");
      setShowFeedback(false);
      setFeedbackRating(0);
      setFeedbackComment("");
    } catch {
      toast.error("Không thể gửi phản hồi. Vui lòng thử lại.");
    }
  };

  // Handle suggestion click
  const handleSuggestionClick = (suggestion: string) => {
    handleSend(suggestion);
  };

  // Confidence bar color
  const getConfidenceColor = (value: number) => {
    if (value >= 0.8) return "bg-green-500";
    if (value >= 0.5) return "bg-yellow-500";
    return "bg-red-500";
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="animate-fade-in">
          <h1 className="text-2xl font-bold text-foreground md:text-3xl">
            Hỗ trợ khách hàng
          </h1>
          <p className="mt-1 text-muted-foreground">
            Chat với AI hoặc liên hệ trực tiếp qua các kênh hỗ trợ
          </p>
        </div>

        {/* Info banner - contact via widget */}
        <div className="flex items-center gap-3 rounded-2xl border border-primary/20 bg-primary/5 p-4 animate-slide-up">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl gradient-primary text-primary-foreground">
            <MessageSquare className="h-5 w-5" />
          </div>
          <div className="flex-1">
            <p className="font-medium text-foreground">
              Cần liên hệ trực tiếp?
            </p>
            <p className="text-sm text-muted-foreground">
              Nhấn vào nút{" "}
              <span className="font-semibold text-primary">Liên hệ</span> ở góc
              phải để chat qua Zalo, Facebook, Telegram hoặc gọi Hotline.
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-6 lg:flex-row">
          {/* Chat Section */}
          <div
            className="flex flex-1 flex-col rounded-2xl border border-border bg-card animate-slide-up min-h-[400px]"
            style={{ height: "min(calc(100vh - 20rem), 600px)" }}
          >
            {/* Chat Header */}
            <div className="flex items-center justify-between border-b border-border p-4">
              <div className="flex items-center gap-3">
                <div className="relative">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full gradient-primary">
                    <Sparkles className="h-5 w-5 text-primary-foreground" />
                  </div>
                  <div className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-card bg-success" />
                </div>
                <div>
                  <p className="font-semibold text-foreground">
                    ParkSmart AI Assistant
                  </p>
                  <p className="text-xs text-success">Đang hoạt động</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {conversationId && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowFeedback(!showFeedback)}
                    className="text-xs gap-1"
                  >
                    <Star className="h-3 w-3" />
                    Đánh giá
                  </Button>
                )}
                <Badge
                  variant="outline"
                  className="bg-primary/10 text-primary gap-1"
                >
                  <Sparkles className="h-3 w-3" />
                  AI v3.0
                </Badge>
              </div>
            </div>

            {/* Feedback Panel */}
            {showFeedback && conversationId && (
              <div className="border-b border-border p-4 bg-muted/50 space-y-3">
                <p className="text-sm font-medium">Đánh giá cuộc trò chuyện</p>
                <div className="flex items-center gap-1">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      onClick={() => setFeedbackRating(star)}
                      className={cn(
                        "transition-colors",
                        star <= feedbackRating
                          ? "text-yellow-500"
                          : "text-muted-foreground/30",
                      )}
                    >
                      <Star className="h-6 w-6 fill-current" />
                    </button>
                  ))}
                  <span className="ml-2 text-sm text-muted-foreground">
                    {feedbackRating > 0 ? `${feedbackRating}/5` : "Chọn điểm"}
                  </span>
                </div>
                <input
                  type="text"
                  placeholder="Nhận xét thêm (tùy chọn)..."
                  value={feedbackComment}
                  onChange={(e) => setFeedbackComment(e.target.value)}
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                />
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    onClick={handleSubmitFeedback}
                    disabled={feedbackRating === 0}
                  >
                    Gửi đánh giá
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setShowFeedback(false)}
                  >
                    Đóng
                  </Button>
                </div>
              </div>
            )}

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={cn(
                    "flex gap-3",
                    message.sender === "user" ? "flex-row-reverse" : "",
                  )}
                >
                  <div
                    className={cn(
                      "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
                      message.sender === "user"
                        ? "bg-primary/10 text-primary"
                        : "gradient-primary text-primary-foreground",
                    )}
                  >
                    {message.sender === "user" ? (
                      <User className="h-4 w-4" />
                    ) : (
                      <Bot className="h-4 w-4" />
                    )}
                  </div>
                  <div
                    className={cn(
                      "max-w-[80%] rounded-2xl px-4 py-3",
                      message.sender === "user"
                        ? "bg-primary text-primary-foreground rounded-tr-sm"
                        : "bg-muted text-foreground rounded-tl-sm",
                    )}
                  >
                    {message.isLoading ? (
                      <div className="flex items-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        <span className="text-sm">Đang suy nghĩ...</span>
                      </div>
                    ) : (
                      <>
                        {/* Safety hint banner */}
                        {message.safetyCode &&
                          message.safetyCode !== "SAFE" &&
                          message.safetyHint && (
                            <div className="mb-2 flex items-center gap-2 rounded-lg bg-yellow-500/10 px-3 py-1.5 text-xs">
                              <ShieldCheck className="h-3.5 w-3.5 text-yellow-600" />
                              <span
                                className={
                                  safetyCodeLabels[message.safetyCode]?.color ||
                                  "text-yellow-600"
                                }
                              >
                                {message.safetyHint}
                              </span>
                            </div>
                          )}

                        {/* Message content */}
                        <p className="text-sm whitespace-pre-wrap">
                          {message.content}
                        </p>

                        {/* Map / QR Code indicators */}
                        {(message.showMap || message.showQrCode) && (
                          <div className="mt-2 flex gap-2">
                            {message.showMap && (
                              <div className="flex items-center gap-1.5 rounded-lg bg-blue-500/10 px-2.5 py-1.5 text-xs text-blue-600">
                                <Map className="h-3.5 w-3.5" />
                                Xem bản đồ
                              </div>
                            )}
                            {message.showQrCode && (
                              <div className="flex items-center gap-1.5 rounded-lg bg-purple-500/10 px-2.5 py-1.5 text-xs text-purple-600">
                                <QrCode className="h-3.5 w-3.5" />
                                Mã QR
                              </div>
                            )}
                          </div>
                        )}

                        {/* Clarification indicator */}
                        {message.clarificationNeeded && (
                          <div className="mt-2 flex items-center gap-1.5 text-xs text-amber-600">
                            <HelpCircle className="h-3.5 w-3.5" />
                            Cần thêm thông tin để xử lý yêu cầu
                          </div>
                        )}

                        {/* Confirmation buttons */}
                        {message.confirmationNeeded && pendingConfirmation && (
                          <div className="mt-3 flex items-center gap-2">
                            <Button
                              size="sm"
                              onClick={handleConfirm}
                              disabled={isLoading}
                              className="gap-1 bg-green-600 hover:bg-green-700 text-white text-xs"
                            >
                              <CheckCircle2 className="h-3.5 w-3.5" />
                              Xác nhận
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={handleCancel}
                              disabled={isLoading}
                              className="gap-1 text-xs"
                            >
                              <XCircle className="h-3.5 w-3.5" />
                              Hủy bỏ
                            </Button>
                          </div>
                        )}

                        {/* Confidence + timing info */}
                        {message.sender === "assistant" &&
                          message.id !== "welcome" &&
                          (message.confidence != null ||
                            message.processingTimeMs != null) && (
                            <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                              {message.confidence != null && (
                                <div className="flex items-center gap-1.5">
                                  <span>Độ tin cậy:</span>
                                  <div className="h-1.5 w-16 rounded-full bg-muted-foreground/20 overflow-hidden">
                                    <div
                                      className={cn(
                                        "h-full rounded-full transition-all",
                                        getConfidenceColor(message.confidence),
                                      )}
                                      style={{
                                        width: `${Math.round(message.confidence * 100)}%`,
                                      }}
                                    />
                                  </div>
                                  <span>
                                    {Math.round(message.confidence * 100)}%
                                  </span>
                                </div>
                              )}
                              {message.processingTimeMs != null && (
                                <span>⚡ {message.processingTimeMs}ms</span>
                              )}
                            </div>
                          )}

                        {/* Timestamp */}
                        <p
                          className={cn(
                            "mt-1 text-xs",
                            message.sender === "user"
                              ? "text-primary-foreground/70"
                              : "text-muted-foreground",
                          )}
                        >
                          {new Date(message.timestamp).toLocaleTimeString(
                            "vi-VN",
                            {
                              hour: "2-digit",
                              minute: "2-digit",
                            },
                          )}
                        </p>

                        {/* Suggestions */}
                        {message.suggestions &&
                          message.suggestions.length > 0 && (
                            <div className="mt-3 flex flex-wrap gap-2">
                              {message.suggestions.map((suggestion, index) => (
                                <button
                                  key={index}
                                  onClick={() =>
                                    handleSuggestionClick(suggestion)
                                  }
                                  disabled={isLoading}
                                  className="rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs font-medium text-primary transition-colors hover:bg-primary/20 disabled:opacity-50"
                                >
                                  {suggestion}
                                </button>
                              ))}
                            </div>
                          )}
                      </>
                    )}
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            {/* Quick Actions */}
            <div className="border-t border-border p-3">
              <div className="mb-2 flex flex-wrap gap-2">
                {quickActions.map((action) => (
                  <button
                    key={action.label}
                    onClick={() => handleSend(action.prompt)}
                    disabled={isLoading}
                    className="flex items-center gap-2 rounded-full border border-border bg-background px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:border-primary hover:text-primary disabled:opacity-50"
                  >
                    <action.icon className="h-3 w-3" />
                    {action.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Input Area */}
            <div className="border-t border-border p-4">
              <div className="flex items-center gap-3">
                <Button variant="ghost" size="icon" className="shrink-0">
                  <Paperclip className="h-5 w-5" />
                </Button>
                <Button variant="ghost" size="icon" className="shrink-0">
                  <Image className="h-5 w-5" />
                </Button>
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && handleSend()}
                  placeholder="Nhập tin nhắn... (VD: Đặt chỗ ô tô ngày mai)"
                  disabled={isLoading}
                  className="flex-1 rounded-xl border border-border bg-background px-4 py-2.5 text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-50"
                />
                <Button
                  className="gradient-primary"
                  size="icon"
                  onClick={() => handleSend()}
                  disabled={!inputValue.trim() || isLoading}
                >
                  {isLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>
          </div>

          {/* Contact Info Sidebar */}
          <div className="w-full lg:w-80 space-y-4">
            {/* AI Info */}
            <div className="rounded-2xl border border-border bg-card p-5 animate-slide-up">
              <div className="flex items-center gap-3 mb-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl gradient-primary">
                  <Sparkles className="h-6 w-6 text-primary-foreground" />
                </div>
                <div>
                  <h3 className="font-semibold text-foreground">
                    AI Assistant v3.0
                  </h3>
                  <p className="text-sm text-muted-foreground">Hỗ trợ 24/7</p>
                </div>
              </div>
              <div className="space-y-2 text-sm text-muted-foreground">
                <p>
                  Chatbot AI có thể giúp bạn đặt chỗ, xem lịch, hủy booking và
                  giải đáp thắc mắc bằng ngôn ngữ tự nhiên.
                </p>
                <div className="mt-3 space-y-1.5">
                  <div className="flex items-center gap-2 text-xs">
                    <ShieldCheck className="h-3.5 w-3.5 text-green-500" />
                    <span>An toàn & kiểm duyệt nội dung</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    <Sparkles className="h-3.5 w-3.5 text-blue-500" />
                    <span>Nhận diện ý định thông minh</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    <CheckCircle2 className="h-3.5 w-3.5 text-purple-500" />
                    <span>Xác nhận trước khi thao tác</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Email Support */}
            <div className="rounded-2xl border border-border bg-card p-5 animate-slide-up">
              <h3 className="flex items-center gap-2 font-semibold text-foreground mb-3">
                <Mail className="h-5 w-5 text-primary" />
                Email hỗ trợ
              </h3>
              <p className="text-sm text-muted-foreground mb-2">
                Gửi email để được hỗ trợ chi tiết
              </p>
              <a
                href="mailto:support@parksmart.vn"
                className="text-sm font-medium text-primary hover:underline"
              >
                support@parksmart.vn
              </a>
            </div>

            {/* Working Hours */}
            <div className="rounded-2xl border border-border bg-card p-5 animate-slide-up">
              <h3 className="flex items-center gap-2 font-semibold text-foreground mb-4">
                <Clock className="h-5 w-5 text-primary" />
                Giờ làm việc
              </h3>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Thứ 2 - Thứ 6</span>
                  <span className="font-medium text-foreground">
                    7:00 - 22:00
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Thứ 7 - CN</span>
                  <span className="font-medium text-foreground">
                    8:00 - 20:00
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Hotline</span>
                  <span className="font-medium text-success">24/7</span>
                </div>
              </div>
              <div className="mt-4 flex items-center gap-2 rounded-xl bg-success/10 p-3">
                <MessageSquare className="h-4 w-4 text-success" />
                <span className="text-sm text-success font-medium">
                  AI hoạt động 24/7
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
