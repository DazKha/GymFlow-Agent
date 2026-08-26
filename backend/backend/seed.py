"""Database initialization, migration, and seeding.

Handles:
- Migration from old schema (products, amenities, etc.) to new schema
- Preserves existing bookings and slots during migration
- Idempotent catalog seeding from california-catalog.json
- 7-day slot generation
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from .database import Base, DATABASE_URL, engine
from .loader import load_catalog, load_slots
from .models import Booking, Slot

OLD_DB_PATH = Path("gym.db")


def _backup_bookings_and_slots(db: Session) -> tuple[list[dict], list[dict]]:
    """Read existing bookings and slots from the current database before migration."""
    bookings_data: list[dict] = []
    slots_data: list[dict] = []

    try:
        bookings_data = [
            {
                "booking_ref": b.booking_ref,
                "customer_name": b.customer_name,
                "phone": b.phone,
                "appointment_dt": b.appointment_dt,
                "note": b.note,
                "status": b.status,
                "created_at": b.created_at,
            }
            for b in db.query(Booking).all()
        ]
    except Exception:
        pass

    try:
        slots_data = [
            {"date": s.date, "time_slot": s.time_slot, "is_available": s.is_available}
            for s in db.query(Slot).all()
        ]
    except Exception:
        pass

    return bookings_data, slots_data


def _restore_bookings_and_slots(db: Session, bookings_data: list[dict], slots_data: list[dict]) -> None:
    for sd in slots_data:
        existing = db.query(Slot).filter(Slot.date == sd["date"], Slot.time_slot == sd["time_slot"]).first()
        if not existing:
            db.add(Slot(date=sd["date"], time_slot=sd["time_slot"], is_available=sd["is_available"]))

    for bd in bookings_data:
        existing = db.query(Booking).filter(Booking.booking_ref == bd["booking_ref"]).first()
        if not existing:
            db.add(Booking(
                booking_ref=bd["booking_ref"],
                customer_name=bd["customer_name"],
                phone=bd["phone"],
                appointment_dt=bd["appointment_dt"],
                note=bd.get("note"),
                status=bd.get("status", "confirmed"),
                created_at=bd.get("created_at", datetime.utcnow()),
                booking_type="trial",
            ))

    db.flush()


def _needs_migration() -> bool:
    """Check if the old schema (products table) still exists."""
    if not OLD_DB_PATH.is_file():
        return False
    try:
        conn = sqlite3.connect(str(OLD_DB_PATH))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='products'")
        has_old = cursor.fetchone() is not None
        conn.close()
        return has_old
    except Exception:
        return False


def _drop_old_tables() -> None:
    """Drop all tables to rebuild with new schema."""
    Base.metadata.drop_all(bind=engine)


def seed_data(db: Session) -> None:
    if _needs_migration():
        bookings_data, slots_data = _backup_bookings_and_slots(db)
        db.close()
        _drop_old_tables()
        Base.metadata.create_all(bind=engine)
        from .database import SessionLocal

        db2 = SessionLocal()
        _restore_bookings_and_slots(db2, bookings_data, slots_data)
        db2.commit()
        db2.close()

    Base.metadata.create_all(bind=engine)
    load_catalog(db)
    load_slots(db)
    db.commit()
