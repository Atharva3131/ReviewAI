"""
Webhook endpoints for external service integrations
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_async_db
from app.services.customer_risk_service import CustomerRiskService
from app.services.external.google_reviews import (
    GoogleReviewsWebhookSimulator,
    create_google_reviews_service,
)
from app.services.realtime_metrics import RealTimeMetricsService
from app.services.review_service import ReviewService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/google-reviews", tags=["webhooks"])
async def google_reviews_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Google Reviews webhook endpoint

    Receives notifications about new reviews, review updates, and responses.
    Since Google My Business API has limited webhook support, this endpoint
    can also be used with webhook simulation for testing.
    """
    try:
        # Get request body
        body = await request.body()

        # Verify webhook signature if configured
        if settings.GOOGLE_WEBHOOK_SECRET:
            signature = request.headers.get("X-Google-Signature")
            if not signature or not _verify_google_signature(body, signature):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid webhook signature",
                )

        # Parse webhook data
        try:
            webhook_data = json.loads(body)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload"
            )

        # Log webhook received
        logger.info(
            "Google Reviews webhook received",
            extra={
                "event_type": webhook_data.get("event_type"),
                "timestamp": webhook_data.get("timestamp"),
                "source": webhook_data.get("source", "google_reviews"),
            },
        )

        # Process webhook in background
        background_tasks.add_task(_process_google_reviews_webhook, webhook_data, db)

        return {
            "status": "received",
            "message": "Webhook processed successfully",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Google Reviews webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error processing webhook",
        )


@router.post("/google-reviews/simulate", tags=["webhooks"])
async def simulate_google_reviews_webhook(
    background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_async_db)
):
    """
    Simulate Google Reviews webhook for testing

    This endpoint simulates webhook notifications by polling the Google Reviews API
    for new reviews and processing them as if they came via webhook.
    """
    try:
        # Create Google Reviews service and simulator
        google_service = create_google_reviews_service()
        simulator = GoogleReviewsWebhookSimulator(google_service)

        # Simulate webhook polling
        webhook_events = await simulator.simulate_webhook_polling()

        # Process each event
        for event in webhook_events:
            background_tasks.add_task(_process_google_reviews_webhook, event, db)

        logger.info(f"Simulated {len(webhook_events)} Google Reviews webhook events")

        return {
            "status": "simulated",
            "events_generated": len(webhook_events),
            "message": f"Generated {len(webhook_events)} webhook events",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error simulating Google Reviews webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error simulating webhook",
        )


@router.post("/google-reviews/test", tags=["webhooks"])
async def generate_test_google_review(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
    rating: int = 5,
    content: str = None,
):
    """
    Generate a test Google review for development

    Creates a fake review event for testing the review processing pipeline.
    """
    try:
        # Create Google Reviews service and simulator
        google_service = create_google_reviews_service()
        simulator = GoogleReviewsWebhookSimulator(google_service)

        # Generate test event
        test_event = await simulator.generate_test_review_event(rating, content)

        # Process the test event
        background_tasks.add_task(_process_google_reviews_webhook, test_event, db)

        logger.info(f"Generated test Google review with {rating} stars")

        return {
            "status": "generated",
            "test_event": test_event,
            "message": f"Generated test {rating}-star review",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error generating test Google review: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating test review",
        )


@router.get("/google-reviews/status", tags=["webhooks"])
async def get_google_reviews_status():
    """
    Get Google Reviews integration status

    Returns the current status of the Google Reviews API integration,
    including connection health and recent activity.
    """
    try:
        # Create Google Reviews service
        google_service = create_google_reviews_service()

        # Get service status
        status_info = await google_service.get_service_status()

        # Test connection
        connection_test = await google_service.test_connection()

        return {
            "service_status": status_info,
            "connection_test": {
                "success": connection_test.success,
                "error": connection_test.error,
                "response_time_ms": connection_test.response_time_ms,
            },
            "webhook_endpoint": "/api/v1/webhooks/google-reviews",
            "simulation_endpoint": "/api/v1/webhooks/google-reviews/simulate",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting Google Reviews status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving status",
        )


async def _process_google_reviews_webhook(
    webhook_data: Dict[str, Any], db: AsyncSession
):
    """Process Google Reviews webhook data"""
    try:
        event_type = webhook_data.get("event_type")
        review_data = webhook_data.get("data", {})

        if event_type == "review.created":
            await _handle_new_review(review_data, db)
        elif event_type == "review.updated":
            await _handle_updated_review(review_data, db)
        elif event_type == "review.response":
            await _handle_review_response(review_data, db)
        else:
            logger.warning(f"Unknown Google Reviews webhook event type: {event_type}")

    except Exception as e:
        logger.error(f"Error processing Google Reviews webhook: {e}", exc_info=True)


async def _handle_new_review(review_data: Dict[str, Any], db: AsyncSession):
    """Handle new review from Google"""
    try:
        # Create review service
        review_service = ReviewService(db)

        # Convert webhook data to review format
        review_input = {
            "platform": "google",
            "external_id": review_data.get("review_id"),
            "customer_name": review_data.get("customer_name"),
            "rating": review_data.get("rating"),
            "content": review_data.get("content", ""),
            "created_at": review_data.get("created_at"),
            "metadata": {
                "location_id": review_data.get("location_id"),
                "reviewer_profile_url": review_data.get("reviewer_profile_url"),
                "source": "google_reviews_webhook",
            },
        }

        # Process the review (this will trigger sentiment analysis, etc.)
        processed_review = await review_service.ingest_review(review_input)

        if processed_review:
            logger.info(
                f"Successfully processed new Google review: {review_data.get('review_id')}"
            )

            # Trigger real-time metrics update
            # Note: organization_id would need to be determined from the review or location
            organization_id = "default_org"  # TODO: Map location to organization
            await RealTimeMetricsService.on_review_created(organization_id, review_data)

    except Exception as e:
        logger.error(f"Error handling new Google review: {e}", exc_info=True)


async def _handle_updated_review(review_data: Dict[str, Any], db: AsyncSession):
    """Handle updated review from Google"""
    try:
        # TODO: Implement review update logic
        logger.info(f"Google review updated: {review_data.get('review_id')}")

    except Exception as e:
        logger.error(f"Error handling updated Google review: {e}", exc_info=True)


async def _handle_review_response(review_data: Dict[str, Any], db: AsyncSession):
    """Handle review response from Google"""
    try:
        # TODO: Implement review response handling
        logger.info(f"Google review response: {review_data.get('review_id')}")

    except Exception as e:
        logger.error(f"Error handling Google review response: {e}", exc_info=True)


def _verify_google_signature(payload: bytes, signature: str) -> bool:
    """Verify Google webhook signature"""
    try:
        if not settings.GOOGLE_WEBHOOK_SECRET:
            return True  # Skip verification if no secret configured

        # Google uses HMAC-SHA256
        expected_signature = hmac.new(
            settings.GOOGLE_WEBHOOK_SECRET.encode(), payload, hashlib.sha256
        ).hexdigest()

        # Compare signatures
        return hmac.compare_digest(signature, f"sha256={expected_signature}")

    except Exception as e:
        logger.error(f"Error verifying Google webhook signature: {e}")
        return False


# Webhook verification endpoints


@router.get("/google-reviews/verify", tags=["webhooks"])
async def verify_google_webhook(challenge: str = None):
    """
    Verify Google webhook endpoint

    Google may send a verification challenge to confirm the webhook endpoint.
    """
    if challenge:
        return {"challenge": challenge}

    return {
        "status": "verified",
        "endpoint": "/api/v1/webhooks/google-reviews",
        "timestamp": datetime.utcnow().isoformat(),
    }


# CRM System Webhook Endpoints


@router.post("/crm/customer-updated", tags=["webhooks"])
async def crm_customer_updated_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
):
    """
    CRM customer updated webhook endpoint

    Receives notifications when customer data is updated in the CRM system.
    This helps keep customer risk assessments up to date.
    """
    try:
        # Get request body
        body = await request.body()

        # Verify webhook signature if configured
        if settings.CRM_WEBHOOK_SECRET:
            signature = request.headers.get("X-CRM-Signature")
            if not signature or not _verify_crm_signature(body, signature):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid webhook signature",
                )

        # Parse webhook data
        try:
            webhook_data = json.loads(body)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload"
            )

        # Log webhook received
        logger.info(
            "CRM customer updated webhook received",
            extra={
                "customer_id": webhook_data.get("customer_id"),
                "event_type": webhook_data.get("event_type"),
                "timestamp": webhook_data.get("timestamp"),
            },
        )

        # Process webhook in background
        background_tasks.add_task(_process_crm_customer_webhook, webhook_data, db)

        return {
            "status": "received",
            "message": "CRM customer webhook processed successfully",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing CRM customer webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error processing webhook",
        )


@router.post("/crm/support-ticket", tags=["webhooks"])
async def crm_support_ticket_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
):
    """
    CRM support ticket webhook endpoint

    Receives notifications about support ticket creation, updates, and resolution.
    This helps identify at-risk customers and trigger recovery actions.
    """
    try:
        # Get request body
        body = await request.body()

        # Verify webhook signature if configured
        if settings.CRM_WEBHOOK_SECRET:
            signature = request.headers.get("X-CRM-Signature")
            if not signature or not _verify_crm_signature(body, signature):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid webhook signature",
                )

        # Parse webhook data
        try:
            webhook_data = json.loads(body)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload"
            )

        # Log webhook received
        logger.info(
            "CRM support ticket webhook received",
            extra={
                "ticket_id": webhook_data.get("ticket_id"),
                "customer_id": webhook_data.get("customer_id"),
                "event_type": webhook_data.get("event_type"),
                "priority": webhook_data.get("priority"),
                "timestamp": webhook_data.get("timestamp"),
            },
        )

        # Process webhook in background
        background_tasks.add_task(_process_crm_ticket_webhook, webhook_data, db)

        return {
            "status": "received",
            "message": "CRM support ticket webhook processed successfully",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing CRM support ticket webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error processing webhook",
        )


@router.post("/crm/interaction", tags=["webhooks"])
async def crm_interaction_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
):
    """
    CRM customer interaction webhook endpoint

    Receives notifications about customer interactions (calls, emails, meetings).
    This helps maintain customer context and improve risk assessment.
    """
    try:
        # Get request body
        body = await request.body()

        # Verify webhook signature if configured
        if settings.CRM_WEBHOOK_SECRET:
            signature = request.headers.get("X-CRM-Signature")
            if not signature or not _verify_crm_signature(body, signature):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid webhook signature",
                )

        # Parse webhook data
        try:
            webhook_data = json.loads(body)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload"
            )

        # Log webhook received
        logger.info(
            "CRM interaction webhook received",
            extra={
                "interaction_id": webhook_data.get("interaction_id"),
                "customer_id": webhook_data.get("customer_id"),
                "interaction_type": webhook_data.get("interaction_type"),
                "timestamp": webhook_data.get("timestamp"),
            },
        )

        # Process webhook in background
        background_tasks.add_task(_process_crm_interaction_webhook, webhook_data, db)

        return {
            "status": "received",
            "message": "CRM interaction webhook processed successfully",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing CRM interaction webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error processing webhook",
        )


@router.get("/crm/status", tags=["webhooks"])
async def get_crm_webhook_status():
    """
    Get CRM webhook integration status

    Returns the current status of CRM webhook endpoints and recent activity.
    """
    try:
        return {
            "webhook_endpoints": {
                "customer_updated": "/api/v1/webhooks/crm/customer-updated",
                "support_ticket": "/api/v1/webhooks/crm/support-ticket",
                "interaction": "/api/v1/webhooks/crm/interaction",
            },
            "webhook_verification": {
                "signature_verification": bool(settings.CRM_WEBHOOK_SECRET),
                "supported_events": [
                    "customer.created",
                    "customer.updated",
                    "customer.deleted",
                    "ticket.created",
                    "ticket.updated",
                    "ticket.resolved",
                    "interaction.created",
                ],
            },
            "status": "active",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting CRM webhook status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving CRM webhook status",
        )


@router.get("/health", tags=["webhooks"])
async def get_external_services_health():
    """
    Get health status of all external services

    Returns comprehensive health information including error statistics,
    circuit breaker states, and recent error history.
    """
    try:
        from app.services.external.error_handler import get_service_health_summary

        health_summary = await get_service_health_summary()

        return {
            "status": "success",
            "data": health_summary,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting external services health: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving external services health",
        )


@router.get("/errors/{service_name}", tags=["webhooks"])
async def get_service_errors(service_name: str, limit: int = 50):
    """
    Get recent errors for a specific external service

    Returns error history, statistics, and resolution status.
    """
    try:
        from app.services.external.error_handler import error_handler

        errors = await error_handler.get_service_errors(service_name, limit)
        error_stats = await error_handler.get_error_stats(service_name)

        return {
            "status": "success",
            "data": {
                "service_name": service_name,
                "errors": errors,
                "statistics": error_stats,
                "total_returned": len(errors),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(
            f"Error getting service errors for {service_name}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving errors for service {service_name}",
        )


# CRM Webhook Processing Functions


async def _process_crm_customer_webhook(webhook_data: Dict[str, Any], db: AsyncSession):
    """Process CRM customer webhook data"""
    try:
        event_type = webhook_data.get("event_type")
        customer_data = webhook_data.get("data", {})

        if event_type == "customer.created":
            await _handle_crm_customer_created(customer_data, db)
        elif event_type == "customer.updated":
            await _handle_crm_customer_updated(customer_data, db)
        elif event_type == "customer.deleted":
            await _handle_crm_customer_deleted(customer_data, db)
        else:
            logger.warning(f"Unknown CRM customer webhook event type: {event_type}")

    except Exception as e:
        logger.error(f"Error processing CRM customer webhook: {e}", exc_info=True)


async def _process_crm_ticket_webhook(webhook_data: Dict[str, Any], db: AsyncSession):
    """Process CRM support ticket webhook data"""
    try:
        event_type = webhook_data.get("event_type")
        ticket_data = webhook_data.get("data", {})

        if event_type == "ticket.created":
            await _handle_crm_ticket_created(ticket_data, db)
        elif event_type == "ticket.updated":
            await _handle_crm_ticket_updated(ticket_data, db)
        elif event_type == "ticket.resolved":
            await _handle_crm_ticket_resolved(ticket_data, db)
        else:
            logger.warning(f"Unknown CRM ticket webhook event type: {event_type}")

    except Exception as e:
        logger.error(f"Error processing CRM ticket webhook: {e}", exc_info=True)


async def _process_crm_interaction_webhook(
    webhook_data: Dict[str, Any], db: AsyncSession
):
    """Process CRM interaction webhook data"""
    try:
        event_type = webhook_data.get("event_type")
        interaction_data = webhook_data.get("data", {})

        if event_type == "interaction.created":
            await _handle_crm_interaction_created(interaction_data, db)
        else:
            logger.warning(f"Unknown CRM interaction webhook event type: {event_type}")

    except Exception as e:
        logger.error(f"Error processing CRM interaction webhook: {e}", exc_info=True)


async def _handle_crm_customer_created(customer_data: Dict[str, Any], db: AsyncSession):
    """Handle new customer from CRM"""
    try:
        # TODO: Implement customer creation logic
        # This would sync customer data from CRM to our database
        logger.info(f"CRM customer created: {customer_data.get('customer_id')}")

    except Exception as e:
        logger.error(f"Error handling CRM customer creation: {e}", exc_info=True)


async def _handle_crm_customer_updated(customer_data: Dict[str, Any], db: AsyncSession):
    """Handle customer update from CRM"""
    try:
        customer_id = customer_data.get("customer_id")

        # Update customer risk assessment based on new data
        risk_service = CustomerRiskService(db)
        await risk_service.update_customer_from_crm_data(customer_id, customer_data)

        logger.info(f"CRM customer updated: {customer_id}")

    except Exception as e:
        logger.error(f"Error handling CRM customer update: {e}", exc_info=True)


async def _handle_crm_customer_deleted(customer_data: Dict[str, Any], db: AsyncSession):
    """Handle customer deletion from CRM"""
    try:
        # TODO: Implement customer deletion logic
        # This would handle customer data cleanup
        logger.info(f"CRM customer deleted: {customer_data.get('customer_id')}")

    except Exception as e:
        logger.error(f"Error handling CRM customer deletion: {e}", exc_info=True)


async def _handle_crm_ticket_created(ticket_data: Dict[str, Any], db: AsyncSession):
    """Handle new support ticket from CRM"""
    try:
        customer_id = ticket_data.get("customer_id")
        ticket_priority = ticket_data.get("priority", "medium")

        # Update customer risk assessment based on new ticket
        risk_service = CustomerRiskService(db)
        await risk_service.update_risk_from_support_ticket(customer_id, ticket_data)

        # If high priority ticket, trigger immediate risk assessment
        if ticket_priority == "high":
            await risk_service.trigger_immediate_recovery_assessment(customer_id)

        logger.info(f"CRM support ticket created: {ticket_data.get('ticket_id')}")

    except Exception as e:
        logger.error(f"Error handling CRM ticket creation: {e}", exc_info=True)


async def _handle_crm_ticket_updated(ticket_data: Dict[str, Any], db: AsyncSession):
    """Handle support ticket update from CRM"""
    try:
        # TODO: Implement ticket update logic
        logger.info(f"CRM support ticket updated: {ticket_data.get('ticket_id')}")

    except Exception as e:
        logger.error(f"Error handling CRM ticket update: {e}", exc_info=True)


async def _handle_crm_ticket_resolved(ticket_data: Dict[str, Any], db: AsyncSession):
    """Handle support ticket resolution from CRM"""
    try:
        customer_id = ticket_data.get("customer_id")

        # Update customer risk assessment - resolved tickets reduce risk
        risk_service = CustomerRiskService(db)
        await risk_service.update_risk_from_ticket_resolution(customer_id, ticket_data)

        logger.info(f"CRM support ticket resolved: {ticket_data.get('ticket_id')}")

    except Exception as e:
        logger.error(f"Error handling CRM ticket resolution: {e}", exc_info=True)


async def _handle_crm_interaction_created(
    interaction_data: Dict[str, Any], db: AsyncSession
):
    """Handle new customer interaction from CRM"""
    try:
        customer_id = interaction_data.get("customer_id")
        interaction_type = interaction_data.get("interaction_type")

        # Update customer context with new interaction
        risk_service = CustomerRiskService(db)
        await risk_service.update_customer_context_from_interaction(
            customer_id, interaction_data
        )

        logger.info(
            f"CRM interaction created: {interaction_type} for customer {customer_id}"
        )

    except Exception as e:
        logger.error(f"Error handling CRM interaction: {e}", exc_info=True)


def _verify_crm_signature(payload: bytes, signature: str) -> bool:
    """Verify CRM webhook signature"""
    try:
        if not settings.CRM_WEBHOOK_SECRET:
            return True  # Skip verification if no secret configured

        # Use HMAC-SHA256 for CRM webhook verification
        expected_signature = hmac.new(
            settings.CRM_WEBHOOK_SECRET.encode(), payload, hashlib.sha256
        ).hexdigest()

        # Compare signatures
        return hmac.compare_digest(signature, f"sha256={expected_signature}")

    except Exception as e:
        logger.error(f"Error verifying CRM webhook signature: {e}")
        return False
