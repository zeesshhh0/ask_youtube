"""
Pydantic request/response schemas for the Ask YouTube API.

These models define the contract between frontend and backend
for all /api/v1/threads endpoints.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


# ──────────────────────────────────────────────
# Request Schemas
# ──────────────────────────────────────────────

class CreateThreadRequest(BaseModel):
    """POST /threads — Initialize a new thread from a YouTube video."""
    video_url: HttpUrl


class SendMessageRequest(BaseModel):
    """POST /threads/{id}/messages — Send a user message."""
    content: str = Field(..., min_length=1, max_length=5000)


# ──────────────────────────────────────────────
# Response Schemas
# ──────────────────────────────────────────────

class CreateThreadResponse(BaseModel):
    """Response for POST /threads."""
    thread_id: str
    video_id: str
    title: str | None = None
    duration: int | None = None
    summary: str | None = None


class ThreadListItem(BaseModel):
    """Single item in GET /threads list."""
    thread_id: str
    title: str | None = None
    video_id: str
    created_at: datetime


class MessageResponse(BaseModel):
    """Single message in a thread's history."""
    message_id: str
    role: str  # "human" or "ai"
    content: str
    metadata: dict | None = None
    created_at: datetime


class ThreadMessagesResponse(BaseModel):
    """Response for GET /threads/{id}/messages."""
    thread_id: str
    messages: list[MessageResponse]


class DeleteThreadResponse(BaseModel):
    """Response for DELETE /threads/{id}."""
    success: bool
    thread_id: str


# ──────────────────────────────────────────────
# SSE Event Shapes (for documentation / frontend contract)
# ──────────────────────────────────────────────

class SSETokenEvent(BaseModel):
    """Streaming token event sent via SSE."""
    type: Literal["token"]
    content: str


class SSEEndEvent(BaseModel):
    """End-of-stream event sent via SSE."""
    type: Literal["end"]


# ──────────────────────────────────────────────
# Error Response
# ──────────────────────────────────────────────

class ErrorResponse(BaseModel):
    """Standardized error response."""
    detail: str
