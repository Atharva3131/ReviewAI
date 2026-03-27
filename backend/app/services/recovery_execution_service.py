"""
Recovery Action Execution Service

This service handles the execution of recovery actions, including sending emails,
SMS messages, scheduling callbacks, and tracking the success of recovery efforts.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.customer import Customer
from app.models.organization import Organization
from app.models.recovery_action import ActionStatus, ActionType, RecoveryAction


class RecoveryExecutionService:
    """Service for executing recovery actions and tracking their success"""

    def __init__(self):
        # Mock external service configurations
        self.email_service_config = {
            "provider": "mock",
            "from_email": "support@reviveai.com",
            "from_name": "Revive AI Support",
        }

        self.sms_service_config = {"provider": "mock", "from_number": "+1-555-REVIVE"}

    async def execute_action(
        self, action_id: str, db: AsyncSession, force_execute: bool = False
    ) -> Dict[str, Any]:
        """Execute a specific recovery action"""
        # Get action with related data
        action = await self._get_action_with_context(action_id, db)
        if not action:
            raise ValueError(f"Recovery action {action_id} not found")

        # Validate action can be executed
        if not force_execute:
            validation_result = self._validate_action_execution(action)
            if not validation_result["can_execute"]:
                return {
                    "success": False,
                    "error": validation_result["reason"],
                    "action_id": action_id,
                }

        # Mark action as being executed
        action.execute()
        await db.commit()

        try:
            # Execute based on action type
            if action.action_type == ActionType.EMAIL:
                result = await self._execute_email_action(action, db)
            elif action.action_type == ActionType.SMS:
                result = await self._execute_sms_action(action, db)
            elif action.action_type == ActionType.PHONE_CALL:
                result = await self._execute_phone_call_action(action, db)
            elif action.action_type == ActionType.DISCOUNT_OFFER:
                result = await self._execute_discount_offer_action(action, db)
            elif action.action_type == ActionType.REFUND:
                result = await self._execute_refund_action(action, db)
            else:
                result = await self._execute_generic_action(action, db)

            # Update action status based on result
            if result["success"]:
                action.mark_success(result.get("response_data"))
            else:
                action.mark_failure(result.get("error", "Unknown error"))

            await db.commit()

            # Add action details to result
            result["action_id"] = action_id
            result["action_type"] = action.action_type.value
            result["customer_id"] = str(action.customer_id)

            return result

        except Exception as e:
            # Mark action as failed
            action.mark_failure(str(e))
            await db.commit()

            return {
                "success": False,
                "error": str(e),
                "action_id": action_id,
                "action_type": action.action_type.value,
            }

    async def _get_action_with_context(
        self, action_id: str, db: AsyncSession
    ) -> Optional[RecoveryAction]:
        """Get recovery action with all related context"""
        stmt = (
            select(RecoveryAction)
            .options(
                selectinload(RecoveryAction.customer),
                selectinload(RecoveryAction.organization),
                selectinload(RecoveryAction.review),
                selectinload(RecoveryAction.ticket),
            )
            .where(RecoveryAction.id == action_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    def _validate_action_execution(self, action: RecoveryAction) -> Dict[str, Any]:
        """Validate that an action can be executed"""
        now = datetime.now(timezone.utc)

        # Check if action is expired
        if action.is_expired:
            return {"can_execute": False, "reason": "Action has expired"}

        # Check if action is already completed
        if action.is_completed:
            return {"can_execute": False, "reason": "Action is already completed"}

        # Check if action requires approval
        if action.requires_approval and not action.approved_at:
            return {
                "can_execute": False,
                "reason": "Action requires approval before execution",
            }

        return {"can_execute": True}

    async def _execute_email_action(
        self, action: RecoveryAction, db: AsyncSession
    ) -> Dict[str, Any]:
        """Execute email recovery action"""
        customer = action.customer

        if not customer.email:
            return {"success": False, "error": "Customer has no email address"}

        # Mock email sending
        import random

        success = random.random() < 0.9  # 90% success rate

        if success:
            return {
                "success": True,
                "response_data": {
                    "message_id": f"mock_email_{action.id.hex[:8]}",
                    "provider": "mock_email",
                    "delivered_at": datetime.now(timezone.utc).isoformat(),
                },
            }
        else:
            return {"success": False, "error": "Mock email delivery failed"}

    async def _execute_sms_action(
        self, action: RecoveryAction, db: AsyncSession
    ) -> Dict[str, Any]:
        """Execute SMS recovery action"""
        customer = action.customer

        if not customer.phone:
            return {"success": False, "error": "Customer has no phone number"}

        # Mock SMS sending
        import random

        success = random.random() < 0.85  # 85% success rate

        if success:
            return {
                "success": True,
                "response_data": {
                    "message_id": f"mock_sms_{action.id.hex[:8]}",
                    "provider": "mock_sms",
                    "delivered_at": datetime.now(timezone.utc).isoformat(),
                },
            }
        else:
            return {"success": False, "error": "Mock SMS delivery failed"}

    async def _execute_phone_call_action(
        self, action: RecoveryAction, db: AsyncSession
    ) -> Dict[str, Any]:
        """Execute phone call recovery action"""
        customer = action.customer

        if not customer.phone:
            return {"success": False, "error": "Customer has no phone number"}

        # Create call task for human agents
        return {
            "success": True,
            "response_data": {
                "call_task_id": f"call_{action.id.hex[:8]}",
                "scheduled_for": "next_available_agent",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    async def _execute_discount_offer_action(
        self, action: RecoveryAction, db: AsyncSession
    ) -> Dict[str, Any]:
        """Execute discount offer recovery action"""
        customer = action.customer
        discount_percentage = action.get_discount_percentage() or 10

        # Generate discount code
        discount_code = f"RECOVERY{action.id.hex[:8].upper()}"

        return {
            "success": True,
            "response_data": {
                "discount_code": discount_code,
                "discount_percentage": discount_percentage,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "email_sent": customer.email is not None,
            },
        }

    async def _execute_refund_action(
        self, action: RecoveryAction, db: AsyncSession
    ) -> Dict[str, Any]:
        """Execute refund recovery action"""
        max_amount = action.get_metadata_value("max_amount", 100)
        refund_id = f"refund_{action.id.hex[:8]}"

        return {
            "success": True,
            "response_data": {
                "refund_id": refund_id,
                "amount": max_amount,
                "status": "pending_approval",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    async def _execute_generic_action(
        self, action: RecoveryAction, db: AsyncSession
    ) -> Dict[str, Any]:
        """Execute generic recovery action"""
        return {
            "success": True,
            "response_data": {
                "action_id": str(action.id),
                "executed_at": datetime.now(timezone.utc).isoformat(),
                "type": action.action_type.value,
            },
        }

    async def execute_pending_actions(
        self, organization_id: str, db: AsyncSession, limit: int = 10
    ) -> Dict[str, Any]:
        """Execute pending recovery actions for an organization"""
        # Get pending actions that are ready to execute
        now = datetime.now(timezone.utc)

        stmt = (
            select(RecoveryAction)
            .where(
                and_(
                    RecoveryAction.organization_id == organization_id,
                    RecoveryAction.status.in_(["pending", "scheduled"]),
                    or_(
                        RecoveryAction.scheduled_at.is_(None),
                        RecoveryAction.scheduled_at <= now,
                    ),
                    or_(
                        RecoveryAction.expires_at.is_(None),
                        RecoveryAction.expires_at > now,
                    ),
                    or_(
                        RecoveryAction.requires_approval == False,
                        RecoveryAction.approved_at.isnot(None),
                    ),
                )
            )
            .order_by(RecoveryAction.priority.desc(), RecoveryAction.scheduled_at.asc())
            .limit(limit)
        )

        result = await db.execute(stmt)
        pending_actions = result.scalars().all()

        executed_count = 0
        failed_count = 0
        results = []

        for action in pending_actions:
            try:
                execution_result = await self.execute_action(
                    str(action.id), db, force_execute=True
                )
                results.append(execution_result)

                if execution_result["success"]:
                    executed_count += 1
                else:
                    failed_count += 1

            except Exception as e:
                failed_count += 1
                results.append(
                    {"success": False, "error": str(e), "action_id": str(action.id)}
                )

        return {
            "total_processed": len(pending_actions),
            "executed_successfully": executed_count,
            "failed": failed_count,
            "results": results,
        }

    async def get_execution_metrics(
        self, organization_id: str, db: AsyncSession, days: int = 30
    ) -> Dict[str, Any]:
        """Get execution metrics for recovery actions"""
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Total actions executed
        total_executed = await db.execute(
            select(func.count(RecoveryAction.id)).where(
                and_(
                    RecoveryAction.organization_id == organization_id,
                    RecoveryAction.executed_at >= start_date,
                )
            )
        )
        total_count = total_executed.scalar() or 0

        # Successful actions
        successful_actions = await db.execute(
            select(func.count(RecoveryAction.id)).where(
                and_(
                    RecoveryAction.organization_id == organization_id,
                    RecoveryAction.executed_at >= start_date,
                    RecoveryAction.success == True,
                )
            )
        )
        success_count = successful_actions.scalar() or 0

        # Customer responses
        customer_responses = await db.execute(
            select(func.count(RecoveryAction.id)).where(
                and_(
                    RecoveryAction.organization_id == organization_id,
                    RecoveryAction.executed_at >= start_date,
                    RecoveryAction.customer_responded == True,
                )
            )
        )
        response_count = customer_responses.scalar() or 0

        # Calculate rates
        success_rate = (success_count / total_count) if total_count > 0 else 0
        response_rate = (response_count / total_count) if total_count > 0 else 0

        return {
            "period_days": days,
            "total_actions_executed": total_count,
            "successful_executions": success_count,
            "customer_responses": response_count,
            "execution_success_rate": round(success_rate, 3),
            "customer_response_rate": round(response_rate, 3),
        }
