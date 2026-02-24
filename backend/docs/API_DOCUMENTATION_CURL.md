# Revive AI API - cURL Examples

## Health Check

```bash
# No authentication required
curl -X GET "https://api.revive-ai.com/health"
```

## Complete Workflow Example

```bash
#!/bin/bash

# 1. Register
echo "Registering new account..."
curl -X POST "https://api.revive-ai.com/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123",
    "organization_name": "My Company"
  }'

# 2. Login and save token
echo "Logging in..."
TOKEN=$(curl -X POST "https://api.revive-ai.com/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }' | jq -r '.access_token')

echo "Token: $TOKEN"

# 3. Ingest a review
echo "Ingesting review..."
REVIEW_ID=$(curl -X POST "https://api.revive-ai.com/api/v1/reviews/ingest" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "google",
    "external_id": "review_123",
    "customer_name": "John Doe",
    "rating": 2,
    "content": "Service was terrible",
    "created_at": "2024-01-15T10:30:00Z"
  }' | jq -r '.review_id')

echo "Review ID: $REVIEW_ID"

# 4. Get dashboard metrics
echo "Getting dashboard metrics..."
curl -X GET "https://api.revive-ai.com/api/v1/dashboard/metrics?period=30d" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Support

For additional help:
- **Documentation**: https://docs.revive-ai.com
- **Support Email**: support@revive-ai.com
- **Status Page**: https://status.revive-ai.com

---

**Last Updated**: January 2024  
**API Version**: 1.0.0
