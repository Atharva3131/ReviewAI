'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { KPICard } from '@/components/dashboard/kpi-card';
import { ActivityFeed } from '@/components/dashboard/activity-feed';
import { SentimentChart } from '@/components/dashboard/sentiment-chart';
import { ActionQueue } from '@/components/dashboard/action-queue';
import { useDashboardMetrics, useActivityFeed, useActionQueue } from '@/hooks/use-realtime-updates';
import { useTour } from '@/components/tour/tour-provider';
import { dashboardTourSteps, DASHBOARD_TOUR_ID } from '@/components/tour/dashboard-tour';
import {
  Star,
  MessageSquare,
  Users,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

interface DashboardMetrics {
  average_rating: number;
  rating_trend: number;
  monthly_reviews: number;
  reviews_trend: number;
  at_risk_customers: number;
  risk_trend: number;
  recovery_success_rate: number;
  recovery_trend: number;
}

interface ActivityItem {
  id: string;
  type: string;
  title: string;
  description: string;
  timestamp: string;
  priority?: 'low' | 'medium' | 'high';
}

interface ActionItem {
  id: string;
  type: string;
  title: string;
  description: string;
  priority: 'low' | 'medium' | 'high';
  created_at: string;
}

export default function DashboardPage() {
  const {
    data: metrics,
    isLoading: metricsLoading,
    error: metricsError,
    lastUpdated: metricsLastUpdated,
    refetch: refetchMetrics,
  } = useDashboardMetrics();

  const {
    data: activityData,
    isLoading: activityLoading,
    error: activityError,
    refetch: refetchActivity,
  } = useActivityFeed();

  const {
    data: actionData,
    isLoading: actionLoading,
    error: actionError,
    refetch: refetchActions,
  } = useActionQueue();

  const { startTour, hasCompletedTour, markTourComplete } = useTour();

  // Auto-start tour for first-time users
  useEffect(() => {
    if (!hasCompletedTour(DASHBOARD_TOUR_ID)) {
      const timer = setTimeout(() => {
        startTour(dashboardTourSteps);
        markTourComplete(DASHBOARD_TOUR_ID);
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [hasCompletedTour, startTour, markTourComplete]);

  // Mock data fallback for development
  const [mockMetrics] = useState<DashboardMetrics>({
    average_rating: 4.2,
    rating_trend: 0.3,
    monthly_reviews: 127,
    reviews_trend: 15,
    at_risk_customers: 23,
    risk_trend: -5,
    recovery_success_rate: 78,
    recovery_trend: 12,
  });

  const [mockActivities] = useState<ActivityItem[]>([
    {
      id: '1',
      type: 'review',
      title: 'New 2★ review requires attention',
      description: 'Customer complained about service quality',
      timestamp: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
      priority: 'high',
    },
    {
      id: '2',
      type: 'recovery',
      title: 'Recovery email sent to high-risk customer',
      description: 'Personalized apology sent to John Doe',
      timestamp: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
      priority: 'medium',
    },
    {
      id: '3',
      type: 'response',
      title: '5★ review response published',
      description: 'Thank you message posted to Google Reviews',
      timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
      priority: 'low',
    },
  ]);

  const [mockActions] = useState<ActionItem[]>([
    {
      id: '1',
      type: 'review_response',
      title: '3 reviews pending response',
      description: 'Reviews from Google and Yelp need responses',
      priority: 'medium',
      created_at: new Date().toISOString(),
    },
    {
      id: '2',
      type: 'customer_recovery',
      title: '2 customers need recovery',
      description: 'High churn risk customers identified',
      priority: 'high',
      created_at: new Date().toISOString(),
    },
    {
      id: '3',
      type: 'escalation',
      title: '1 case escalated to manager',
      description: 'Complex issue requires human intervention',
      priority: 'high',
      created_at: new Date().toISOString(),
    },
  ]);

  const handleRefreshAll = async () => {
    await Promise.all([refetchMetrics(), refetchActivity(), refetchActions()]);
  };

  // Use real data if available, otherwise fall back to mock data
  const displayMetrics = metrics || mockMetrics;
  const displayActivities = activityData?.activities || mockActivities;
  const displayActions = actionData?.actions || mockActions;

  const hasError = metricsError || activityError || actionError;
  // Only show loading on initial load when we have no data at all
  const isLoading =
    !metrics &&
    !activityData &&
    !actionData &&
    (metricsLoading || activityLoading || actionLoading);

  if (isLoading) {
    return (
      <div className='px-4 sm:px-6 lg:px-8'>
        <div className='animate-pulse'>
          <div className='h-8 bg-gray-200 rounded w-1/4 mb-6'></div>
          <div className='grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4 mb-8'>
            {[...Array(4)].map((_, i) => (
              <div key={i} className='bg-white p-6 rounded-lg shadow h-32'></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className='px-4 sm:px-6 lg:px-8'>
      <div className='mb-8 flex items-center justify-between' data-tour='dashboard-title'>
        <div>
          <h1 className='text-2xl font-bold text-gray-900'>Dashboard</h1>
          <p className='mt-1 text-sm text-gray-500'>
            Overview of your reputation management performance
          </p>
        </div>

        <div className='flex items-center space-x-4'>
          {metricsLastUpdated && (
            <span className='text-xs text-gray-500'>
              Last updated: {metricsLastUpdated.toLocaleTimeString()}
            </span>
          )}
          <Button
            variant='outline'
            size='sm'
            onClick={handleRefreshAll}
            disabled={metricsLoading || activityLoading || actionLoading}
          >
            <RefreshCw
              className={`h-4 w-4 mr-2 ${metricsLoading || activityLoading || actionLoading ? 'animate-spin' : ''}`}
            />
            Refresh
          </Button>
        </div>
      </div>

      {hasError && (
        <div className='mb-6 bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded-md'>
          <div className='flex'>
            <AlertTriangle className='h-5 w-5 mr-2' />
            <span className='text-sm'>
              Some data may be unavailable - Showing sample data for demonstration
            </span>
          </div>
        </div>
      )}

      {/* KPI Cards */}
      <div
        className='grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4 mb-8'
        data-tour='kpi-cards'
      >
        <KPICard
          title='Average Rating'
          value={`${displayMetrics?.average_rating?.toFixed(1)}★` || '0.0★'}
          trend={displayMetrics?.rating_trend || 0}
          icon={Star}
          color='blue'
        />
        <KPICard
          title='Reviews This Month'
          value={displayMetrics?.monthly_reviews?.toString() || '0'}
          trend={displayMetrics?.reviews_trend || 0}
          icon={MessageSquare}
          color='green'
        />
        <KPICard
          title='Customers At Risk'
          value={displayMetrics?.at_risk_customers?.toString() || '0'}
          trend={displayMetrics?.risk_trend || 0}
          icon={Users}
          color='red'
          invertTrend
        />
        <KPICard
          title='Recovery Success'
          value={`${displayMetrics?.recovery_success_rate?.toString()}%` || '0%'}
          trend={displayMetrics?.recovery_trend || 0}
          icon={CheckCircle}
          color='purple'
        />
      </div>

      {/* Main Content Grid */}
      <div className='grid grid-cols-1 lg:grid-cols-3 gap-8'>
        {/* Activity Feed */}
        <div className='lg:col-span-2' data-tour='activity-feed'>
          <Card>
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
              <CardDescription>
                Latest updates from your reputation management system
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ActivityFeed activities={displayActivities} />
            </CardContent>
          </Card>
        </div>

        {/* Action Queue */}
        <div data-tour='action-queue'>
          <Card>
            <CardHeader>
              <CardTitle>Action Queue</CardTitle>
              <CardDescription>Items requiring your attention</CardDescription>
            </CardHeader>
            <CardContent>
              <ActionQueue actions={displayActions} />
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Sentiment Trends Chart */}
      <div className='mt-8' data-tour='sentiment-chart'>
        <Card>
          <CardHeader>
            <CardTitle>Sentiment Trends</CardTitle>
            <CardDescription>Customer sentiment over time</CardDescription>
          </CardHeader>
          <CardContent>
            <SentimentChart />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
