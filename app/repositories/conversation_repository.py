from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models.conversation_log import ConversationLog


def create_log(db: Session, user_input: str, parsed_intent: str, response_output: str):
    log = ConversationLog(
        user_input=user_input,
        parsed_intent=parsed_intent,
        response_output=response_output,
    )

    db.add(log)
    db.commit()
    db.refresh(log)

    return log


def get_all_logs(db: Session, limit: int = 50):
    return (
        db.query(ConversationLog)
        .order_by(ConversationLog.created_at.desc())
        .limit(limit)
        .all()
    )


def get_logs_for_today(db: Session, today_date):
    return (
        db.query(ConversationLog)
        .filter(ConversationLog.created_at >= datetime.combine(today_date, datetime.min.time()))
        .order_by(ConversationLog.created_at.desc())
        .all()
    )


def get_latest_log(db: Session):
    return (
        db.query(ConversationLog)
        .order_by(ConversationLog.created_at.desc())
        .first()
    )