from app.db.base import Base
from app.db.session import engine
from app.db.models import Client, Project, Task, TaskUpdate, ConversationLog  # noqa: F401


def init_db() -> None:
    Base.metadata.create_all(bind=engine)