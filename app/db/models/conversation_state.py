from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ConversationState(Base):
    __tablename__ = "conversation_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversation_key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    chat_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    chat_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    message_thread_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    assistant_memory_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    conversation_context_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
