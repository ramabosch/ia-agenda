from datetime import date

from app.db.session import SessionLocal
from app.repositories.conversation_repository import (
    create_log,
    get_all_logs,
    get_latest_log,
    get_logs_for_today,
)


def save_conversation(user_input: str, parsed_intent: str, response_output: str):
    db = SessionLocal()
    try:
        return create_log(db, user_input, parsed_intent, response_output)
    finally:
        db.close()


def get_conversations_for_today():
    db = SessionLocal()
    try:
        return get_logs_for_today(db, date.today())
    finally:
        db.close()


def get_last_conversation():
    db = SessionLocal()
    try:
        return get_latest_log(db)
    finally:
        db.close()


def get_recent_conversations(limit: int = 20):
    db = SessionLocal()
    try:
        return get_all_logs(db, limit=limit)
    finally:
        db.close()