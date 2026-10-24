"""Create the active ReviewAI single-user schema.

Revision ID: 0001_initial_single_user_schema
Revises:
Create Date: 2026-10-22

The nullable ``organization_id`` columns are retained because they are still
present on the active ORM models. They are compatibility fields only: this
revision deliberately creates no organizations, users, subscriptions, or
foreign keys to removed SaaS tables.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0001_initial_single_user_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _enum(name: str, *values: str) -> None:
    quoted_values = ", ".join("'%s'" % value for value in values)
    op.execute(f"CREATE TYPE {name} AS ENUM ({quoted_values})")


def _pg_enum(name: str) -> postgresql.ENUM:
    return postgresql.ENUM(name=name, create_type=False)


def upgrade() -> None:
    """Create all tables represented by the active SQLAlchemy metadata."""
    # SQLAlchemy Enum(PythonEnum) stores enum member names by default. Keep
    # these values aligned with the current models, rather than the obsolete
    # lowercase enum definitions in database/init.sql.
    _enum(
        "inputtype",
        "REVIEW",
        "SUPPORT_TICKET",
        "CUSTOMER_PROFILE",
        "RECOVERY_ACTION",
    )
    _enum(
        "decisiontype",
        "RESPOND_PUBLIC",
        "RECOVER_PRIVATE",
        "ESCALATE",
        "NO_ACTION",
        "SCHEDULE_FOLLOWUP",
        "REQUEST_APPROVAL",
    )
    _enum("decisionstatus", "PENDING", "APPROVED", "REJECTED", "EXECUTED", "FAILED")
    _enum(
        "reviewplatform",
        "GOOGLE",
        "YELP",
        "FACEBOOK",
        "TRUSTPILOT",
        "TRIPADVISOR",
        "AMAZON",
        "OTHER",
    )
    _enum("urgencylevel", "LOW", "MEDIUM", "HIGH")
    _enum("reviewstatus", "PENDING", "RESPONDED", "ESCALATED", "IGNORED")
    _enum(
        "issuecategory",
        "SUPPORT",
        "PRICING",
        "DELIVERY",
        "QUALITY",
        "BILLING",
        "TECHNICAL",
        "OTHER",
    )
    _enum(
        "actiontype",
        "EMAIL",
        "SMS",
        "PHONE_CALL",
        "DISCOUNT_OFFER",
        "REFUND",
        "ESCALATE_TO_MANAGER",
        "FOLLOW_UP",
        "SURVEY",
        "CALLBACK_REQUEST",
        "PERSONALIZED_MESSAGE",
    )
    _enum(
        "actionstatus",
        "PENDING",
        "SCHEDULED",
        "SENT",
        "DELIVERED",
        "OPENED",
        "CLICKED",
        "RESPONDED",
        "FAILED",
        "CANCELLED",
        "COMPLETED",
    )
    _enum("actionpriority", "LOW", "MEDIUM", "HIGH", "URGENT")
    _enum("ticketstatus", "OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED", "REOPENED")
    _enum("ticketpriority", "LOW", "MEDIUM", "HIGH", "CRITICAL")
    _enum(
        "ticketcategory",
        "TECHNICAL",
        "BILLING",
        "ACCOUNT",
        "PRODUCT",
        "SHIPPING",
        "REFUND",
        "COMPLAINT",
        "FEATURE_REQUEST",
        "OTHER",
    )

    uuid = postgresql.UUID(as_uuid=True)
    timestamp = sa.DateTime(timezone=True)

    op.create_table(
        "customers",
        sa.Column("id", uuid, nullable=False),
        sa.Column("organization_id", uuid, nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("churn_risk_score", sa.DECIMAL(precision=3, scale=2), nullable=True),
        sa.Column("bad_review_likelihood", sa.DECIMAL(precision=3, scale=2), nullable=True),
        sa.Column("last_interaction", timestamp, nullable=True),
        sa.Column("interaction_count", sa.Integer(), nullable=False),
        sa.Column("context_summary", sa.Text(), nullable=True),
        sa.Column("tags", sa.Text(), nullable=True),
        sa.Column("lifetime_value", sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column("total_orders", sa.Integer(), nullable=False),
        sa.Column("avg_order_value", sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column("avg_rating_given", sa.DECIMAL(precision=3, scale=2), nullable=True),
        sa.Column("total_reviews", sa.Integer(), nullable=False),
        sa.Column("positive_reviews", sa.Integer(), nullable=False),
        sa.Column("negative_reviews", sa.Integer(), nullable=False),
        sa.Column("preferred_contact_method", sa.String(length=50), nullable=True),
        sa.Column("timezone", sa.String(length=50), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", timestamp, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", timestamp, server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "business_knowledge",
        sa.Column("id", uuid, nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=False),
        sa.Column("created_at", timestamp, server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", timestamp, server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "agent_decisions",
        sa.Column("id", uuid, nullable=False),
        sa.Column("organization_id", uuid, nullable=True),
        sa.Column("input_type", _pg_enum("inputtype"), nullable=False),
        sa.Column("input_id", uuid, nullable=False),
        sa.Column("decision_type", _pg_enum("decisiontype"), nullable=False),
        sa.Column("status", _pg_enum("decisionstatus"), nullable=False),
        sa.Column("confidence_score", sa.DECIMAL(precision=3, scale=2), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("input_data", sa.JSON(), nullable=True),
        sa.Column("context_factors", sa.JSON(), nullable=True),
        sa.Column("generated_content", sa.Text(), nullable=True),
        sa.Column("content_type", sa.String(length=50), nullable=True),
        sa.Column("executed_at", timestamp, nullable=True),
        sa.Column("executed_by", sa.String(length=255), nullable=True),
        sa.Column("execution_result", sa.JSON(), nullable=True),
        sa.Column("reviewed_by", sa.String(length=255), nullable=True),
        sa.Column("reviewed_at", timestamp, nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("outcome_success", sa.Boolean(), nullable=True),
        sa.Column("outcome_rating", sa.DECIMAL(precision=3, scale=2), nullable=True),
        sa.Column("customer_feedback", sa.Text(), nullable=True),
        sa.Column("model_version", sa.String(length=50), nullable=True),
        sa.Column("model_provider", sa.String(length=50), nullable=True),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", timestamp, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", timestamp, server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "reviews",
        sa.Column("id", uuid, nullable=False),
        sa.Column("organization_id", uuid, nullable=True),
        sa.Column("platform", _pg_enum("reviewplatform"), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("review_url", sa.Text(), nullable=True),
        sa.Column("customer_name", sa.String(length=255), nullable=True),
        sa.Column("customer_email", sa.String(length=255), nullable=True),
        sa.Column("customer_id", uuid, nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("sentiment_score", sa.DECIMAL(precision=3, scale=2), nullable=True),
        sa.Column("urgency_level", _pg_enum("urgencylevel"), nullable=True),
        sa.Column("issue_categories", postgresql.ARRAY(_pg_enum("issuecategory")), nullable=True),
        sa.Column("status", _pg_enum("reviewstatus"), nullable=False),
        sa.Column("requires_private_recovery", sa.Boolean(), nullable=False),
        sa.Column("public_response", sa.Text(), nullable=True),
        sa.Column("public_response_date", timestamp, nullable=True),
        sa.Column("internal_notes", sa.Text(), nullable=True),
        sa.Column("review_date", timestamp, nullable=True),
        sa.Column("processed_at", timestamp, nullable=True),
        sa.Column("created_at", timestamp, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", timestamp, server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "support_tickets",
        sa.Column("id", uuid, nullable=False),
        sa.Column("organization_id", uuid, nullable=True),
        sa.Column("customer_id", uuid, nullable=True),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("ticket_number", sa.String(length=50), nullable=True),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", _pg_enum("ticketstatus"), nullable=False),
        sa.Column("priority", _pg_enum("ticketpriority"), nullable=False),
        sa.Column("category", _pg_enum("ticketcategory"), nullable=True),
        sa.Column("sentiment_score", sa.DECIMAL(precision=3, scale=2), nullable=True),
        sa.Column("urgency_score", sa.DECIMAL(precision=3, scale=2), nullable=True),
        sa.Column("escalation_risk", sa.DECIMAL(precision=3, scale=2), nullable=True),
        sa.Column("assigned_to", sa.String(length=255), nullable=True),
        sa.Column("assigned_at", timestamp, nullable=True),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("resolved_at", timestamp, nullable=True),
        sa.Column("resolved_by", sa.String(length=255), nullable=True),
        sa.Column("satisfaction_rating", sa.Integer(), nullable=True),
        sa.Column("satisfaction_feedback", sa.Text(), nullable=True),
        sa.Column("first_response_at", timestamp, nullable=True),
        sa.Column("last_response_at", timestamp, nullable=True),
        sa.Column("response_count", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=True),
        sa.Column("tags", sa.Text(), nullable=True),
        sa.Column("internal_notes", sa.Text(), nullable=True),
        sa.Column("created_at", timestamp, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", timestamp, server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "recovery_actions",
        sa.Column("id", uuid, nullable=False),
        sa.Column("organization_id", uuid, nullable=True),
        sa.Column("customer_id", uuid, nullable=False),
        sa.Column("review_id", uuid, nullable=True),
        sa.Column("ticket_id", uuid, nullable=True),
        sa.Column("action_type", _pg_enum("actiontype"), nullable=False),
        sa.Column("status", _pg_enum("actionstatus"), nullable=False),
        sa.Column("priority", _pg_enum("actionpriority"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("action_metadata", sa.JSON(), nullable=True),
        sa.Column("scheduled_at", timestamp, nullable=True),
        sa.Column("executed_at", timestamp, nullable=True),
        sa.Column("expires_at", timestamp, nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("last_attempt_at", timestamp, nullable=True),
        sa.Column("success", sa.Boolean(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("response_data", sa.JSON(), nullable=True),
        sa.Column("customer_responded", sa.Boolean(), nullable=False),
        sa.Column("customer_response_date", timestamp, nullable=True),
        sa.Column("outcome_rating", sa.DECIMAL(precision=3, scale=2), nullable=True),
        sa.Column("trigger_reason", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.DECIMAL(precision=3, scale=2), nullable=True),
        sa.Column("requires_approval", sa.Boolean(), nullable=False),
        sa.Column("approved_by", sa.String(length=255), nullable=True),
        sa.Column("approved_at", timestamp, nullable=True),
        sa.Column("created_at", timestamp, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", timestamp, server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ticket_id"], ["support_tickets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    indexed_columns = {
        "customers": [
            "id", "organization_id", "email", "phone", "name", "external_id",
            "churn_risk_score", "bad_review_likelihood", "last_interaction", "status",
        ],
        "business_knowledge": ["id", "category"],
        "agent_decisions": [
            "id", "organization_id", "input_type", "input_id", "decision_type",
            "status", "confidence_score",
        ],
        "reviews": [
            "id", "organization_id", "platform", "external_id", "customer_id", "rating",
            "sentiment_score", "urgency_level", "status", "requires_private_recovery",
        ],
        "support_tickets": [
            "id", "organization_id", "customer_id", "external_id", "ticket_number",
            "subject", "status", "priority", "category", "sentiment_score",
        ],
        "recovery_actions": [
            "id", "organization_id", "customer_id", "review_id", "ticket_id", "action_type",
            "status", "priority", "scheduled_at",
        ],
    }
    for table_name, columns in indexed_columns.items():
        for column_name in columns:
            is_unique = table_name == "support_tickets" and column_name == "ticket_number"
            op.create_index(
                f"ix_{table_name}_{column_name}",
                table_name,
                [column_name],
                unique=is_unique,
            )


def downgrade() -> None:
    """Remove the schema in dependency-safe reverse order."""
    for table_name in ("recovery_actions", "support_tickets", "reviews", "agent_decisions", "business_knowledge", "customers"):
        op.drop_table(table_name)

    for enum_name in (
        "ticketcategory", "ticketpriority", "ticketstatus", "actionpriority", "actionstatus",
        "actiontype", "issuecategory", "reviewstatus", "urgencylevel", "reviewplatform",
        "decisionstatus", "decisiontype", "inputtype",
    ):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
