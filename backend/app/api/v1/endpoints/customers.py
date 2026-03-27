"""
Customer management endpoints
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.dependencies import get_access_control_context, get_current_user
from app.core.permissions import AccessControlContext
from app.models.customer import Customer
from app.models.recovery_action import RecoveryAction
from app.models.user import User
from app.services.customer_risk_service import CustomerRiskAssessmentService
from app.services.recovery_execution_service import RecoveryExecutionService
from app.services.recovery_recommendation_service import RecoveryRecommendationEngine

router = APIRouter()


# Pydantic models for request/response
class CustomerRecoveryRequest(BaseModel):
    customer_id: str = Field(..., description="Customer ID to recover")
    trigger_context: Optional[Dict[str, Any]] = Field(
        None, description="Context that triggered recovery"
    )
    execute_immediately: bool = Field(
        False, description="Execute actions immediately vs schedule"
    )


class CustomerRiskResponse(BaseModel):
    customer_id: str
    churn_risk: float
    bad_review_likelihood: float
    risk_factors: Dict[str, Any]
    risk_level: str
    updated_at: str


class RecoveryActionResponse(BaseModel):
    id: str
    action_type: str
    priority: str
    title: str
    content: str
    scheduled_at: Optional[str]
    status: str
    confidence_score: Optional[float]


@router.get("/")
async def get_customers(
    skip: int = 0,
    limit: int = 100,
    at_risk_only: bool = False,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    org_context: AccessControlContext = Depends(get_access_control_context),
):
    """Get customers for the organization"""
    from sqlalchemy import func as sql_func

    from app.models.review import Review

    query = select(Customer).where(
        Customer.organization_id == org_context.organization_id
    )

    if at_risk_only:
        query = query.where(
            and_(
                Customer.churn_risk_score >= 0.6, Customer.bad_review_likelihood >= 0.6
            )
        )

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    customers = result.scalars().all()

    # Transform customers to match frontend expectations
    customers_data = []
    for customer in customers:
        # Get review statistics for this customer
        review_stats = await db.execute(
            select(
                sql_func.count(Review.id).label("total_reviews"),
                sql_func.avg(Review.rating).label("average_rating"),
                sql_func.max(Review.review_date).label("last_review_date"),
                sql_func.min(Review.review_date).label("first_review_date"),
            ).where(Review.customer_id == customer.id)
        )
        stats = review_stats.first()

        customer_dict = {
            "id": str(customer.id),
            "name": customer.name or "Unknown",
            "email": customer.email,
            "phone": customer.phone,
            "total_reviews": stats.total_reviews or 0,
            "average_rating": (
                float(stats.average_rating) if stats.average_rating else None
            ),
            "last_review_date": (
                stats.last_review_date.isoformat() if stats.last_review_date else None
            ),
            "first_review_date": (
                stats.first_review_date.isoformat() if stats.first_review_date else None
            ),
            "risk_score": (
                float(customer.churn_risk_score) if customer.churn_risk_score else 0.0
            ),
            "risk_level": customer.risk_level.lower() if customer.risk_level else "low",
            "churn_probability": (
                float(customer.bad_review_likelihood)
                if customer.bad_review_likelihood
                else 0.0
            ),
            "lifetime_value": (
                float(customer.lifetime_value) if customer.lifetime_value else 0.0
            ),
            "status": customer.status,
            "tags": customer.get_tags(),
            "created_at": (
                customer.created_at.isoformat() if customer.created_at else None
            ),
            "updated_at": (
                customer.updated_at.isoformat() if customer.updated_at else None
            ),
            "metadata": {
                "location": None,  # Could be added to customer model later
                "preferred_contact_method": customer.preferred_contact_method,
                "timezone": customer.timezone,
            },
        }
        customers_data.append(customer_dict)

    return {
        "customers": customers_data,
        "total": len(customers_data),
        "at_risk_filter": at_risk_only,
    }


@router.get("/{customer_id}/risk")
async def get_customer_risk(
    customer_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    org_context: AccessControlContext = Depends(get_access_control_context),
) -> CustomerRiskResponse:
    """Get risk assessment for a specific customer"""
    # Verify customer belongs to organization
    customer = await db.get(Customer, customer_id)
    if not customer or customer.organization_id != org_context.organization_id:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Get risk assessment
    risk_service = CustomerRiskAssessmentService()
    risk_data = await risk_service.assess_customer_risk(customer_id, db)

    return CustomerRiskResponse(
        customer_id=customer_id,
        churn_risk=risk_data["churn_risk"],
        bad_review_likelihood=risk_data["bad_review_likelihood"],
        risk_factors=risk_data["risk_factors"],
        risk_level=customer.risk_level,
        updated_at=customer.updated_at.isoformat(),
    )


@router.post("/recover")
async def recover_customer(
    request: CustomerRecoveryRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    org_context: AccessControlContext = Depends(get_access_control_context),
):
    """Initiate customer recovery process"""
    # Verify customer belongs to organization
    customer = await db.get(Customer, request.customer_id)
    if not customer or customer.organization_id != org_context.organization_id:
        raise HTTPException(status_code=404, detail="Customer not found")

    try:
        # Get recovery recommendations
        recommendation_engine = RecoveryRecommendationEngine()
        recommendations = await recommendation_engine.recommend_recovery_actions(
            request.customer_id, db, request.trigger_context
        )

        # Create recovery actions
        recovery_actions = await recommendation_engine.create_recovery_actions(
            request.customer_id, recommendations, db, request.trigger_context
        )

        # Execute immediately if requested
        executed_actions = []
        if request.execute_immediately:
            execution_service = RecoveryExecutionService()
            for action in recovery_actions:
                if not action.requires_approval:  # Only execute non-approval actions
                    result = await execution_service.execute_action(str(action.id), db)
                    executed_actions.append(result)

        return {
            "customer_id": request.customer_id,
            "recovery_actions_created": len(recovery_actions),
            "actions": [
                RecoveryActionResponse(
                    id=str(action.id),
                    action_type=action.action_type.value,
                    priority=action.priority.value,
                    title=action.title,
                    content=action.content,
                    scheduled_at=(
                        action.scheduled_at.isoformat() if action.scheduled_at else None
                    ),
                    status=action.status.value,
                    confidence_score=(
                        float(action.confidence_score)
                        if action.confidence_score
                        else None
                    ),
                )
                for action in recovery_actions
            ],
            "executed_immediately": len(executed_actions),
            "execution_results": executed_actions,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Recovery process failed: {str(e)}"
        )


@router.get("/{customer_id}/recovery-actions")
async def get_customer_recovery_actions(
    customer_id: str,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    org_context: AccessControlContext = Depends(get_access_control_context),
):
    """Get recovery actions for a specific customer"""
    # Verify customer belongs to organization
    customer = await db.get(Customer, customer_id)
    if not customer or customer.organization_id != org_context.organization_id:
        raise HTTPException(status_code=404, detail="Customer not found")

    query = select(RecoveryAction).where(RecoveryAction.customer_id == customer_id)

    if status_filter:
        query = query.where(RecoveryAction.status == status_filter)

    query = query.order_by(RecoveryAction.created_at.desc())

    result = await db.execute(query)
    actions = result.scalars().all()

    return {
        "customer_id": customer_id,
        "recovery_actions": [action.to_dict() for action in actions],
        "total": len(actions),
        "status_filter": status_filter,
    }


@router.post("/batch-risk-update")
async def batch_update_risk_scores(
    limit: int = 50,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    org_context: AccessControlContext = Depends(get_access_control_context),
):
    """Update risk scores for multiple customers in batch"""
    risk_service = CustomerRiskAssessmentService()

    result = await risk_service.batch_update_risk_scores(
        str(org_context.organization_id), db, limit
    )

    return {
        "organization_id": str(org_context.organization_id),
        "batch_update_result": result,
    }


@router.get("/at-risk")
async def get_at_risk_customers(
    risk_threshold: float = 0.6,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    org_context: AccessControlContext = Depends(get_access_control_context),
):
    """Get customers above risk threshold"""
    risk_service = CustomerRiskAssessmentService()

    at_risk_customers = await risk_service.get_at_risk_customers(
        str(org_context.organization_id), db, risk_threshold, limit
    )

    return {
        "at_risk_customers": [customer.to_dict() for customer in at_risk_customers],
        "total": len(at_risk_customers),
        "risk_threshold": risk_threshold,
    }
