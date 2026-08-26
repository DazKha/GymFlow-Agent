from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import FacilityType
from ..schemas import FacilityTypeOut

router = APIRouter(tags=["facilities"])


@router.get("/facilities", response_model=list[FacilityTypeOut])
def get_facility_types(category: str = Query(default=""), db: Session = Depends(get_db)):
    query = db.query(FacilityType)
    if category:
        query = query.filter(FacilityType.category == category.lower())
    facilities = query.order_by(FacilityType.name.asc()).all()
    return [
        FacilityTypeOut(
            id=ft.id, code=ft.code, name=ft.name,
            category=ft.category, description=ft.description,
        )
        for ft in facilities
    ]
