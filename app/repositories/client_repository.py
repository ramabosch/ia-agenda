from sqlalchemy.orm import Session

from app.db.models.client import Client


def create_client(db: Session, name: str, company: str | None = None, notes: str | None = None) -> Client:
    client = Client(name=name, company=company, notes=notes)
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def get_all_clients(db: Session) -> list[Client]:
    return db.query(Client).all()


def get_client_by_id(db: Session, client_id: int) -> Client | None:
    return db.query(Client).filter(Client.id == client_id).first()

def get_active_clients(db: Session) -> list[Client]:
    return db.query(Client).filter(Client.projects.any()).order_by(Client.name.asc()).all()

def get_client_by_name(db: Session, name: str) -> Client | None:
    search = f"%{name.strip()}%"
    return db.query(Client).filter(Client.name.ilike(search)).order_by(Client.name.asc()).first()

def search_clients_by_name(db: Session, name: str, limit: int = 5):
    search = f"%{name.strip()}%"
    return (
        db.query(Client)
        .filter(Client.name.ilike(search))
        .order_by(Client.name.asc())
        .limit(limit)
        .all()
    )