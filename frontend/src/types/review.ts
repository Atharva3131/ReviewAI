export interface Review {
  id: string;
  platform: string;
  external_id: string;
  customer_name: string;
  rating: number;
  content: string;
  sentiment_score: number;
  urgency_level: 'low' | 'medium' | 'high';
  issue_categories: string[];
  status: 'pending' | 'responded' | 'escalated';
  requires_private_recovery: boolean;
  created_at: string;
  updated_at: string;
  response?: ReviewResponse;
  metadata?: {
    location_id?: string;
    reviewer_profile_url?: string;
    source?: string;
  };
}

export interface ReviewResponse {
  id: string;
  review_id: string;
  content: string;
  status: 'draft' | 'published' | 'failed';
  created_at: string;
  published_at?: string;
}

export interface ReviewFilters {
  platform?: string;
  rating?: number[];
  sentiment?: number[];
  urgency?: string[];
  status?: string[];
  categories?: string[];
  dateRange?: {
    start: string;
    end: string;
  };
  date_range?: {
    start: string;
    end: string;
  };
  search?: string;
}

export interface ReviewSortOptions {
  field: 'created_at' | 'rating' | 'sentiment_score' | 'urgency_level';
  direction: 'asc' | 'desc';
}

export interface ReviewsListResponse {
  reviews: Review[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface ReviewAnalytics {
  total_reviews: number;
  average_rating: number;
  sentiment_distribution: {
    positive: number;
    neutral: number;
    negative: number;
  };
  platform_breakdown: Record<string, number>;
  urgency_breakdown: Record<string, number>;
  response_rate: number;
}
