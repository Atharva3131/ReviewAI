"""
Agent orchestration endpoints
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.agent import (
    AgentDecisionRequest, AgentDecisionResponse, AgentDecisionValidationRequest,
    AgentDecisionExecutionRequest, AgentDecisionFilter, AgentDecisionStats,
    DecisionRulesResponse
)

from app.core.database import get_async_db
from app.core.dependencies import get_current_user, get_access_control_context
from app.core.permissions import AccessControlContext
from app.models.user import User
from app.models.review import Review
from app.models.support_ticket import SupportTicket
from app.models.agent_decision import AgentDecision, DecisionType, InputType, DecisionStatus
from app.services.agent_engine import AgentEngine
from app.services.review_service import ReviewService

router = APIRouter()




@router.post("/decide-action", response_model=AgentDecisionResponse)
async def decide_action(
    request: AgentDecisionRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    org_context: AccessControlContext = Depends(get_access_control_context)
):
    """
    Agent decision endpoint for determining actions on reviews or support tickets
    """
    agent_engine = AgentEngine()
    
    try:
        # Get input object based on type
        if request.input_type == "review":
            input_obj = await ReviewService.get_review_by_id(
                db, request.input_id, org_context.organization_id
            )
            if not input_obj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Review not found"
                )
            
            # Process review decision
            decision_result = await agent_engine.process_review(
                review=input_obj,
                db=db,
                organization_id=org_context.organization_id,
                additional_context=request.context
            )
            
        elif request.input_type == "support_ticket":
            # For now, we'll return a placeholder since support tickets aren't fully implemented
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Support ticket processing not yet implemented"
            )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid input type"
            )
        
        # Validate the decision
        validation_result = await agent_engine.validate_decision(
            decision_result=decision_result,
            input_data={"rating": getattr(input_obj, "rating", None)}
        )
        
        # Get the logged decision from database
        # Find the most recent decision for this input
        from sqlalchemy import select, desc
        result = await db.execute(
            select(AgentDecision)
            .where(
                AgentDecision.organization_id == org_context.organization_id,
                AgentDecision.input_type == InputType.REVIEW if request.input_type == "review" else InputType.SUPPORT_TICKET,
                AgentDecision.input_id == input_obj.id
            )
            .order_by(desc(AgentDecision.created_at))
            .limit(1)
        )
        
        logged_decision = result.scalar_one_or_none()
        
        if not logged_decision:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to log decision"
            )
        
        return AgentDecisionResponse(
            decision_id=str(logged_decision.id),
            input_type=request.input_type,
            input_id=request.input_id,
            decision_type=decision_result.decision_type.value,
            confidence_score=decision_result.confidence_score,
            reasoning=decision_result.reasoning,
            generated_content=decision_result.generated_content,
            content_type=decision_result.content_type,
            requires_approval=decision_result.requires_approval,
            processing_time_ms=decision_result.processing_time_ms,
            context_factors=decision_result.context_factors,
            validation_result=validation_result,
            created_at=logged_decision.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent decision failed: {str(e)}"
        )


@router.get("/decisions", response_model=List[Dict[str, Any]])
async def get_agent_decisions(
    skip: int = 0,
    limit: int = 100,
    input_type: Optional[str] = None,
    decision_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    org_context: AccessControlContext = Depends(get_access_control_context)
):
    """
    Get agent decisions with filtering
    """
    from sqlalchemy import select, desc, and_
    
    query = select(AgentDecision).where(
        AgentDecision.organization_id == org_context.organization_id
    )
    
    # Apply filters
    if input_type:
        try:
            input_type_enum = InputType(input_type)
            query = query.where(AgentDecision.input_type == input_type_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid input type"
            )
    
    if decision_type:
        try:
            decision_type_enum = DecisionType(decision_type)
            query = query.where(AgentDecision.decision_type == decision_type_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid decision type"
            )
    
    if status:
        try:
            status_enum = DecisionStatus(status)
            query = query.where(AgentDecision.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status"
            )
    
    # Apply pagination and ordering
    query = query.order_by(desc(AgentDecision.created_at)).offset(skip).limit(limit)
    
    result = await db.execute(query)
    decisions = result.scalars().all()
    
    return [decision.to_dict() for decision in decisions]


@router.get("/decisions/{decision_id}", response_model=Dict[str, Any])
async def get_agent_decision(
    decision_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    org_context: AccessControlContext = Depends(get_access_control_context)
):
    """
    Get a specific agent decision by ID
    """
    from sqlalchemy import select, and_
    import uuid
    
    try:
        decision_uuid = uuid.UUID(decision_id)
        result = await db.execute(
            select(AgentDecision).where(
                and_(
                    AgentDecision.id == decision_uuid,
                    AgentDecision.organization_id == org_context.organization_id
                )
            )
        )
        
        decision = result.scalar_one_or_none()
        
        if not decision:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Decision not found"
            )
        
        return decision.to_dict()
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid decision ID format"
        )


@router.post("/decisions/{decision_id}/validate")
async def validate_agent_decision(
    decision_id: str,
    request: AgentDecisionValidationRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    org_context: AccessControlContext = Depends(get_access_control_context)
):
    """
    Approve or reject an agent decision
    """
    from sqlalchemy import select, and_
    import uuid
    
    try:
        decision_uuid = uuid.UUID(decision_id)
        result = await db.execute(
            select(AgentDecision).where(
                and_(
                    AgentDecision.id == decision_uuid,
                    AgentDecision.organization_id == org_context.organization_id
                )
            )
        )
        
        decision = result.scalar_one_or_none()
        
        if not decision:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Decision not found"
            )
        
        if decision.status != DecisionStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Decision has already been reviewed"
            )
        
        # Update decision status
        if request.action == "approve":
            decision.approve(str(current_user.id), request.notes)
        else:
            decision.reject(str(current_user.id), request.notes or "Rejected by user")
        
        await db.commit()
        
        return {
            "decision_id": decision_id,
            "action": request.action,
            "status": decision.status.value,
            "reviewed_by": decision.reviewed_by,
            "reviewed_at": decision.reviewed_at.isoformat() if decision.reviewed_at else None,
            "notes": decision.review_notes
        }
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid decision ID format"
        )


@router.post("/decisions/{decision_id}/execute")
async def execute_agent_decision(
    decision_id: str,
    request: AgentDecisionExecutionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    org_context: AccessControlContext = Depends(get_access_control_context)
):
    """
    Execute an approved agent decision
    """
    from sqlalchemy import select, and_
    import uuid
    
    try:
        decision_uuid = uuid.UUID(decision_id)
        result = await db.execute(
            select(AgentDecision).where(
                and_(
                    AgentDecision.id == decision_uuid,
                    AgentDecision.organization_id == org_context.organization_id
                )
            )
        )
        
        decision = result.scalar_one_or_none()
        
        if not decision:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Decision not found"
            )
        
        if decision.status != DecisionStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Decision must be approved before execution"
            )
        
        # Queue execution as background task
        background_tasks.add_task(
            _execute_decision_background,
            decision_id=str(decision.id),
            organization_id=org_context.organization_id,
            executed_by=str(current_user.id),
            execution_context=request.execution_context
        )
        
        return {
            "decision_id": decision_id,
            "status": "queued_for_execution",
            "message": "Decision execution has been queued"
        }
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid decision ID format"
        )


@router.get("/rules/summary")
async def get_decision_rules_summary(
    current_user: User = Depends(get_current_user),
    org_context: AccessControlContext = Depends(get_access_control_context)
):
    """
    Get summary of all decision rules
    """
    from app.services.decision_rules_engine import DecisionRulesEngine
    
    rules_engine = DecisionRulesEngine()
    return rules_engine.get_rule_summary()


async def _execute_decision_background(
    decision_id: str,
    organization_id: str,
    executed_by: str,
    execution_context: Optional[Dict[str, Any]] = None
):
    """
    Background task to execute agent decision
    """
    # This would implement the actual execution logic
    # For now, just mark as executed
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import select
    import uuid
    
    async with AsyncSessionLocal() as db:
        try:
            decision_uuid = uuid.UUID(decision_id)
            result = await db.execute(
                select(AgentDecision).where(AgentDecision.id == decision_uuid)
            )
            
            decision = result.scalar_one_or_none()
            if decision:
                decision.execute(
                    executed_by=executed_by,
                    result={"execution_context": execution_context, "status": "completed"}
                )
                await db.commit()
                
        except Exception as e:
            # Mark as failed
            if decision:
                decision.mark_failed(str(e))
                await db.commit()
