'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/components/auth/auth-provider';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import {
  Star,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
  Building2,
  Mail,
  MessageSquare,
  Sparkles,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import api from '@/lib/api';

interface OnboardingData {
  business_type?: string;
  review_platforms?: string[];
  email_provider?: string;
  goals?: string[];
  team_size?: string;
}

const STEPS = [
  {
    id: 'welcome',
    title: 'Welcome to Revive AI',
    description: "Let's get you set up in just a few steps",
  },
  {
    id: 'business',
    title: 'Tell us about your business',
    description: 'Help us customize your experience',
  },
  {
    id: 'integrations',
    title: 'Connect your platforms',
    description: 'Choose which platforms you want to monitor',
  },
  {
    id: 'goals',
    title: 'What are your goals?',
    description: "We'll help you achieve them",
  },
  {
    id: 'complete',
    title: "You're all set!",
    description: "Let's start managing your reputation",
  },
];

const BUSINESS_TYPES = [
  { value: 'restaurant', label: 'Restaurant' },
  { value: 'retail', label: 'Retail Store' },
  { value: 'healthcare', label: 'Healthcare' },
  { value: 'hospitality', label: 'Hotel/Hospitality' },
  { value: 'services', label: 'Professional Services' },
  { value: 'other', label: 'Other' },
];

const REVIEW_PLATFORMS = [
  { value: 'google', label: 'Google Reviews', icon: '🔍' },
  { value: 'yelp', label: 'Yelp', icon: '⭐' },
  { value: 'facebook', label: 'Facebook', icon: '👥' },
  { value: 'trustpilot', label: 'Trustpilot', icon: '✓' },
];

const GOALS = [
  { value: 'improve_rating', label: 'Improve overall rating' },
  { value: 'respond_faster', label: 'Respond to reviews faster' },
  { value: 'reduce_churn', label: 'Reduce customer churn' },
  { value: 'automate_responses', label: 'Automate review responses' },
  { value: 'monitor_sentiment', label: 'Monitor customer sentiment' },
  { value: 'recover_customers', label: 'Recover at-risk customers' },
];

const TEAM_SIZES = [
  { value: '1-5', label: '1-5 employees' },
  { value: '6-20', label: '6-20 employees' },
  { value: '21-50', label: '21-50 employees' },
  { value: '51-200', label: '51-200 employees' },
  { value: '200+', label: '200+ employees' },
];

export default function OnboardingPage() {
  const [currentStep, setCurrentStep] = useState(0);
  const [onboardingData, setOnboardingData] = useState<OnboardingData>({});
  const [isLoading, setIsLoading] = useState(false);
  const { user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    // Check if user has already completed onboarding
    const checkOnboardingStatus = async () => {
      try {
        const response = await api.get('/users/me');
        if (response.data.onboarding_completed) {
          router.push('/dashboard');
        }
      } catch (error) {
        console.error('Failed to check onboarding status:', error);
      }
    };

    if (user) {
      checkOnboardingStatus();
    }
  }, [user, router]);

  const progress = ((currentStep + 1) / STEPS.length) * 100;

  const handleNext = () => {
    if (currentStep < STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleComplete = async () => {
    setIsLoading(true);
    try {
      // Save onboarding data
      await api.post('/users/complete-onboarding', {
        ...onboardingData,
        onboarding_completed: true,
      });

      router.push('/dashboard');
    } catch (error) {
      console.error('Failed to complete onboarding:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleSelection = (field: keyof OnboardingData, value: string) => {
    const currentValues = (onboardingData[field] as string[]) || [];
    const newValues = currentValues.includes(value)
      ? currentValues.filter(v => v !== value)
      : [...currentValues, value];

    setOnboardingData({ ...onboardingData, [field]: newValues });
  };

  const renderStepContent = () => {
    switch (STEPS[currentStep].id) {
      case 'welcome':
        return (
          <div className='text-center space-y-6 py-8'>
            <div className='flex justify-center'>
              <div className='h-20 w-20 rounded-full bg-blue-100 flex items-center justify-center'>
                <Star className='h-10 w-10 text-blue-600' />
              </div>
            </div>
            <div>
              <h2 className='text-2xl font-bold text-gray-900 mb-2'>
                Welcome to Revive AI, {user?.email?.split('@')[0]}!
              </h2>
              <p className='text-gray-600'>
                We're excited to help you manage your online reputation and recover at-risk
                customers.
              </p>
            </div>
            <div className='grid grid-cols-1 md:grid-cols-3 gap-4 pt-4'>
              <div className='p-4 bg-blue-50 rounded-lg'>
                <MessageSquare className='h-8 w-8 text-blue-600 mx-auto mb-2' />
                <h3 className='font-semibold text-sm mb-1'>Monitor Reviews</h3>
                <p className='text-xs text-gray-600'>Track reviews across all platforms</p>
              </div>
              <div className='p-4 bg-green-50 rounded-lg'>
                <Sparkles className='h-8 w-8 text-green-600 mx-auto mb-2' />
                <h3 className='font-semibold text-sm mb-1'>AI-Powered Responses</h3>
                <p className='text-xs text-gray-600'>Generate smart, compliant replies</p>
              </div>
              <div className='p-4 bg-purple-50 rounded-lg'>
                <CheckCircle2 className='h-8 w-8 text-purple-600 mx-auto mb-2' />
                <h3 className='font-semibold text-sm mb-1'>Recover Customers</h3>
                <p className='text-xs text-gray-600'>Prevent churn with proactive outreach</p>
              </div>
            </div>
          </div>
        );

      case 'business':
        return (
          <div className='space-y-6'>
            <div className='space-y-4'>
              <div>
                <Label className='text-base font-semibold mb-3 block'>
                  What type of business do you run?
                </Label>
                <div className='grid grid-cols-2 gap-3'>
                  {BUSINESS_TYPES.map(type => (
                    <button
                      key={type.value}
                      onClick={() =>
                        setOnboardingData({ ...onboardingData, business_type: type.value })
                      }
                      className={cn(
                        'p-4 border-2 rounded-lg text-left transition-all hover:border-blue-300',
                        onboardingData.business_type === type.value
                          ? 'border-blue-600 bg-blue-50'
                          : 'border-gray-200',
                      )}
                    >
                      <Building2 className='h-5 w-5 mb-2 text-gray-600' />
                      <div className='font-medium'>{type.label}</div>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <Label className='text-base font-semibold mb-3 block'>
                  How large is your team?
                </Label>
                <div className='grid grid-cols-1 gap-2'>
                  {TEAM_SIZES.map(size => (
                    <button
                      key={size.value}
                      onClick={() =>
                        setOnboardingData({ ...onboardingData, team_size: size.value })
                      }
                      className={cn(
                        'p-3 border-2 rounded-lg text-left transition-all hover:border-blue-300',
                        onboardingData.team_size === size.value
                          ? 'border-blue-600 bg-blue-50'
                          : 'border-gray-200',
                      )}
                    >
                      <div className='font-medium'>{size.label}</div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        );

      case 'integrations':
        return (
          <div className='space-y-6'>
            <div>
              <Label className='text-base font-semibold mb-3 block'>
                Which review platforms do you want to monitor?
              </Label>
              <p className='text-sm text-gray-600 mb-4'>
                Select all that apply. You can add more later.
              </p>
              <div className='grid grid-cols-1 md:grid-cols-2 gap-3'>
                {REVIEW_PLATFORMS.map(platform => (
                  <button
                    key={platform.value}
                    onClick={() => toggleSelection('review_platforms', platform.value)}
                    className={cn(
                      'p-4 border-2 rounded-lg text-left transition-all hover:border-blue-300 flex items-center',
                      (onboardingData.review_platforms || []).includes(platform.value)
                        ? 'border-blue-600 bg-blue-50'
                        : 'border-gray-200',
                    )}
                  >
                    <span className='text-2xl mr-3'>{platform.icon}</span>
                    <div className='flex-1'>
                      <div className='font-medium'>{platform.label}</div>
                    </div>
                    {(onboardingData.review_platforms || []).includes(platform.value) && (
                      <CheckCircle2 className='h-5 w-5 text-blue-600' />
                    )}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <Label className='text-base font-semibold mb-3 block'>
                Email provider (optional)
              </Label>
              <Input
                type='text'
                placeholder='e.g., Gmail, Outlook, SendGrid'
                value={onboardingData.email_provider || ''}
                onChange={e =>
                  setOnboardingData({ ...onboardingData, email_provider: e.target.value })
                }
                className='max-w-md'
              />
              <p className='text-xs text-gray-500 mt-1'>
                We'll use this to send recovery emails to customers
              </p>
            </div>
          </div>
        );

      case 'goals':
        return (
          <div className='space-y-6'>
            <div>
              <Label className='text-base font-semibold mb-3 block'>
                What do you want to achieve with Revive AI?
              </Label>
              <p className='text-sm text-gray-600 mb-4'>
                Select all that apply. We'll prioritize these in your dashboard.
              </p>
              <div className='grid grid-cols-1 gap-3'>
                {GOALS.map(goal => (
                  <button
                    key={goal.value}
                    onClick={() => toggleSelection('goals', goal.value)}
                    className={cn(
                      'p-4 border-2 rounded-lg text-left transition-all hover:border-blue-300 flex items-center',
                      (onboardingData.goals || []).includes(goal.value)
                        ? 'border-blue-600 bg-blue-50'
                        : 'border-gray-200',
                    )}
                  >
                    <div className='flex-1'>
                      <div className='font-medium'>{goal.label}</div>
                    </div>
                    {(onboardingData.goals || []).includes(goal.value) && (
                      <CheckCircle2 className='h-5 w-5 text-blue-600' />
                    )}
                  </button>
                ))}
              </div>
            </div>
          </div>
        );

      case 'complete':
        return (
          <div className='text-center space-y-6 py-8'>
            <div className='flex justify-center'>
              <div className='h-20 w-20 rounded-full bg-green-100 flex items-center justify-center'>
                <CheckCircle2 className='h-10 w-10 text-green-600' />
              </div>
            </div>
            <div>
              <h2 className='text-2xl font-bold text-gray-900 mb-2'>You're all set!</h2>
              <p className='text-gray-600'>
                Your Revive AI workspace is ready. Let's start improving your reputation.
              </p>
            </div>
            <div className='bg-blue-50 border border-blue-200 rounded-lg p-6 text-left max-w-md mx-auto'>
              <h3 className='font-semibold text-blue-900 mb-3'>What's next?</h3>
              <ul className='space-y-2 text-sm text-blue-800'>
                <li className='flex items-start'>
                  <CheckCircle2 className='h-4 w-4 mr-2 mt-0.5 flex-shrink-0' />
                  <span>Connect your review platforms in Settings</span>
                </li>
                <li className='flex items-start'>
                  <CheckCircle2 className='h-4 w-4 mr-2 mt-0.5 flex-shrink-0' />
                  <span>Import your existing reviews</span>
                </li>
                <li className='flex items-start'>
                  <CheckCircle2 className='h-4 w-4 mr-2 mt-0.5 flex-shrink-0' />
                  <span>Set up automated response rules</span>
                </li>
                <li className='flex items-start'>
                  <CheckCircle2 className='h-4 w-4 mr-2 mt-0.5 flex-shrink-0' />
                  <span>Invite your team members</span>
                </li>
              </ul>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className='min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 py-12 px-4 sm:px-6 lg:px-8'>
      <div className='max-w-3xl mx-auto'>
        {/* Progress bar */}
        <div className='mb-8'>
          <div className='flex items-center justify-between mb-2'>
            <span className='text-sm font-medium text-gray-700'>
              Step {currentStep + 1} of {STEPS.length}
            </span>
            <span className='text-sm text-gray-500'>{Math.round(progress)}% complete</span>
          </div>
          <Progress value={progress} className='h-2' />
        </div>

        {/* Main card */}
        <Card className='shadow-xl'>
          <CardHeader>
            <CardTitle className='text-2xl'>{STEPS[currentStep].title}</CardTitle>
            <CardDescription className='text-base'>
              {STEPS[currentStep].description}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {renderStepContent()}

            {/* Navigation buttons */}
            <div className='flex justify-between mt-8 pt-6 border-t'>
              <Button
                variant='outline'
                onClick={handleBack}
                disabled={currentStep === 0}
                className='min-w-[100px]'
              >
                <ArrowLeft className='h-4 w-4 mr-2' />
                Back
              </Button>

              {currentStep === STEPS.length - 1 ? (
                <Button onClick={handleComplete} disabled={isLoading} className='min-w-[150px]'>
                  {isLoading ? 'Completing...' : 'Go to Dashboard'}
                  <ArrowRight className='h-4 w-4 ml-2' />
                </Button>
              ) : (
                <Button onClick={handleNext} className='min-w-[100px]'>
                  Next
                  <ArrowRight className='h-4 w-4 ml-2' />
                </Button>
              )}
            </div>

            {/* Skip option */}
            {currentStep > 0 && currentStep < STEPS.length - 1 && (
              <div className='text-center mt-4'>
                <button
                  onClick={() => setCurrentStep(STEPS.length - 1)}
                  className='text-sm text-gray-500 hover:text-gray-700'
                >
                  Skip to dashboard
                </button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
