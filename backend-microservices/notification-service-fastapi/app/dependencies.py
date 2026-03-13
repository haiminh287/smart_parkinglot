"""
Dependencies for FastAPI routes
"""

from fastapi import Request, HTTPException


def get_current_user_id(request: Request) -> str:
    """Extract user ID from gateway-injected headers"""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")
    return user_id
