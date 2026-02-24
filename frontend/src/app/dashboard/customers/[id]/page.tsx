'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  RiskIndicator,
  ChurnProbability,
  CustomerStatusBadge,
} from '@/components/customers/risk-indicator';
import { RecoveryActionsTimeline } from '@/components/customers/recovery-actions-timeline';
import { CommunicationHistory } from '@/components/customers/communication-history';
import {
  ArrowLeft,
  ExternalLink,
  Users,
  Calendar,
  Mail,
  Phone,
  MessageSquare,
  Star,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Edit,
  Tag,
  BarChart,
  Clock,
  DollarSign,
  Activity,
} from 'lucide-react';
import { cn, formatDateTime } from '@/lib/utils';
import type { Customer, RecoveryAction, CustomerCommunication } from '@/types/customer';
import type { Review } from '@/types/review';
import api from '@/lib/api';

interface CustomerDetailPageProps {
  params: {
    id: string;
  };
}

export default function CustomerDetailPage({ params }: CustomerDetailPageProps) {
  const router = useRouter();
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [recentReviews, setRecentReviews] = useState<Review[]>([]);
  const [recoveryActions, setRecoveryActions] = useState<RecoveryAction[]>([]);
  const [communications, setCommunications] = useState<CustomerCommunication[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);

  useEffect(() => {
    fetchCustomerData();
  }, [params.id]);

  const fetchCustomerData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Fetch customer details
      const customerResponse = await api.get(`/customers/${params.id}`);
      setCustomer(customerResponse.data);

      // Fetch related data
      const [reviewsResponse, actionsResponse, communicationsResponse] = await Promise.all([
        api.get(`/customers/${params.id}/reviews?limit=5`),
        api.get(`/customers/${params.id}/recovery-actions`),
        api.get(`/customers/${params.id}/communications?limit=10`),
      ]);

      setRecentReviews(reviewsResponse.data.reviews || []);
      setRecoveryActions(actionsResponse.data.actions || []);
      setCommunications(communicationsResponse.data.communications || []);
    } catch (err: any) {
      console.error('Error fetching customer data:', err);
      setError('Failed to load customer data');

      // Mock data for development
      const mockCustomer: Customer = {
        id: params.id,
        name: 'John Smith',
        email: 'john.smith@email.com',
        phone: '+1-555-0123',
        total_reviews: 8,
        average_rating: 2.1,
        last_review_date: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2).toISOString(),
        first_review_date: new Date(Date.now() - 1000 * 60 * 60 * 24 * 180).toISOString(),
        risk_score: 0.85,
        risk_level: 'high',
        churn_probability: 0.92,
        lifetime_value: 1250,
        status: 'at_risk',
        tags: ['vip', 'frequent_complainer', 'high_value'],
        created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 200).toISOString(),
        updated_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2).toISOString(),
        metadata: {
          location: 'New York, NY',
          preferred_contact_method: 'email',
          timezone: 'America/New_York',
          language: 'en',
        },
      };

      const mockReviews: Review[] = [
        {
          id: '1',
          platform: 'google',
          external_id: 'google_123',
          customer_name: 'John Smith',
          rating: 1,
          content: 'Terrible service, waited 2 hours for my order. Very disappointed.',
          sentiment_score: 0.1,
          urgency_level: 'high',
          issue_categories: ['service', 'wait_time'],
          status: 'pending',
          requires_private_recovery: true,
          created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2).toISOString(),
          updated_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2).toISOString(),
        },
        {
          id: '2',
          platform: 'yelp',
          external_id: 'yelp_456',
          customer_name: 'John Smith',
          rating: 3,
          content: 'Food was okay, but service could be better.',
          sentiment_score: 0.45,
          urgency_level: 'medium',
          issue_categories: ['service'],
          status: 'responded',
          requires_private_recovery: false,
          created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 30).toISOString(),
          updated_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 29).toISOString(),
        },
      ];

      setCustomer(mockCustomer);
      setRecentReviews(mockReviews);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdateCustomerStatus = async (newStatus: Customer['status']) => {
    if (!customer) {
      return;
    }

    setIsUpdating(true);
    try {
      await api.patch(`/customers/${customer.id}`, { status: newStatus });
      setCustomer(prev => (prev ? { ...prev, status: newStatus } : null));
    } catch (error) {
      console.error('Error updating customer status:', error);
    } finally {
      setIsUpdating(false);
    }
  };

  const handleAddRecoveryAction = () => {
    // In a real app, this would open a modal to create a new recovery action
    console.log('Add recovery action for customer:', customer?.id);
  };

  const handleUpdateRecoveryAction = (actionId: string, updates: Partial<RecoveryAction>) => {
    setRecoveryActions(prev =>
      prev.map(action => (action.id === actionId ? { ...action, ...updates } : action)),
    );
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

  if (error || !customer) {
    return (
      <div className='px-4 sm:px-6 lg:px-8'>
        <div className='text-center py-12'>
          <AlertTriangle className='h-12 w-12 text-red-400 mx-auto mb-4' />
          <h2 className='text-lg font-medium text-gray-900 mb-2'>Customer Not Found</h2>
          <p className='text-gray-600 mb-4'>
            {error || "The customer you're looking for doesn't exist or has been removed."}
          </p>
          <Button onClick={() => router.push('/dashboard/customers')}>
            <ArrowLeft className='h-4 w-4 mr-1' />
            Back to Customers
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
            <Button variant='outline' size='sm' onClick={() => router.push('/dashboard/customers')}>
              <ArrowLeft className='h-4 w-4 mr-1' />
              Back to Customers
            </Button>
            <div>
              <h1 className='text-2xl font-bold text-gray-900'>{customer.name}</h1>
              <p className='text-sm text-gray-500'>
                Customer since {formatDateTime(customer.created_at)}
              </p>
            </div>
          </div>

          <div className='flex items-center space-x-2'>
            <Button
              variant='outline'
              size='sm'
              onClick={() => router.push(`/dashboard/customers/${customer.id}/analytics`)}
            >
              <BarChart className='h-4 w-4 mr-1' />
              Analytics
            </Button>

            <Button
              variant='outline'
              size='sm'
              onClick={() => router.push(`/dashboard/reviews?search=${customer.name}`)}
            >
              <MessageSquare className='h-4 w-4 mr-1' />
              View Reviews
            </Button>
          </div>
        </div>
      </div>

      <div className='grid grid-cols-1 lg:grid-cols-3 gap-8'>
        {/* Main Content */}
        <div className='lg:col-span-2 space-y-6'>
          {/* Customer Overview */}
          <Card>
            <CardHeader>
              <div className='flex items-center justify-between'>
                <CardTitle>Customer Overview</CardTitle>
                <CustomerStatusBadge status={customer.status} />
              </div>
            </CardHeader>
            <CardContent>
              <div className='grid grid-cols-1 md:grid-cols-3 gap-6'>
                {/* Contact Info */}
                <div className='space-y-4'>
                  <h4 className='font-medium text-gray-900'>Contact Information</h4>
                  <div className='space-y-2'>
                    {customer.email && (
                      <div className='flex items-center space-x-2 text-sm'>
                        <Mail className='h-4 w-4 text-gray-400' />
                        <span>{customer.email}</span>
                      </div>
                    )}
                    {customer.phone && (
                      <div className='flex items-center space-x-2 text-sm'>
                        <Phone className='h-4 w-4 text-gray-400' />
                        <span>{customer.phone}</span>
                      </div>
                    )}
                    {customer.metadata?.location && (
                      <div className='flex items-center space-x-2 text-sm'>
                        <Users className='h-4 w-4 text-gray-400' />
                        <span>{customer.metadata.location}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Review Stats */}
                <div className='space-y-4'>
                  <h4 className='font-medium text-gray-900'>Review Statistics</h4>
                  <div className='space-y-2'>
                    <div className='flex items-center justify-between text-sm'>
                      <span className='text-gray-600'>Total Reviews</span>
                      <span className='font-medium'>{customer.total_reviews}</span>
                    </div>
                    <div className='flex items-center justify-between text-sm'>
                      <span className='text-gray-600'>Average Rating</span>
                      <div className='flex items-center space-x-1'>
                        <Star className='h-4 w-4 text-yellow-500' />
                        <span className='font-medium'>{customer.average_rating.toFixed(1)}</span>
                      </div>
                    </div>
                    <div className='flex items-center justify-between text-sm'>
                      <span className='text-gray-600'>Last Review</span>
                      <span className='font-medium'>
                        {formatDateTime(customer.last_review_date)}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Business Metrics */}
                <div className='space-y-4'>
                  <h4 className='font-medium text-gray-900'>Business Metrics</h4>
                  <div className='space-y-2'>
                    <div className='flex items-center justify-between text-sm'>
                      <span className='text-gray-600'>Lifetime Value</span>
                      <span className='font-medium'>
                        ${customer.lifetime_value.toLocaleString()}
                      </span>
                    </div>
                    <div className='flex items-center justify-between text-sm'>
                      <span className='text-gray-600'>Risk Score</span>
                      <span className='font-medium'>{Math.round(customer.risk_score * 100)}%</span>
                    </div>
                    <div className='flex items-center justify-between text-sm'>
                      <span className='text-gray-600'>Customer Since</span>
                      <span className='font-medium'>
                        {Math.round(
                          (Date.now() - new Date(customer.created_at).getTime()) /
                            (1000 * 60 * 60 * 24),
                        )}{' '}
                        days
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Tags */}
              {customer.tags.length > 0 && (
                <div className='mt-6 pt-6 border-t'>
                  <h4 className='font-medium text-gray-900 mb-3'>Tags</h4>
                  <div className='flex flex-wrap gap-2'>
                    {customer.tags.map(tag => (
                      <span
                        key={tag}
                        className='inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800'
                      >
                        <Tag className='h-3 w-3 mr-1' />
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Recent Reviews */}
          <Card>
            <CardHeader>
              <div className='flex items-center justify-between'>
                <CardTitle>Recent Reviews</CardTitle>
                <Button
                  variant='outline'
                  size='sm'
                  onClick={() => router.push(`/dashboard/reviews?search=${customer.name}`)}
                >
                  View All Reviews
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {recentReviews.length === 0 ? (
                <div className='text-center py-8'>
                  <MessageSquare className='h-12 w-12 text-gray-400 mx-auto mb-4' />
                  <h3 className='text-lg font-medium text-gray-900 mb-2'>No Reviews</h3>
                  <p className='text-gray-600'>This customer hasn't left any reviews yet.</p>
                </div>
              ) : (
                <div className='space-y-4'>
                  {recentReviews.map(review => (
                    <div key={review.id} className='border rounded-lg p-4'>
                      <div className='flex items-center justify-between mb-2'>
                        <div className='flex items-center space-x-2'>
                          <span className='text-yellow-500'>
                            {'★'.repeat(review.rating)}
                            {'☆'.repeat(5 - review.rating)}
                          </span>
                          <span className='text-sm text-gray-600'>
                            {review.platform} • {formatDateTime(review.created_at)}
                          </span>
                        </div>
                        <span
                          className={cn(
                            'px-2 py-1 rounded-full text-xs font-medium',
                            review.status === 'responded'
                              ? 'bg-green-100 text-green-800'
                              : review.status === 'escalated'
                                ? 'bg-red-100 text-red-800'
                                : 'bg-yellow-100 text-yellow-800',
                          )}
                        >
                          {review.status}
                        </span>
                      </div>
                      <p className='text-sm text-gray-700 mb-2'>{review.content}</p>
                      <Button
                        variant='ghost'
                        size='sm'
                        onClick={() => router.push(`/dashboard/reviews/${review.id}`)}
                      >
                        <ExternalLink className='h-4 w-4 mr-1' />
                        View Details
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Recovery Actions Timeline */}
          <RecoveryActionsTimeline
            customerId={customer.id}
            actions={recoveryActions}
            onAddAction={handleAddRecoveryAction}
            onUpdateAction={handleUpdateRecoveryAction}
          />

          {/* Communication History */}
          <CommunicationHistory customerId={customer.id} communications={communications} />
        </div>

        {/* Sidebar */}
        <div className='space-y-6'>
          {/* Risk Assessment */}
          <Card>
            <CardHeader>
              <CardTitle>Risk Assessment</CardTitle>
            </CardHeader>
            <CardContent className='space-y-4'>
              <RiskIndicator level={customer.risk_level} score={customer.risk_score} showScore />

              <div className='space-y-3'>
                <ChurnProbability probability={customer.churn_probability} />

                <div className='pt-3 border-t'>
                  <p className='text-sm font-medium text-gray-900 mb-2'>Risk Factors</p>
                  <div className='space-y-2 text-sm text-gray-600'>
                    {customer.average_rating < 3 && (
                      <div className='flex items-center space-x-2'>
                        <TrendingDown className='h-4 w-4 text-red-500' />
                        <span>Low average rating ({customer.average_rating.toFixed(1)})</span>
                      </div>
                    )}
                    {customer.churn_probability > 0.7 && (
                      <div className='flex items-center space-x-2'>
                        <AlertTriangle className='h-4 w-4 text-red-500' />
                        <span>High churn probability</span>
                      </div>
                    )}
                    {customer.total_reviews > 5 && customer.average_rating < 3 && (
                      <div className='flex items-center space-x-2'>
                        <MessageSquare className='h-4 w-4 text-yellow-500' />
                        <span>Frequent negative feedback</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className='space-y-2'>
              <Button
                variant='outline'
                className='w-full justify-start'
                onClick={handleAddRecoveryAction}
                disabled={isUpdating}
              >
                <TrendingUp className='h-4 w-4 mr-2' />
                Start Recovery Action
              </Button>

              <Button
                variant='outline'
                className='w-full justify-start'
                onClick={() => handleUpdateCustomerStatus('recovered')}
                disabled={isUpdating || customer.status === 'recovered'}
              >
                <Activity className='h-4 w-4 mr-2' />
                Mark as Recovered
              </Button>

              <Button
                variant='outline'
                className='w-full justify-start'
                onClick={() => router.push(`/dashboard/reviews?search=${customer.name}`)}
              >
                <MessageSquare className='h-4 w-4 mr-2' />
                View All Reviews
              </Button>

              {customer.email && (
                <Button
                  variant='outline'
                  className='w-full justify-start'
                  onClick={() => window.open(`mailto:${customer.email}`, '_blank')}
                >
                  <Mail className='h-4 w-4 mr-2' />
                  Send Email
                </Button>
              )}

              {customer.phone && (
                <Button
                  variant='outline'
                  className='w-full justify-start'
                  onClick={() => window.open(`tel:${customer.phone}`, '_blank')}
                >
                  <Phone className='h-4 w-4 mr-2' />
                  Call Customer
                </Button>
              )}
            </CardContent>
          </Card>

          {/* Customer Preferences */}
          {customer.metadata && (
            <Card>
              <CardHeader>
                <CardTitle>Preferences</CardTitle>
              </CardHeader>
              <CardContent className='space-y-3'>
                {customer.metadata.preferred_contact_method && (
                  <div className='flex items-center justify-between text-sm'>
                    <span className='text-gray-600'>Preferred Contact</span>
                    <span className='font-medium capitalize'>
                      {customer.metadata.preferred_contact_method}
                    </span>
                  </div>
                )}

                {customer.metadata.timezone && (
                  <div className='flex items-center justify-between text-sm'>
                    <span className='text-gray-600'>Timezone</span>
                    <span className='font-medium'>{customer.metadata.timezone}</span>
                  </div>
                )}

                {customer.metadata.language && (
                  <div className='flex items-center justify-between text-sm'>
                    <span className='text-gray-600'>Language</span>
                    <span className='font-medium uppercase'>{customer.metadata.language}</span>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
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
