from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import MembershipPlan, MembershipPlanBenefit
from ..schemas import BenefitOut, MembershipPlanBenefitOut, MembershipPlanDetail, MembershipPlanSummary

router = APIRouter(prefix="/memberships", tags=["memberships"])


def _plan_summary(plan: MembershipPlan) -> MembershipPlanSummary:
    return MembershipPlanSummary(
        id=plan.id,
        code=plan.code,
        name=plan.name,
        tier=plan.tier,
        price_vnd=plan.price_vnd,
        billing_cycle_days=plan.billing_cycle_days,
        access_scope=plan.access_scope,
        access_description=plan.access_description,
        is_marked_popular=plan.is_marked_popular,
        minimum_commitment_cycles=plan.minimum_commitment_cycles,
        benefits=[
            BenefitOut(code=pb.benefit.code, name=pb.benefit.name, description=pb.benefit.description)
            for pb in plan.benefits if pb.included
        ],
    )


def _plan_detail(plan: MembershipPlan) -> MembershipPlanDetail:
    return MembershipPlanDetail(
        id=plan.id,
        code=plan.code,
        name=plan.name,
        tier=plan.tier,
        price_vnd=plan.price_vnd,
        billing_cycle_days=plan.billing_cycle_days,
        minimum_commitment_cycles=plan.minimum_commitment_cycles,
        access_scope=plan.access_scope,
        access_description=plan.access_description,
        is_marked_popular=plan.is_marked_popular,
        benefits=[
            MembershipPlanBenefitOut(
                code=pb.benefit.code, name=pb.benefit.name,
                included=pb.included, details=pb.details,
            )
            for pb in plan.benefits
        ],
    )


@router.get("/search", response_model=list[MembershipPlanSummary])
def search_membership_plans(
    tier: str = Query(default=""),
    max_price_vnd: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(MembershipPlan).options(
        joinedload(MembershipPlan.benefits).joinedload(MembershipPlanBenefit.benefit),
    )
    if tier:
        query = query.filter(MembershipPlan.tier == tier.upper())
    if max_price_vnd > 0:
        query = query.filter(MembershipPlan.price_vnd <= max_price_vnd)

    plans = query.order_by(MembershipPlan.price_vnd.asc()).all()
    return [_plan_summary(p) for p in plans]


@router.get("/compare", response_model=list[MembershipPlanDetail])
def compare_membership_plans(codes: str = Query(...), db: Session = Depends(get_db)):
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    if len(code_list) < 2:
        raise HTTPException(status_code=400, detail="At least 2 plan codes are required")

    plans = (
        db.query(MembershipPlan)
        .options(
            joinedload(MembershipPlan.benefits).joinedload(MembershipPlanBenefit.benefit),
        )
        .filter(MembershipPlan.code.in_(code_list))
        .all()
    )
    if len(plans) != len(set(code_list)):
        raise HTTPException(status_code=404, detail="One or more plan codes not found")

    index = {p.code: p for p in plans}
    return [_plan_detail(index[c]) for c in code_list]


@router.get("/{plan_code}", response_model=MembershipPlanDetail)
def get_membership_plan(plan_code: str, db: Session = Depends(get_db)):
    plan = (
        db.query(MembershipPlan)
        .options(
            joinedload(MembershipPlan.benefits).joinedload(MembershipPlanBenefit.benefit),
        )
        .filter(MembershipPlan.code == plan_code)
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Membership plan not found")
    return _plan_detail(plan)
