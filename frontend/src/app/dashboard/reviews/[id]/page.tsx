'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { SentimentBadge } from '@/components/reviews/sentiment-badge';
import { UrgencyIndicator } from '@/components/reviews/urgency-indicator';
import { ReviewResponseEditor } from '@/components/reviews/review-response-editor';
import {
  ArrowLeft,
  ExternalLink,
  MessageSquare,
  Calendar,
  User,
  Tag,
  AlertTriangle,
  CheckCircle,
  Clock,
  Edit,
  Trash2,
} from 'lucide-react';
import { cn, formatDateTime } from '@/lib/utils';
import type { Review } from '@/types/review';
import api from '@/lib/api';

interface ReviewDetailPageProps {
  params: {
    id: string;
  };
}

export default function ReviewDetailPage({ params }: ReviewDetailPageProps) {
  const router = useRouter();
  const [review, setReview] = useState<Review | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showResponseEditor, setShowResponseEditor] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);

  useEffect(() => {
    fetchReview();
  }, [params.id]);

  const fetchReview = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.get(`/reviews/${params.id}`);
      setReview(response.data);
    } catch (err: any) {
      console.error('Error fetching review:', err);
      setError('Failed to load review');

      // Mock data for development
      const mockReview: Review = {
        id: params.id,
        platform: 'google',
        external_id: 'google_123',
        customer_name: 'John Smith',
        rating: 2,
        content:
          'Service was terrible, waited 2 hours for my order. Very disappointed with the quality. The staff seemed overwhelmed and unprofessional. I expected much better from this establishment.',
        sentiment_score: 0.15,
        urgency_level: 'high',
        issue_categories: ['service', 'quality', 'staff'],
        status: 'pending',
        requires_private_recovery: true,
        created_at: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
        updated_at: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
        metadata: {
          location_id: 'loc_123',
          reviewer_profile_url: 'https://google.com/profile/john-smith',
          source: 'google_reviews_api',
        },
      };
      setReview(mockReview);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveResponse = async (content: string) => {
    if (!review) {
      return;
    }

    setIsUpdating(true);
    try {
      const response = await api.post(`/reviews/${review.id}/response`, {
        content,
        action: 'save_draft',
      });

      // Update review with the response from backend
      setReview(response.data);
      setShowResponseEditor(false);
    } catch (error) {
      console.error('Error saving response:', error);
      alert('Failed to save response. Please try again.');
    } finally {
      setIsUpdating(false);
    }
  };

  const handlePublishResponse = async (content: string) => {
    if (!review) {
      return;
    }

    setIsUpdating(true);
    try {
      const response = await api.post(`/reviews/${review.id}/response`, {
        content,
        action: 'publish',
      });

      // Update review with the response from backend
      setReview(response.data);
      setShowResponseEditor(false);
    } catch (error) {
      console.error('Error publishing response:', error);
      alert('Failed to publish response. Please try again.');
    } finally {
      setIsUpdating(false);
    }
  };

  const handleEscalate = async () => {
    if (!review) {
      return;
    }

    setIsUpdating(true);
    try {
      await api.post(`/reviews/${review.id}/escalate`);
      setReview(prev => (prev ? { ...prev, status: 'escalated' } : null));
    } catch (error) {
      console.error('Error escalating review:', error);
    } finally {
      setIsUpdating(false);
    }
  };

  const getPlatformIcon = (platform: string) => {
    return <MessageSquare className='h-5 w-5' />;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'responded':
        return <CheckCircle className='h-5 w-5 text-green-600' />;
      case 'escalated':
        return <AlertTriangle className='h-5 w-5 text-red-600' />;
      default:
        return <Clock className='h-5 w-5 text-yellow-600' />;
    }
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

  if (isLoading) {
    return (
      <div className='px-4 sm:px-6 lg:px-8'>
        <div className='animate-pulse space-y-6'>
          <div className='h-8 bg-gray-200 rounded w-1/4'></div>
          <div className='h-64 bg-gray-200 rounded'></div>
          <div className='h-32 bg-gray-200 rounded'></div>
        </div>
      </div>
    );
  }

  if (error || !review) {
    return (
      <div className='px-4 sm:px-6 lg:px-8'>
        <div className='text-center py-12'>
          <AlertTriangle className='h-12 w-12 text-red-400 mx-auto mb-4' />
          <h2 className='text-lg font-medium text-gray-900 mb-2'>Review Not Found</h2>
          <p className='text-gray-600 mb-4'>
            {error || "The review you're looking for doesn't exist or has been removed."}
          </p>
          <Button onClick={() => router.push('/dashboard/reviews')}>
            <ArrowLeft className='h-4 w-4 mr-1' />
            Back to Reviews
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className='px-4 sm:px-6 lg:px-8'>
      {/* Header */}
      <div className='mb-8'>
        <div className='flex items-center justify-between'>
          <div className='flex items-center space-x-4'>
            <Button variant='outline' size='sm' onClick={() => router.push('/dashboard/reviews')}>
              <ArrowLeft className='h-4 w-4 mr-1' />
              Back to Reviews
            </Button>
            <div>
              <h1 className='text-2xl font-bold text-gray-900'>Review Details</h1>
              <p className='text-sm text-gray-500'>
                {review.platform.charAt(0).toUpperCase() + review.platform.slice(1)} •{' '}
                {formatDateTime(review.created_at)}
              </p>
            </div>
          </div>

          <div className='flex items-center space-x-2'>
            {review.metadata?.reviewer_profile_url && (
              <Button
                variant='outline'
                size='sm'
                onClick={() => window.open(review.metadata?.reviewer_profile_url, '_blank')}
              >
                <ExternalLink className='h-4 w-4 mr-1' />
                View Profile
              </Button>
            )}

            {review.status === 'pending' && (
              <>
                <Button
                  variant='outline'
                  size='sm'
                  onClick={() => setShowResponseEditor(true)}
                  disabled={isUpdating}
                >
                  <Edit className='h-4 w-4 mr-1' />
                  Respond
                </Button>
                <Button variant='outline' size='sm' onClick={handleEscalate} disabled={isUpdating}>
                  <AlertTriangle className='h-4 w-4 mr-1' />
                  Escalate
                </Button>
              </>
            )}
          </div>
        </div>
      </div>

      <div className='grid grid-cols-1 lg:grid-cols-3 gap-8'>
        {/* Main Content */}
        <div className='lg:col-span-2 space-y-6'>
          {/* Review Content */}
          <Card>
            <CardHeader>
              <div className='flex items-center justify-between'>
                <div className='flex items-center space-x-3'>
                  {getPlatformIcon(review.platform)}
                  <div>
                    <CardTitle className='flex items-center space-x-2'>
                      <span>{review.customer_name}</span>
                      <div className='flex items-center'>
                        <span className='text-yellow-500'>
                          {'★'.repeat(review.rating)}
                          {'☆'.repeat(5 - review.rating)}
                        </span>
                        <span className='ml-1 text-sm text-gray-600'>({review.rating}/5)</span>
                      </div>
                    </CardTitle>
                    <CardDescription>
                      {formatDateTime(review.created_at)} •{' '}
                      {review.platform.charAt(0).toUpperCase() + review.platform.slice(1)}
                    </CardDescription>
                  </div>
                </div>

                <div className='flex items-center space-x-2'>
                  {getStatusIcon(review.status)}
                  <span
                    className={cn(
                      'px-3 py-1 rounded-full text-sm font-medium border',
                      getStatusColor(review.status),
                    )}
                  >
                    {review.status.charAt(0).toUpperCase() + review.status.slice(1)}
                  </span>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className='space-y-4'>
                <div>
                  <h4 className='font-medium text-gray-900 mb-2'>Review Content</h4>
                  <p className='text-gray-700 leading-relaxed'>{review.content}</p>
                </div>

                <div className='flex items-center space-x-4'>
                  <SentimentBadge score={review.sentiment_score} />
                  <UrgencyIndicator level={review.urgency_level} />
                </div>

                {review.issue_categories.length > 0 && (
                  <div>
                    <h4 className='font-medium text-gray-900 mb-2'>Issue Categories</h4>
                    <div className='flex flex-wrap gap-2'>
                      {review.issue_categories.map(category => (
                        <span
                          key={category}
                          className='inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800'
                        >
                          <Tag className='h-3 w-3 mr-1' />
                          {category}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Current Response */}
          {review.response && (
            <Card>
              <CardHeader>
                <CardTitle className='flex items-center justify-between'>
                  <span>Response</span>
                  <span
                    className={cn(
                      'px-2 py-1 rounded-full text-xs font-medium',
                      review.response.status === 'published'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-yellow-100 text-yellow-800',
                    )}
                  >
                    {review.response.status}
                  </span>
                </CardTitle>
                <CardDescription>
                  {review.response.status === 'published' && review.response.published_at
                    ? `Published ${formatDateTime(review.response.published_at)}`
                    : `Draft saved ${formatDateTime(review.response.created_at)}`}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className='text-gray-700 leading-relaxed'>{review.response.content}</p>

                {review.response.status === 'draft' && (
                  <div className='mt-4 flex items-center space-x-2'>
                    <Button
                      size='sm'
                      onClick={() => setShowResponseEditor(true)}
                      disabled={isUpdating}
                    >
                      <Edit className='h-4 w-4 mr-1' />
                      Edit Response
                    </Button>
                    <Button
                      variant='outline'
                      size='sm'
                      onClick={() => handlePublishResponse(review.response!.content)}
                      disabled={isUpdating}
                    >
                      <CheckCircle className='h-4 w-4 mr-1' />
                      Publish Now
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Response Editor */}
          {showResponseEditor && (
            <ReviewResponseEditor
              review={review}
              onSave={handleSaveResponse}
              onPublish={handlePublishResponse}
              onCancel={() => setShowResponseEditor(false)}
              initialContent={review.response?.content || ''}
              isLoading={isUpdating}
            />
          )}
        </div>

        {/* Sidebar */}
        <div className='space-y-6'>
          {/* Review Metadata */}
          <Card>
            <CardHeader>
              <CardTitle>Review Information</CardTitle>
            </CardHeader>
            <CardContent className='space-y-4'>
              <div className='flex items-center space-x-3'>
                <User className='h-4 w-4 text-gray-400' />
                <div>
                  <p className='text-sm font-medium text-gray-900'>{review.customer_name}</p>
                  <p className='text-xs text-gray-500'>Customer</p>
                </div>
              </div>

              <div className='flex items-center space-x-3'>
                <Calendar className='h-4 w-4 text-gray-400' />
                <div>
                  <p className='text-sm font-medium text-gray-900'>
                    {formatDateTime(review.created_at)}
                  </p>
                  <p className='text-xs text-gray-500'>Review Date</p>
                </div>
              </div>

              <div className='flex items-center space-x-3'>
                {getPlatformIcon(review.platform)}
                <div>
                  <p className='text-sm font-medium text-gray-900 capitalize'>{review.platform}</p>
                  <p className='text-xs text-gray-500'>Platform</p>
                </div>
              </div>

              {review.external_id && (
                <div className='flex items-center space-x-3'>
                  <ExternalLink className='h-4 w-4 text-gray-400' />
                  <div>
                    <p className='text-sm font-medium text-gray-900 font-mono'>
                      {review.external_id}
                    </p>
                    <p className='text-xs text-gray-500'>External ID</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Analysis Results */}
          <Card>
            <CardHeader>
              <CardTitle>AI Analysis</CardTitle>
            </CardHeader>
            <CardContent className='space-y-4'>
              <div>
                <p className='text-sm font-medium text-gray-900 mb-1'>Sentiment Score</p>
                <div className='flex items-center space-x-2'>
                  <div className='flex-1 bg-gray-200 rounded-full h-2'>
                    <div
                      className={cn(
                        'h-2 rounded-full',
                        review.sentiment_score >= 0.7
                          ? 'bg-green-500'
                          : review.sentiment_score >= 0.4
                            ? 'bg-yellow-500'
                            : 'bg-red-500',
                      )}
                      style={{ width: `${review.sentiment_score * 100}%` }}
                    />
                  </div>
                  <span className='text-sm text-gray-600'>
                    {Math.round(review.sentiment_score * 100)}%
                  </span>
                </div>
              </div>

              <div>
                <p className='text-sm font-medium text-gray-900 mb-2'>Priority Level</p>
                <UrgencyIndicator level={review.urgency_level} />
              </div>

              <div>
                <p className='text-sm font-medium text-gray-900 mb-1'>Recovery Required</p>
                <p className='text-sm text-gray-600'>
                  {review.requires_private_recovery
                    ? 'Yes - Private outreach recommended'
                    : 'No - Public response sufficient'}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className='space-y-2'>
              {review.status === 'pending' && (
                <>
                  <Button
                    variant='outline'
                    className='w-full justify-start'
                    onClick={() => setShowResponseEditor(true)}
                    disabled={isUpdating}
                  >
                    <Edit className='h-4 w-4 mr-2' />
                    Write Response
                  </Button>
                  <Button
                    variant='outline'
                    className='w-full justify-start'
                    onClick={handleEscalate}
                    disabled={isUpdating}
                  >
                    <AlertTriangle className='h-4 w-4 mr-2' />
                    Escalate to Manager
                  </Button>
                </>
              )}

              <Button
                variant='outline'
                className='w-full justify-start'
                onClick={() => router.push(`/dashboard/customers?search=${review.customer_name}`)}
              >
                <User className='h-4 w-4 mr-2' />
                View Customer Profile
              </Button>

              {review.metadata?.reviewer_profile_url && (
                <Button
                  variant='outline'
                  className='w-full justify-start'
                  onClick={() => window.open(review.metadata?.reviewer_profile_url, '_blank')}
                >
                  <ExternalLink className='h-4 w-4 mr-2' />
                  View on {review.platform.charAt(0).toUpperCase() + review.platform.slice(1)}
                </Button>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {error && (
        <div className='mt-8 bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded-md'>
          <p className='text-sm'>{error} - Showing sample data for demonstration</p>
        </div>
      )}
    </div>
  );
}
