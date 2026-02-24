'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Check, Loader2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

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

export default function PricingPage() {
  const router = useRouter();
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [billingPeriod, setBillingPeriod] = useState<'monthly' | 'yearly'>('monthly');

  useEffect(() => {
    fetchPlans();
  }, []);

  const fetchPlans = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/billing/plans`);
      const data = await response.json();
      setPlans(data);
    } catch (error) {
      console.error('Failed to fetch plans:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectPlan = (planId: string) => {
    // Redirect to registration with plan selection
    router.push(`/register?plan=${planId}&period=${billingPeriod}`);
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(amount);
  };

  if (loading) {
    return (
      <div className='flex items-center justify-center min-h-screen'>
        <Loader2 className='h-8 w-8 animate-spin' />
      </div>
    );
  }

  return (
    <div className='min-h-screen bg-gradient-to-b from-gray-50 to-white'>
      {/* Header */}
      <header className='border-b'>
        <div className='container mx-auto px-4 py-4 flex items-center justify-between'>
          <Link href='/' className='text-2xl font-bold text-primary'>
            ReviewAI <span className='text-sm font-normal text-muted-foreground'>Beta</span>
          </Link>
          <div className='flex items-center gap-4'>
            <Link href='/login'>
              <Button variant='ghost'>Sign In</Button>
            </Link>
            <Link href='/register'>
              <Button>Get Started</Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className='container mx-auto px-4 py-16 text-center'>
        <h1 className='text-5xl font-bold mb-4'>Simple, Transparent Pricing</h1>
        <p className='text-xl text-muted-foreground mb-8 max-w-2xl mx-auto'>
          Choose the perfect plan for your business. All plans include a 14-day free trial.
        </p>

        {/* Billing Toggle */}
        <div className='flex items-center justify-center gap-4 mb-12'>
          <Button
            variant={billingPeriod === 'monthly' ? 'default' : 'outline'}
            onClick={() => setBillingPeriod('monthly')}
          >
            Monthly
          </Button>
          <Button
            variant={billingPeriod === 'yearly' ? 'default' : 'outline'}
            onClick={() => setBillingPeriod('yearly')}
          >
            Yearly
            <Badge variant='secondary' className='ml-2'>
              Save 17%
            </Badge>
          </Button>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className='container mx-auto px-4 pb-16'>
        <div className='grid md:grid-cols-3 gap-8 max-w-6xl mx-auto'>
          {plans.map((plan, index) => (
            <Card
              key={plan.id}
              className={`relative ${index === 1 ? 'border-primary shadow-lg scale-105' : ''}`}
            >
              {index === 1 && (
                <div className='absolute -top-4 left-1/2 transform -translate-x-1/2'>
                  <Badge className='px-4 py-1'>Most Popular</Badge>
                </div>
              )}

              <CardHeader className='text-center'>
                <CardTitle className='text-2xl'>{plan.name}</CardTitle>
                <CardDescription className='mt-2'>{plan.description}</CardDescription>

                <div className='mt-6'>
                  <span className='text-5xl font-bold'>
                    {formatCurrency(
                      billingPeriod === 'monthly' ? plan.price_monthly : plan.price_yearly,
                    )}
                  </span>
                  <span className='text-muted-foreground text-lg'>
                    /{billingPeriod === 'monthly' ? 'month' : 'year'}
                  </span>
                </div>

                {billingPeriod === 'yearly' && (
                  <p className='text-sm text-muted-foreground mt-2'>
                    {formatCurrency(plan.price_yearly / 12)}/month billed annually
                  </p>
                )}
              </CardHeader>

              <CardContent className='space-y-6'>
                {/* Features */}
                <div className='space-y-3'>
                  {Object.entries(plan.features)
                    .filter(([_, enabled]) => enabled)
                    .map(([feature]) => (
                      <div key={feature} className='flex items-start'>
                        <Check className='h-5 w-5 mr-3 text-green-500 flex-shrink-0 mt-0.5' />
                        <span className='text-sm'>
                          {feature.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        </span>
                      </div>
                    ))}
                </div>

                {/* Limits */}
                <div className='border-t pt-4 space-y-2'>
                  <p className='font-medium text-sm'>Plan Limits:</p>
                  {Object.entries(plan.limits).map(([key, value]) => (
                    <div key={key} className='flex justify-between text-sm'>
                      <span className='text-muted-foreground'>
                        {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                      </span>
                      <span className='font-medium'>
                        {value === -1 ? 'Unlimited' : value.toLocaleString()}
                      </span>
                    </div>
                  ))}
                </div>

                <Button
                  className='w-full'
                  variant={index === 1 ? 'default' : 'outline'}
                  size='lg'
                  onClick={() => handleSelectPlan(plan.id)}
                >
                  Start Free Trial
                </Button>

                <p className='text-xs text-center text-muted-foreground'>
                  14-day free trial • No credit card required
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* FAQ Section */}
      <section className='container mx-auto px-4 py-16 border-t'>
        <h2 className='text-3xl font-bold text-center mb-12'>Frequently Asked Questions</h2>

        <div className='max-w-3xl mx-auto space-y-6'>
          <Card>
            <CardHeader>
              <CardTitle className='text-lg'>Can I change plans later?</CardTitle>
            </CardHeader>
            <CardContent>
              <p className='text-muted-foreground'>
                Yes! You can upgrade or downgrade your plan at any time. Changes will be prorated
                and reflected in your next billing cycle.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className='text-lg'>What payment methods do you accept?</CardTitle>
            </CardHeader>
            <CardContent>
              <p className='text-muted-foreground'>
                We accept all major credit cards (Visa, MasterCard, American Express) through our
                secure payment processor, Stripe.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className='text-lg'>Can I cancel anytime?</CardTitle>
            </CardHeader>
            <CardContent>
              <p className='text-muted-foreground'>
                Absolutely. You can cancel your subscription at any time. You'll continue to have
                access until the end of your billing period.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className='text-lg'>Do you offer refunds?</CardTitle>
            </CardHeader>
            <CardContent>
              <p className='text-muted-foreground'>
                We offer a 30-day money-back guarantee. If you're not satisfied with ReviewAI within
                the first 30 days, contact us for a full refund.
              </p>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Footer */}
      <footer className='border-t py-8'>
        <div className='container mx-auto px-4 text-center text-muted-foreground'>
          <p>&copy; 2026 ReviewAI. All rights reserved.</p>
          <p className='mt-2 text-xs'>
            Powered by <span className='font-semibold'>Axionyx Labs</span>
          </p>
        </div>
      </footer>
    </div>
  );
}
