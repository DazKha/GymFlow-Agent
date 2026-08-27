from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base


class SourceDocument(Base):
    __tablename__ = "source_documents"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(500), unique=True, nullable=False)
    title = Column(String(255), nullable=True)
    document_type = Column(String(50), nullable=False)
    fetched_at = Column(DateTime, nullable=False)
    content_hash = Column(String(64), nullable=False)
    raw_text = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="active")


class MembershipPlan(Base):
    __tablename__ = "membership_plans"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(150), nullable=False)
    tier = Column(String(30), nullable=False)
    price_vnd = Column(Integer, nullable=False)
    billing_cycle_days = Column(Integer, nullable=False)
    minimum_commitment_cycles = Column(Integer, nullable=False)
    access_scope = Column(String(50), nullable=False)
    access_description = Column(Text, nullable=False)
    is_marked_popular = Column(Boolean, nullable=False, default=False)
    active = Column(Boolean, nullable=False, default=True)
    valid_from = Column(DateTime, nullable=True)
    valid_until = Column(DateTime, nullable=True)
    source_document_id = Column(Integer, ForeignKey("source_documents.id"), nullable=True)

    benefits = relationship("MembershipPlanBenefit", back_populates="plan")
    source = relationship("SourceDocument", lazy="joined")


class Benefit(Base):
    __tablename__ = "benefits"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)

    plan_benefits = relationship("MembershipPlanBenefit", back_populates="benefit")


class MembershipPlanBenefit(Base):
    __tablename__ = "membership_plan_benefits"

    plan_id = Column(Integer, ForeignKey("membership_plans.id", ondelete="CASCADE"), primary_key=True)
    benefit_id = Column(Integer, ForeignKey("benefits.id", ondelete="CASCADE"), primary_key=True)
    included = Column(Boolean, nullable=False, default=True)
    details = Column(Text, nullable=True)
    source_document_id = Column(Integer, ForeignKey("source_documents.id"), nullable=True)

    plan = relationship("MembershipPlan", back_populates="benefits")
    benefit = relationship("Benefit", back_populates="plan_benefits")


class Club(Base):
    __tablename__ = "clubs"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    brand = Column(String(30), nullable=False)
    city = Column(String(100), nullable=False)
    district = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)
    latitude = Column(String(20), nullable=True)
    longitude = Column(String(20), nullable=True)
    phone = Column(String(30), nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    source_document_id = Column(Integer, ForeignKey("source_documents.id"), nullable=True)

    opening_hours = relationship("ClubOpeningHour", back_populates="club")
    facilities = relationship("ClubFacility", back_populates="club")
    source = relationship("SourceDocument", lazy="joined")


class ClubOpeningHour(Base):
    __tablename__ = "club_opening_hours"

    id = Column(Integer, primary_key=True, index=True)
    club_id = Column(Integer, ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False)
    day_of_week = Column(String(10), nullable=False)
    opens_at = Column(String(5), nullable=False)
    closes_at = Column(String(5), nullable=False)
    source_document_id = Column(Integer, ForeignKey("source_documents.id"), nullable=True)

    club = relationship("Club", back_populates="opening_hours")
    __table_args__ = (UniqueConstraint("club_id", "day_of_week"),)


class FacilityType(Base):
    __tablename__ = "facility_types"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(150), nullable=False)
    category = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)


class ClubFacility(Base):
    __tablename__ = "club_facilities"

    club_id = Column(Integer, ForeignKey("clubs.id", ondelete="CASCADE"), primary_key=True)
    facility_type_id = Column(Integer, ForeignKey("facility_types.id", ondelete="CASCADE"), primary_key=True)
    availability_status = Column(String(20), nullable=False, default="not_published")
    brand = Column(String(100), nullable=True)
    quantity = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)
    source_document_id = Column(Integer, ForeignKey("source_documents.id"), nullable=True)

    club = relationship("Club", back_populates="facilities")
    facility_type = relationship("FacilityType", lazy="joined")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    booking_ref = Column(String(30), unique=True, nullable=False, index=True)
    customer_name = Column(String(120), nullable=False)
    phone = Column(String(30), nullable=False)
    appointment_dt = Column(DateTime, nullable=False, index=True)
    note: Optional[str] = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="confirmed")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    club_id = Column(Integer, ForeignKey("clubs.id"), nullable=True)
    booking_type = Column(String(20), nullable=False, default="trial")


class Slot(Base):
    __tablename__ = "slots"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String(10), nullable=False, index=True)
    time_slot = Column(String(5), nullable=False, index=True)
    is_available = Column(Boolean, nullable=False, default=True)
