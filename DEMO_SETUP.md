# ReviewAI Demo Setup Guide

## Overview
ReviewAI is now a **single-user AI customer recovery demonstration** showcasing:
- ✅ Real-time review ingestion (simulated Google Reviews)
- ✅ Structured decision model (Laya/Mock abstraction)
- ✅ ML churn risk prediction (XGBoost on synthetic data)
- ✅ Deterministic policy engine
- ✅ Knowledge grounding (RAG-style)
- ✅ Complete lifecycle visualization in dashboard

## Quick Start (5 minutes)

### 1. Backend Setup

```bash
cd ReviewAI/backend

# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\activate  # Windows
# or source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Setup demo (initializes DB, trains ML models)
python setup_demo.py

# Run backend
uvicorn app.main:app --reload
```

Backend will be available at: `http://localhost:8000`

### 2. Frontend Setup

```bash
cd ReviewAI/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at: `http://localhost:3000`

## Testing the Demo Flow

### Via API (Recommended)

**1. Check status:**
```bash
curl http://localhost:8000/api/v1/demo/demo-status
```

**2. Submit a demo review:**
```bash
curl -X POST http://localhost:8000/api/v1/demo/ingest-demo-review \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "John Smith",
    "rating": 2,
    "review_text": "The product was broken when it arrived. Customer service was unhelpful and I cannot get a refund. Very disappointed."
  }'
```

**Response includes:**
- Sentiment score
- Urgency level
- Structured decision (category, urgency, risks)
- ML churn risk prediction
- Policy decision (AUTO_EXECUTE / APPROVAL_REQUIRED / ESCALATE)

### Via Frontend Dashboard

1. Open `http://localhost:3000`
2. You're logged in automatically (demo mode)
3. Navigate to Reviews section
4. Click "Simulate Google Review" button
5. Fill in: customer name, rating, review text
6. Watch the AI pipeline execute in real-time
7. See decision, policy determination, and execution status

## Architecture Overview

```
Google Review (Demo Simulation)
    ↓
FastAPI Ingestion Endpoint
    ↓
┌─────────────────────────────────────┐
│ Sentiment Analysis                  │
│ Urgency Classification              │
│ Category Detection                  │
└──────────────┬──────────────────────┘
               ↓
    ┌──────────────────────┐
    │ Structured Decision  │
    │ (Laya Mock)          │
    │                      │
    │ - Category           │
    │ - Urgency (1-5)      │
    │ - Churn Risk         │
    │ - Escalation Flag    │
    └──────────┬───────────┘
               ↓
    ┌──────────────────────┐
    │ ML Churn Prediction  │
    │ (XGBoost)            │
    │ Trained on synthetic │
    │ demo data            │
    └──────────┬───────────┘
               ↓
    ┌──────────────────────┐
    │ Policy Engine        │
    │ (Deterministic)      │
    │                      │
    │ AUTO_EXECUTE if:     │
    │ - Positive + high    │
    │   confidence         │
    │                      │
    │ APPROVAL if:         │
    │ - Medium confidence  │
    │ - Medium risk        │
    │                      │
    │ ESCALATE if:         │
    │ - Safety concern     │
    │ - Low confidence     │
    │ - High risk          │
    └──────────┬───────────┘
               ↓
    ┌──────────────────────┐
    │ Execute Action       │
    │ or Queue for Approval│
    └──────────┬───────────┘
               ↓
         Dashboard Display
```

## Components

### Backend
- **FastAPI**: Web framework
- **PostgreSQL**: Persistent data store
- **Decision Models**: Laya (mock), Mock implementations
- **ML Model**: XGBoost churn prediction (synthetic training data)
- **Policy Engine**: Deterministic routing (confidence + risk based)
- **Knowledge Service**: Simple RAG (demo knowledge base)

### Frontend
- **Next.js 14**: React framework
- **Direct Dashboard**: Opens directly (demo mode, no login required)
- **Review List**: Shows all ingested reviews with full lifecycle
- **AI Pipeline Visualization**: See decision at each step
- **Demo Simulation**: Simple form to submit test reviews

## Environment Variables

Create `.env` file in `ReviewAI/backend/`:

```env
# Database (local default works)
DATABASE_URL=postgresql://postgres:password@localhost:5432/reviewai_demo

# LLM (for response generation)
MISTRAL_API_KEY=your_key_here  # or OPENAI_API_KEY, etc.
DEFAULT_LLM_PROVIDER=mock  # Use mock for quick demo

# Decision Model
DECISION_MODEL_PROVIDER=mock  # or "laya" when available
# LAYA_MODEL_PATH=/path/to/laya/model  # Optional

# Redis (optional, for caching)
REDIS_URL=redis://localhost:6379

# Development
DEBUG=true
LOG_LEVEL=INFO
ENVIRONMENT=demo
```

## Key Files Modified/Created

### New Components
- `app/models/decision.py` - Structured decision schema
- `app/services/decision_model/` - Decision model abstraction (Laya, Mock, Base)
- `app/services/ml_churn_model.py` - XGBoost churn prediction
- `app/services/policy_engine.py` - Deterministic policy validation
- `app/services/knowledge_service.py` - Knowledge base management
- `app/models/knowledge.py` - Knowledge storage model
- `app/api/v1/endpoints/demo.py` - Demo endpoints
- `setup_demo.py` - Database and model initialization

### Modified
- `app/api/v1/api.py` - Added demo router
- `app/core/config.py` - Added decision model config
- `requirements.txt` - Added scikit-learn, xgboost, lightgbm
- `frontend/src/config/auth.ts` - Demo mode enabled (no auth)

### Removed/Simplified
- Multi-tenancy database constraints (optional)
- Subscription/billing UI (kept backend for reference)
- Registration/login flows (direct dashboard)

## What's **NOT** Implemented (By Design)

This is a focused demo, not a full SaaS:
- ❌ Real Google Reviews API integration (webhook simulation instead)
- ❌ Kafka event bus (single-user app doesn't need it)
- ❌ Multi-tenant organization complexity
- ❌ Subscription management UI
- ❌ AWS deployment (local/Docker only)
- ❌ Advanced role-based access
- ❌ Real Laya/Jev model (mock abstraction in place)

## Demo Scenarios

### Scenario 1: Positive Review (5 stars)
```json
{
  "customer_name": "Happy Customer",
  "rating": 5,
  "review_text": "Excellent product! Arrived quickly and works perfectly. Highly recommend!"
}
```
Expected: AUTO_EXECUTE → Thank you response

### Scenario 2: Negative Review (1-2 stars)
```json
{
  "customer_name": "Unhappy Customer",
  "rating": 1,
  "review_text": "Product broke after 2 days. Tried to return but no response from support. DO NOT BUY."
}
```
Expected: ESCALATE → High priority, needs human review

### Scenario 3: Quality Issue (3 stars)
```json
{
  "customer_name": "Neutral Customer",
  "rating": 3,
  "review_text": "Product works but not as described. Quality could be better. Considering switching brands."
}
```
Expected: APPROVAL_REQUIRED → Send to queue for human decision

## Troubleshooting

### Database Connection Error
```
Error: could not translate host name "localhost" to address
```
**Solution**: Ensure PostgreSQL is running locally
```bash
# Windows (via WSL2 or local Postgres)
# Verify: psql -U postgres -d postgres

# Or use Docker:
docker run --name reviewai-db -e POSTGRES_PASSWORD=password \
  -p 5432:5432 -d postgres
```

### ML Model Training Fails
```
Error: Failed to setup ML model
```
**Solution**: Delete cached model and retrain
```bash
rm ReviewAI/backend/models/*.pkl ReviewAI/backend/models/*.json
python setup_demo.py
```

### Frontend Won't Connect to Backend
```
Error: CORS or network error
```
**Solution**: Ensure backend is running on port 8000
```bash
# Check:
curl http://localhost:8000/api/v1/health
```

## Performance Notes

- Sentiment/urgency: < 50ms (deterministic rules)
- Structured decision: < 100ms (mock Laya)
- ML prediction: < 200ms (XGBoost inference)
- Total end-to-end: < 500ms for a review

---

## Next Steps

1. **Test the demo** using the scenarios above
2. **Explore the code** in `app/services/` to understand the architecture
3. **Customize policies** in `policy_engine.py`
4. **Add real knowledge** in the knowledge base
5. **Integrate real LLM** by setting `MISTRAL_API_KEY` or `OPENAI_API_KEY`
6. **Customize the frontend** dashboard to your needs

---

For questions or issues, see the main README or contact the team.
