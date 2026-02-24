import api from './api';
import {
  Review,
  ReviewFilters,
  ReviewSortOptions,
  ReviewAnalytics,
  ReviewResponse,
} from '@/types/review';

export class ReviewsAPI {
  static async getReviews(
    page: number = 1,
    limit: number = 20,
    filters?: ReviewFilters,
    sort?: ReviewSortOptions,
  ): Promise<{
    reviews: Review[];
    total: number;
    page: number;
    limit: number;
    totalPages: number;
  }> {
    const params = new URLSearchParams({
      page: page.toString(),
      limit: limit.toString(),
    });

    if (filters) {
      if (filters.platform) {
        params.append('platform', filters.platform);
      }
      if (filters.rating) {
        params.append('rating', filters.rating.join(','));
      }
      if (filters.sentiment) {
        params.append('sentiment', filters.sentiment.join(','));
      }
      if (filters.urgency) {
        params.append('urgency', filters.urgency.join(','));
      }
      if (filters.status) {
        params.append('status', filters.status.join(','));
      }
      if (filters.categories) {
        params.append('categories', filters.categories.join(','));
      }
      if (filters.search) {
        params.append('search', filters.search);
      }
      if (filters.dateRange) {
        params.append('start_date', filters.dateRange.start);
        params.append('end_date', filters.dateRange.end);
      }
    }

    if (sort) {
      params.append('sort_by', sort.field);
      params.append('sort_order', sort.direction);
    }

    const response = await api.get(`/reviews?${params.toString()}`);
    return response.data;
  }

  static async getReview(id: string): Promise<Review> {
    const response = await api.get(`/reviews/${id}`);
    return response.data;
  }

  static async updateReviewStatus(id: string, status: Review['status']): Promise<Review> {
    const response = await api.patch(`/reviews/${id}/status`, { status });
    return response.data;
  }

  static async createResponse(reviewId: string, content: string): Promise<ReviewResponse> {
    const response = await api.post(`/reviews/${reviewId}/response`, { content });
    return response.data;
  }

  static async updateResponse(responseId: string, content: string): Promise<ReviewResponse> {
    const response = await api.patch(`/responses/${responseId}`, { content });
    return response.data;
  }

  static async publishResponse(responseId: string): Promise<ReviewResponse> {
    const response = await api.post(`/responses/${responseId}/publish`);
    return response.data;
  }

  static async deleteResponse(responseId: string): Promise<void> {
    await api.delete(`/responses/${responseId}`);
  }

  static async bulkUpdateStatus(reviewIds: string[], status: Review['status']): Promise<void> {
    await api.patch('/reviews/bulk/status', { review_ids: reviewIds, status });
  }

  static async bulkAssignCategory(reviewIds: string[], category: string): Promise<void> {
    await api.patch('/reviews/bulk/category', { review_ids: reviewIds, category });
  }

  static async getAnalytics(filters?: ReviewFilters): Promise<ReviewAnalytics> {
    const params = new URLSearchParams();

    if (filters) {
      if (filters.platform) {
        params.append('platform', filters.platform);
      }
      if (filters.dateRange) {
        params.append('start_date', filters.dateRange.start);
        params.append('end_date', filters.dateRange.end);
      }
    }

    const response = await api.get(`/reviews/analytics?${params.toString()}`);
    return response.data;
  }

  static async generateResponse(reviewId: string): Promise<{ content: string }> {
    const response = await api.post(`/reviews/${reviewId}/generate-response`);
    return response.data;
  }

  static async escalateReview(reviewId: string, reason: string): Promise<Review> {
    const response = await api.post(`/reviews/${reviewId}/escalate`, { reason });
    return response.data;
  }
}
