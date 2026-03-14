"""SQLAlchemy ORM models for chat, conversation, and user entities."""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class User(Base):  # pylint: disable=too-few-public-methods
    """Database model representing an application user."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Integer, default=1)
    conversations = relationship("Conversation", back_populates="user")


class Conversation(Base):  # pylint: disable=too-few-public-methods
    """Database model representing a chat conversation."""

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # pylint: disable=not-callable
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())  # pylint: disable=not-callable

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete")


class Message(Base):  # pylint: disable=too-few-public-methods
    """Database model representing a single chat message."""

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # pylint: disable=not-callable

    conversation = relationship("Conversation", back_populates="messages")
