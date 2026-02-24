# Revive AI - Demo Scenarios Guide

This document describes the demo data scenarios created by the `seed_demo_data.py` script and how to use them for testing and demonstrations.

## Overview

The demo data includes three different business types with realistic scenarios:

1. **Bella's Italian Restaurant** - Restaurant business with food service reviews
2. **TechSupport Pro** - SaaS company with technical support scenarios
3. **QuickShip Logistics** - Logistics company with delivery-related issues

## Demo Organizations

### 1. Bella's Italian Restaurant

**Business Type:** Restaurant  
**Domain:** bellas-restaurant.com  
**Settings:**
- Auto-respond threshold: 0.7
- Escalation threshold: 0.9

**Login Credentials:**
- Admin: `admin@bellas-restaurant.com` / `demo123`
- User: `user@bellas-restaurant.com` / `demo123`

**Scenarios:**
- Positive reviews about food quality and service
- Negative reviews about wait times and cold food
- Mixed reviews about delivery experience
- High-risk customers with multiple complaints
- Recovery actions for dissatisfied diners

### 2. TechSupport Pro

**Business Type:** SaaS  
**Domain:** techsupportpro.com  
**Settings:**
- Auto-respond threshold: 0.8
- Escalation threshold: 0.85

**Login Credentials:**
- Admin: `admin@techsupportpro.com` / `demo123`
- User: `user@techsupportpro.com` / `demo123`

**Scenarios:**
- Technical support tickets with varying priorities
- Billing-related customer concerns
- Feature requests from users
- Service downtime complaints
- Churn risk customers with unresolved issues

### 3. QuickShip Logistics

**Business Type:** Logistics  
**Domain:** quickship.com  
**Settings:**
- Auto-respond threshold: 0.75
- Escalation threshold: 0.9

**Login Credentials:**
- Admin: `admin@quickship.com` / `demo123`
- User: `user@quickship.com` / `demo123`

**Scenarios:**
- Delivery delay complaints
- Package quality issues
- Pricing concerns
- Customer service reviews
- Recovery actions for shipping problems

## Customer Risk Profiles

Each organization has 5 customers with different risk levels:

### High Risk (Churn Risk: 0.85, Bad Review Likelihood: 0.78)
- **Customer:** John Smith
- **Characteristics:**
  - Multiple recent complaints
  - Low sentiment scores
  - High escalation count
  - Recent negative interactions
- **Recovery Actions:**
  - Personal call scheduled
  - 20% discount offer
  - Manager escalation

### Medium-High Risk (Churn Risk: 0.65, Bad Review Likelihood: 0.55)
- **Customer:** Sarah Johnson
- **Characteristics:**
  - Some unresolved issues
  - Mixed sentiment
  - Moderate interaction frequency
- **Recovery Actions:**
  - Personalized email
  - 10% discount offer

### Medium Risk (Churn Risk: 0.45, Bad Review Likelihood: 0.35)
- **Customer:** Michael Brown
- **Characteristics:**
  - Occasional complaints
  - Generally positive sentiment
  - Regular customer
- **Recovery Actions:**
  - Follow-up email

### Low Risk (Churn Risk: 0.15, Bad Review Likelihood: 0.10)
- **Customers:** Emily Davis, David Wilson
- **Characteristics:**
  - Satisfied customers
  - Positive interactions
  - Loyal customer base
- **Recovery Actions:**
  - None required (proactive engagement only)

## Review Scenarios

### Positive Reviews (5★ and 4★)

**Scenario 1: Excellent Service**
- Rating: 5★
- Sentiment: 0.95
- Urgency: Low
- Categories: Quality
- Agent Decision: Respond publicly with thanks
- Status: Responded

**Scenario 2: Great Experience**
- Rating: 5★
- Sentiment: 0.92
- Urgency: Low
- Categories: Support, Delivery
- Agent Decision: Respond publicly
- Status: Responded

**Scenario 3: Worth the Money**
- Rating: 4★
- Sentiment: 0.88
- Urgency: Low
- Categories: Quality
- Agent Decision: Respond publicly
- Status: Responded

### Moderate Reviews (3★)

**Scenario 4: Okay But Slow**
- Rating: 3★
- Sentiment: 0.55
- Urgency: Medium
- Categories: Delivery, Quality
- Agent Decision: Respond publicly with improvement commitment
- Status: Pending

**Scenario 5: Issues Resolved**
- Rating: 3★
- Sentiment: 0.50
- Urgency: Medium
- Categories: Support
- Agent Decision: Respond publicly, acknowledge resolution
- Status: Pending

### Negative Reviews (1★ and 2★)

**Scenario 6: Long Wait, Cold Food**
- Rating: 2★
- Sentiment: 0.15
- Urgency: High
- Categories: Delivery, Quality
- Agent Decision: Private recovery required
- Recovery Actions: Apology email + discount
- Status: Pending

**Scenario 7: Rude Staff**
- Rating: 1★
- Sentiment: 0.05
- Urgency: High
- Categories: Support, Quality
- Agent Decision: Escalate to manager
- Recovery Actions: Personal call + compensation
- Status: Escalated

**Scenario 8: Overpriced**
- Rating: 2★
- Sentiment: 0.20
- Urgency: High
- Categories: Pricing, Quality
- Agent Decision: Private recovery
- Recovery Actions: Value explanation + offer
- Status: Pending

## Support Ticket Scenarios

### High Priority Tickets

**Scenario 1: Payment Not Processed**
- Priority: High
- Category: Billing
- Sentiment: 0.15
- Status: Open
- Customer Risk: High
- Expected Action: Immediate investigation + refund/reprocess

**Scenario 2: Service Down**
- Priority: High
- Category: Technical
- Sentiment: 0.10
- Status: Open
- Customer Risk: Very High
- Expected Action: Emergency response + compensation

### Medium Priority Tickets

**Scenario 3: Billing Question**
- Priority: Medium
- Category: Billing
- Sentiment: 0.45
- Status: In Progress
- Customer Risk: Medium
- Expected Action: Detailed explanation within 24 hours

**Scenario 4: Feature Request**
- Priority: Medium
- Category: Feature Request
- Sentiment: 0.70
- Status: In Progress
- Customer Risk: Low
- Expected Action: Acknowledge + roadmap update

### Low Priority Tickets

**Scenario 5: General Inquiry**
- Priority: Low
- Category: General
- Sentiment: 0.75
- Status: Open
- Customer Risk: Low
- Expected Action: Standard response within 48 hours

## Agent Decision Scenarios

### Decision Type: Respond Public

**Criteria:**
- Rating ≥ 4 stars
- OR Rating = 3 and sentiment > 0.5
- Confidence: 0.75 - 0.90

**Example:**
```json
{
  "decision_type": "respond_public",
  "confidence_score": 0.90,
  "reasoning": "Positive review - thank customer publicly",
  "status": "executed"
}
```

### Decision Type: Recover Private

**Criteria:**
- Rating ≤ 2 stars
- AND urgency = high
- Confidence: 0.80 - 0.95

**Example:**
```json
{
  "decision_type": "recover_private",
  "confidence_score": 0.95,
  "reasoning": "Critical negative review requiring immediate private recovery",
  "status": "pending"
}
```

### Decision Type: Escalate

**Criteria:**
- Urgency = high
- AND multiple issue categories (> 2)
- OR complex case requiring human judgment
- Confidence: 0.60 - 0.70

**Example:**
```json
{
  "decision_type": "escalate",
  "confidence_score": 0.60,
  "reasoning": "Complex multi-issue case requiring human review",
  "status": "pending"
}
```

## Recovery Action Scenarios

### Email Recovery

**Scenario:** High-risk customer with recent complaint
- Action Type: Email
- Priority: High
- Content: Personalized apology + resolution offer
- Status: Sent
- Scheduled: 2 hours from creation
- Executed: Immediately or within schedule

**Template:**
```
Dear [Customer Name],

We noticed you've had some concerns recently and we sincerely apologize 
for any inconvenience. Your satisfaction is our top priority.

We would like to make this right by [specific resolution].

Please let us know if there's anything else we can do.

Best regards,
[Business Name] Team
```

### Discount Offer

**Scenario:** Very high-risk customer (churn risk > 0.8)
- Action Type: Discount
- Priority: High
- Content: 20% discount on next purchase
- Status: Pending
- Scheduled: 1 hour from creation

**Template:**
```
As a gesture of goodwill, we'd like to offer you 20% off your next 
purchase. Use code: SORRY20

This offer is valid for 30 days.
```

### Phone Call

**Scenario:** Critical customer with multiple escalations
- Action Type: Call
- Priority: Critical
- Content: Manager callback scheduled
- Status: Scheduled
- Scheduled: Within 1 hour

### SMS/WhatsApp

**Scenario:** Urgent delivery issue
- Action Type: SMS
- Priority: High
- Content: Quick update on resolution
- Status: Sent

## Testing Workflows

### Workflow 1: Review Ingestion to Response

1. **Ingest Review** via API
   ```bash
   POST /api/v1/reviews/ingest
   ```

2. **Automatic Analysis**
   - Sentiment scoring
   - Urgency classification
   - Issue categorization

3. **Agent Decision**
   - Rule-based decision making
   - Confidence scoring

4. **Action Execution**
   - Public response OR
   - Private recovery OR
   - Human escalation

### Workflow 2: Customer Risk Assessment

1. **Analyze Customer Data**
   - Review history
   - Support ticket sentiment
   - Interaction frequency

2. **Calculate Risk Scores**
   - Churn risk
   - Bad review likelihood

3. **Generate Recovery Plan**
   - Prioritized actions
   - Scheduled execution

4. **Execute Recovery**
   - Send communications
   - Track outcomes

### Workflow 3: Dashboard Monitoring

1. **View KPIs**
   - Average rating
   - Monthly reviews
   - At-risk customers
   - Recovery success rate

2. **Activity Feed**
   - Recent reviews
   - Recovery actions
   - Agent decisions

3. **Action Queue**
   - Pending responses
   - Scheduled recoveries
   - Escalated cases

## API Testing Scenarios

### Scenario 1: Analyze New Review

```bash
curl -X POST http://localhost:8000/api/v1/reviews/analyze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "review_id": "<review_uuid>"
  }'
```

**Expected Response:**
```json
{
  "sentiment_score": 0.15,
  "urgency_level": "high",
  "issue_categories": ["delivery", "quality"],
  "recommended_action": "recover_private"
}
```

### Scenario 2: Assess Customer Risk

```bash
curl -X POST http://localhost:8000/api/v1/customers/recover \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "customer_id": "<customer_uuid>",
    "trigger_type": "support_ticket"
  }'
```

**Expected Response:**
```json
{
  "churn_risk": 0.75,
  "bad_review_likelihood": 0.68,
  "actions": [
    {
      "type": "personalized_email",
      "priority": "high",
      "scheduled_at": "2024-02-15T11:00:00Z"
    }
  ]
}
```

### Scenario 3: Get Dashboard Metrics

```bash
curl -X GET http://localhost:8000/api/v1/dashboard/metrics \
  -H "Authorization: Bearer <token>"
```

**Expected Response:**
```json
{
  "average_rating": 3.8,
  "monthly_reviews": 24,
  "at_risk_customers": 2,
  "recovery_success_rate": 0.65,
  "activity_feed": [...]
}
```

## Data Validation

### Review Data Integrity

- ✅ Sentiment scores between 0.0 and 1.0
- ✅ Ratings between 1 and 5
- ✅ Low ratings (1-2) have low sentiment (< 0.4)
- ✅ High ratings (4-5) have high sentiment (> 0.6)
- ✅ High urgency reviews have ratings ≤ 3

### Customer Risk Consistency

- ✅ Churn risk scores between 0.0 and 1.0
- ✅ High-risk customers have multiple tickets
- ✅ Risk scores correlate with sentiment
- ✅ Recovery actions prioritized by risk level

### Agent Decision Logic

- ✅ Critical reviews (≤2★, high urgency) → Private recovery
- ✅ Positive reviews (≥4★) → Public response
- ✅ Complex cases (multiple issues) → Escalation
- ✅ Confidence scores reflect decision certainty

## Cleanup and Reset

### Clear Demo Data

```bash
python backend/scripts/seed_demo_data.py --clear
```

### Reseed Fresh Data

```bash
python backend/scripts/seed_demo_data.py --clear --environment development
```

### Verify Data

```bash
# Check database
psql $DATABASE_URL -c "SELECT COUNT(*) FROM organizations;"
psql $DATABASE_URL -c "SELECT COUNT(*) FROM reviews;"
psql $DATABASE_URL -c "SELECT COUNT(*) FROM customers;"
```

## Troubleshooting

### Issue: Script fails with database connection error

**Solution:**
```bash
# Verify DATABASE_URL is set
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1;"
```

### Issue: Duplicate data errors

**Solution:**
```bash
# Clear existing data first
python backend/scripts/seed_demo_data.py --clear
```

### Issue: Import errors

**Solution:**
```bash
# Ensure you're in the backend directory
cd backend

# Install dependencies
pip install -r requirements.txt
```

## Best Practices

1. **Always use development environment** for demo data
2. **Clear data between demos** to ensure consistency
3. **Test workflows end-to-end** using demo scenarios
4. **Verify data integrity** after seeding
5. **Use realistic scenarios** for demonstrations
6. **Document custom scenarios** if you add new templates

## Next Steps

After seeding demo data:

1. ✅ Start the backend server
2. ✅ Login with demo credentials
3. ✅ Explore the dashboard
4. ✅ Test review analysis workflows
5. ✅ Verify customer risk assessments
6. ✅ Check recovery action execution
7. ✅ Review agent decision logs

## Support

For issues with demo data:
- Check the script output for errors
- Verify database connectivity
- Review the data validation section
- Check application logs for API errors
