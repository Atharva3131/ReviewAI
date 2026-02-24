'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Star,
  TrendingUp,
  Users,
  MessageSquare,
  Zap,
  Shield,
  BarChart3,
  CheckCircle2,
  ArrowRight,
  Sparkles,
} from 'lucide-react';
import Link from 'next/link';

export default function LandingPage() {
  return (
    <div className='min-h-screen bg-gradient-to-b from-white to-gray-50'>
      {/* Header */}
      <header className='border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50'>
        <div className='container mx-auto px-4 py-4 flex items-center justify-between'>
          <Link href='/' className='flex items-center gap-2'>
            <Sparkles className='h-8 w-8 text-primary' />
            <span className='text-2xl font-bold text-primary'>ReviewAI <span className='text-sm font-normal text-muted-foreground'>Beta</span></span>
          </Link>
          <nav className='hidden md:flex items-center gap-6'>
            <Link
              href='#features'
              className='text-sm font-medium hover:text-primary transition-colors'
            >
              Features
            </Link>
            <Link
              href='#how-it-works'
              className='text-sm font-medium hover:text-primary transition-colors'
            >
              How It Works
            </Link>
            <Link
              href='/pricing'
              className='text-sm font-medium hover:text-primary transition-colors'
            >
              Pricing
            </Link>
            <Link
              href='#testimonials'
              className='text-sm font-medium hover:text-primary transition-colors'
            >
              Testimonials
            </Link>
          </nav>
          <div className='flex items-center gap-3'>
            <Link href='/login'>
              <Button variant='ghost' size='sm'>
                Sign In
              </Button>
            </Link>
            <Link href='/register'>
              <Button size='sm'>
                Get Started Free
                <ArrowRight className='ml-2 h-4 w-4' />
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className='container mx-auto px-4 py-20 md:py-32'>
        <div className='max-w-4xl mx-auto text-center'>
          <Badge className='mb-4' variant='secondary'>
            <Sparkles className='h-3 w-3 mr-1' />
            AI-Powered Reputation Management
          </Badge>
          <h1 className='text-5xl md:text-6xl lg:text-7xl font-bold mb-6 bg-gradient-to-r from-primary to-blue-600 bg-clip-text text-transparent'>
            Turn Negative Reviews Into Revenue
          </h1>
          <p className='text-xl md:text-2xl text-muted-foreground mb-8 max-w-3xl mx-auto'>
            Automatically monitor reviews, predict customer churn, and take intelligent recovery
            actions to improve your ratings, retention, and revenue.
          </p>
          <div className='flex flex-col sm:flex-row gap-4 justify-center items-center'>
            <Link href='/register'>
              <Button size='lg' className='text-lg px-8'>
                Start Free Trial
                <ArrowRight className='ml-2 h-5 w-5' />
              </Button>
            </Link>
            <Link href='/pricing'>
              <Button size='lg' variant='outline' className='text-lg px-8'>
                View Pricing
              </Button>
            </Link>
          </div>
          <p className='text-sm text-muted-foreground mt-4'>
            14-day free trial • No credit card required • Cancel anytime
          </p>
        </div>

        {/* Stats */}
        <div className='grid md:grid-cols-3 gap-8 max-w-4xl mx-auto mt-20'>
          <div className='text-center'>
            <div className='text-4xl font-bold text-primary mb-2'>78%</div>
            <p className='text-muted-foreground'>Average Recovery Success Rate</p>
          </div>
          <div className='text-center'>
            <div className='text-4xl font-bold text-primary mb-2'>4.2★</div>
            <p className='text-muted-foreground'>Average Rating Improvement</p>
          </div>
          <div className='text-center'>
            <div className='text-4xl font-bold text-primary mb-2'>24/7</div>
            <p className='text-muted-foreground'>Automated Monitoring</p>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id='features' className='container mx-auto px-4 py-20 bg-white'>
        <div className='text-center mb-16'>
          <Badge className='mb-4' variant='secondary'>
            Features
          </Badge>
          <h2 className='text-4xl md:text-5xl font-bold mb-4'>
            Everything You Need to Protect Your Reputation
          </h2>
          <p className='text-xl text-muted-foreground max-w-2xl mx-auto'>
            Powered by advanced AI and intelligent automation to help you stay ahead of customer
            issues
          </p>
        </div>

        <div className='grid md:grid-cols-2 lg:grid-cols-3 gap-8 max-w-6xl mx-auto'>
          <Card className='border-2 hover:border-primary transition-colors'>
            <CardHeader>
              <Star className='h-12 w-12 text-primary mb-4' />
              <CardTitle>Review Intelligence</CardTitle>
              <CardDescription>
                Automatically collect and analyze reviews from Google, Yelp, and other platforms
                with AI-powered sentiment analysis
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className='border-2 hover:border-primary transition-colors'>
            <CardHeader>
              <TrendingUp className='h-12 w-12 text-primary mb-4' />
              <CardTitle>Churn Prediction</CardTitle>
              <CardDescription>
                Identify at-risk customers before they leave negative reviews using predictive
                analytics and behavioral patterns
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className='border-2 hover:border-primary transition-colors'>
            <CardHeader>
              <MessageSquare className='h-12 w-12 text-primary mb-4' />
              <CardTitle>Smart Responses</CardTitle>
              <CardDescription>
                Generate policy-compliant, human-like responses to reviews that maintain your brand
                voice and customer engagement
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className='border-2 hover:border-primary transition-colors'>
            <CardHeader>
              <Users className='h-12 w-12 text-primary mb-4' />
              <CardTitle>Customer Recovery</CardTitle>
              <CardDescription>
                Automated recovery actions including personalized emails, discount offers, and
                callback scheduling for at-risk customers
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className='border-2 hover:border-primary transition-colors'>
            <CardHeader>
              <Zap className='h-12 w-12 text-primary mb-4' />
              <CardTitle>Agent Orchestration</CardTitle>
              <CardDescription>
                Intelligent routing between automated responses and human escalation based on
                urgency, sentiment, and complexity
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className='border-2 hover:border-primary transition-colors'>
            <CardHeader>
              <BarChart3 className='h-12 w-12 text-primary mb-4' />
              <CardTitle>Real-Time Analytics</CardTitle>
              <CardDescription>
                Track sentiment trends, response rates, recovery success, and ROI with comprehensive
                dashboards and reports
              </CardDescription>
            </CardHeader>
          </Card>
        </div>
      </section>

      {/* How It Works Section */}
      <section id='how-it-works' className='container mx-auto px-4 py-20'>
        <div className='text-center mb-16'>
          <Badge className='mb-4' variant='secondary'>
            How It Works
          </Badge>
          <h2 className='text-4xl md:text-5xl font-bold mb-4'>Simple Setup, Powerful Results</h2>
          <p className='text-xl text-muted-foreground max-w-2xl mx-auto'>
            Get started in minutes and let AI handle your reputation management
          </p>
        </div>

        <div className='max-w-4xl mx-auto space-y-12'>
          <div className='flex flex-col md:flex-row gap-8 items-center'>
            <div className='flex-shrink-0 w-16 h-16 rounded-full bg-primary text-white flex items-center justify-center text-2xl font-bold'>
              1
            </div>
            <div className='flex-1'>
              <h3 className='text-2xl font-bold mb-2'>Connect Your Platforms</h3>
              <p className='text-muted-foreground text-lg'>
                Link your Google Reviews, support tickets, and CRM systems in just a few clicks.
                We'll start monitoring immediately.
              </p>
            </div>
          </div>

          <div className='flex flex-col md:flex-row gap-8 items-center'>
            <div className='flex-shrink-0 w-16 h-16 rounded-full bg-primary text-white flex items-center justify-center text-2xl font-bold'>
              2
            </div>
            <div className='flex-1'>
              <h3 className='text-2xl font-bold mb-2'>AI Analyzes Everything</h3>
              <p className='text-muted-foreground text-lg'>
                Our AI engine processes reviews and customer interactions, calculating sentiment
                scores, urgency levels, and churn risk in real-time.
              </p>
            </div>
          </div>

          <div className='flex flex-col md:flex-row gap-8 items-center'>
            <div className='flex-shrink-0 w-16 h-16 rounded-full bg-primary text-white flex items-center justify-center text-2xl font-bold'>
              3
            </div>
            <div className='flex-1'>
              <h3 className='text-2xl font-bold mb-2'>Automated Actions</h3>
              <p className='text-muted-foreground text-lg'>
                ReviewAI automatically responds to reviews, sends recovery emails, and escalates
                critical cases to your team - all while you focus on your business.
              </p>
            </div>
          </div>

          <div className='flex flex-col md:flex-row gap-8 items-center'>
            <div className='flex-shrink-0 w-16 h-16 rounded-full bg-primary text-white flex items-center justify-center text-2xl font-bold'>
              4
            </div>
            <div className='flex-1'>
              <h3 className='text-2xl font-bold mb-2'>Track Your Success</h3>
              <p className='text-muted-foreground text-lg'>
                Monitor improvements in your ratings, customer retention, and revenue through
                comprehensive dashboards and detailed analytics.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section className='container mx-auto px-4 py-20 bg-white'>
        <div className='max-w-6xl mx-auto'>
          <div className='grid md:grid-cols-2 gap-12 items-center'>
            <div>
              <Badge className='mb-4' variant='secondary'>
                Why Choose ReviewAI
              </Badge>
              <h2 className='text-4xl font-bold mb-6'>Built for Modern Businesses</h2>
              <div className='space-y-4'>
                <div className='flex gap-3'>
                  <CheckCircle2 className='h-6 w-6 text-primary flex-shrink-0 mt-1' />
                  <div>
                    <h4 className='font-semibold mb-1'>Save Time & Resources</h4>
                    <p className='text-muted-foreground'>
                      Automate 80% of review responses and customer recovery actions
                    </p>
                  </div>
                </div>
                <div className='flex gap-3'>
                  <CheckCircle2 className='h-6 w-6 text-primary flex-shrink-0 mt-1' />
                  <div>
                    <h4 className='font-semibold mb-1'>Improve Customer Retention</h4>
                    <p className='text-muted-foreground'>
                      Identify and recover at-risk customers before they churn
                    </p>
                  </div>
                </div>
                <div className='flex gap-3'>
                  <CheckCircle2 className='h-6 w-6 text-primary flex-shrink-0 mt-1' />
                  <div>
                    <h4 className='font-semibold mb-1'>Boost Your Ratings</h4>
                    <p className='text-muted-foreground'>
                      Turn negative experiences into positive outcomes with proactive recovery
                    </p>
                  </div>
                </div>
                <div className='flex gap-3'>
                  <CheckCircle2 className='h-6 w-6 text-primary flex-shrink-0 mt-1' />
                  <div>
                    <h4 className='font-semibold mb-1'>Enterprise-Grade Security</h4>
                    <p className='text-muted-foreground'>
                      GDPR compliant with encryption, audit logs, and multi-tenant isolation
                    </p>
                  </div>
                </div>
                <div className='flex gap-3'>
                  <CheckCircle2 className='h-6 w-6 text-primary flex-shrink-0 mt-1' />
                  <div>
                    <h4 className='font-semibold mb-1'>Seamless Integrations</h4>
                    <p className='text-muted-foreground'>
                      Works with Google Reviews, email, WhatsApp, and major CRM systems
                    </p>
                  </div>
                </div>
              </div>
            </div>
            <div className='bg-gradient-to-br from-primary/10 to-blue-600/10 rounded-2xl p-8'>
              <Shield className='h-20 w-20 text-primary mb-6' />
              <h3 className='text-2xl font-bold mb-4'>Trusted by Businesses Worldwide</h3>
              <p className='text-muted-foreground mb-6'>
                Join hundreds of companies using ReviewAI to protect and enhance their online
                reputation
              </p>
              <div className='space-y-3'>
                <div className='flex items-center gap-2'>
                  <Star className='h-5 w-5 text-yellow-500 fill-yellow-500' />
                  <span className='font-semibold'>4.9/5 Average Customer Rating</span>
                </div>
                <div className='flex items-center gap-2'>
                  <CheckCircle2 className='h-5 w-5 text-green-500' />
                  <span className='font-semibold'>99.9% Uptime SLA</span>
                </div>
                <div className='flex items-center gap-2'>
                  <Shield className='h-5 w-5 text-blue-500' />
                  <span className='font-semibold'>SOC 2 Type II Certified</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Testimonials Section */}
      <section id='testimonials' className='container mx-auto px-4 py-20'>
        <div className='text-center mb-16'>
          <Badge className='mb-4' variant='secondary'>
            Testimonials
          </Badge>
          <h2 className='text-4xl md:text-5xl font-bold mb-4'>Loved by Business Owners</h2>
          <p className='text-xl text-muted-foreground max-w-2xl mx-auto'>
            See how ReviewAI is helping businesses improve their reputation and revenue
          </p>
        </div>

        <div className='grid md:grid-cols-3 gap-8 max-w-6xl mx-auto'>
          <Card>
            <CardHeader>
              <div className='flex gap-1 mb-4'>
                {[...Array(5)].map((_, i) => (
                  <Star key={i} className='h-5 w-5 text-yellow-500 fill-yellow-500' />
                ))}
              </div>
              <CardDescription className='text-base'>
                "ReviewAI helped us improve our Google rating from 3.8 to 4.5 in just 3 months. The
                automated recovery emails are incredibly effective!"
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className='font-semibold'>Sarah Johnson</p>
              <p className='text-sm text-muted-foreground'>Owner, Local Restaurant Chain</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className='flex gap-1 mb-4'>
                {[...Array(5)].map((_, i) => (
                  <Star key={i} className='h-5 w-5 text-yellow-500 fill-yellow-500' />
                ))}
              </div>
              <CardDescription className='text-base'>
                "The churn prediction feature is a game-changer. We've reduced customer churn by 35%
                by proactively addressing issues before they escalate."
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className='font-semibold'>Michael Chen</p>
              <p className='text-sm text-muted-foreground'>CEO, SaaS Startup</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className='flex gap-1 mb-4'>
                {[...Array(5)].map((_, i) => (
                  <Star key={i} className='h-5 w-5 text-yellow-500 fill-yellow-500' />
                ))}
              </div>
              <CardDescription className='text-base'>
                "Finally, a tool that actually saves us time! The AI responses are so good that we
                rarely need to intervene. Highly recommended!"
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className='font-semibold'>Emily Rodriguez</p>
              <p className='text-sm text-muted-foreground'>Marketing Director, E-commerce</p>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* CTA Section */}
      <section className='container mx-auto px-4 py-20 bg-gradient-to-r from-primary to-blue-600 rounded-3xl text-white'>
        <div className='max-w-3xl mx-auto text-center'>
          <h2 className='text-4xl md:text-5xl font-bold mb-6'>
            Ready to Transform Your Reputation?
          </h2>
          <p className='text-xl mb-8 opacity-90'>
            Join hundreds of businesses using ReviewAI to improve ratings, retention, and revenue
          </p>
          <div className='flex flex-col sm:flex-row gap-4 justify-center'>
            <Link href='/register'>
              <Button size='lg' variant='secondary' className='text-lg px-8'>
                Start Free Trial
                <ArrowRight className='ml-2 h-5 w-5' />
              </Button>
            </Link>
            <Link href='/pricing'>
              <Button
                size='lg'
                variant='outline'
                className='text-lg px-8 bg-transparent text-white border-white hover:bg-white/10'
              >
                View Pricing
              </Button>
            </Link>
          </div>
          <p className='text-sm mt-4 opacity-75'>
            14-day free trial • No credit card required • Cancel anytime
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className='border-t py-12 bg-white'>
        <div className='container mx-auto px-4'>
          <div className='grid md:grid-cols-4 gap-8 mb-8'>
            <div>
              <div className='flex items-center gap-2 mb-4'>
                <Sparkles className='h-6 w-6 text-primary' />
                <span className='text-xl font-bold'>ReviewAI <span className='text-sm font-normal text-muted-foreground'>Beta</span></span>
              </div>
              <p className='text-sm text-muted-foreground'>
                AI-powered reputation management for modern businesses
              </p>
            </div>
            <div>
              <h4 className='font-semibold mb-4'>Product</h4>
              <ul className='space-y-2 text-sm text-muted-foreground'>
                <li>
                  <Link href='#features' className='hover:text-primary'>
                    Features
                  </Link>
                </li>
                <li>
                  <Link href='/pricing' className='hover:text-primary'>
                    Pricing
                  </Link>
                </li>
                <li>
                  <Link href='#how-it-works' className='hover:text-primary'>
                    How It Works
                  </Link>
                </li>
                <li>
                  <Link href='#testimonials' className='hover:text-primary'>
                    Testimonials
                  </Link>
                </li>
              </ul>
            </div>
            <div>
              <h4 className='font-semibold mb-4'>Company</h4>
              <ul className='space-y-2 text-sm text-muted-foreground'>
                <li>
                  <Link href='#' className='hover:text-primary'>
                    About Us
                  </Link>
                </li>
                <li>
                  <Link href='#' className='hover:text-primary'>
                    Blog
                  </Link>
                </li>
                <li>
                  <Link href='#' className='hover:text-primary'>
                    Careers
                  </Link>
                </li>
                <li>
                  <Link href='#' className='hover:text-primary'>
                    Contact
                  </Link>
                </li>
              </ul>
            </div>
            <div>
              <h4 className='font-semibold mb-4'>Legal</h4>
              <ul className='space-y-2 text-sm text-muted-foreground'>
                <li>
                  <Link href='#' className='hover:text-primary'>
                    Privacy Policy
                  </Link>
                </li>
                <li>
                  <Link href='#' className='hover:text-primary'>
                    Terms of Service
                  </Link>
                </li>
                <li>
                  <Link href='#' className='hover:text-primary'>
                    Security
                  </Link>
                </li>
                <li>
                  <Link href='#' className='hover:text-primary'>
                    GDPR
                  </Link>
                </li>
              </ul>
            </div>
          </div>
          <div className='border-t pt-8 text-center text-sm text-muted-foreground'>
            <p>&copy; 2026 ReviewAI. All rights reserved.</p>
            <p className='mt-2 text-xs'>
              Powered by <span className='font-semibold'>Axionyx Labs</span>
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
