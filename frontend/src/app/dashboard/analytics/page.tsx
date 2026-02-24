'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  BarChart,
  TrendingUp,
  Users,
  Star,
  MessageSquare,
  ArrowRight,
  RefreshCw,
} from 'lucide-react';
import api from '@/lib/api';

interface AnalyticsSummary {
  reviews: {
    total: number;
    average_rating: number;
    response_rate: number;
    trend: number;
  };
  sentiment: {
    positive: number;
    neutral: number;
    negative: number;
    average_score: number;
  };
  customers: {
    total: number;
    at_risk: number;
    high_value: number;
    churn_rate: number;
  };
  recovery: {
    actions_created: number;
    success_rate: number;
    avg_response_time: number;
    recovered_customers: number;
  };
}

export default function AnalyticsPage() {
  const router = useRouter();
  const [data, setData] = useState<AnalyticsSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchAnalyticsSummary();
  }, []);

  const fetchAnalyticsSummary = async () => {
    setIsLoading(true);
    try {
      const response = await api.get('/analytics/summary');
      setData(response.data);
    } catch (error) {
      console.error('Error fetching analytics:', error);
      // Use mock data for development
      setData({
        reviews: {
          total: 127,
          average_rating: 4.2,
          response_rate: 87.5,
          trend: 15,
        },
        sentiment: {
          positive: 65,
          neutral: 20,
          negative: 15,
          average_score: 0.72,
        },
        customers: {
          total: 342,
          at_risk: 23,
          high_value: 45,
          churn_rate: 6.7,
        },
        recovery: {
          actions_created: 89,
          success_rate: 78,
          avg_response_time: 4.2,
          recovered_customers: 34,
        },
      });
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className='px-4 sm:px-6 lg:px-8'>
        <div className='animate-pulse space-y-6'>
          <div className='h-8 bg-gray-200 rounded w-1/4'></div>
          <div className='grid grid-cols-1 gap-6 lg:grid-cols-2'>
            {[...Array(4)].map((_, i) => (
              <div key={i} className='h-64 bg-gray-200 rounded'></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className='px-4 sm:px-6 lg:px-8'>
      <div className='mb-8 flex items-center justify-between'>
        <div>
          <h1 className='text-2xl font-bold text-gray-900'>Analytics</h1>
          <p className='mt-1 text-sm text-gray-500'>Detailed insights and performance metrics</p>
        </div>
        <Button variant='outline' size='sm' onClick={fetchAnalyticsSummary} disabled={isLoading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      <div className='grid grid-cols-1 gap-6 lg:grid-cols-2'>
        {/* Review Analytics */}
        <Card className='hover:shadow-lg transition-shadow'>
          <CardHeader>
            <CardTitle className='flex items-center'>
              <BarChart className='h-5 w-5 mr-2 text-blue-600' />
              Review Analytics
            </CardTitle>
            <CardDescription>Comprehensive review performance metrics</CardDescription>
          </CardHeader>
          <CardContent>
            {data ? (
              <div className='space-y-4'>
                <div className='grid grid-cols-2 gap-4'>
                  <div>
                    <p className='text-sm text-gray-600'>Total Reviews</p>
                    <p className='text-2xl font-bold text-gray-900'>{data.reviews.total}</p>
                  </div>
                  <div>
                    <p className='text-sm text-gray-600'>Avg Rating</p>
                    <div className='flex items-center space-x-1'>
                      <p className='text-2xl font-bold text-gray-900'>
                        {data.reviews.average_rating}
                      </p>
                      <Star className='h-5 w-5 text-yellow-500 fill-current' />
                    </div>
                  </div>
                  <div>
                    <p className='text-sm text-gray-600'>Response Rate</p>
                    <p className='text-2xl font-bold text-gray-900'>
                      {data.reviews.response_rate}%
                    </p>
                  </div>
                  <div>
                    <p className='text-sm text-gray-600'>This Month</p>
                    <p className='text-2xl font-bold text-green-600'>+{data.reviews.trend}%</p>
                  </div>
                </div>
                <Button
                  variant='outline'
                  className='w-full'
                  onClick={() => router.push('/dashboard/reviews/analytics')}
                >
                  View Detailed Analytics
                  <ArrowRight className='h-4 w-4 ml-2' />
                </Button>
              </div>
            ) : (
              <div className='text-center py-8 text-gray-500'>
                <MessageSquare className='h-12 w-12 mx-auto mb-4 text-gray-400' />
                <p>No review data available</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Sentiment Trends */}
        <Card className='hover:shadow-lg transition-shadow'>
          <CardHeader>
            <CardTitle className='flex items-center'>
              <TrendingUp className='h-5 w-5 mr-2 text-green-600' />
              Sentiment Trends
            </CardTitle>
            <CardDescription>Customer sentiment over time</CardDescription>
          </CardHeader>
          <CardContent>
            {data ? (
              <div className='space-y-4'>
                <div className='space-y-3'>
                  <div className='flex items-center justify-between'>
                    <span className='text-sm text-gray-600'>Positive</span>
                    <span className='text-sm font-medium text-green-600'>
                      {data.sentiment.positive}%
                    </span>
                  </div>
                  <div className='w-full bg-gray-200 rounded-full h-2'>
                    <div
                      className='bg-green-500 h-2 rounded-full'
                      style={{ width: `${data.sentiment.positive}%` }}
                    />
                  </div>

                  <div className='flex items-center justify-between'>
                    <span className='text-sm text-gray-600'>Neutral</span>
                    <span className='text-sm font-medium text-yellow-600'>
                      {data.sentiment.neutral}%
                    </span>
                  </div>
                  <div className='w-full bg-gray-200 rounded-full h-2'>
                    <div
                      className='bg-yellow-500 h-2 rounded-full'
                      style={{ width: `${data.sentiment.neutral}%` }}
                    />
                  </div>

                  <div className='flex items-center justify-between'>
                    <span className='text-sm text-gray-600'>Negative</span>
                    <span className='text-sm font-medium text-red-600'>
                      {data.sentiment.negative}%
                    </span>
                  </div>
                  <div className='w-full bg-gray-200 rounded-full h-2'>
                    <div
                      className='bg-red-500 h-2 rounded-full'
                      style={{ width: `${data.sentiment.negative}%` }}
                    />
                  </div>
                </div>

                <div className='pt-2 border-t'>
                  <div className='flex items-center justify-between'>
                    <span className='text-sm text-gray-600'>Average Sentiment Score</span>
                    <span className='text-lg font-bold text-gray-900'>
                      {data.sentiment.average_score}
                    </span>
                  </div>
                </div>

                <Button
                  variant='outline'
                  className='w-full'
                  onClick={() => router.push('/dashboard/reviews/analytics')}
                >
                  View Sentiment Details
                  <ArrowRight className='h-4 w-4 ml-2' />
                </Button>
              </div>
            ) : (
              <div className='text-center py-8 text-gray-500'>
                <Star className='h-12 w-12 mx-auto mb-4 text-gray-400' />
                <p>No sentiment data available</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Customer Insights */}
        <Card className='hover:shadow-lg transition-shadow'>
          <CardHeader>
            <CardTitle className='flex items-center'>
              <Users className='h-5 w-5 mr-2 text-purple-600' />
              Customer Insights
            </CardTitle>
            <CardDescription>Customer behavior and engagement</CardDescription>
          </CardHeader>
          <CardContent>
            {data ? (
              <div className='space-y-4'>
                <div className='grid grid-cols-2 gap-4'>
                  <div>
                    <p className='text-sm text-gray-600'>Total Customers</p>
                    <p className='text-2xl font-bold text-gray-900'>{data.customers.total}</p>
                  </div>
                  <div>
                    <p className='text-sm text-gray-600'>At Risk</p>
                    <p className='text-2xl font-bold text-red-600'>{data.customers.at_risk}</p>
                  </div>
                  <div>
                    <p className='text-sm text-gray-600'>High Value</p>
                    <p className='text-2xl font-bold text-green-600'>{data.customers.high_value}</p>
                  </div>
                  <div>
                    <p className='text-sm text-gray-600'>Churn Rate</p>
                    <p className='text-2xl font-bold text-gray-900'>{data.customers.churn_rate}%</p>
                  </div>
                </div>
                <Button
                  variant='outline'
                  className='w-full'
                  onClick={() => router.push('/dashboard/customers')}
                >
                  View All Customers
                  <ArrowRight className='h-4 w-4 ml-2' />
                </Button>
              </div>
            ) : (
              <div className='text-center py-8 text-gray-500'>
                <Users className='h-12 w-12 mx-auto mb-4 text-gray-400' />
                <p>No customer data available</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recovery Performance */}
        <Card className='hover:shadow-lg transition-shadow'>
          <CardHeader>
            <CardTitle className='flex items-center'>
              <TrendingUp className='h-5 w-5 mr-2 text-orange-600' />
              Recovery Performance
            </CardTitle>
            <CardDescription>Recovery action effectiveness</CardDescription>
          </CardHeader>
          <CardContent>
            {data ? (
              <div className='space-y-4'>
                <div className='grid grid-cols-2 gap-4'>
                  <div>
                    <p className='text-sm text-gray-600'>Actions Created</p>
                    <p className='text-2xl font-bold text-gray-900'>
                      {data.recovery.actions_created}
                    </p>
                  </div>
                  <div>
                    <p className='text-sm text-gray-600'>Success Rate</p>
                    <p className='text-2xl font-bold text-green-600'>
                      {data.recovery.success_rate}%
                    </p>
                  </div>
                  <div>
                    <p className='text-sm text-gray-600'>Avg Response Time</p>
                    <p className='text-2xl font-bold text-gray-900'>
                      {data.recovery.avg_response_time}h
                    </p>
                  </div>
                  <div>
                    <p className='text-sm text-gray-600'>Recovered</p>
                    <p className='text-2xl font-bold text-green-600'>
                      {data.recovery.recovered_customers}
                    </p>
                  </div>
                </div>
                <Button
                  variant='outline'
                  className='w-full'
                  onClick={() => router.push('/dashboard/customers?status=recovered')}
                >
                  View Recovery Details
                  <ArrowRight className='h-4 w-4 ml-2' />
                </Button>
              </div>
            ) : (
              <div className='text-center py-8 text-gray-500'>
                <TrendingUp className='h-12 w-12 mx-auto mb-4 text-gray-400' />
                <p>No recovery data available</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
