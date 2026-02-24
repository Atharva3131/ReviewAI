/**
 * Stripe client configuration
 * This file provides utilities for Stripe integration on the frontend
 */

export const STRIPE_PUBLISHABLE_KEY = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || '';

/**
 * Check if Stripe is configured
 */
export const isStripeConfigured = (): boolean => {
  return !!STRIPE_PUBLISHABLE_KEY;
};

/**
 * Format currency for display
 */
export const formatCurrency = (amount: number, currency: string = 'USD'): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 0,
  }).format(amount);
};

/**
 * Calculate savings percentage for yearly billing
 */
export const calculateYearlySavings = (monthlyPrice: number, yearlyPrice: number): number => {
  const monthlyTotal = monthlyPrice * 12;
  const savings = ((monthlyTotal - yearlyPrice) / monthlyTotal) * 100;
  return Math.round(savings);
};

/**
 * Get plan price based on billing period
 */
export const getPlanPrice = (
  plan: { price_monthly: number; price_yearly: number },
  period: 'monthly' | 'yearly',
): number => {
  return period === 'monthly' ? plan.price_monthly : plan.price_yearly;
};
