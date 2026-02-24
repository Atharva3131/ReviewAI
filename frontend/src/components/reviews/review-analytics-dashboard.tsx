'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  Area,
  AreaChart,
} from 'recharts';
import {
  TrendingUp,
  TrendingDown,
  Star,
  MessageSquare,
  AlertTriangle,
  CheckCircle,
  Clock,
  Users,
  Calendar,
  Filter,
  Download,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ReviewAnalytics } from '@/types/review';
import api from '@/lib/api';

interface ReviewAnalyticsDashboardProps {
  className?: string;
}

interface AnalyticsData {
  overview: {
    total_reviews: number;
    average_rating: number;
    response_rate: number;
    avg_response_time_hours: number;
  };
  sentiment_distribution: {
    positive: number;
    neutral: number;
    negative: number;
  };
  platform_breakdown: Record<string, number>;
  urgency_breakdown: Record<string, number>;
  rating_distribution: Record<string, number>;
  trends: {
    date: string;
    reviews: number;
    average_rating: number;
    sentiment_score: number;
  }[];
  top_issues: {
    category: string;
    count: number;
    percentage: number;
  }[];
}

const COLORS = {
  positive: '#10B981',
  neutral: '#F59E0B',
  negative: '#EF4444',
  primary: '#3B82F6',
  secondary: '#8B5CF6',
};

export function ReviewAnalyticsDashboard({ className }: ReviewAnalyticsDashboardProps) {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d' | '1y'>('30d');

  useEffect(() => {
    fetchAnalytics();
  }, [timeRange]);

  const fetchAnalytics = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.get(`/reviews/analytics?period=${timeRange}`);
      setData(response.data);
    } catch (err: any) {
      console.error('Error fetching analytics:', err);
      setError('Failed to load analytics');

      // Mock data for development
      const mockData: AnalyticsData = {
        overview: {
          total_reviews: 1247,
          average_rating: 4.2,
          response_rate: 87.5,
          avg_response_time_hours: 4.2,
        },
        sentiment_distribution: {
          positive: 65,
          neutral: 20,
          negative: 15,
        },
        platform_breakdown: {
          google: 45,
          yelp: 25,
          facebook: 20,
          tripadvisor: 10,
        },
        urgency_breakdown: {
          low: 60,
          medium: 30,
          high: 10,
        },
        rating_distribution: {
          '1': 8,
          '2': 7,
          '3': 15,
          '4': 25,
          '5': 45,
        },
        trends: [
          { date: '2024-01-01', reviews: 45, average_rating: 4.1, sentiment_score: 0.72 },
          { date: '2024-01-02', reviews: 52, average_rating: 4.3, sentiment_score: 0.75 },
          { date: '2024-01-03', reviews: 38, average_rating: 4.0, sentiment_score: 0.68 },
          { date: '2024-01-04', reviews: 61, average_rating: 4.4, sentiment_score: 0.78 },
          { date: '2024-01-05', reviews: 43, average_rating: 4.2, sentiment_score: 0.71 },
          { date: '2024-01-06', reviews: 55, average_rating: 4.5, sentiment_score: 0.8 },
          { date: '2024-01-07', reviews: 49, average_rating: 4.1, sentiment_score: 0.69 },
        ],
        top_issues: [
          { category: 'service', count: 156, percentage: 35 },
          { category: 'quality', count: 98, percentage: 22 },
          { category: 'delivery', count: 87, percentage: 20 },
          { category: 'pricing', count: 67, percentage: 15 },
          { category: 'staff', count: 35, percentage: 8 },
        ],
      };
      setData(mockData);
    } finally {
      setIsLoading(false);
    }
  };

  const exportAnalytics = async () => {
    try {
      const response = await api.get(`/reviews/analytics/export?period=${timeRange}&format=csv`);
      const blob = new Blob([response.data], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `review-analytics-${timeRange}-${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Error exporting analytics:', error);
    }
  };

  if (isLoading) {
    return (
      <div className={cn('space-y-6', className)}>
        <div className='animate-pulse space-y-4'>
          <div className='h-8 bg-gray-200 rounded w-1/4'></div>
          <div className='grid grid-cols-1 md:grid-cols-4 gap-4'>
            {[...Array(4)].map((_, i) => (
              <div key={i} className='h-32 bg-gray-200 rounded'></div>
            ))}
          </div>
          <div className='h-64 bg-gray-200 rounded'></div>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className={cn('text-center py-12', className)}>
        <AlertTriangle className='h-12 w-12 text-red-400 mx-auto mb-4' />
        <h3 className='text-lg font-medium text-gray-900 mb-2'>Analytics Unavailable</h3>
        <p className='text-gray-600 mb-4'>{error || 'Unable to load analytics data'}</p>
        <Button onClick={fetchAnalytics}>Try Again</Button>
      </div>
    );
  }

  const sentimentData = [
    { name: 'Positive', value: data.sentiment_distribution.positive, color: COLORS.positive },
    { name: 'Neutral', value: data.sentiment_distribution.neutral, color: COLORS.neutral },
    { name: 'Negative', value: data.sentiment_distribution.negative, color: COLORS.negative },
  ];

  const platformData = Object.entries(data.platform_breakdown).map(([platform, count]) => ({
    platform: platform.charAt(0).toUpperCase() + platform.slice(1),
    count,
  }));

  const ratingData = Object.entries(data.rating_distribution).map(([rating, count]) => ({
    rating: `${rating}★`,
    count,
  }));

  return (
    <div className={cn('space-y-6', className)}>
      {/* Header */}
      <div className='flex items-center justify-between'>
        <div>
          <h2 className='text-2xl font-bold text-gray-900'>Review Analytics</h2>
          <p className='text-gray-600'>Comprehensive insights into your review performance</p>
        </div>

        <div className='flex items-center space-x-2'>
          <div className='flex items-center space-x-1 bg-gray-100 rounded-lg p-1'>
            {(['7d', '30d', '90d', '1y'] as const).map(period => (
              <button
                key={period}
                onClick={() => setTimeRange(period)}
                className={cn(
                  'px-3 py-1 text-sm rounded-md transition-colors',
                  timeRange === period
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900',
                )}
              >
                {period === '7d'
                  ? '7 Days'
                  : period === '30d'
                    ? '30 Days'
                    : period === '90d'
                      ? '90 Days'
                      : '1 Year'}
              </button>
            ))}
          </div>

          <Button variant='outline' size='sm' onClick={exportAnalytics}>
            <Download className='h-4 w-4 mr-1' />
            Export
          </Button>
        </div>
      </div>

      {/* Overview Cards */}
      <div className='grid grid-cols-1 md:grid-cols-4 gap-4'>
        <Card>
          <CardContent className='p-6'>
            <div className='flex items-center justify-between'>
              <div>
                <p className='text-sm font-medium text-gray-600'>Total Reviews</p>
                <p className='text-2xl font-bold text-gray-900'>
                  {data.overview.total_reviews.toLocaleString()}
                </p>
              </div>
              <MessageSquare className='h-8 w-8 text-blue-600' />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className='p-6'>
            <div className='flex items-center justify-between'>
              <div>
                <p className='text-sm font-medium text-gray-600'>Average Rating</p>
                <div className='flex items-center space-x-1'>
                  <p className='text-2xl font-bold text-gray-900'>{data.overview.average_rating}</p>
                  <Star className='h-5 w-5 text-yellow-500 fill-current' />
                </div>
              </div>
              <div className='flex items-center'>
                <TrendingUp className='h-8 w-8 text-green-600' />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className='p-6'>
            <div className='flex items-center justify-between'>
              <div>
                <p className='text-sm font-medium text-gray-600'>Response Rate</p>
                <p className='text-2xl font-bold text-gray-900'>{data.overview.response_rate}%</p>
              </div>
              <CheckCircle className='h-8 w-8 text-green-600' />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className='p-6'>
            <div className='flex items-center justify-between'>
              <div>
                <p className='text-sm font-medium text-gray-600'>Avg Response Time</p>
                <p className='text-2xl font-bold text-gray-900'>
                  {data.overview.avg_response_time_hours}h
                </p>
              </div>
              <Clock className='h-8 w-8 text-blue-600' />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row 1 */}
      <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
        {/* Review Trends */}
        <Card>
          <CardHeader>
            <CardTitle>Review Trends</CardTitle>
            <CardDescription>Daily review volume and ratings over time</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width='100%' height={300}>
              <AreaChart data={data.trends}>
                <CartesianGrid strokeDasharray='3 3' />
                <XAxis
                  dataKey='date'
                  tickFormatter={value => new Date(value).toLocaleDateString()}
                />
                <YAxis />
                <Tooltip labelFormatter={value => new Date(value).toLocaleDateString()} />
                <Area
                  type='monotone'
                  dataKey='reviews'
                  stroke={COLORS.primary}
                  fill={COLORS.primary}
                  fillOpacity={0.3}
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Sentiment Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Sentiment Distribution</CardTitle>
            <CardDescription>Breakdown of review sentiment</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width='100%' height={300}>
              <PieChart>
                <Pie
                  data={sentimentData}
                  cx='50%'
                  cy='50%'
                  innerRadius={60}
                  outerRadius={120}
                  paddingAngle={5}
                  dataKey='value'
                >
                  {sentimentData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip formatter={value => `${value}%`} />
              </PieChart>
            </ResponsiveContainer>
            <div className='flex justify-center space-x-4 mt-4'>
              {sentimentData.map(entry => (
                <div key={entry.name} className='flex items-center space-x-2'>
                  <div className='w-3 h-3 rounded-full' style={{ backgroundColor: entry.color }} />
                  <span className='text-sm text-gray-600'>
                    {entry.name} ({entry.value}%)
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row 2 */}
      <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
        {/* Platform Breakdown */}
        <Card>
          <CardHeader>
            <CardTitle>Platform Distribution</CardTitle>
            <CardDescription>Reviews by platform</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width='100%' height={300}>
              <BarChart data={platformData}>
                <CartesianGrid strokeDasharray='3 3' />
                <XAxis dataKey='platform' />
                <YAxis />
                <Tooltip />
                <Bar dataKey='count' fill={COLORS.primary} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Rating Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Rating Distribution</CardTitle>
            <CardDescription>Breakdown by star rating</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width='100%' height={300}>
              <BarChart data={ratingData}>
                <CartesianGrid strokeDasharray='3 3' />
                <XAxis dataKey='rating' />
                <YAxis />
                <Tooltip />
                <Bar dataKey='count' fill={COLORS.secondary} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Top Issues */}
      <Card>
        <CardHeader>
          <CardTitle>Top Issue Categories</CardTitle>
          <CardDescription>Most common issues mentioned in reviews</CardDescription>
        </CardHeader>
        <CardContent>
          <div className='space-y-4'>
            {data.top_issues.map((issue, index) => (
              <div key={issue.category} className='flex items-center space-x-4'>
                <div className='flex-shrink-0 w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center'>
                  <span className='text-sm font-medium text-gray-600'>{index + 1}</span>
                </div>
                <div className='flex-1'>
                  <div className='flex items-center justify-between mb-1'>
                    <span className='text-sm font-medium text-gray-900 capitalize'>
                      {issue.category}
                    </span>
                    <span className='text-sm text-gray-600'>
                      {issue.count} ({issue.percentage}%)
                    </span>
                  </div>
                  <div className='w-full bg-gray-200 rounded-full h-2'>
                    <div
                      className='bg-blue-600 h-2 rounded-full'
                      style={{ width: `${issue.percentage}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {error && (
        <div className='bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded-md'>
          <p className='text-sm'>{error} - Showing sample data for demonstration</p>
        </div>
      )}
    </div>
  );
}
