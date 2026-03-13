"""
Domain exceptions for chatbot service.
"""


class ChatbotError(Exception):
    """Base chatbot domain error."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class ConversationNotFoundError(ChatbotError):
    def __init__(self, conversation_id: str):
        super().__init__("CONVERSATION_NOT_FOUND", f"Conversation {conversation_id} not found")


class LLMError(ChatbotError):
    def __init__(self, detail: str = "LLM service unavailable"):
        super().__init__("LLM_ERROR", detail)


class ServiceUnavailableError(ChatbotError):
    def __init__(self, service: str):
        super().__init__("SERVICE_UNAVAILABLE", f"{service} is unavailable")


class ActionNotUndoableError(ChatbotError):
    def __init__(self, action_id: str):
        super().__init__("ACTION_NOT_UNDOABLE", f"Action {action_id} cannot be undone")
