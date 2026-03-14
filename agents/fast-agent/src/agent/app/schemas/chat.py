"""Pydantic schemas for chat, conversation, message, and user data."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

# User schemas


class UserBase(BaseModel):
    """Base schema with shared user fields."""

    username: str
    email: str  # Changed from EmailStr to str to simplify dependencies


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str


class UserInDB(UserBase):
    """Schema for a user record stored in the database."""

    id: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class User(UserInDB):
    """Public-facing user schema."""


# Message schemas


class MessageBase(BaseModel):
    """Base schema with shared message fields."""

    role: str
    content: str


class MessageCreate(MessageBase):
    """Schema for creating a new message."""


class Message(MessageBase):
    """Schema for a message record returned from the database."""

    id: int
    conversation_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Conversation schemas


class ConversationBase(BaseModel):
    """Base schema with shared conversation fields."""

    title: str


class ConversationCreate(ConversationBase):
    """Schema for creating a new conversation."""


class Conversation(ConversationBase):
    """Schema for a conversation record returned from the database."""

    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    messages: List[Message] = []

    model_config = ConfigDict(from_attributes=True)


# Chat specific schemas


class ChatRequest(BaseModel):
    """Schema for an incoming chat request."""

    message: str
    conversation_id: Optional[int] = None


class ChatResponse(BaseModel):
    """Schema for a chat response returned to the client."""

    message: str
    conversation_id: int
