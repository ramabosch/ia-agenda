from app.db.session import SessionLocal
from app.repositories import client_repository


def create_client(name: str, company: str | None = None, notes: str | None = None):
    db = SessionLocal()
    try:
        return client_repository.create_client(db, name, company, notes)
    finally:
        db.close()


def get_all_clients():
    db = SessionLocal()
    try:
        return client_repository.get_all_clients(db)
    finally:
        db.close()

def get_active_clients():
    db = SessionLocal()
    try:
        return client_repository.get_active_clients(db)
    finally:
        db.close()

def get_client_by_name(name: str):
    db = SessionLocal()
    try:
        return client_repository.get_client_by_name(db, name)
    finally:
        db.close()

def search_clients_by_name(name: str, limit: int = 5):
    db = SessionLocal()
    try:
        return client_repository.search_clients_by_name(db, name, limit)
    finally:
        db.close()