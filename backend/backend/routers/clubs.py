from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import Club, ClubFacility, ClubOpeningHour
from ..schemas import ClubDetail, ClubFacilityOut, ClubSummary, FacilityTypeOut, OpeningHourOut

router = APIRouter(prefix="/clubs", tags=["clubs"])


def _club_summary(club: Club) -> ClubSummary:
    return ClubSummary(
        id=club.id,
        code=club.code,
        name=club.name,
        brand=club.brand,
        city=club.city,
        district=club.district,
        address=club.address,
        active=club.active,
    )


def _club_detail(club: Club) -> ClubDetail:
    return ClubDetail(
        id=club.id,
        code=club.code,
        name=club.name,
        brand=club.brand,
        city=club.city,
        district=club.district,
        address=club.address,
        phone=club.phone,
        active=club.active,
        opening_hours=[
            OpeningHourOut(day_of_week=oh.day_of_week, opens_at=oh.opens_at, closes_at=oh.closes_at)
            for oh in club.opening_hours
        ],
        facilities=[
            ClubFacilityOut(
                facility_type=FacilityTypeOut(
                    id=cf.facility_type.id,
                    code=cf.facility_type.code,
                    name=cf.facility_type.name,
                    category=cf.facility_type.category,
                    description=cf.facility_type.description,
                ),
                availability_status=cf.availability_status,
                brand=cf.brand,
                quantity=cf.quantity,
                details=cf.details,
            )
            for cf in club.facilities
        ],
    )


@router.get("/search", response_model=list[ClubSummary])
def search_clubs(
    city: str = Query(default=""),
    district: str = Query(default=""),
    brand: str = Query(default=""),
    db: Session = Depends(get_db),
):
    query = db.query(Club)
    if city:
        query = query.filter(Club.city.ilike(f"%{city}%"))
    if district:
        query = query.filter(Club.district.ilike(f"%{district}%"))
    if brand:
        query = query.filter(Club.brand == brand.upper())
    clubs = query.order_by(Club.city, Club.name).all()
    return [_club_summary(c) for c in clubs]


@router.get("/{club_code}", response_model=ClubDetail)
def get_club_details(club_code: str, db: Session = Depends(get_db)):
    club = (
        db.query(Club)
        .options(
            joinedload(Club.opening_hours),
            joinedload(Club.facilities).joinedload(ClubFacility.facility_type),
        )
        .filter(Club.code == club_code)
        .first()
    )
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    return _club_detail(club)


@router.get("/{club_code}/hours", response_model=list[OpeningHourOut])
def get_club_opening_hours(club_code: str, day_of_week: str = Query(default=""), db: Session = Depends(get_db)):
    club = db.query(Club).filter(Club.code == club_code).first()
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")

    query = db.query(ClubOpeningHour).filter(ClubOpeningHour.club_id == club.id)
    if day_of_week:
        query = query.filter(ClubOpeningHour.day_of_week == day_of_week.lower())
    hours = query.order_by(ClubOpeningHour.day_of_week).all()
    return [
        OpeningHourOut(day_of_week=h.day_of_week, opens_at=h.opens_at, closes_at=h.closes_at)
        for h in hours
    ]
