from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class BenefitOut(BaseModel):
    code: str
    name: str
    description: str

    model_config = {"from_attributes": True}


class MembershipPlanBenefitOut(BaseModel):
    code: str
    name: str
    included: bool
    details: Optional[str] = None


class MembershipPlanSummary(BaseModel):
    id: int
    code: str
    name: str
    tier: str
    price_vnd: int
    billing_cycle_days: int
    access_scope: str
    access_description: str
    is_marked_popular: bool
    minimum_commitment_cycles: int
    benefits: list[BenefitOut]


class MembershipPlanDetail(BaseModel):
    id: int
    code: str
    name: str
    tier: str
    price_vnd: int
    billing_cycle_days: int
    minimum_commitment_cycles: int
    access_scope: str
    access_description: str
    is_marked_popular: bool
    benefits: list[MembershipPlanBenefitOut]


class FacilityTypeOut(BaseModel):
    id: int
    code: str
    name: str
    category: str
    description: str

    model_config = {"from_attributes": True}


class ClubFacilityOut(BaseModel):
    facility_type: FacilityTypeOut
    availability_status: str
    brand: Optional[str] = None
    quantity: Optional[int] = None
    details: Optional[str] = None

    model_config = {"from_attributes": True}


class OpeningHourOut(BaseModel):
    day_of_week: str
    opens_at: str
    closes_at: str

    model_config = {"from_attributes": True}


class ClubSummary(BaseModel):
    id: int
    code: str
    name: str
    brand: str
    city: str
    district: Optional[str] = None
    address: Optional[str] = None
    active: bool

    model_config = {"from_attributes": True}


class ClubDetail(BaseModel):
    id: int
    code: str
    name: str
    brand: str
    city: str
    district: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    active: bool
    opening_hours: list[OpeningHourOut]
    facilities: list[ClubFacilityOut]

    model_config = {"from_attributes": True}


class SlotOut(BaseModel):
    date: str
    time_slot: str


class BookingRequest(BaseModel):
    customer_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=8, max_length=30)
    appointment_dt: datetime
    note: Optional[str] = None
    club_code: Optional[str] = None
    booking_type: str = "trial"

    @field_validator("appointment_dt")
    @classmethod
    def appointment_must_be_future(cls, value: datetime) -> datetime:
        if value <= datetime.now():
            raise ValueError("appointment_dt must be in the future")
        return value


class BookingResponse(BaseModel):
    booking_ref: str
    customer_name: str
    phone: str
    appointment_dt: datetime
    status: str
    message: str


class BookingDetail(BaseModel):
    booking_ref: str
    customer_name: str
    phone: str
    appointment_dt: datetime
    note: Optional[str] = None
    status: str
    booking_type: str
    created_at: datetime

    model_config = {"from_attributes": True}
