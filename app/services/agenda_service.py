from __future__ import annotations

from datetime import date, datetime, time, timedelta

from app.db import init_db
from app.db.session import SessionLocal
from app.repositories import agenda_repository


WEEKDAY_INDEX = {
    "lunes": 0,
    "martes": 1,
    "miercoles": 2,
    "miércoles": 2,
    "jueves": 3,
    "viernes": 4,
    "sabado": 5,
    "sábado": 5,
    "domingo": 6,
}

_DB_READY = False


def _ensure_agenda_db() -> None:
    global _DB_READY
    if _DB_READY:
        return
    init_db()
    _DB_READY = True


def create_agenda_item_conversational(
    title: str,
    *,
    scheduled_date: date,
    scheduled_time: time | None = None,
    kind: str = "event",
    note: str | None = None,
):
    _ensure_agenda_db()
    db = SessionLocal()
    try:
        item = agenda_repository.create_agenda_item(
            db,
            title.strip(),
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
            kind=kind,
            note=note,
        )
        return {
            "created": True,
            "agenda_item_id": item.id,
            "title": item.title,
            "scheduled_date": item.scheduled_date,
            "scheduled_time": item.scheduled_time,
            "kind": item.kind,
            "note": item.note,
            "agenda_item": item,
        }
    finally:
        db.close()


def get_agenda_items_for_date(target_date: date):
    _ensure_agenda_db()
    db = SessionLocal()
    try:
        return agenda_repository.get_agenda_items_for_date(db, target_date)
    finally:
        db.close()


def get_agenda_items_between_dates(start_date: date, end_date: date):
    _ensure_agenda_db()
    db = SessionLocal()
    try:
        return agenda_repository.get_agenda_items_between_dates(db, start_date, end_date)
    finally:
        db.close()


def resolve_agenda_date_hint(date_hint: str | None, *, today: date | None = None) -> dict:
    today = today or date.today()
    normalized = _normalize_agenda_text(date_hint)
    if not normalized:
        return {
            "resolved": False,
            "scope": None,
            "target_date": None,
            "start_date": None,
            "end_date": None,
            "label": None,
            "error": "missing_date",
        }

    if normalized == "hoy":
        return {
            "resolved": True,
            "scope": "today",
            "target_date": today,
            "start_date": today,
            "end_date": today,
            "label": "hoy",
            "error": None,
        }

    if normalized in {"manana", "mañana"}:
        target = today + timedelta(days=1)
        return {
            "resolved": True,
            "scope": "tomorrow",
            "target_date": target,
            "start_date": target,
            "end_date": target,
            "label": "mañana",
            "error": None,
        }

    if normalized == "esta semana":
        end_of_week = today + timedelta(days=max(0, 6 - today.weekday()))
        return {
            "resolved": True,
            "scope": "this_week",
            "target_date": None,
            "start_date": today,
            "end_date": end_of_week,
            "label": "esta semana",
            "error": None,
        }

    weekday = WEEKDAY_INDEX.get(normalized)
    if weekday is not None:
        delta = (weekday - today.weekday()) % 7
        if delta == 0:
            delta = 7
        target = today + timedelta(days=delta)
        return {
            "resolved": True,
            "scope": "weekday",
            "target_date": target,
            "start_date": target,
            "end_date": target,
            "label": normalized,
            "error": None,
        }

    return {
        "resolved": False,
        "scope": None,
        "target_date": None,
        "start_date": None,
        "end_date": None,
        "label": None,
        "error": "unsupported_date",
    }


def resolve_agenda_time_hint(time_hint: str | None) -> dict:
    normalized = _normalize_agenda_text(time_hint)
    if not normalized:
        return {
            "resolved": True,
            "scheduled_time": None,
            "label": None,
            "error": None,
        }

    cleaned = normalized.replace("hs", "").replace("h", "").strip()
    parts = cleaned.split(":")
    if len(parts) == 1 and parts[0].isdigit():
        hour = int(parts[0])
        minute = 0
    elif len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        hour = int(parts[0])
        minute = int(parts[1])
    else:
        return {
            "resolved": False,
            "scheduled_time": None,
            "label": None,
            "error": "invalid_time",
        }

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return {
            "resolved": False,
            "scheduled_time": None,
            "label": None,
            "error": "invalid_time",
        }

    scheduled_time = time(hour=hour, minute=minute)
    return {
        "resolved": True,
        "scheduled_time": scheduled_time,
        "label": scheduled_time.strftime("%H:%M"),
        "error": None,
    }


def _normalize_agenda_text(value: str | None) -> str:
    return (value or "").strip().lower()
