from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TaskUpdate(Base):
    __tablename__ = "task_updates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False)

    content: Mapped[str] = mapped_column(Text, nullable=False)
    update_type: Mapped[str] = mapped_column(String(50), default="manual")
    source: Mapped[str] = mapped_column(String(50), default="ui")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="updates")