'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Loader2, CreditCard, Download, ExternalLink, Check } from 'lucide-react';
import { api } from '@/lib/api';
import { formatCurrency, formatDate } from '@/lib/utils';

interface SubscriptionPlan {
  id: string;
  name: string;
  description: string;
  price_monthly: number;
  price_yearly: number;
  features: Record<string, boolean>;
  limits: Record<string, number>;
  is_active: boolean;
}

interface Subscription {
  id: string;
  plan_id: string;
  status: string;
  billing_period: string;
  current_period_start: string;
  current_period_end: string;
  cancel_at_period_end: boolean;
  is_trial: boolean;
  trial_end: string | null;
  plan: SubscriptionPlan;
}

interface Invoice {
  id: string;
  amount: number;
  currency: string;
  status: string;
  invoice_number: string | null;
  invoice_pdf: string | null;
  paid_at: string | null;
  created_at: string;
}

export default function BillingPage() {
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [billingPeriod, setBillingPeriod] = useState<'monthly' | 'yearly'>('monthly');
  const [processingAction, setProcessingAction] = useState<string | null>(null);

  useEffect(() => {
    fetchBillingData();
  }, []);

  const fetchBillingData = async () => {
    try {
      setLoading(true);
      const [subResponse, invoicesResponse, plansResponse] = await Promise.all([
        api.get('/billing/subscription'),
        api.get('/billing/invoices?limit=10'),
        api.get('/billing/plans'),
      ]);

      setSubscription(subResponse.data);
      setInvoices(invoicesResponse.data);
      setPlans(plansResponse.data);
    } catch (error) {
      console.error('Failed to fetch billing data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (planId: string) => {
    try {
      setProcessingAction(planId);
      const response = await api.post('/billing/checkout', {
        plan_id: planId,
        billing_period: billingPeriod,
        success_url: `${window.location.origin}/dashboard/settings/billing?success=true`,
        cancel_url: `${window.location.origin}/dashboard/settings/billing?canceled=true`,
      });

      // Redirect to Stripe checkout
      if (response.data.url) {
        window.location.href = response.data.url;
      }
    } catch (error) {
      console.error('Failed to create checkout session:', error);
      alert('Failed to start checkout process. Please try again.');
    } finally {
      setProcessingAction(null);
    }
  };

  const handleManageBilling = async () => {
    try {
      setProcessingAction('portal');
      const response = await api.post('/billing/portal', {
        return_url: `${window.location.origin}/dashboard/settings/billing`,
      });

      if (response.data.url) {
        window.location.href = response.data.url;
      }
    } catch (error) {
      console.error('Failed to open billing portal:', error);
      alert('Failed to open billing portal. Please try again.');
    } finally {
      setProcessingAction(null);
    }
  };

  const handleCancelSubscription = async () => {
    if (!subscription) {
      return;
    }

    const confirmed = confirm(
      "Are you sure you want to cancel your subscription? You'll continue to have access until the end of your billing period.",
    );

    if (!confirmed) {
      return;
    }

    try {
      setProcessingAction('cancel');
      await api.post(`/billing/subscription/${subscription.id}/cancel`, null, {
        params: { immediate: false },
      });

      await fetchBillingData();
      alert(
        "Subscription canceled successfully. You'll have access until the end of your billing period.",
      );
    } catch (error) {
      console.error('Failed to cancel subscription:', error);
      alert('Failed to cancel subscription. Please try again.');
    } finally {
      setProcessingAction(null);
    }
  };

  if (loading) {
    return (
      <div className='flex items-center justify-center min-h-screen'>
        <Loader2 className='h-8 w-8 animate-spin' />
      </div>
    );
  }

  return (
    <div className='space-y-6'>
      <div>
        <h1 className='text-3xl font-bold'>Billing & Subscription</h1>
        <p className='text-muted-foreground mt-2'>
          Manage your subscription, billing, and invoices
        </p>
      </div>

      {/* Current Subscription */}
      {subscription ? (
        <Card>
          <CardHeader>
            <CardTitle>Current Plan</CardTitle>
            <CardDescription>Your active subscription details</CardDescription>
          </CardHeader>
          <CardContent className='space-y-4'>
            <div className='flex items-center justify-between'>
              <div>
                <h3 className='text-2xl font-bold'>{subscription.plan.name}</h3>
                <p className='text-muted-foreground'>{subscription.plan.description}</p>
              </div>
              <Badge variant={subscription.status === 'active' ? 'default' : 'secondary'}>
                {subscription.status}
              </Badge>
            </div>

            <div className='grid grid-cols-2 gap-4'>
              <div>
                <p className='text-sm text-muted-foreground'>Billing Period</p>
                <p className='font-medium capitalize'>{subscription.billing_period}</p>
              </div>
              <div>
                <p className='text-sm text-muted-foreground'>Amount</p>
                <p className='font-medium'>
                  {formatCurrency(
                    subscription.billing_period === 'monthly'
                      ? subscription.plan.price_monthly
                      : subscription.plan.price_yearly,
                  )}
                  /{subscription.billing_period === 'monthly' ? 'mo' : 'yr'}
                </p>
              </div>
              <div>
                <p className='text-sm text-muted-foreground'>Current Period</p>
                <p className='font-medium'>
                  {formatDate(subscription.current_period_start)} -{' '}
                  {formatDate(subscription.current_period_end)}
                </p>
              </div>
              {subscription.is_trial && subscription.trial_end && (
                <div>
                  <p className='text-sm text-muted-foreground'>Trial Ends</p>
                  <p className='font-medium'>{formatDate(subscription.trial_end)}</p>
                </div>
              )}
            </div>

            {subscription.cancel_at_period_end && (
              <div className='bg-yellow-50 border border-yellow-200 rounded-md p-4'>
                <p className='text-sm text-yellow-800'>
                  Your subscription will be canceled at the end of the current billing period.
                </p>
              </div>
            )}

            <div className='flex gap-2'>
              <Button onClick={handleManageBilling} disabled={processingAction === 'portal'}>
                {processingAction === 'portal' && <Loader2 className='mr-2 h-4 w-4 animate-spin' />}
                <CreditCard className='mr-2 h-4 w-4' />
                Manage Billing
              </Button>
              {!subscription.cancel_at_period_end && (
                <Button
                  variant='outline'
                  onClick={handleCancelSubscription}
                  disabled={processingAction === 'cancel'}
                >
                  {processingAction === 'cancel' && (
                    <Loader2 className='mr-2 h-4 w-4 animate-spin' />
                  )}
                  Cancel Subscription
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>No Active Subscription</CardTitle>
            <CardDescription>Choose a plan to get started</CardDescription>
          </CardHeader>
        </Card>
      )}

      {/* Available Plans */}
      {!subscription && plans.length > 0 && (
        <div>
          <div className='flex items-center justify-between mb-4'>
            <h2 className='text-2xl font-bold'>Choose Your Plan</h2>
            <div className='flex items-center gap-2'>
              <Button
                variant={billingPeriod === 'monthly' ? 'default' : 'outline'}
                size='sm'
                onClick={() => setBillingPeriod('monthly')}
              >
                Monthly
              </Button>
              <Button
                variant={billingPeriod === 'yearly' ? 'default' : 'outline'}
                size='sm'
                onClick={() => setBillingPeriod('yearly')}
              >
                Yearly (Save 17%)
              </Button>
            </div>
          </div>

          <div className='grid md:grid-cols-3 gap-6'>
            {plans.map(plan => (
              <Card key={plan.id} className='relative'>
                <CardHeader>
                  <CardTitle>{plan.name}</CardTitle>
                  <CardDescription>{plan.description}</CardDescription>
                  <div className='mt-4'>
                    <span className='text-4xl font-bold'>
                      {formatCurrency(
                        billingPeriod === 'monthly' ? plan.price_monthly : plan.price_yearly,
                      )}
                    </span>
                    <span className='text-muted-foreground'>
                      /{billingPeriod === 'monthly' ? 'mo' : 'yr'}
                    </span>
                  </div>
                </CardHeader>
                <CardContent className='space-y-4'>
                  <div className='space-y-2'>
                    <p className='font-medium text-sm'>Features:</p>
                    <ul className='space-y-1'>
                      {Object.entries(plan.features)
                        .filter(([_, enabled]) => enabled)
                        .map(([feature]) => (
                          <li key={feature} className='flex items-center text-sm'>
                            <Check className='h-4 w-4 mr-2 text-green-500' />
                            {feature.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          </li>
                        ))}
                    </ul>
                  </div>

                  <div className='space-y-2'>
                    <p className='font-medium text-sm'>Limits:</p>
                    <ul className='space-y-1 text-sm text-muted-foreground'>
                      {Object.entries(plan.limits).map(([key, value]) => (
                        <li key={key}>
                          {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:{' '}
                          {value === -1 ? 'Unlimited' : value}
                        </li>
                      ))}
                    </ul>
                  </div>

                  <Button
                    className='w-full'
                    onClick={() => handleUpgrade(plan.id)}
                    disabled={processingAction === plan.id}
                  >
                    {processingAction === plan.id && (
                      <Loader2 className='mr-2 h-4 w-4 animate-spin' />
                    )}
                    Get Started
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Invoices */}
      {invoices.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Billing History</CardTitle>
            <CardDescription>Your past invoices and payments</CardDescription>
          </CardHeader>
          <CardContent>
            <div className='space-y-4'>
              {invoices.map(invoice => (
                <div
                  key={invoice.id}
                  className='flex items-center justify-between border-b pb-4 last:border-0'
                >
                  <div>
                    <p className='font-medium'>
                      {invoice.invoice_number || `Invoice #${invoice.id.slice(0, 8)}`}
                    </p>
                    <p className='text-sm text-muted-foreground'>
                      {formatDate(invoice.paid_at || invoice.created_at)}
                    </p>
                  </div>
                  <div className='flex items-center gap-4'>
                    <div className='text-right'>
                      <p className='font-medium'>{formatCurrency(invoice.amount)}</p>
                      <Badge variant={invoice.status === 'paid' ? 'default' : 'secondary'}>
                        {invoice.status}
                      </Badge>
                    </div>
                    {invoice.invoice_pdf && (
                      <Button
                        variant='ghost'
                        size='sm'
                        onClick={() => window.open(invoice.invoice_pdf!, '_blank')}
                      >
                        <Download className='h-4 w-4' />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
