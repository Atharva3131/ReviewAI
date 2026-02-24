"""Support ticket API endpoints"""
from fastapi import APIRouter, Depends, Query, status
from typing import Optional, List
from uuid import UUID

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.models.support_ticket import TicketStatus, TicketPriority, TicketCategory
from app.schemas.support_ticket import (
    SupportTicketCreate,
    SupportTicketUpdate,
    SupportTicketResponse,
    SupportTicketListResponse,
    TicketAssignRequest,
    TicketResolveRequest,
    TicketReopenRequest,
    TicketSatisfactionRequest,
    TicketResponseRequest,
    TicketAnalyzeRequest,
    TicketAnalyzeResponse,
    TicketStatsResponse
)
from app.services.support_ticket_service import SupportTicketService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post(
    "/",
    response_model=SupportTicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new support ticket"
)
async def create_ticket(
    ticket_data: SupportTicketCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new support ticket.
    
    - **subject**: Ticket subject (required)
    - **content**: Ticket description (required)
    - **priority**: Ticket priority (default: medium)
    - **category**: Ticket category (optional)
    - **customer_id**: Associated customer ID (optional)
    - **source**: Ticket source (email, chat, phone, web)
    - **tags**: List of tags (optional)
    """
    service = SupportTicketService(db)
    ticket = await service.create_ticket(current_user.organization_id, ticket_data)
    return ticket


@router.get(
    "/",
    response_model=SupportTicketListResponse,
    summary="List support tickets"
)
async def list_tickets(
    status_filter: Optional[TicketStatus] = Query(None, alias="status"),
    priority: Optional[TicketPriority] = None,
    category: Optional[TicketCategory] = None,
    customer_id: Optional[UUID] = None,
    assigned_to: Optional[str] = None,
    is_overdue: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List support tickets with optional filters and pagination.
    
    - **status**: Filter by ticket status
    - **priority**: Filter by priority
    - **category**: Filter by category
    - **customer_id**: Filter by customer
    - **assigned_to**: Filter by assigned user
    - **is_overdue**: Filter overdue tickets
    - **search**: Search in subject, content, or ticket number
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 50, max: 100)
    """
    service = SupportTicketService(db)
    tickets, total = await service.list_tickets(
        organization_id=current_user.organization_id,
        status=status_filter,
        priority=priority,
        category=category,
        customer_id=customer_id,
        assigned_to=assigned_to,
        is_overdue=is_overdue,
        search=search,
        page=page,
        page_size=page_size
    )
    
    total_pages = (total + page_size - 1) // page_size
    
    return SupportTicketListResponse(
        tickets=tickets,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get(
    "/stats",
    response_model=TicketStatsResponse,
    summary="Get ticket statistics"
)
async def get_ticket_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive ticket statistics for the organization.
    
    Returns counts, averages, and breakdowns by priority, category, and source.
    """
    service = SupportTicketService(db)
    stats = await service.get_ticket_stats(current_user.organization_id)
    return stats


@router.get(
    "/{ticket_id}",
    response_model=SupportTicketResponse,
    summary="Get a support ticket"
)
async def get_ticket(
    ticket_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific support ticket by ID.
    """
    service = SupportTicketService(db)
    ticket = await service.get_ticket(ticket_id, current_user.organization_id)
    return ticket


@router.patch(
    "/{ticket_id}",
    response_model=SupportTicketResponse,
    summary="Update a support ticket"
)
async def update_ticket(
    ticket_id: UUID,
    update_data: SupportTicketUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a support ticket.
    
    Only provided fields will be updated.
    """
    service = SupportTicketService(db)
    ticket = await service.update_ticket(ticket_id, current_user.organization_id, update_data)
    return ticket


@router.post(
    "/{ticket_id}/assign",
    response_model=SupportTicketResponse,
    summary="Assign a ticket"
)
async def assign_ticket(
    ticket_id: UUID,
    assign_data: TicketAssignRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Assign a ticket to a user.
    
    Automatically changes status from OPEN to IN_PROGRESS.
    """
    service = SupportTicketService(db)
    ticket = await service.assign_ticket(
        ticket_id,
        current_user.organization_id,
        assign_data.assigned_to
    )
    return ticket


@router.post(
    "/{ticket_id}/resolve",
    response_model=SupportTicketResponse,
    summary="Resolve a ticket"
)
async def resolve_ticket(
    ticket_id: UUID,
    resolve_data: TicketResolveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Resolve a support ticket.
    
    - **resolution**: Description of how the issue was resolved
    - **resolved_by**: User ID or name who resolved the ticket
    """
    service = SupportTicketService(db)
    ticket = await service.resolve_ticket(
        ticket_id,
        current_user.organization_id,
        resolve_data.resolution,
        resolve_data.resolved_by
    )
    return ticket


@router.post(
    "/{ticket_id}/close",
    response_model=SupportTicketResponse,
    summary="Close a ticket"
)
async def close_ticket(
    ticket_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Close a resolved ticket.
    
    Ticket must be in RESOLVED status before it can be closed.
    """
    service = SupportTicketService(db)
    ticket = await service.close_ticket(ticket_id, current_user.organization_id)
    return ticket


@router.post(
    "/{ticket_id}/reopen",
    response_model=SupportTicketResponse,
    summary="Reopen a ticket"
)
async def reopen_ticket(
    ticket_id: UUID,
    reopen_data: TicketReopenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Reopen a resolved or closed ticket.
    
    - **reason**: Optional reason for reopening
    """
    service = SupportTicketService(db)
    ticket = await service.reopen_ticket(
        ticket_id,
        current_user.organization_id,
        reopen_data.reason
    )
    return ticket


@router.post(
    "/{ticket_id}/response",
    response_model=SupportTicketResponse,
    summary="Add a response to a ticket"
)
async def add_response(
    ticket_id: UUID,
    response_data: TicketResponseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a response to a ticket.
    
    - **content**: Response content
    - **is_internal**: Whether this is an internal note (not visible to customer)
    """
    service = SupportTicketService(db)
    ticket = await service.add_response(
        ticket_id,
        current_user.organization_id,
        response_data.content,
        response_data.is_internal
    )
    return ticket


@router.post(
    "/{ticket_id}/satisfaction",
    response_model=SupportTicketResponse,
    summary="Set customer satisfaction rating"
)
async def set_satisfaction(
    ticket_id: UUID,
    satisfaction_data: TicketSatisfactionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Set customer satisfaction rating for a resolved ticket.
    
    - **rating**: Satisfaction rating (1-5 stars)
    - **feedback**: Optional customer feedback
    """
    service = SupportTicketService(db)
    ticket = await service.set_satisfaction(
        ticket_id,
        current_user.organization_id,
        satisfaction_data.rating,
        satisfaction_data.feedback
    )
    return ticket


@router.post(
    "/analyze",
    response_model=TicketAnalyzeResponse,
    summary="Analyze a ticket"
)
async def analyze_ticket(
    analyze_data: TicketAnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze a ticket for sentiment, urgency, and get recommendations.
    
    Returns:
    - Sentiment score and label
    - Urgency score
    - Escalation risk
    - Recommended priority
    - Recommended category
    - Suggested actions
    """
    service = SupportTicketService(db)
    analysis = await service.analyze_ticket(
        analyze_data.ticket_id,
        current_user.organization_id
    )
    return analysis


@router.delete(
    "/{ticket_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a support ticket"
)
async def delete_ticket(
    ticket_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a support ticket.
    
    This is a permanent action and cannot be undone.
    """
    service = SupportTicketService(db)
    await service.delete_ticket(ticket_id, current_user.organization_id)
    return None

