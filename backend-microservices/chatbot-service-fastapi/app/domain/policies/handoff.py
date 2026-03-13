"""
Domain Policy — Handoff Policy.

Determines when to escalate to human support.
Only triggers when user EXPLICITLY requests human support.
"""

_HANDOFF_KEYWORDS = [
    "nói chuyện với người thật",
    "nhân viên",
    "hỗ trợ viên",
    "talk to human",
    "agent",
    "manager",
    "gặp nhân viên",
    "chuyển nhân viên",
    "nói với người",
]


def should_handoff(
    frustration_score: float,
    clarification_count: int,
    message: str,
) -> bool:
    """
    Decide if conversation should be handed off to a human.

    Rules:
    1. Frustration score > 0.9 (very high)
    2. Clarification count >= 6 (bot keeps failing badly)
    3. User explicitly asks for human support
    """
    if frustration_score > 0.9:
        return True

    if clarification_count >= 6:
        return True

    msg_lower = message.lower()
    if any(kw in msg_lower for kw in _HANDOFF_KEYWORDS):
        return True

    return False
