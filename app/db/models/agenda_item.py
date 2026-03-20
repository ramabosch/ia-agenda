from datetime import date, datetime, time

from sqlalchemy import Date, DateTime, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AgendaItem(Base):
    __tablename__ = "agenda_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    scheduled_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    kind: Mapped[str] = mapped_column(String(50), nullable=False, default="event")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
