/**
 * Adapter to transform backend dashboard API responses to frontend format
 */

interface BackendKPIValue {
  value: number;
  trend: string;
  previous_value?: number;
}

interface BackendKPIs {
  average_rating: BackendKPIValue;
  monthly_reviews: BackendKPIValue;
  at_risk_customers: BackendKPIValue;
  recovery_success_rate: BackendKPIValue;
}

interface BackendDashboardMetrics {
  kpis: BackendKPIs;
  activity_feed?: any[];
  alerts?: any[];
  trends?: any;
  charts?: any;
  metadata?: any;
}

interface FrontendDashboardMetrics {
  average_rating: number;
  rating_trend: number;
  monthly_reviews: number;
  reviews_trend: number;
  at_risk_customers: number;
  risk_trend: number;
  recovery_success_rate: number;
  recovery_trend: number;
}

/**
 * Convert trend string to numeric percentage
 */
function trendToNumber(trend: string, previousValue?: number, currentValue?: number): number {
  if (trend === 'up') {
    return 5;
  }
  if (trend === 'down') {
    return -5;
  }
  if (trend === 'neutral') {
    return 0;
  }

  // Calculate actual percentage if we have both values
  if (previousValue && currentValue && previousValue > 0) {
    return ((currentValue - previousValue) / previousValue) * 100;
  }

  return 0;
}

/**
 * Transform backend dashboard metrics to frontend format
 */
export function transformDashboardMetrics(
  backendData: BackendDashboardMetrics,
): FrontendDashboardMetrics {
  const kpis = backendData.kpis;

  return {
    average_rating: kpis.average_rating.value,
    rating_trend: trendToNumber(
      kpis.average_rating.trend,
      kpis.average_rating.previous_value,
      kpis.average_rating.value,
    ),
    monthly_reviews: kpis.monthly_reviews.value,
    reviews_trend: trendToNumber(
      kpis.monthly_reviews.trend,
      kpis.monthly_reviews.previous_value,
      kpis.monthly_reviews.value,
    ),
    at_risk_customers: kpis.at_risk_customers.value,
    risk_trend: trendToNumber(
      kpis.at_risk_customers.trend,
      kpis.at_risk_customers.previous_value,
      kpis.at_risk_customers.value,
    ),
    recovery_success_rate: kpis.recovery_success_rate.value,
    recovery_trend: trendToNumber(
      kpis.recovery_success_rate.trend,
      kpis.recovery_success_rate.previous_value,
      kpis.recovery_success_rate.value,
    ),
  };
}

/**
 * Transform backend activity feed to frontend format
 */
export function transformActivityFeed(backendData: any) {
  if (backendData?.activities) {
    return backendData.activities;
  }
  if (backendData?.activity_feed) {
    return backendData.activity_feed;
  }
  return [];
}

/**
 * Transform backend action queue to frontend format
 * Note: Backend doesn't have a dedicated actions endpoint yet,
 * so we'll use alerts as a fallback
 */
export function transformActionQueue(backendData: any) {
  if (backendData?.actions) {
    return backendData.actions;
  }
  if (backendData?.alerts) {
    // Transform alerts to action items
    return backendData.alerts.map((alert: any) => ({
      id: alert.id,
      type: alert.type,
      title: alert.title,
      description: alert.description,
      priority: alert.priority || 'medium',
      created_at: new Date().toISOString(),
    }));
  }
  return [];
}
