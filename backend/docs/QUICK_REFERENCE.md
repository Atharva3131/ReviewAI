# Revive AI API - Quick Reference

## Base URLs

```
Development:  http://localhost:8000
Staging:      https://staging-api.revive-ai.com
Production:   https://api.revive-ai.com
```

## Authentication

```bash
# Register
POST /api/v1/auth/register
{
  "email": "user@example.com",
  "password": "password123",
  "organization_name": "Company"
}

# Login
POST /api/v1/auth/login
{
  "email": "user@example.com",
  "password": "password123"
}

# Use token in requests
Authorization: Bearer <token>
```

## Core Endpoints

### Reviews

```bash
# Ingest review
POST /api/v1/reviews/ingest
{
  "platform": "google",
  "rating": 2,
  "content": "Service was terrible",
  "created_at": "2024-01-15T10:30:00Z"
}

# List reviews
GET /api/v1/reviews?page=1&page_size=20&urgency_level=high

# Get review details
GET /api/v1/reviews/{review_id}

# Generate response
POST /api/v1/reviews/respond
{
  "review_id": "rev_123",
  "tone": "empathetic"
}
```

### Customers

```bash
# Assess risk
POST /api/v1/customers/recover
{
  "customer_id": "cust_123",
  "trigger_type": "support_ticket",
  "context": {
    "issue_summary": "Billing problem"
  }
}

# List customers
GET /api/v1/customers?risk_level=high

# Get customer details
GET /api/v1/customers/{customer_id}
```

### Dashboard

```bash
# Get metrics
GET /api/v1/dashboard/metrics?period=30d&include_trends=true
```

### Agents

```bash
# Make decision
POST /api/v1/agents/decide-action
{
  "input_type": "review",
  "input_id": "rev_123"
}

# List decisions
GET /api/v1/agents/decisions?page=1
```

## Rate Limits

| Tier | Requests/Hour |
|------|---------------|
| Anonymous | 100 |
| Authenticated | 1,000 |
| Premium | 5,000 |
| Admin | 10,000 |

## Response Headers

```
X-Request-ID: unique-request-id
X-Process-Time: 0.123
X-API-Version: v1
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 995
X-RateLimit-Reset: 1640998800
```

## Error Codes

| Code | Meaning |
|------|---------|
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 422 | Validation Error |
| 429 | Rate Limit Exceeded |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

## Common Query Parameters

```
page=1              # Page number (default: 1)
page_size=20        # Items per page (default: 20)
sort_by=created_at  # Sort field
order=desc          # Sort order (asc/desc)
start_date=...      # Filter start date (ISO 8601)
end_date=...        # Filter end date (ISO 8601)
```

## Webhook Events

```
review.ingested
review.analyzed
review.responded
customer.at_risk
customer.recovered
recovery.completed
agent.decision_made
```

## Health Check

```bash
GET /health  # No auth required

Response:
{
  "status": "healthy",
  "components": {
    "database": {"status": "healthy"},
    "redis": {"status": "healthy"},
    "celery": {"status": "healthy"}
  }
}
```

## Support

- Docs: https://docs.revive-ai.com
- Email: support@revive-ai.com
- Status: https://status.revive-ai.com
