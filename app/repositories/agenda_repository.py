from datetime import date, time

from sqlalchemy.orm import Session

from app.db.models.agenda_item import AgendaItem


def create_agenda_item(
    db: Session,
    title: str,
    *,
    scheduled_date: date,
    scheduled_time: time | None = None,
    kind: str = "event",
    note: str | None = None,
) -> AgendaItem:
    item = AgendaItem(
        title=title,
        scheduled_date=scheduled_date,
        scheduled_time=scheduled_time,
        kind=kind,
        note=note,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_agenda_items_for_date(db: Session, target_date: date) -> list[AgendaItem]:
    return (
        db.query(AgendaItem)
        .filter(AgendaItem.scheduled_date == target_date)
        .order_by(AgendaItem.scheduled_time.asc(), AgendaItem.id.asc())
        .all()
    )


def get_agenda_items_between_dates(db: Session, start_date: date, end_date: date) -> list[AgendaItem]:
    return (
        db.query(AgendaItem)
        .filter(AgendaItem.scheduled_date >= start_date)
        .filter(AgendaItem.scheduled_date <= end_date)
        .order_by(AgendaItem.scheduled_date.asc(), AgendaItem.scheduled_time.asc(), AgendaItem.id.asc())
        .all()
    )


def get_all_agenda_items(db: Session) -> list[AgendaItem]:
    return (
        db.query(AgendaItem)
        .order_by(AgendaItem.scheduled_date.asc(), AgendaItem.scheduled_time.asc(), AgendaItem.id.asc())
        .all()
    )


def get_agenda_item_by_id(db: Session, agenda_item_id: int) -> AgendaItem | None:
    return db.query(AgendaItem).filter(AgendaItem.id == agenda_item_id).first()


def update_agenda_item(
    db: Session,
    agenda_item_id: int,
    *,
    scheduled_date: date | None = None,
    scheduled_time: time | None = None,
) -> AgendaItem | None:
    item = get_agenda_item_by_id(db, agenda_item_id)
    if not item:
        return None
    if scheduled_date is not None:
        item.scheduled_date = scheduled_date
    item.scheduled_time = scheduled_time
    db.commit()
    db.refresh(item)
    return item


def delete_agenda_item(db: Session, agenda_item_id: int) -> AgendaItem | None:
    item = get_agenda_item_by_id(db, agenda_item_id)
    if not item:
        return None
    db.delete(item)
    db.commit()
    return item
