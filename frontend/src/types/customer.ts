export interface Customer {
  id: string;
  name: string;
  email?: string;
  phone?: string;
  total_reviews: number;
  average_rating: number;
  last_review_date: string;
  first_review_date: string;
  risk_score: number;
  risk_level: 'low' | 'medium' | 'high';
  churn_probability: number;
  lifetime_value: number;
  status: 'active' | 'at_risk' | 'churned' | 'recovered';
  tags: string[];
  created_at: string;
  updated_at: string;
  metadata?: {
    location?: string;
    preferred_contact_method?: 'email' | 'phone' | 'sms';
    timezone?: string;
    language?: string;
  };
}

export interface CustomerFilters {
  search?: string;
  risk_level?: string[];
  status?: string[];
  rating_range?: {
    min: number;
    max: number;
  };
  review_count_range?: {
    min: number;
    max: number;
  };
  date_range?: {
    start: string;
    end: string;
  };
  tags?: string[];
}

export interface CustomerSortOptions {
  field:
    | 'name'
    | 'total_reviews'
    | 'average_rating'
    | 'risk_score'
    | 'last_review_date'
    | 'created_at';
  direction: 'asc' | 'desc';
}

export interface CustomersListResponse {
  customers: Customer[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface RecoveryAction {
  id: string;
  customer_id: string;
  type: 'email' | 'phone_call' | 'sms' | 'discount_offer' | 'personal_outreach';
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  priority: 'low' | 'medium' | 'high';
  title: string;
  description: string;
  scheduled_at?: string;
  completed_at?: string;
  created_at: string;
  updated_at: string;
  metadata?: {
    template_id?: string;
    discount_amount?: number;
    contact_person?: string;
    notes?: string;
  };
}

export interface CustomerCommunication {
  id: string;
  customer_id: string;
  type: 'email' | 'phone' | 'sms' | 'review_response' | 'support_ticket';
  direction: 'inbound' | 'outbound';
  subject?: string;
  content: string;
  status: 'sent' | 'delivered' | 'read' | 'replied' | 'failed' | 'completed' | 'resolved';
  created_at: string;
  metadata?: {
    platform?: string;
    review_id?: string;
    ticket_id?: string;
    template_used?: string;
    duration?: string;
    agent?: string;
    campaign?: string;
    priority?: string;
  };
}

export interface CustomerAnalytics {
  total_customers: number;
  at_risk_customers: number;
  churned_customers: number;
  recovered_customers: number;
  average_risk_score: number;
  churn_rate: number;
  recovery_rate: number;
  customer_lifetime_value: number;
}
