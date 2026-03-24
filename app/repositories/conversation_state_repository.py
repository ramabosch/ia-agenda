from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.conversation_state import ConversationState


def get_conversation_state_by_key(db: Session, conversation_key: str) -> ConversationState | None:
    return (
        db.query(ConversationState)
        .filter(ConversationState.conversation_key == str(conversation_key))
        .first()
    )


def save_conversation_state(
    db: Session,
    *,
    conversation_key: str,
    conversation_context_json: str | None,
    assistant_memory_json: str | None,
    user_id: str | None = None,
    chat_id: str | None = None,
    chat_type: str | None = None,
    message_thread_id: str | None = None,
) -> ConversationState:
    state = get_conversation_state_by_key(db, conversation_key)
    if state is None:
        state = ConversationState(conversation_key=str(conversation_key))
        db.add(state)

    state.user_id = user_id
    state.chat_id = chat_id
    state.chat_type = chat_type
    state.message_thread_id = message_thread_id
    state.assistant_memory_json = assistant_memory_json
    state.conversation_context_json = conversation_context_json

    db.commit()
    db.refresh(state)
    return state


def delete_conversation_state(db: Session, conversation_key: str) -> bool:
    state = get_conversation_state_by_key(db, conversation_key)
    if state is None:
        return False
    db.delete(state)
    db.commit()
    return True


def delete_all_conversation_states(db: Session) -> int:
    deleted = db.query(ConversationState).delete()
    db.commit()
    return int(deleted or 0)
