'use client';

import { useEffect, useRef, useState } from 'react';
import api from '@/lib/api';
import {
  transformDashboardMetrics,
  transformActivityFeed,
  transformActionQueue,
} from '@/lib/dashboard-adapter';

interface UseRealtimeUpdatesOptions {
  endpoint: string;
  interval?: number; // in milliseconds
  enabled?: boolean;
}

interface RealtimeState<T> {
  data: T | null;
  isLoading: boolean;
  error: string | null;
  lastUpdated: Date | null;
}

export function useRealtimeUpdates<T>({
  endpoint,
  interval = 30000, // 30 seconds default
  enabled = true,
}: UseRealtimeUpdatesOptions): RealtimeState<T> & {
  refetch: () => Promise<void>;
} {
  const [state, setState] = useState<RealtimeState<T>>({
    data: null,
    isLoading: true,
    error: null,
    lastUpdated: null,
  });

  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchData = async () => {
    if (!enabled) {
      return;
    }

    try {
      const response = await api.get(endpoint);

      const newState = {
        data: response.data,
        isLoading: false,
        error: null,
        lastUpdated: new Date(),
      };
      setState(newState);
    } catch (error: any) {
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error.response?.data?.detail || 'Failed to fetch data',
      }));
    }
  };

  const refetch = async () => {
    await fetchData();
  };

  useEffect(() => {
    if (!enabled) {
      return;
    }

    // Initial fetch
    fetchData();

    // Set up polling
    intervalRef.current = setInterval(fetchData, interval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [endpoint, interval, enabled]);

  useEffect(() => {
    return () => {
      // Cleanup on unmount
    };
  }, []);

  return {
    ...state,
    refetch,
  };
}

// Specialized hook for dashboard metrics
export function useDashboardMetrics() {
  const result = useRealtimeUpdates({
    endpoint: '/dashboard/metrics',
    interval: 30000, // 30 seconds
  });

  // Transform the data to match frontend expectations
  const transformedData = result.data
    ? (() => {
        try {
          // Check if data has the required structure
          if (result.data && typeof result.data === 'object' && 'kpis' in result.data) {
            return transformDashboardMetrics(result.data as any);
          }
          return null;
        } catch (error) {
          console.error('[useDashboardMetrics] Transform error:', error);
          return null;
        }
      })()
    : null;

  return {
    ...result,
    data: transformedData,
  };
}

// Specialized hook for activity feed
export function useActivityFeed() {
  const result = useRealtimeUpdates({
    endpoint: '/dashboard/activity',
    interval: 15000, // 15 seconds for more frequent updates
  });

  // Transform the data to match frontend expectations
  return {
    ...result,
    data: result.data ? { activities: transformActivityFeed(result.data) } : null,
  };
}

// Specialized hook for action queue
// Note: Backend doesn't have /dashboard/actions yet, so we use /dashboard/alerts
export function useActionQueue() {
  const result = useRealtimeUpdates({
    endpoint: '/dashboard/alerts',
    interval: 20000, // 20 seconds
  });

  // Transform the data to match frontend expectations
  return {
    ...result,
    data: result.data ? { actions: transformActionQueue(result.data) } : null,
  };
}
