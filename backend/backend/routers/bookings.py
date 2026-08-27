import random
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Booking, Club, Slot
from ..schemas import BookingDetail, BookingRequest, BookingResponse, SlotOut

router = APIRouter(tags=["bookings"])


def _generate_booking_ref() -> str:
    return f"BK-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"


@router.get("/slots", response_model=list[SlotOut])
def get_slots(date: str = Query(...), db: Session = Depends(get_db)):
    slots = (
        db.query(Slot)
        .filter(Slot.date == date, Slot.is_available.is_(True))
        .order_by(Slot.time_slot.asc())
        .all()
    )
    return [SlotOut(date=s.date, time_slot=s.time_slot) for s in slots]


@router.post("/bookings", response_model=BookingResponse)
def create_booking(payload: BookingRequest, db: Session = Depends(get_db)):
    if payload.appointment_dt <= datetime.now():
        raise HTTPException(status_code=400, detail="appointment_dt must be in the future")

    appt_date = payload.appointment_dt.strftime("%Y-%m-%d")
    appt_time = payload.appointment_dt.strftime("%H:%M")
    slot = (
        db.query(Slot)
        .filter(Slot.date == appt_date, Slot.time_slot == appt_time, Slot.is_available.is_(True))
        .first()
    )
    if not slot:
        raise HTTPException(status_code=400, detail="Selected slot is unavailable")

    club_id = None
    if payload.club_code:
        club = db.query(Club).filter(Club.code == payload.club_code).first()
        if not club:
            raise HTTPException(status_code=404, detail="Club not found")
        club_id = club.id

    booking_ref = _generate_booking_ref()
    while db.query(Booking).filter(Booking.booking_ref == booking_ref).first():
        booking_ref = _generate_booking_ref()

    booking = Booking(
        booking_ref=booking_ref,
        customer_name=payload.customer_name,
        phone=payload.phone,
        appointment_dt=payload.appointment_dt,
        note=payload.note,
        status="confirmed",
        club_id=club_id,
        booking_type=payload.booking_type or "trial",
    )
    slot.is_available = False
    db.add(booking)
    db.commit()
    db.refresh(booking)

    return BookingResponse(
        booking_ref=booking.booking_ref,
        customer_name=booking.customer_name,
        phone=booking.phone,
        appointment_dt=booking.appointment_dt,
        status=booking.status,
        message="Booking created successfully",
    )


@router.get("/bookings/{booking_ref}", response_model=BookingDetail)
def get_booking_detail(booking_ref: str, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.booking_ref == booking_ref).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return BookingDetail.model_validate(booking)
