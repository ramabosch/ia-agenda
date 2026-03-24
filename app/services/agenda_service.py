from __future__ import annotations

from datetime import date, datetime, time, timedelta
import unicodedata

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

NUMBER_WORDS = {
    "un": 1,
    "una": 1,
    "uno": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10,
    "quince": 15,
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


def get_all_agenda_items():
    _ensure_agenda_db()
    db = SessionLocal()
    try:
        return agenda_repository.get_all_agenda_items(db)
    finally:
        db.close()


def update_agenda_item_conversational(
    agenda_item_id: int,
    *,
    scheduled_date: date | None = None,
    scheduled_time: time | None = None,
):
    _ensure_agenda_db()
    db = SessionLocal()
    try:
        item = agenda_repository.update_agenda_item(
            db,
            agenda_item_id,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
        )
        if not item:
            return {"updated": False, "error": "not_found"}
        return {
            "updated": True,
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


def delete_agenda_item_conversational(agenda_item_id: int):
    _ensure_agenda_db()
    db = SessionLocal()
    try:
        item = agenda_repository.delete_agenda_item(db, agenda_item_id)
        if not item:
            return {"deleted": False, "error": "not_found"}
        return {
            "deleted": True,
            "agenda_item_id": item.id,
            "title": item.title,
            "scheduled_date": item.scheduled_date,
            "scheduled_time": item.scheduled_time,
            "kind": item.kind,
            "note": item.note,
        }
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

    if normalized in {"la semana que viene", "semana que viene", "proxima semana", "la proxima semana"}:
        start_of_current_week = today - timedelta(days=today.weekday())
        start_of_next_week = start_of_current_week + timedelta(days=7)
        end_of_next_week = start_of_next_week + timedelta(days=6)
        return {
            "resolved": True,
            "scope": "next_week",
            "target_date": None,
            "start_date": start_of_next_week,
            "end_date": end_of_next_week,
            "label": "la semana que viene",
            "error": None,
        }

    if normalized in {"proximos dias", "los proximos dias"}:
        start_date = today + timedelta(days=1)
        end_date = today + timedelta(days=7)
        return {
            "resolved": True,
            "scope": "next_days",
            "target_date": None,
            "start_date": start_date,
            "end_date": end_date,
            "label": "los proximos dias",
            "error": None,
        }

    if normalized in {"que se viene", "mas adelante", "en el futuro", "futuro cercano"}:
        start_date = today + timedelta(days=1)
        end_date = today + timedelta(days=30)
        return {
            "resolved": True,
            "scope": "future_horizon",
            "target_date": None,
            "start_date": start_date,
            "end_date": end_date,
            "label": "mas adelante",
            "error": None,
        }

    relative_weeks = _parse_relative_weeks(normalized)
    if relative_weeks is not None:
        target = today + timedelta(days=relative_weeks * 7)
        label = "dentro de una semana" if relative_weeks == 1 else f"dentro de {relative_weeks} semanas"
        return {
            "resolved": True,
            "scope": "relative_weeks",
            "target_date": target,
            "start_date": target,
            "end_date": target,
            "label": label,
            "error": None,
        }

    relative_days = _parse_relative_days(normalized)
    if relative_days is not None:
        target = today + timedelta(days=relative_days)
        return {
            "resolved": True,
            "scope": "relative_days",
            "target_date": target,
            "start_date": target,
            "end_date": target,
            "label": f"en {relative_days} dias",
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
    normalized = unicodedata.normalize("NFKD", (value or "").strip().lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _parse_relative_weeks(normalized: str) -> int | None:
    if not normalized.startswith("dentro de "):
        return None
    suffix = normalized.removeprefix("dentro de ").strip()
    if suffix in {"una semana", "1 semana"}:
        return 1
    if suffix in {"dos semanas", "2 semanas"}:
        return 2
    return None


def _parse_relative_days(normalized: str) -> int | None:
    if not normalized.startswith("en "):
        return None
    suffix = normalized.removeprefix("en ").strip()
    if not suffix.endswith((" dia", " dias")):
        return None
    value = suffix.replace(" dias", "").replace(" dia", "").strip()
    if value.isdigit():
        return int(value)
    return NUMBER_WORDS.get(value)
