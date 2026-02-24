# Revive AI - Technical Design Document

## System Architecture

### High-Level Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend       │    │   External      │
│   (Next.js)     │◄──►│   (FastAPI)      │◄──►│   Services      │
│                 │    │                  │    │                 │
│ • Dashboard     │    │ • REST APIs      │    │ • Google Reviews│
│ • Auth UI       │    │ • Agent Engine   │    │ • Email/SMS     │
│ • KPI Views     │    │ • Background     │    │ • CRM Systems   │
└─────────────────┘    │   Tasks          │    └─────────────────┘
                       └──────────────────┘
                                │
                       ┌──────────────────┐
                       │   Data Layer     │
                       │                  │
                       │ • PostgreSQL     │
                       │ • pgvector       │
                       │ • Redis Cache    │
                       └──────────────────┘
```

### Component Architecture
```
Backend Services:
├── API Layer (FastAPI)
│   ├── Authentication Service
│   ├── Review Intelligence API
│   ├── Customer Recovery API
│   └── Dashboard Metrics API
├── Core Services
│   ├── Agent Orchestration Engine
│   ├── Sentiment Analysis Service
│   ├── LLM Integration Service
│   └── Notification Service
├── Data Access Layer
│   ├── Repository Pattern
│   ├── Database Models
│   └── Vector Store Operations
└── Background Tasks
    ├── Review Ingestion Worker
    ├── Recovery Action Executor
    └── Metrics Aggregator
```

## Database Schema

### Core Tables

#### Organizations
```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255),
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### Users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### Reviews
```sql
CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    platform VARCHAR(50) NOT NULL, -- 'google', 'yelp', etc.
    external_id VARCHAR(255),
    customer_name VARCHAR(255),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    content TEXT,
    sentiment_score DECIMAL(3,2), -- 0.00 to 1.00
    urgency_level VARCHAR(20), -- 'low', 'medium', 'high'
    issue_categories TEXT[], -- ['support', 'pricing', 'delivery', 'quality']
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'responded', 'escalated'
    requires_private_recovery BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### Customers
```sql
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    email VARCHAR(255),
    phone VARCHAR(50),
    name VARCHAR(255),
    churn_risk_score DECIMAL(3,2), -- 0.00 to 1.00
    bad_review_likelihood DECIMAL(3,2), -- 0.00 to 1.00
    last_interaction TIMESTAMP,
    context_summary TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### Support Tickets
```sql
CREATE TABLE support_tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    customer_id UUID REFERENCES customers(id),
    external_id VARCHAR(255),
    subject VARCHAR(500),
    content TEXT,
    status VARCHAR(50) DEFAULT 'open',
    priority VARCHAR(20) DEFAULT 'medium',
    sentiment_score DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### Recovery Actions
```sql
CREATE TABLE recovery_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    customer_id UUID REFERENCES customers(id),
    review_id UUID REFERENCES reviews(id),
    ticket_id UUID REFERENCES support_tickets(id),
    action_type VARCHAR(50) NOT NULL, -- 'email', 'sms', 'call', 'discount'
    content TEXT,
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'sent', 'failed'
    scheduled_at TIMESTAMP,
    executed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### Agent Decisions
```sql
CREATE TABLE agent_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    input_type VARCHAR(50), -- 'review', 'ticket'
    input_id UUID,
    decision_type VARCHAR(50), -- 'respond_public', 'recover_private', 'escalate'
    confidence_score DECIMAL(3,2),
    reasoning TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### Vector Embeddings
```sql
CREATE TABLE embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    content_type VARCHAR(50), -- 'review', 'ticket', 'response'
    content_id UUID,
    embedding vector(1536), -- OpenAI embedding dimension
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create vector similarity index
CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops);
```

## Agent Logic Design

### Core Agent Engine

The agent operates as a rule-based system with LLM enhancement:

```python
class AgentEngine:
    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
        self.urgency_classifier = UrgencyClassifier()
        self.llm_service = LLMService()
        self.decision_rules = DecisionRules()
    
    async def process_review(self, review: Review) -> AgentDecision:
        # Step 1: Analyze sentiment (deterministic)
        sentiment_score = self.sentiment_analyzer.analyze(review.content)
        
        # Step 2: Classify urgency (rule-based)
        urgency_level = self.urgency_classifier.classify(
            review.content, 
            review.rating
        )
        
        # Step 3: Categorize issues (ML-based)
        issue_categories = self.categorize_issues(review.content)
        
        # Step 4: Apply decision rules
        decision = self.decision_rules.decide_action(
            sentiment_score=sentiment_score,
            urgency_level=urgency_level,
            rating=review.rating,
            categories=issue_categories
        )
        
        # Step 5: Generate response if needed (LLM)
        if decision.action_type == "respond_public":
            response = await self.llm_service.generate_review_response(
                review=review,
                sentiment=sentiment_score,
                categories=issue_categories
            )
            decision.content = response
        
        return decision
```

### Decision Rules Engine

```python
class DecisionRules:
    def decide_action(self, sentiment_score: float, urgency_level: str, 
                     rating: int, categories: List[str]) -> AgentDecision:
        
        # Rule 1: Critical negative reviews (1-2 stars, high urgency)
        if rating <= 2 and urgency_level == "high":
            return AgentDecision(
                action_type="recover_private",
                confidence_score=0.95,
                reasoning="Critical negative review requiring immediate private recovery"
            )
        
        # Rule 2: Moderate negative reviews with specific issues
        if rating <= 3 and any(cat in ["support", "quality"] for cat in categories):
            if sentiment_score < 0.3:
                return AgentDecision(
                    action_type="recover_private",
                    confidence_score=0.8,
                    reasoning="Negative review with service issues"
                )
            else:
                return AgentDecision(
                    action_type="respond_public",
                    confidence_score=0.7,
                    reasoning="Moderate review suitable for public response"
                )
        
        # Rule 3: Positive reviews (4-5 stars)
        if rating >= 4:
            return AgentDecision(
                action_type="respond_public",
                confidence_score=0.9,
                reasoning="Positive review - thank customer publicly"
            )
        
        # Rule 4: Complex cases requiring human review
        if urgency_level == "high" and len(categories) > 2:
            return AgentDecision(
                action_type="escalate",
                confidence_score=0.6,
                reasoning="Complex multi-issue case requiring human review"
            )
        
        # Default: Public response
        return AgentDecision(
            action_type="respond_public",
            confidence_score=0.5,
            reasoning="Standard case - public response appropriate"
        )
```

### Customer Recovery Logic

```python
class CustomerRecoveryAgent:
    async def assess_customer_risk(self, customer: Customer, 
                                 recent_tickets: List[SupportTicket]) -> RiskAssessment:
        
        # Calculate churn risk based on multiple factors
        churn_indicators = {
            "ticket_frequency": len(recent_tickets),
            "avg_sentiment": np.mean([t.sentiment_score for t in recent_tickets]),
            "escalation_count": sum(1 for t in recent_tickets if t.priority == "high"),
            "days_since_last_interaction": (datetime.now() - customer.last_interaction).days
        }
        
        # Rule-based risk scoring
        churn_risk = self.calculate_churn_risk(churn_indicators)
        bad_review_likelihood = self.calculate_review_risk(churn_indicators)
        
        return RiskAssessment(
            churn_risk=churn_risk,
            bad_review_likelihood=bad_review_likelihood,
            recommended_actions=self.recommend_recovery_actions(churn_risk)
        )
    
    def recommend_recovery_actions(self, churn_risk: float) -> List[RecoveryAction]:
        actions = []
        
        if churn_risk > 0.8:
            actions.extend([
                RecoveryAction(type="personal_call", priority="high"),
                RecoveryAction(type="discount_offer", value="20%"),
                RecoveryAction(type="escalate_to_manager")
            ])
        elif churn_risk > 0.6:
            actions.extend([
                RecoveryAction(type="personalized_email"),
                RecoveryAction(type="discount_offer", value="10%")
            ])
        elif churn_risk > 0.4:
            actions.append(
                RecoveryAction(type="follow_up_email")
            )
        
        return actions
```

## API Design

### Core Endpoints

#### Review Intelligence API

```python
# POST /api/v1/reviews/ingest
{
    "platform": "google",
    "external_id": "review_123",
    "customer_name": "John Doe",
    "rating": 2,
    "content": "Service was terrible, waited 2 hours...",
    "created_at": "2024-01-15T10:30:00Z"
}

# Response
{
    "review_id": "uuid",
    "sentiment_score": 0.15,
    "urgency_level": "high",
    "issue_categories": ["support", "quality"],
    "recommended_action": "recover_private",
    "requires_private_recovery": true
}
```

#### Customer Recovery API

```python
# POST /api/v1/customers/recover
{
    "customer_id": "uuid",
    "trigger_type": "support_ticket",
    "context": {
        "ticket_id": "uuid",
        "issue_summary": "Billing problem, customer frustrated"
    }
}

# Response
{
    "recovery_plan": {
        "churn_risk": 0.75,
        "bad_review_likelihood": 0.68,
        "actions": [
            {
                "type": "personalized_email",
                "content": "Dear John, we sincerely apologize...",
                "scheduled_at": "2024-01-15T11:00:00Z"
            },
            {
                "type": "discount_offer",
                "value": "15%",
                "expires_at": "2024-01-22T23:59:59Z"
            }
        ]
    }
}
```

#### Agent Decision API

```python
# POST /api/v1/agents/decide-action
{
    "input_type": "review",
    "input_id": "uuid",
    "context": {
        "customer_history": "Previous positive interactions",
        "business_rules": {
            "auto_respond_threshold": 0.7,
            "escalation_threshold": 0.9
        }
    }
}

# Response
{
    "decision": {
        "action_type": "respond_public",
        "confidence_score": 0.85,
        "reasoning": "Moderate negative review suitable for public response",
        "generated_content": "Thank you for your feedback. We take all concerns seriously...",
        "requires_approval": false
    }
}
```

## LLM Integration

### Prompt Templates

#### Review Response Generation
```python
REVIEW_RESPONSE_PROMPT = """
You are a professional customer service representative responding to an online review.

Review Details:
- Rating: {rating}/5 stars
- Content: "{content}"
- Sentiment Score: {sentiment_score}
- Issue Categories: {categories}

Guidelines:
- Be empathetic and professional
- Address specific concerns mentioned
- Offer concrete next steps
- Keep response under 150 words
- Do not make promises you cannot keep
- Invite private conversation for complex issues

Generate a response that follows these guidelines:
"""
```

#### Recovery Email Generation
```python
RECOVERY_EMAIL_PROMPT = """
Generate a personalized customer recovery email.

Customer Context:
- Name: {customer_name}
- Churn Risk: {churn_risk}
- Recent Issues: {issue_summary}
- Interaction History: {history_summary}

Email Requirements:
- Acknowledge specific issues
- Show genuine empathy
- Offer concrete resolution
- Include appropriate compensation if churn_risk > 0.6
- Professional but warm tone
- Clear next steps

Generate the email content:
"""
```

### LLM Service Implementation

```python
class LLMService:
    def __init__(self):
        self.provider = self._get_provider()  # OpenAI or Gemini
        self.prompt_templates = PromptTemplates()
    
    async def generate_review_response(self, review: Review, 
                                     sentiment: float, 
                                     categories: List[str]) -> str:
        prompt = self.prompt_templates.review_response.format(
            rating=review.rating,
            content=review.content,
            sentiment_score=sentiment,
            categories=", ".join(categories)
        )
        
        response = await self.provider.generate(
            prompt=prompt,
            max_tokens=200,
            temperature=0.7
        )
        
        return self._sanitize_response(response)
    
    async def generate_recovery_email(self, customer: Customer, 
                                    context: dict) -> str:
        prompt = self.prompt_templates.recovery_email.format(
            customer_name=customer.name,
            churn_risk=context["churn_risk"],
            issue_summary=context["issue_summary"],
            history_summary=context.get("history_summary", "")
        )
        
        response = await self.provider.generate(
            prompt=prompt,
            max_tokens=300,
            temperature=0.8
        )
        
        return self._sanitize_response(response)
    
    def _sanitize_response(self, response: str) -> str:
        # Remove any potentially harmful content
        # Ensure compliance with platform policies
        # Validate tone and professionalism
        return response.strip()
```

## Frontend Architecture

### Dashboard Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Header: Logo | Organization | User Menu                      │
├─────────────────────────────────────────────────────────────┤
│ Navigation: Dashboard | Reviews | Customers | Settings       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ KPI Cards Row:                                              │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────┐ │
│ │Avg Rating   │ │Reviews This │ │Customers    │ │Recovery │ │
│ │    4.2★     │ │   Month     │ │  At Risk    │ │ Success │ │
│ │   ↑ 0.3     │ │     127     │ │     23      │ │   78%   │ │
│ └─────────────┘ └─────────────┘ └─────────────┘ └─────────┘ │
│                                                             │
│ Main Content Area:                                          │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Recent Activity Feed                                    │ │
│ │ • New 2★ review requires immediate attention            │ │
│ │ • Recovery email sent to high-risk customer            │ │
│ │ • 5★ review response published                          │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─────────────────────┐ ┌─────────────────────────────────┐ │
│ │ Sentiment Trends    │ │ Action Queue                    │ │
│ │ [Chart showing      │ │ • 3 reviews pending response    │ │
│ │  sentiment over     │ │ • 2 customers need recovery     │ │
│ │  time]              │ │ • 1 case escalated to manager   │ │
│ └─────────────────────┘ └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Component Structure

```typescript
// Next.js App Structure
src/
├── app/
│   ├── (auth)/
│   │   ├── login/
│   │   └── register/
│   ├── dashboard/
│   │   ├── page.tsx
│   │   └── components/
│   ├── reviews/
│   │   ├── page.tsx
│   │   └── [id]/
│   ├── customers/
│   │   ├── page.tsx
│   │   └── [id]/
│   └── settings/
├── components/
│   ├── ui/ (shadcn components)
│   ├── dashboard/
│   │   ├── KPICard.tsx
│   │   ├── ActivityFeed.tsx
│   │   └── SentimentChart.tsx
│   ├── reviews/
│   │   ├── ReviewCard.tsx
│   │   ├── ResponseEditor.tsx
│   │   └── SentimentBadge.tsx
│   └── customers/
│       ├── CustomerCard.tsx
│       ├── RiskIndicator.tsx
│       └── RecoveryActions.tsx
├── lib/
│   ├── api.ts
│   ├── auth.ts
│   └── utils.ts
└── types/
    ├── review.ts
    ├── customer.ts
    └── agent.ts
```

## Correctness Properties

### Property 1: Sentiment Analysis Consistency
**Validates: Requirements 1.1, 1.2**
- For any given review text, sentiment analysis must return consistent scores (±0.05) across multiple runs
- Sentiment scores must be between 0.0 and 1.0
- Reviews with ratings 1-2 should have sentiment scores < 0.4
- Reviews with ratings 4-5 should have sentiment scores > 0.6

### Property 2: Decision Rule Determinism
**Validates: Requirements 2.1, 2.2**
- Given identical input parameters (sentiment, urgency, rating, categories), the agent must always make the same decision
- Critical reviews (rating ≤ 2, urgency = high) must always trigger private recovery
- Positive reviews (rating ≥ 4) must never be escalated unless explicitly flagged

### Property 3: Recovery Action Compliance
**Validates: Requirements 2.3, 3.1**
- All generated responses must be under 500 characters
- No recovery action should promise specific outcomes without approval
- High-risk customers (churn_risk > 0.8) must receive at least 2 recovery actions
- All actions must be logged with timestamps and reasoning

### Property 4: Multi-tenant Data Isolation
**Validates: Requirements 3.2**
- Users can only access data from their organization
- API responses must never contain data from other organizations
- Database queries must always include organization_id filter

### Property 5: Response Generation Safety
**Validates: Requirements 1.3, 3.1**
- Generated responses must not contain profanity or inappropriate language
- Responses must not make commitments beyond defined business rules
- All generated content must be under specified character limits

## Testing Framework

Using **fast-check** for property-based testing with Jest:

```typescript
// Example property test
import fc from 'fast-check';
import { SentimentAnalyzer } from '../src/services/sentiment';

describe('Sentiment Analysis Properties', () => {
  const analyzer = new SentimentAnalyzer();
  
  test('Property: Sentiment scores are consistent', () => {
    fc.assert(fc.property(
      fc.string({ minLength: 10, maxLength: 500 }),
      async (reviewText) => {
        const score1 = await analyzer.analyze(reviewText);
        const score2 = await analyzer.analyze(reviewText);
        
        expect(Math.abs(score1 - score2)).toBeLessThan(0.05);
        expect(score1).toBeGreaterThanOrEqual(0);
        expect(score1).toBeLessThanOrEqual(1);
      }
    ));
  });
});
```

## Deployment Architecture

### Production Stack
- **Backend**: FastAPI on AWS ECS/Fargate
- **Database**: AWS RDS PostgreSQL with pgvector extension
- **Cache**: AWS ElastiCache Redis
- **Frontend**: Next.js on Vercel
- **File Storage**: AWS S3
- **Monitoring**: DataDog/New Relic
- **CI/CD**: GitHub Actions

### Environment Configuration
```yaml
# docker-compose.yml for local development
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/revive_ai
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
  
  db:
    image: pgvector/pgvector:pg15
    environment:
      - POSTGRES_DB=revive_ai
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
```

This design provides a solid foundation for a production-ready MVP that can scale with business growth while maintaining code quality and compliance requirements.