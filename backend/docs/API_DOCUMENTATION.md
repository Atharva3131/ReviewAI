# Revive AI API Documentation

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Authentication](#authentication)
4. [API Endpoints](#api-endpoints)
5. [Rate Limiting](#rate-limiting)
6. [Error Handling](#error-handling)
7. [Versioning](#versioning)
8. [Monitoring](#monitoring)
9. [Best Practices](#best-practices)
10. [Code Examples](#code-examples)

---

## Overview

Revive AI is a comprehensive SaaS platform that helps businesses monitor public reviews, analyze customer conversations, predict churn risks, and take automated recovery actions to improve ratings, retention, and revenue.

### Key Features

- **Review Intelligence Engine**: Automated sentiment analysis, urgency classification, and issue categorization
- **Customer Recovery Agent**: Predictive churn risk assessment and automated recovery action generation
- **Agent Orchestration**: Intelligent decision-making for routing customer issues
- **LLM Integration**: Multi-provider AI integration for response generation
- **Background Processing**: Scalable task queue system for asynchronous operations

### Base URL

- **Development**: `http://localhost:8000`
- **Staging**: `https://staging-api.revive-ai.com`
- **Production**: `https://api.revive-ai.com`

### API Version

Current stable version: **v1**

All endpoints are prefixed with `/api/v1/`

---

## Getting Started

### Prerequisites

- Valid email address for registration
- API client (curl, Postman, or HTTP library)
- Understanding of REST API principles

### Quick Start

1. **Register an account**
2. **Login to get access token**
3. **Make authenticated requests**


---

## Authentication

All API endpoints (except public ones) require authentication using JWT Bearer tokens.

### Authentication Flow

```
1. Register → 2. Login → 3. Get Token → 4. Use Token in Requests
```

### Register a New Account

**Endpoint**: `POST /api/v1/auth/register`

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "organization_name": "My Company"
}
```

**Response** (201 Created):
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "organization_id": "org_123",
  "role": "user",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Login

**Endpoint**: `POST /api/v1/auth/login`

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "organization_id": "org_123"
  }
}
```

### Using the Token

Include the token in the `Authorization` header for all authenticated requests:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Token Expiration

- Access tokens expire after 1 hour (3600 seconds)
- Refresh tokens are valid for 30 days
- Use the refresh endpoint to get a new access token

**Endpoint**: `POST /api/v1/auth/refresh`

**Request Body**:
```json
{
  "refresh_token": "your_refresh_token"
}
```


---

## API Endpoints

### Health & Status

#### Health Check

**Endpoint**: `GET /health`

**Authentication**: Not required

**Description**: Comprehensive health check for all system components

**Response** (200 OK):
```json
{
  "status": "healthy",
  "service": "revive-ai-api",
  "version": "1.0.0",
  "timestamp": 1640995200,
  "environment": "production",
  "components": {
    "database": {
      "status": "healthy",
      "response_time_ms": 5
    },
    "redis": {
      "status": "healthy",
      "response_time_ms": 2
    },
    "celery": {
      "status": "healthy",
      "active_workers": 3
    }
  }
}
```

### Review Intelligence

#### Ingest Review

**Endpoint**: `POST /api/v1/reviews/ingest`

**Authentication**: Required

**Description**: Ingest a new review from external platforms for analysis

**Request Body**:
```json
{
  "platform": "google",
  "external_id": "review_123456",
  "customer_name": "John Doe",
  "rating": 2,
  "content": "Service was terrible, waited 2 hours for my order. Very disappointed.",
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Response** (201 Created):
```json
{
  "review_id": "rev_123e4567",
  "sentiment_score": 0.15,
  "urgency_level": "high",
  "issue_categories": ["support", "quality"],
  "recommended_action": "recover_private",
  "requires_private_recovery": true,
  "status": "pending"
}
```

#### Analyze Review

**Endpoint**: `POST /api/v1/reviews/analyze`

**Authentication**: Required

**Description**: Analyze an existing review for sentiment, urgency, and categorization

**Request Body**:
```json
{
  "review_id": "rev_123e4567"
}
```

**Response** (200 OK):
```json
{
  "review_id": "rev_123e4567",
  "sentiment_score": 0.15,
  "urgency_level": "high",
  "issue_categories": ["support", "quality"],
  "analysis_timestamp": "2024-01-15T10:31:00Z"
}
```


#### Generate Review Response

**Endpoint**: `POST /api/v1/reviews/respond`

**Authentication**: Required

**Description**: Generate an AI-powered response to a review

**Request Body**:
```json
{
  "review_id": "rev_123e4567",
  "tone": "empathetic",
  "include_resolution": true
}
```

**Response** (200 OK):
```json
{
  "review_id": "rev_123e4567",
  "generated_response": "Thank you for your feedback. We sincerely apologize for the long wait time you experienced. This is not the level of service we strive to provide. We would like to make this right. Please contact us at support@company.com so we can address your concerns directly.",
  "confidence_score": 0.85,
  "requires_approval": false,
  "character_count": 245
}
```

#### List Reviews

**Endpoint**: `GET /api/v1/reviews`

**Authentication**: Required

**Description**: List all reviews with filtering and pagination

**Query Parameters**:
- `page` (integer, default: 1): Page number
- `page_size` (integer, default: 20): Items per page
- `rating` (integer, 1-5): Filter by rating
- `urgency_level` (string): Filter by urgency (low, medium, high)
- `status` (string): Filter by status (pending, responded, escalated)
- `platform` (string): Filter by platform (google, yelp, etc.)
- `start_date` (ISO 8601): Filter reviews after this date
- `end_date` (ISO 8601): Filter reviews before this date

**Response** (200 OK):
```json
{
  "items": [
    {
      "id": "rev_123e4567",
      "platform": "google",
      "customer_name": "John Doe",
      "rating": 2,
      "content": "Service was terrible...",
      "sentiment_score": 0.15,
      "urgency_level": "high",
      "status": "pending",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 127,
  "page": 1,
  "page_size": 20,
  "total_pages": 7
}
```

#### Get Review Details

**Endpoint**: `GET /api/v1/reviews/{review_id}`

**Authentication**: Required

**Description**: Get detailed information about a specific review

**Response** (200 OK):
```json
{
  "id": "rev_123e4567",
  "organization_id": "org_123",
  "platform": "google",
  "external_id": "review_123456",
  "customer_name": "John Doe",
  "rating": 2,
  "content": "Service was terrible, waited 2 hours for my order.",
  "sentiment_score": 0.15,
  "urgency_level": "high",
  "issue_categories": ["support", "quality"],
  "status": "pending",
  "requires_private_recovery": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:31:00Z"
}
```


### Customer Recovery

#### Assess Customer Risk

**Endpoint**: `POST /api/v1/customers/recover`

**Authentication**: Required

**Description**: Assess customer churn risk and generate recovery actions

**Request Body**:
```json
{
  "customer_id": "cust_123",
  "trigger_type": "support_ticket",
  "context": {
    "ticket_id": "ticket_456",
    "issue_summary": "Billing problem, customer frustrated with multiple failed charges"
  }
}
```

**Response** (200 OK):
```json
{
  "customer_id": "cust_123",
  "recovery_plan": {
    "churn_risk": 0.75,
    "bad_review_likelihood": 0.68,
    "risk_factors": [
      "Multiple support tickets in 7 days",
      "Negative sentiment in recent interactions",
      "High-priority escalation"
    ],
    "actions": [
      {
        "type": "personalized_email",
        "priority": "high",
        "content": "Dear John, we sincerely apologize...",
        "scheduled_at": "2024-01-15T11:00:00Z"
      },
      {
        "type": "discount_offer",
        "priority": "medium",
        "value": "15%",
        "expires_at": "2024-01-22T23:59:59Z"
      }
    ]
  }
}
```

#### List Customers

**Endpoint**: `GET /api/v1/customers`

**Authentication**: Required

**Description**: List all customers with filtering and pagination

**Query Parameters**:
- `page` (integer, default: 1): Page number
- `page_size` (integer, default: 20): Items per page
- `risk_level` (string): Filter by risk level (low, medium, high)
- `sort_by` (string): Sort field (churn_risk, last_interaction)
- `order` (string): Sort order (asc, desc)

**Response** (200 OK):
```json
{
  "items": [
    {
      "id": "cust_123",
      "email": "customer@example.com",
      "name": "John Doe",
      "churn_risk_score": 0.75,
      "bad_review_likelihood": 0.68,
      "last_interaction": "2024-01-15T09:00:00Z",
      "status": "at_risk"
    }
  ],
  "total": 523,
  "page": 1,
  "page_size": 20,
  "total_pages": 27
}
```

#### Get Customer Details

**Endpoint**: `GET /api/v1/customers/{customer_id}`

**Authentication**: Required

**Description**: Get detailed information about a specific customer

**Response** (200 OK):
```json
{
  "id": "cust_123",
  "organization_id": "org_123",
  "email": "customer@example.com",
  "phone": "+1234567890",
  "name": "John Doe",
  "churn_risk_score": 0.75,
  "bad_review_likelihood": 0.68,
  "last_interaction": "2024-01-15T09:00:00Z",
  "context_summary": "Customer has had 3 support tickets in the past week...",
  "recent_tickets": [
    {
      "id": "ticket_456",
      "subject": "Billing issue",
      "status": "open",
      "created_at": "2024-01-14T10:00:00Z"
    }
  ],
  "recovery_actions": [
    {
      "id": "action_789",
      "type": "personalized_email",
      "status": "sent",
      "executed_at": "2024-01-15T11:00:00Z"
    }
  ]
}
```


### Agent Orchestration

#### Make Agent Decision

**Endpoint**: `POST /api/v1/agents/decide-action`

**Authentication**: Required

**Description**: Use the agent orchestration engine to decide on the best action for a customer issue

**Request Body**:
```json
{
  "input_type": "review",
  "input_id": "rev_123e4567",
  "context": {
    "customer_history": "Previous positive interactions",
    "business_rules": {
      "auto_respond_threshold": 0.7,
      "escalation_threshold": 0.9
    }
  }
}
```

**Response** (200 OK):
```json
{
  "decision_id": "dec_123",
  "decision": {
    "action_type": "respond_public",
    "confidence_score": 0.85,
    "reasoning": "Moderate negative review suitable for public response",
    "generated_content": "Thank you for your feedback. We take all concerns seriously...",
    "requires_approval": false,
    "alternative_actions": [
      {
        "action_type": "recover_private",
        "confidence_score": 0.65
      }
    ]
  }
}
```

#### List Agent Decisions

**Endpoint**: `GET /api/v1/agents/decisions`

**Authentication**: Required

**Description**: List all agent decisions with filtering

**Query Parameters**:
- `page` (integer, default: 1): Page number
- `page_size` (integer, default: 20): Items per page
- `action_type` (string): Filter by action type
- `start_date` (ISO 8601): Filter decisions after this date
- `end_date` (ISO 8601): Filter decisions before this date

**Response** (200 OK):
```json
{
  "items": [
    {
      "id": "dec_123",
      "input_type": "review",
      "input_id": "rev_123e4567",
      "decision_type": "respond_public",
      "confidence_score": 0.85,
      "reasoning": "Moderate negative review suitable for public response",
      "created_at": "2024-01-15T10:32:00Z"
    }
  ],
  "total": 456,
  "page": 1,
  "page_size": 20,
  "total_pages": 23
}
```

### Dashboard & Metrics

#### Get Dashboard Metrics

**Endpoint**: `GET /api/v1/dashboard/metrics`

**Authentication**: Required

**Description**: Get comprehensive dashboard metrics and KPIs

**Query Parameters**:
- `period` (string, default: "30d"): Time period (7d, 30d, 90d, 1y)
- `include_trends` (boolean, default: true): Include trend data

**Response** (200 OK):
```json
{
  "kpis": {
    "average_rating": {
      "value": 4.2,
      "change": 0.3,
      "trend": "up"
    },
    "monthly_reviews": {
      "value": 127,
      "change": 15,
      "trend": "up"
    },
    "at_risk_customers": {
      "value": 23,
      "change": -5,
      "trend": "down"
    },
    "recovery_success_rate": {
      "value": 0.78,
      "change": 0.05,
      "trend": "up"
    }
  },
  "sentiment_trends": [
    {
      "date": "2024-01-01",
      "positive": 65,
      "neutral": 20,
      "negative": 15
    }
  ],
  "activity_feed": [
    {
      "id": "activity_1",
      "type": "review_ingested",
      "message": "New 2★ review requires immediate attention",
      "timestamp": "2024-01-15T10:30:00Z",
      "priority": "high"
    }
  ]
}
```


### User Management

#### Get Current User

**Endpoint**: `GET /api/v1/users/me`

**Authentication**: Required

**Description**: Get information about the currently authenticated user

**Response** (200 OK):
```json
{
  "id": "user_123",
  "email": "user@example.com",
  "organization_id": "org_123",
  "organization_name": "My Company",
  "role": "user",
  "created_at": "2024-01-01T00:00:00Z",
  "last_login": "2024-01-15T10:00:00Z"
}
```

#### Update User Profile

**Endpoint**: `PUT /api/v1/users/me`

**Authentication**: Required

**Description**: Update the current user's profile

**Request Body**:
```json
{
  "email": "newemail@example.com",
  "password": "newpassword123"
}
```

**Response** (200 OK):
```json
{
  "id": "user_123",
  "email": "newemail@example.com",
  "updated_at": "2024-01-15T10:35:00Z"
}
```

### Webhooks

#### Register Webhook

**Endpoint**: `POST /api/v1/webhooks`

**Authentication**: Required

**Description**: Register a webhook for receiving real-time notifications

**Request Body**:
```json
{
  "url": "https://your-app.com/webhook",
  "events": ["review.ingested", "customer.at_risk", "recovery.completed"],
  "secret": "your_webhook_secret"
}
```

**Response** (201 Created):
```json
{
  "id": "webhook_123",
  "url": "https://your-app.com/webhook",
  "events": ["review.ingested", "customer.at_risk", "recovery.completed"],
  "status": "active",
  "created_at": "2024-01-15T10:40:00Z"
}
```

#### List Webhooks

**Endpoint**: `GET /api/v1/webhooks`

**Authentication**: Required

**Description**: List all registered webhooks

**Response** (200 OK):
```json
{
  "items": [
    {
      "id": "webhook_123",
      "url": "https://your-app.com/webhook",
      "events": ["review.ingested"],
      "status": "active",
      "last_triggered": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 3
}
```

### Privacy & Compliance

#### Export User Data

**Endpoint**: `POST /api/v1/privacy/export`

**Authentication**: Required

**Description**: Request export of all user data (GDPR compliance)

**Response** (202 Accepted):
```json
{
  "export_id": "export_123",
  "status": "processing",
  "estimated_completion": "2024-01-15T11:00:00Z"
}
```

#### Delete User Data

**Endpoint**: `DELETE /api/v1/privacy/delete`

**Authentication**: Required

**Description**: Request deletion of all user data (GDPR right to be forgotten)

**Response** (202 Accepted):
```json
{
  "deletion_id": "del_123",
  "status": "scheduled",
  "scheduled_for": "2024-01-22T00:00:00Z",
  "message": "Your data will be permanently deleted in 7 days as required by law"
}
```


---

## Rate Limiting

The API implements sophisticated rate limiting to ensure fair usage and system stability.

### Rate Limit Tiers

| User Tier | Requests/Hour | Requests/Minute | Burst Limit |
|-----------|---------------|-----------------|-------------|
| Anonymous | 100 | 10 | 20 |
| Authenticated | 1,000 | 50 | 100 |
| Premium | 5,000 | 200 | 500 |
| Admin | 10,000 | 500 | 1,000 |

### Endpoint-Specific Limits

Some endpoints have additional rate limits:

- **POST /api/v1/reviews/ingest**: 100 requests/minute (authenticated)
- **POST /api/v1/customers/recover**: 50 requests/minute (authenticated)
- **POST /api/v1/agents/decide-action**: 200 requests/minute (authenticated)

### Rate Limit Headers

All responses include rate limit information in headers:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 995
X-RateLimit-Reset: 1640998800
```

### Rate Limit Exceeded Response

When rate limit is exceeded, you'll receive a 429 status code:

```json
{
  "error": {
    "type": "rate_limit_exceeded",
    "message": "Rate limit exceeded. Please try again later.",
    "status_code": 429,
    "request_id": "req_123",
    "timestamp": 1640995200.0,
    "path": "/api/v1/reviews/ingest",
    "details": {
      "limit_type": "endpoint",
      "retry_after": 60,
      "user_tier": "authenticated"
    }
  }
}
```

**Response Headers**:
```
Retry-After: 60
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1640995260
```

### Best Practices

1. **Monitor rate limit headers** in responses
2. **Implement exponential backoff** when approaching limits
3. **Cache responses** when possible to reduce API calls
4. **Use webhooks** instead of polling for real-time updates
5. **Upgrade tier** if you consistently hit limits

---

## Error Handling

All errors follow a consistent format for easy parsing and handling.

### Error Response Format

```json
{
  "error": {
    "type": "error_type",
    "message": "Human-readable error message",
    "status_code": 400,
    "request_id": "req_123e4567",
    "timestamp": 1640995200.0,
    "path": "/api/v1/endpoint",
    "details": {}
  }
}
```

### Common Error Types

#### 400 Bad Request

```json
{
  "error": {
    "type": "bad_request",
    "message": "Invalid request parameters",
    "status_code": 400,
    "request_id": "req_123",
    "timestamp": 1640995200.0,
    "path": "/api/v1/reviews/ingest"
  }
}
```

#### 401 Unauthorized

```json
{
  "error": {
    "type": "unauthorized",
    "message": "Invalid or missing authentication token",
    "status_code": 401,
    "request_id": "req_123",
    "timestamp": 1640995200.0,
    "path": "/api/v1/reviews"
  }
}
```


#### 403 Forbidden

```json
{
  "error": {
    "type": "forbidden",
    "message": "Insufficient permissions to access this resource",
    "status_code": 403,
    "request_id": "req_123",
    "timestamp": 1640995200.0,
    "path": "/api/v1/users/admin"
  }
}
```

#### 404 Not Found

```json
{
  "error": {
    "type": "not_found",
    "message": "Resource not found",
    "status_code": 404,
    "request_id": "req_123",
    "timestamp": 1640995200.0,
    "path": "/api/v1/reviews/invalid_id"
  }
}
```

#### 422 Validation Error

```json
{
  "error": {
    "type": "validation_error",
    "message": "Request validation failed",
    "status_code": 422,
    "request_id": "req_123",
    "timestamp": 1640995200.0,
    "path": "/api/v1/reviews/ingest",
    "details": [
      {
        "field": "rating",
        "message": "Rating must be between 1 and 5",
        "type": "value_error",
        "input": 6
      },
      {
        "field": "content",
        "message": "Content is required",
        "type": "missing",
        "input": null
      }
    ]
  }
}
```

#### 429 Too Many Requests

See [Rate Limiting](#rate-limiting) section for details.

#### 500 Internal Server Error

```json
{
  "error": {
    "type": "internal_server_error",
    "message": "An unexpected error occurred",
    "status_code": 500,
    "request_id": "req_123",
    "timestamp": 1640995200.0,
    "path": "/api/v1/reviews/ingest"
  }
}
```

#### 503 Service Unavailable

```json
{
  "error": {
    "type": "service_unavailable",
    "message": "Service temporarily unavailable",
    "status_code": 503,
    "request_id": "req_123",
    "timestamp": 1640995200.0,
    "path": "/api/v1/reviews/ingest",
    "details": {
      "retry_after": 300,
      "reason": "maintenance"
    }
  }
}
```

### Error Handling Best Practices

1. **Always check status codes** before parsing response body
2. **Use request_id** for support inquiries
3. **Implement retry logic** for 5xx errors with exponential backoff
4. **Parse validation errors** to provide user-friendly messages
5. **Log errors** with full context for debugging

---

## Versioning

The API supports multiple versioning strategies to ensure backward compatibility.

### Versioning Strategies

#### 1. URL Path (Recommended)

Include the version in the URL path:

```
GET /api/v1/reviews
GET /api/v2/reviews
```

This is the recommended approach as it's explicit and easy to understand.

#### 2. Accept Header

Specify the version in the Accept header:

```
Accept: application/vnd.revive-ai.v1+json
```

#### 3. Query Parameter

Specify the version as a query parameter:

```
GET /api/reviews?version=v1
```

### Version Information

**Current Version**: v1 (stable)

**Supported Versions**:
- v1: Current stable version

### Version Lifecycle

- **Active**: Fully supported with new features
- **Deprecated**: Supported but no new features (6 months notice)
- **Sunset**: No longer supported (12 months notice)

### Migration Guides

When new versions are released, migration guides will be available at:
- `https://docs.revive-ai.com/migration/v1-to-v2`


---

## Monitoring

The API provides comprehensive monitoring endpoints for system health and performance.

### System Metrics

**Endpoint**: `GET /metrics`

**Authentication**: Required (Admin only)

**Response**:
```json
{
  "system": {
    "cpu_usage_percent": 45.2,
    "memory_usage_mb": 1024,
    "disk_usage_percent": 60.5,
    "uptime_seconds": 86400
  },
  "endpoints": {
    "summary": {
      "total_endpoints": 45,
      "top_endpoints": {
        "/api/v1/reviews/ingest": {
          "request_count": 1250,
          "avg_response_time_ms": 125,
          "error_rate": 0.02
        }
      }
    }
  },
  "timestamp": 1640995200
}
```

### Endpoint-Specific Metrics

**Endpoint**: `GET /metrics/endpoint/{path}`

**Authentication**: Required (Admin only)

**Example**: `GET /metrics/endpoint/api/v1/reviews/ingest`

**Response**:
```json
{
  "endpoint": "/api/v1/reviews/ingest",
  "metrics": {
    "request_count": 1250,
    "avg_response_time_ms": 125,
    "min_response_time_ms": 50,
    "max_response_time_ms": 500,
    "p50_response_time_ms": 100,
    "p95_response_time_ms": 250,
    "p99_response_time_ms": 400,
    "error_rate": 0.02,
    "status_codes": {
      "200": 1200,
      "400": 20,
      "422": 15,
      "500": 5
    }
  },
  "timestamp": 1640995200
}
```

### Health Check

See [Health Check](#health-check) section for details.

---

## Best Practices

### Authentication

1. **Store tokens securely** - Never commit tokens to version control
2. **Refresh tokens proactively** - Refresh before expiration
3. **Use HTTPS only** - Never send tokens over HTTP
4. **Implement token rotation** - Rotate tokens regularly

### Request Optimization

1. **Use pagination** - Don't fetch all records at once
2. **Implement caching** - Cache responses when appropriate
3. **Batch operations** - Use bulk endpoints when available
4. **Filter server-side** - Use query parameters to filter data

### Error Handling

1. **Implement retry logic** - Use exponential backoff for transient errors
2. **Log request IDs** - Include request_id in error logs
3. **Handle rate limits** - Monitor rate limit headers
4. **Validate before sending** - Validate data client-side to reduce errors

### Security

1. **Validate input** - Always validate and sanitize user input
2. **Use HTTPS** - Always use HTTPS in production
3. **Rotate credentials** - Regularly rotate API keys and tokens
4. **Monitor access** - Monitor API access patterns for anomalies

### Performance

1. **Use webhooks** - Prefer webhooks over polling
2. **Compress requests** - Use gzip compression for large payloads
3. **Parallel requests** - Make independent requests in parallel
4. **Monitor metrics** - Track response times and error rates


---

## Code Examples

### Python

#### Basic Setup

```python
import requests
from typing import Dict, Any

class ReviveAIClient:
    def __init__(self, base_url: str, email: str, password: str):
        self.base_url = base_url
        self.token = None
        self.login(email, password)
    
    def login(self, email: str, password: str):
        """Authenticate and get access token"""
        response = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            json={"email": email, "password": password}
        )
        response.raise_for_status()
        self.token = response.json()["access_token"]
    
    def _headers(self) -> Dict[str, str]:
        """Get headers with authentication"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def ingest_review(self, review_data: Dict[str, Any]) -> Dict[str, Any]:
        """Ingest a new review"""
        response = requests.post(
            f"{self.base_url}/api/v1/reviews/ingest",
            json=review_data,
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()
    
    def get_dashboard_metrics(self, period: str = "30d") -> Dict[str, Any]:
        """Get dashboard metrics"""
        response = requests.get(
            f"{self.base_url}/api/v1/dashboard/metrics",
            params={"period": period},
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()

# Usage
client = ReviveAIClient(
    base_url="https://api.revive-ai.com",
    email="user@example.com",
    password="securepassword"
)

# Ingest a review
review = client.ingest_review({
    "platform": "google",
    "external_id": "review_123",
    "customer_name": "John Doe",
    "rating": 2,
    "content": "Service was terrible",
    "created_at": "2024-01-15T10:30:00Z"
})
print(f"Review ingested: {review['review_id']}")

# Get metrics
metrics = client.get_dashboard_metrics(period="7d")
print(f"Average rating: {metrics['kpis']['average_rating']['value']}")
```

### JavaScript/TypeScript

#### Basic Setup

```typescript
interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

interface ReviewData {
  platform: string;
  external_id: string;
  customer_name: string;
  rating: number;
  content: string;
  created_at: string;
}

class ReviveAIClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  async login(email: string, password: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    if (!response.ok) {
      throw new Error(`Login failed: ${response.statusText}`);
    }

    const data: AuthResponse = await response.json();
    this.token = data.access_token;
  }

  private getHeaders(): HeadersInit {
    return {
      'Authorization': `Bearer ${this.token}`,
      'Content-Type': 'application/json'
    };
  }

  async ingestReview(reviewData: ReviewData): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/v1/reviews/ingest`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(reviewData)
    });

    if (!response.ok) {
      throw new Error(`Failed to ingest review: ${response.statusText}`);
    }

    return response.json();
  }

  async getDashboardMetrics(period: string = '30d'): Promise<any> {
    const response = await fetch(
      `${this.baseUrl}/api/v1/dashboard/metrics?period=${period}`,
      { headers: this.getHeaders() }
    );

    if (!response.ok) {
      throw new Error(`Failed to get metrics: ${response.statusText}`);
    }

    return response.json();
  }
}

// Usage
const client = new ReviveAIClient('https://api.revive-ai.com');

await client.login('user@example.com', 'securepassword');

const review = await client.ingestReview({
  platform: 'google',
  external_id: 'review_123',
  customer_name: 'John Doe',
  rating: 2,
  content: 'Service was terrible',
  created_at: '2024-01-15T10:30:00Z'
});

console.log(`Review ingested: ${review.review_id}`);
```


### cURL Examples

#### Register and Login

```bash
# Register a new account
curl -X POST "https://api.revive-ai.com/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123",
    "organization_name": "My Company"
  }'

# Login
curl -X POST "https://api.revive-ai.com/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }'

# Save the token from response
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

#### Ingest Review

```bash
curl -X POST "https://api.revive-ai.com/api/v1/reviews/ingest" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "google",
    "external_id": "review_123456",
    "customer_name": "John Doe",
    "rating": 2,
    "content": "Service was terrible, waited 2 hours for my order.",
    "created_at": "2024-01-15T10:30:00Z"
  }'
```

#### List Reviews with Filtering

```bash
# Get all high-urgency reviews
curl -X GET "https://api.revive-ai.com/api/v1/reviews?urgency_level=high&page=1&page_size=20" \
  -H "Authorization: Bearer $TOKEN"

# Get reviews from specific platform
curl -X GET "https://api.revive-ai.com/api/v1/reviews?platform=google&rating=2" \
  -H "Authorization: Bearer $TOKEN"
```

#### Assess Customer Risk

```bash
curl -X POST "https://api.revive-ai.com/api/v1/customers/recover" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "cust_123",
    "trigger_type": "support_ticket",
    "context": {
      "ticket_id": "ticket_456",
      "issue_summary": "Billing problem, customer frustrated"
    }
  }'
```

#### Get Dashboard Metrics

```bash
curl -X GET "https://api.revive-ai.com/api/v1/dashboard/metrics?period=30d&include_trends=true" \
  -H "Authorization: Bearer $TOKEN"
```

#### Health Check

```bash
# No authentication required
