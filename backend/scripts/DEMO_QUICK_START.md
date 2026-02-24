# Demo Data Quick Start Guide

Quick reference for seeding and using demo data in Revive AI.

## Quick Commands

### Seed Demo Data

```bash
# From project root
cd backend
python scripts/seed_demo_data.py --environment development
```

### Clear and Reseed

```bash
python scripts/seed_demo_data.py --clear --environment development
```

### Clear Only

```bash
python scripts/seed_demo_data.py --clear
```

## Login Credentials

### Bella's Italian Restaurant
- **Admin:** admin@bellas-restaurant.com / demo123
- **User:** user@bellas-restaurant.com / demo123

### TechSupport Pro
- **Admin:** admin@techsupportpro.com / demo123
- **User:** user@techsupportpro.com / demo123

### QuickShip Logistics
- **Admin:** admin@quickship.com / demo123
- **User:** user@quickship.com / demo123

## What Gets Created

| Entity | Count | Description |
|--------|-------|-------------|
| Organizations | 3 | Different business types |
| Users | 6 | 2 per organization (admin + user) |
| Customers | 15 | 5 per organization with varying risk levels |
| Reviews | ~24 | Mix of positive, moderate, and negative |
| Support Tickets | ~15 | Different priorities and categories |
| Recovery Actions | ~6 | Email, discount, and call actions |
| Agent Decisions | ~15 | Various decision types |

## Quick Test Scenarios

### Test 1: View Dashboard
1. Login as admin@bellas-restaurant.com
2. Navigate to dashboard
3. View KPIs and activity feed

### Test 2: Review Analysis
1. Go to Reviews page
2. Find a 2★ review
3. Check sentiment score and urgency
4. View recommended action

### Test 3: Customer Risk
1. Go to Customers page
2. Find John Smith (high risk)
3. View churn risk score (0.85)
4. Check recovery actions

### Test 4: Agent Decisions
1. View agent decisions log
2. Check decision types
3. Verify confidence scores
4. Review reasoning

## API Testing

### Get Auth Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@bellas-restaurant.com",
    "password": "demo123"
  }'
```

### Get Dashboard Metrics

```bash
curl -X GET http://localhost:8000/api/v1/dashboard/metrics \
  -H "Authorization: Bearer <your_token>"
```

### List Reviews

```bash
curl -X GET http://localhost:8000/api/v1/reviews \
  -H "Authorization: Bearer <your_token>"
```

## Data Characteristics

### Review Distribution
- **5★:** ~3 per organization (positive)
- **4★:** ~1 per organization (positive)
- **3★:** ~2 per organization (moderate)
- **2★:** ~2 per organization (negative)
- **1★:** ~1 per organization (critical)

### Customer Risk Levels
- **High Risk (>0.6):** 2 per organization
- **Medium Risk (0.3-0.6):** 1 per organization
- **Low Risk (<0.3):** 2 per organization

### Ticket Priorities
- **High:** ~2 per organization
- **Medium:** ~2 per organization
- **Low:** ~1 per organization

## Troubleshooting

### Database Connection Error
```bash
# Check DATABASE_URL
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1;"
```

### Import Errors
```bash
# Ensure in backend directory
cd backend

# Install dependencies
pip install -r requirements.txt
```

### Permission Errors
```bash
# Make script executable
chmod +x scripts/seed_demo_data.py
```

## Environment Variables

Required:
```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/revive_ai"
```

Optional:
```bash
export ENVIRONMENT="development"
```

## Safety Notes

⚠️ **Never run in production!**
- Script blocks production environment
- Only use in development or staging
- Always backup before clearing data

## Next Steps

After seeding:
1. ✅ Start backend: `uvicorn main:app --reload`
2. ✅ Login with demo credentials
3. ✅ Explore dashboard and features
4. ✅ Test API endpoints
5. ✅ Review demo scenarios documentation

## Full Documentation

For detailed scenarios and workflows, see:
- `backend/docs/DEMO_SCENARIOS.md` - Complete scenario guide
- `backend/scripts/README.md` - Script documentation
