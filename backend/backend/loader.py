"""Idempotent catalog loader from california-catalog.json."""

from __future__ import annotations

import json
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from .models import (
    Benefit,
    Club,
    ClubOpeningHour,
    FacilityType,
    MembershipPlan,
    MembershipPlanBenefit,
    SourceDocument,
)

CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "california-catalog.json"

EXPECTED_PLAN_CODES = {
    "CALI_GOLD_ACTIVE",
    "CALI_GOLD_REGIONAL",
    "CALI_GOLD_STANDARD",
    "CALI_PLATINUM",
    "CALI_PREMIER",
    "CALI_DIAMOND",
}


def _catalog_is_current(db: Session) -> bool:
    existing = {code for (code,) in db.query(MembershipPlan.code).all()}
    return existing == EXPECTED_PLAN_CODES


def _upsert_source(db: Session, source: dict) -> SourceDocument:
    doc = db.query(SourceDocument).filter(SourceDocument.url == source["url"]).first()
    if doc:
        return doc
    content = json.dumps(source, sort_keys=True, ensure_ascii=False)
    fetched = source.get("fetched_at", "2026-08-08T15:52:00+07:00")
    doc = SourceDocument(
        url=source["url"],
        title=source.get("title"),
        document_type=source["document_type"],
        fetched_at=datetime.fromisoformat(fetched),
        content_hash=sha256(content.encode()).hexdigest(),
        status="active",
    )
    db.add(doc)
    db.flush()
    return doc


def _make_club_code(city: str, label: str) -> str:
    base = f"{city.lower().replace(' ', '_')}_{label.lower().replace(' ', '_').replace('-', '_')}"
    return f"CLUB_{base.upper()[:40]}"


def load_catalog(db: Session) -> None:
    """Idempotent load of the California catalog snapshot."""
    if _catalog_is_current(db):
        return

    with open(CATALOG_PATH, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)

    source_map: dict[str, SourceDocument] = {}
    for src in data.get("sources", []):
        source_map[src["id"]] = _upsert_source(db, src)

    benefit_map: dict[str, Benefit] = {}
    for b in data.get("benefits", []):
        benefit = db.query(Benefit).filter(Benefit.code == b["code"]).first()
        if not benefit:
            benefit = Benefit(code=b["code"], name=b["name"], description=b["description"])
            db.add(benefit)
            db.flush()
        benefit_map[b["code"]] = benefit

    for plan_data in data.get("membership_plans", []):
        plan = db.query(MembershipPlan).filter(MembershipPlan.code == plan_data["code"]).first()
        if not plan:
            plan = MembershipPlan(
                code=plan_data["code"],
                name=plan_data["name"],
                tier=plan_data["tier"],
                price_vnd=plan_data["price_vnd"],
                billing_cycle_days=plan_data.get("billing_cycle_days", 30),
                minimum_commitment_cycles=plan_data.get("minimum_commitment_cycles", 12),
                access_scope=plan_data["access_scope"],
                access_description=plan_data["access_description"],
                is_marked_popular=plan_data.get("is_marked_popular", False),
                source_document_id=source_map[plan_data["source_id"]].id
                if plan_data.get("source_id") in source_map
                else None,
            )
            db.add(plan)
            db.flush()

            for bc in plan_data.get("benefit_codes", []):
                if bc in benefit_map:
                    db.add(MembershipPlanBenefit(plan_id=plan.id, benefit_id=benefit_map[bc].id, included=True))

    facility_map: dict[str, FacilityType] = {}
    for ft_data in data.get("facility_types", []):
        ft = db.query(FacilityType).filter(FacilityType.code == ft_data["code"]).first()
        if not ft:
            ft = FacilityType(
                code=ft_data["code"],
                name=ft_data["name"],
                category=ft_data["category"],
                description=ft_data["description"],
            )
            db.add(ft)
            db.flush()
        facility_map[ft_data["code"]] = ft

    map_source_id = source_map.get("SRC_MAP").id if "SRC_MAP" in source_map else None
    for city, labels in data.get("club_directory", {}).items():
        for label in labels:
            code = _make_club_code(city, label)
            if db.query(Club).filter(Club.code == code).first():
                continue

            verified = []
            for v in data.get("verified_club_details", []):
                label_parts = set(label.lower().replace(" - ", " ").split())
                name_parts = set(v["name"].lower().replace(" - ", " ").split())
                common = label_parts & name_parts
                if len(common) >= 2:
                    verified.append(v)

            brand = "CALIFORNIA"
            if "centuryon" in label.lower():
                brand = "CENTURYON"
            elif "yoga plus" in label.lower():
                brand = "YOGA_PLUS"
            elif "active" in label.lower():
                brand = "CALI_ACTIVE"

            district = label.split(" - ")[0].strip() if " - " in label else None

            club = Club(
                code=code,
                name=label,
                brand=brand,
                city=city,
                district=district,
                address=verified[0]["address"] if verified else None,
                source_document_id=map_source_id,
            )
            db.add(club)
            db.flush()

            if verified:
                for oh in verified[0].get("opening_hours", []):
                    for day in oh["days"]:
                        db.add(ClubOpeningHour(
                            club_id=club.id, day_of_week=day,
                            opens_at=oh["opens"], closes_at=oh["closes"],
                            source_document_id=map_source_id,
                        ))


def load_slots(db: Session) -> None:
    """Ensure 7 days of hourly slots exist. Preserves existing availability."""
    from datetime import date, timedelta

    from .models import Slot

    existing = {(s.date, s.time_slot) for s in db.query(Slot).all()}
    start = date.today()
    for day_index in range(7):
        slot_date = (start + timedelta(days=day_index)).strftime("%Y-%m-%d")
        for hour in range(7, 21):
            time_slot = f"{hour:02d}:00"
            if (slot_date, time_slot) not in existing:
                db.add(Slot(date=slot_date, time_slot=time_slot, is_available=True))
