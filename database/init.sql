-- Initialize Revive AI Database with pgvector extension

-- Create the database (run this as superuser)
-- CREATE DATABASE revive_ai;

-- Connect to the database and create extension
\c revive_ai;

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create custom types
CREATE TYPE urgency_level AS ENUM ('low', 'medium', 'high');
CREATE TYPE review_status AS ENUM ('pending', 'responded', 'escalated');
CREATE TYPE ticket_status AS ENUM ('open', 'in_progress', 'resolved', 'closed');
CREATE TYPE ticket_priority AS ENUM ('low', 'medium', 'high', 'critical');
CREATE TYPE action_type AS ENUM ('email', 'sms', 'call', 'discount', 'escalate');
CREATE TYPE action_status AS ENUM ('pending', 'sent', 'failed', 'completed');
CREATE TYPE decision_type AS ENUM ('respond_public', 'recover_private', 'escalate', 'no_action');
CREATE TYPE user_role AS ENUM ('admin', 'manager', 'user');

-- Create indexes for performance
-- These will be created by the application, but listed here for reference

-- Reviews table indexes
-- CREATE INDEX idx_reviews_organization_id ON reviews(organization_id);
-- CREATE INDEX idx_reviews_platform ON reviews(platform);
-- CREATE INDEX idx_reviews_rating ON reviews(rating);
-- CREATE INDEX idx_reviews_sentiment_score ON reviews(sentiment_score);
-- CREATE INDEX idx_reviews_created_at ON reviews(created_at);
-- CREATE INDEX idx_reviews_status ON reviews(status);

-- Customers table indexes
-- CREATE INDEX idx_customers_organization_id ON customers(organization_id);
-- CREATE INDEX idx_customers_email ON customers(email);
-- CREATE INDEX idx_customers_churn_risk_score ON customers(churn_risk_score);

-- Support tickets table indexes
-- CREATE INDEX idx_support_tickets_organization_id ON support_tickets(organization_id);
-- CREATE INDEX idx_support_tickets_customer_id ON support_tickets(customer_id);
-- CREATE INDEX idx_support_tickets_status ON support_tickets(status);
-- CREATE INDEX idx_support_tickets_priority ON support_tickets(priority);

-- Recovery actions table indexes
-- CREATE INDEX idx_recovery_actions_organization_id ON recovery_actions(organization_id);
-- CREATE INDEX idx_recovery_actions_customer_id ON recovery_actions(customer_id);
-- CREATE INDEX idx_recovery_actions_status ON recovery_actions(status);
-- CREATE INDEX idx_recovery_actions_scheduled_at ON recovery_actions(scheduled_at);

-- Vector embeddings indexes
-- CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops);

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL PRIVILEGES ON DATABASE revive_ai TO revive_ai_user;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO revive_ai_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO revive_ai_user;