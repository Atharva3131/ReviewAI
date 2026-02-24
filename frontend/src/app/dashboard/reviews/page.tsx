'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { SentimentBadge } from '@/components/reviews/sentiment-badge';
import { UrgencyIndicator } from '@/components/reviews/urgency-indicator';
import {
  Search,
  Filter,
  SortAsc,
  SortDesc,
  MessageSquare,
  Star,
  Calendar,
  ExternalLink,
  MoreHorizontal,
  RefreshCw,
  CheckSquare,
  Square,
  BarChart,
  Trash2,
} from 'lucide-react';
import { cn, formatDateTime } from '@/lib/utils';
import type { Review, ReviewFilters, ReviewSortOptions, ReviewsListResponse } from '@/types/review';
import api from '@/lib/api';

const PLATFORMS = ['google', 'yelp', 'facebook', 'tripadvisor'];
const RATINGS = [1, 2, 3, 4, 5];
const URGENCY_LEVELS = ['low', 'medium', 'high'];
const STATUSES = ['pending', 'responded', 'escalated'];

export default function ReviewsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [reviews, setReviews] = useState<Review[]>([]);
  const [totalReviews, setTotalReviews] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedReviews, setSelectedReviews] = useState<Set<string>>(new Set());
  const [bulkActionModalOpen, setBulkActionModalOpen] = useState(false);
  const [bulkActionType, setBulkActionType] = useState<'respond' | 'escalate' | null>(null);
  const [bulkResponseContent, setBulkResponseContent] = useState('');

  // Filters and sorting
  const [filters, setFilters] = useState<ReviewFilters>({
    search: searchParams.get('search') || '',
    platform: searchParams.get('platform') || undefined,
    rating: searchParams.get('rating')?.split(',').map(Number) || undefined,
    urgency: searchParams.get('urgency')?.split(',') || undefined,
    status: searchParams.get('status')?.split(',') || undefined,
  });

  const [sortOptions, setSortOptions] = useState<ReviewSortOptions>({
    field: (searchParams.get('sort') as any) || 'created_at',
    direction: (searchParams.get('order') as any) || 'desc',
  });

  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    fetchReviews();
  }, [currentPage, filters, sortOptions]);

  const fetchReviews = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      params.set('page', currentPage.toString());
      params.set('per_page', '20');
      params.set('sort', sortOptions.field);
      params.set('order', sortOptions.direction);

      if (filters.search) {
        params.set('search', filters.search);
      }
      if (filters.platform) {
        params.set('platform', filters.platform);
      }
      if (filters.rating?.length) {
        params.set('rating', filters.rating.join(','));
      }
      if (filters.urgency?.length) {
        params.set('urgency', filters.urgency.join(','));
      }
      if (filters.status?.length) {
        params.set('status', filters.status.join(','));
      }

      const response = await api.get(`/reviews?${params.toString()}`);

      // Backend returns a simple array, not a paginated response
      const reviewsData = Array.isArray(response.data) ? response.data : [];

      setReviews(reviewsData);
      setTotalReviews(reviewsData.length);
      setTotalPages(1); // No pagination from backend yet
    } catch (err: any) {
      console.error('Error fetching reviews:', err);
      setError('Failed to load reviews');

      // Mock data for development
      const mockReviews: Review[] = [
        {
          id: '1',
          platform: 'google',
          external_id: 'google_123',
          customer_name: 'John Smith',
          rating: 2,
          content:
            'Service was terrible, waited 2 hours for my order. Very disappointed with the quality.',
          sentiment_score: 0.15,
          urgency_level: 'high',
          issue_categories: ['service', 'quality'],
          status: 'pending',
          requires_private_recovery: true,
          created_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
          updated_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
        },
        {
          id: '2',
          platform: 'yelp',
          external_id: 'yelp_456',
          customer_name: 'Sarah Johnson',
          rating: 5,
          content:
            'Amazing experience! The staff was friendly and the food was delicious. Highly recommend!',
          sentiment_score: 0.92,
          urgency_level: 'low',
          issue_categories: ['service', 'quality'],
          status: 'responded',
          requires_private_recovery: false,
          created_at: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
          updated_at: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
          response: {
            id: 'resp_1',
            review_id: '2',
            content:
              "Thank you so much for your wonderful review! We're thrilled you enjoyed your experience.",
            status: 'published',
            created_at: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
            published_at: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
          },
        },
        {
          id: '3',
          platform: 'google',
          external_id: 'google_789',
          customer_name: 'Mike Davis',
          rating: 3,
          content: 'Food was okay, nothing special. Service could be improved.',
          sentiment_score: 0.45,
          urgency_level: 'medium',
          issue_categories: ['service'],
          status: 'pending',
          requires_private_recovery: false,
          created_at: new Date(Date.now() - 1000 * 60 * 60 * 4).toISOString(),
          updated_at: new Date(Date.now() - 1000 * 60 * 60 * 4).toISOString(),
        },
      ];

      setReviews(mockReviews);
      setTotalReviews(mockReviews.length);
      setTotalPages(1);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFilterChange = (key: keyof ReviewFilters, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setCurrentPage(1);
  };

  const handleSortChange = (field: ReviewSortOptions['field']) => {
    setSortOptions(prev => ({
      field,
      direction: prev.field === field && prev.direction === 'desc' ? 'asc' : 'desc',
    }));
  };

  const handleSelectReview = (reviewId: string) => {
    setSelectedReviews(prev => {
      const newSet = new Set(prev);
      if (newSet.has(reviewId)) {
        newSet.delete(reviewId);
      } else {
        newSet.add(reviewId);
      }
      return newSet;
    });
  };

  const handleSelectAll = () => {
    if (selectedReviews.size === (reviews?.length || 0)) {
      setSelectedReviews(new Set());
    } else {
      setSelectedReviews(new Set(reviews?.map(r => r.id) || []));
    }
  };

  const handleBulkAction = async (action: 'respond' | 'escalate' | 'export') => {
    if (selectedReviews.size === 0) {
      return;
    }

    setIsLoading(true);
    try {
      const reviewIds = Array.from(selectedReviews);

      switch (action) {
        case 'respond':
          // Open bulk response modal
          setBulkActionType('respond');
          setBulkActionModalOpen(true);
          break;

        case 'escalate':
          await api.post('/reviews/bulk-escalate', { review_ids: reviewIds });
          // Update local state
          setReviews(prev =>
            prev.map(review =>
              selectedReviews.has(review.id) ? { ...review, status: 'escalated' as const } : review,
            ),
          );
          setSelectedReviews(new Set());
          break;

        case 'export':
          const response = await api.post('/reviews/export', {
            review_ids: reviewIds,
            format: 'csv',
          });
          // Download the file
          const blob = new Blob([response.data], { type: 'text/csv' });
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `reviews-export-${new Date().toISOString().split('T')[0]}.csv`;
          document.body.appendChild(a);
          a.click();
          window.URL.revokeObjectURL(url);
          document.body.removeChild(a);
          break;
      }
    } catch (error) {
      console.error(`Error performing bulk ${action}:`, error);
      // Show error message to user
    } finally {
      setIsLoading(false);
    }
  };

  const handleBulkResponse = async (responseContent: string) => {
    if (selectedReviews.size === 0) {
      return;
    }

    setIsLoading(true);
    try {
      const reviewIds = Array.from(selectedReviews);
      await api.post('/reviews/bulk-respond', {
        review_ids: reviewIds,
        response_content: responseContent,
      });

      // Update local state
      setReviews(prev =>
        prev.map(review =>
          selectedReviews.has(review.id)
            ? {
                ...review,
                status: 'responded' as const,
                response: {
                  id: `bulk_${Date.now()}`,
                  review_id: review.id,
                  content: responseContent,
                  status: 'published' as const,
                  created_at: new Date().toISOString(),
                  published_at: new Date().toISOString(),
                },
              }
            : review,
        ),
      );

      setSelectedReviews(new Set());
      setBulkActionModalOpen(false);
    } catch (error) {
      console.error('Error sending bulk responses:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleViewReview = (reviewId: string) => {
    router.push(`/dashboard/reviews/${reviewId}`);
  };

  const handleDeleteReview = async (reviewId: string) => {
    if (!confirm('Are you sure you want to delete this review? This action cannot be undone.')) {
      return;
    }

    setIsLoading(true);
    try {
      await api.delete(`/reviews/${reviewId}`);

      // Remove from local state
      setReviews(prev => prev.filter(r => r.id !== reviewId));
      setTotalReviews(prev => prev - 1);

      // Show success message (you could add a toast notification here)
      console.log('Review deleted successfully');
    } catch (error) {
      console.error('Error deleting review:', error);
      alert('Failed to delete review. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const getPlatformIcon = (platform: string) => {
    // In a real app, you'd have platform-specific icons
    return <MessageSquare className='h-4 w-4' />;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'responded':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'escalated':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    }
  };

  if (isLoading && (!reviews || reviews.length === 0)) {
    return (
      <div className='px-4 sm:px-6 lg:px-8'>
        <div className='animate-pulse space-y-4'>
          <div className='h-8 bg-gray-200 rounded w-1/4'></div>
          <div className='h-12 bg-gray-200 rounded'></div>
          {[...Array(5)].map((_, i) => (
            <div key={i} className='h-32 bg-gray-200 rounded'></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className='px-4 sm:px-6 lg:px-8'>
      {/* Header */}
      <div className='mb-8'>
        <div className='flex items-center justify-between'>
          <div>
            <h1 className='text-2xl font-bold text-gray-900'>Reviews</h1>
            <p className='mt-1 text-sm text-gray-500'>
              Manage and respond to customer reviews across all platforms
            </p>
          </div>
          <div className='flex items-center space-x-2'>
            <Button size='sm' onClick={() => router.push('/dashboard/reviews/new')}>
              <MessageSquare className='h-4 w-4 mr-1' />
              Add Review
            </Button>
            <Button
              variant='outline'
              size='sm'
              onClick={() => router.push('/dashboard/reviews/analytics')}
            >
              <BarChart className='h-4 w-4 mr-1' />
              Analytics
            </Button>
            <Button variant='outline' size='sm' onClick={fetchReviews} disabled={isLoading}>
              <RefreshCw className={cn('h-4 w-4 mr-1', isLoading && 'animate-spin')} />
              Refresh
            </Button>
          </div>
        </div>
      </div>

      {/* Search and Filters */}
      <Card className='mb-6'>
        <CardContent className='p-4'>
          <div className='flex items-center space-x-4'>
            <div className='flex-1'>
              <div className='relative'>
                <Search className='absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400' />
                <Input
                  placeholder='Search reviews...'
                  value={filters.search || ''}
                  onChange={e => handleFilterChange('search', e.target.value)}
                  className='pl-10'
                />
              </div>
            </div>
            <Button variant='outline' onClick={() => setShowFilters(!showFilters)}>
              <Filter className='h-4 w-4 mr-1' />
              Filters
            </Button>
          </div>

          {showFilters && (
            <div className='mt-4 pt-4 border-t grid grid-cols-1 md:grid-cols-4 gap-4'>
              {/* Platform Filter */}
              <div>
                <Label className='text-sm font-medium'>Platform</Label>
                <select
                  value={filters.platform || ''}
                  onChange={e => handleFilterChange('platform', e.target.value || undefined)}
                  className='mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm'
                >
                  <option value=''>All Platforms</option>
                  {PLATFORMS.map(platform => (
                    <option key={platform} value={platform}>
                      {platform.charAt(0).toUpperCase() + platform.slice(1)}
                    </option>
                  ))}
                </select>
              </div>

              {/* Rating Filter */}
              <div>
                <Label className='text-sm font-medium'>Rating</Label>
                <div className='mt-1 flex flex-wrap gap-1'>
                  {RATINGS.map(rating => (
                    <button
                      key={rating}
                      onClick={() => {
                        const currentRatings = filters.rating || [];
                        const newRatings = currentRatings.includes(rating)
                          ? currentRatings.filter(r => r !== rating)
                          : [...currentRatings, rating];
                        handleFilterChange('rating', newRatings.length ? newRatings : undefined);
                      }}
                      className={cn(
                        'px-2 py-1 text-xs rounded border',
                        filters.rating?.includes(rating)
                          ? 'bg-blue-100 text-blue-800 border-blue-200'
                          : 'bg-gray-100 text-gray-700 border-gray-200',
                      )}
                    >
                      {rating}★
                    </button>
                  ))}
                </div>
              </div>

              {/* Urgency Filter */}
              <div>
                <Label className='text-sm font-medium'>Urgency</Label>
                <div className='mt-1 flex flex-wrap gap-1'>
                  {URGENCY_LEVELS.map(urgency => (
                    <button
                      key={urgency}
                      onClick={() => {
                        const currentUrgency = filters.urgency || [];
                        const newUrgency = currentUrgency.includes(urgency)
                          ? currentUrgency.filter(u => u !== urgency)
                          : [...currentUrgency, urgency];
                        handleFilterChange('urgency', newUrgency.length ? newUrgency : undefined);
                      }}
                      className={cn(
                        'px-2 py-1 text-xs rounded border capitalize',
                        filters.urgency?.includes(urgency)
                          ? 'bg-blue-100 text-blue-800 border-blue-200'
                          : 'bg-gray-100 text-gray-700 border-gray-200',
                      )}
                    >
                      {urgency}
                    </button>
                  ))}
                </div>
              </div>

              {/* Status Filter */}
              <div>
                <Label className='text-sm font-medium'>Status</Label>
                <div className='mt-1 flex flex-wrap gap-1'>
                  {STATUSES.map(status => (
                    <button
                      key={status}
                      onClick={() => {
                        const currentStatus = filters.status || [];
                        const newStatus = currentStatus.includes(status)
                          ? currentStatus.filter(s => s !== status)
                          : [...currentStatus, status];
                        handleFilterChange('status', newStatus.length ? newStatus : undefined);
                      }}
                      className={cn(
                        'px-2 py-1 text-xs rounded border capitalize',
                        filters.status?.includes(status)
                          ? 'bg-blue-100 text-blue-800 border-blue-200'
                          : 'bg-gray-100 text-gray-700 border-gray-200',
                      )}
                    >
                      {status}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Bulk Actions */}
      {selectedReviews.size > 0 && (
        <Card className='mb-4'>
          <CardContent className='p-4'>
            <div className='flex items-center justify-between'>
              <span className='text-sm text-gray-600'>
                {selectedReviews.size} review{selectedReviews.size !== 1 ? 's' : ''} selected
              </span>
              <div className='flex items-center space-x-2'>
                <Button
                  variant='outline'
                  size='sm'
                  onClick={() => handleBulkAction('respond')}
                  disabled={isLoading}
                >
                  Bulk Respond
                </Button>
                <Button
                  variant='outline'
                  size='sm'
                  onClick={() => handleBulkAction('escalate')}
                  disabled={isLoading}
                >
                  Mark as Escalated
                </Button>
                <Button
                  variant='outline'
                  size='sm'
                  onClick={() => handleBulkAction('export')}
                  disabled={isLoading}
                >
                  Export Selected
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Reviews List */}
      <div className='space-y-4'>
        {/* Table Header */}
        <div className='bg-gray-50 px-4 py-3 rounded-lg'>
          <div className='flex items-center space-x-4'>
            <button onClick={handleSelectAll} className='flex items-center'>
              {selectedReviews.size === (reviews || []).length ? (
                <CheckSquare className='h-4 w-4 text-blue-600' />
              ) : (
                <Square className='h-4 w-4 text-gray-400' />
              )}
            </button>

            <div className='flex-1 grid grid-cols-12 gap-4 text-sm font-medium text-gray-700'>
              <div className='col-span-3'>
                <button
                  onClick={() => handleSortChange('created_at')}
                  className='flex items-center hover:text-gray-900'
                >
                  Review
                  {sortOptions.field === 'created_at' &&
                    (sortOptions.direction === 'desc' ? (
                      <SortDesc className='h-4 w-4 ml-1' />
                    ) : (
                      <SortAsc className='h-4 w-4 ml-1' />
                    ))}
                </button>
              </div>
              <div className='col-span-2'>
                <button
                  onClick={() => handleSortChange('rating')}
                  className='flex items-center hover:text-gray-900'
                >
                  Rating
                  {sortOptions.field === 'rating' &&
                    (sortOptions.direction === 'desc' ? (
                      <SortDesc className='h-4 w-4 ml-1' />
                    ) : (
                      <SortAsc className='h-4 w-4 ml-1' />
                    ))}
                </button>
              </div>
              <div className='col-span-2'>
                <button
                  onClick={() => handleSortChange('sentiment_score')}
                  className='flex items-center hover:text-gray-900'
                >
                  Sentiment
                  {sortOptions.field === 'sentiment_score' &&
                    (sortOptions.direction === 'desc' ? (
                      <SortDesc className='h-4 w-4 ml-1' />
                    ) : (
                      <SortAsc className='h-4 w-4 ml-1' />
                    ))}
                </button>
              </div>
              <div className='col-span-2'>
                <button
                  onClick={() => handleSortChange('urgency_level')}
                  className='flex items-center hover:text-gray-900'
                >
                  Urgency
                  {sortOptions.field === 'urgency_level' &&
                    (sortOptions.direction === 'desc' ? (
                      <SortDesc className='h-4 w-4 ml-1' />
                    ) : (
                      <SortAsc className='h-4 w-4 ml-1' />
                    ))}
                </button>
              </div>
              <div className='col-span-2'>Status</div>
              <div className='col-span-1'>Actions</div>
            </div>
          </div>
        </div>

        {/* Reviews */}
        {(reviews || []).map(review => (
          <Card key={review.id} className='hover:shadow-md transition-shadow'>
            <CardContent className='p-4'>
              <div className='flex items-start space-x-4'>
                <button onClick={() => handleSelectReview(review.id)} className='mt-1'>
                  {selectedReviews.has(review.id) ? (
                    <CheckSquare className='h-4 w-4 text-blue-600' />
                  ) : (
                    <Square className='h-4 w-4 text-gray-400' />
                  )}
                </button>

                <div className='flex-1 grid grid-cols-12 gap-4'>
                  {/* Review Content */}
                  <div className='col-span-3'>
                    <div className='flex items-center space-x-2 mb-2'>
                      {getPlatformIcon(review.platform)}
                      <span className='font-medium text-gray-900'>{review.customer_name}</span>
                    </div>
                    <p className='text-sm text-gray-600 line-clamp-2'>{review.content}</p>
                    <p className='text-xs text-gray-500 mt-1'>
                      {formatDateTime(review.created_at)}
                    </p>
                  </div>

                  {/* Rating */}
                  <div className='col-span-2'>
                    <div className='flex items-center space-x-1'>
                      <span className='text-yellow-500'>
                        {'★'.repeat(review.rating)}
                        {'☆'.repeat(5 - review.rating)}
                      </span>
                      <span className='text-sm text-gray-600'>({review.rating})</span>
                    </div>
                  </div>

                  {/* Sentiment */}
                  <div className='col-span-2'>
                    <SentimentBadge score={review.sentiment_score} size='sm' />
                  </div>

                  {/* Urgency */}
                  <div className='col-span-2'>
                    <UrgencyIndicator level={review.urgency_level} size='sm' />
                  </div>

                  {/* Status */}
                  <div className='col-span-2'>
                    <span
                      className={cn(
                        'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border',
                        getStatusColor(review.status),
                      )}
                    >
                      {review.status}
                    </span>
                    {review.response && (
                      <p className='text-xs text-gray-500 mt-1'>
                        Responded {formatDateTime(review.response.created_at)}
                      </p>
                    )}
                  </div>

                  {/* Actions */}
                  <div className='col-span-1 flex items-center space-x-1'>
                    <Button
                      variant='ghost'
                      size='sm'
                      onClick={() => handleViewReview(review.id)}
                      title='View details'
                    >
                      <ExternalLink className='h-4 w-4' />
                    </Button>
                    <Button
                      variant='ghost'
                      size='sm'
                      onClick={() => handleDeleteReview(review.id)}
                      className='text-red-600 hover:text-red-700 hover:bg-red-50'
                      title='Delete review'
                    >
                      <Trash2 className='h-4 w-4' />
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}

        {/* Empty State */}
        {!isLoading && (!reviews || reviews.length === 0) && (
          <div className='text-center py-12'>
            <MessageSquare className='mx-auto h-12 w-12 text-gray-400' />
            <h3 className='mt-2 text-sm font-medium text-gray-900'>No reviews found</h3>
            <p className='mt-1 text-sm text-gray-500'>
              {filters.search ||
              filters.platform ||
              filters.rating ||
              filters.urgency ||
              filters.status
                ? 'Try adjusting your filters'
                : 'Reviews will appear here once they are ingested'}
            </p>
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className='mt-8 flex items-center justify-between'>
          <p className='text-sm text-gray-700'>
            Showing {(currentPage - 1) * 20 + 1} to {Math.min(currentPage * 20, totalReviews)} of{' '}
            {totalReviews} reviews
          </p>
          <div className='flex items-center space-x-2'>
            <Button
              variant='outline'
              size='sm'
              onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
              disabled={currentPage === 1}
            >
              Previous
            </Button>
            <span className='text-sm text-gray-600'>
              Page {currentPage} of {totalPages}
            </span>
            <Button
              variant='outline'
              size='sm'
              onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
              disabled={currentPage === totalPages}
            >
              Next
            </Button>
          </div>
        </div>
      )}

      {error && (
        <div className='mt-4 bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded-md'>
          <p className='text-sm'>{error} - Showing sample data for demonstration</p>
        </div>
      )}

      {/* Bulk Response Modal */}
      {bulkActionModalOpen && bulkActionType === 'respond' && (
        <div className='fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50'>
          <div className='bg-white rounded-lg p-6 w-full max-w-2xl mx-4'>
            <div className='flex items-center justify-between mb-4'>
              <h3 className='text-lg font-medium text-gray-900'>
                Bulk Response ({selectedReviews.size} reviews)
              </h3>
              <Button variant='ghost' size='sm' onClick={() => setBulkActionModalOpen(false)}>
                ×
              </Button>
            </div>

            <div className='space-y-4'>
              <div>
                <Label htmlFor='bulk-response'>Response Message</Label>
                <textarea
                  id='bulk-response'
                  className='w-full mt-1 p-3 border border-gray-300 rounded-md resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                  rows={4}
                  placeholder='Enter your response that will be sent to all selected reviews...'
                  onChange={e => setBulkResponseContent(e.target.value)}
                  value={bulkResponseContent}
                />
                <p className='text-sm text-gray-500 mt-1'>
                  This response will be published to all {selectedReviews.size} selected reviews.
                </p>
              </div>

              <div className='flex items-center justify-end space-x-2'>
                <Button
                  variant='outline'
                  onClick={() => setBulkActionModalOpen(false)}
                  disabled={isLoading}
                >
                  Cancel
                </Button>
                <Button
                  onClick={() => handleBulkResponse(bulkResponseContent)}
                  disabled={isLoading || !bulkResponseContent.trim()}
                >
                  {isLoading ? 'Sending...' : `Send to ${selectedReviews.size} Reviews`}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
