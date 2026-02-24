'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Settings,
  Building,
  Users,
  Bot,
  Bell,
  Key,
  Plug,
  Save,
  Upload,
  Globe,
  Clock,
  Palette,
  Shield,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Organization, OrganizationSettings } from '@/types/settings';
import api from '@/lib/api';

const TIMEZONES = [
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'Europe/London',
  'Europe/Paris',
  'Asia/Tokyo',
  'Asia/Shanghai',
  'Australia/Sydney',
];

const INDUSTRIES = [
  'Restaurant',
  'Retail',
  'Healthcare',
  'Technology',
  'Finance',
  'Education',
  'Real Estate',
  'Automotive',
  'Other',
];

const COMPANY_SIZES = [
  { value: 'startup', label: '1-10 employees' },
  { value: 'small', label: '11-50 employees' },
  { value: 'medium', label: '51-200 employees' },
  { value: 'large', label: '201-1000 employees' },
  { value: 'enterprise', label: '1000+ employees' },
];

export default function SettingsPage() {
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('general');

  useEffect(() => {
    fetchOrganization();
  }, []);

  const fetchOrganization = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.get('/organization');
      setOrganization(response.data);
    } catch (err: any) {
      console.error('Error fetching organization:', err);
      setError('Failed to load organization settings');

      // Mock data for development
      const mockOrganization: Organization = {
        id: '1',
        name: 'Acme Restaurant Group',
        slug: 'acme-restaurant',
        description: 'A family of restaurants serving quality food since 1985',
        website: 'https://acmerestaurants.com',
        industry: 'Restaurant',
        size: 'medium',
        timezone: 'America/New_York',
        country: 'United States',
        logo_url: '/logo.png',
        created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 365).toISOString(),
        updated_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 30).toISOString(),
        settings: {
          business_hours: {
            enabled: true,
            timezone: 'America/New_York',
            schedule: {
              monday: { enabled: true, start: '09:00', end: '22:00' },
              tuesday: { enabled: true, start: '09:00', end: '22:00' },
              wednesday: { enabled: true, start: '09:00', end: '22:00' },
              thursday: { enabled: true, start: '09:00', end: '22:00' },
              friday: { enabled: true, start: '09:00', end: '23:00' },
              saturday: { enabled: true, start: '10:00', end: '23:00' },
              sunday: { enabled: true, start: '10:00', end: '21:00' },
            },
          },
          review_settings: {
            auto_response_enabled: true,
            response_delay_minutes: 30,
            escalation_threshold: 2,
            sentiment_threshold: 0.3,
            require_approval: false,
          },
          recovery_settings: {
            auto_recovery_enabled: true,
            churn_threshold: 0.7,
            recovery_delay_hours: 24,
            max_recovery_attempts: 3,
          },
          notifications: {
            email_enabled: true,
            sms_enabled: false,
            slack_enabled: true,
            webhook_enabled: false,
            notification_types: {
              new_review: true,
              negative_review: true,
              high_risk_customer: true,
              recovery_success: true,
              system_alerts: true,
            },
          },
          branding: {
            primary_color: '#3B82F6',
            secondary_color: '#10B981',
            logo_url: '/logo.png',
          },
        },
      };
      setOrganization(mockOrganization);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    if (!organization) {
      return;
    }

    setIsSaving(true);
    try {
      await api.put('/organization', organization);
      // Show success message
    } catch (error) {
      console.error('Error saving organization:', error);
      setError('Failed to save settings');
    } finally {
      setIsSaving(false);
    }
  };

  const updateOrganization = (updates: Partial<Organization>) => {
    setOrganization(prev => (prev ? { ...prev, ...updates } : null));
  };

  const updateSettings = (updates: Partial<OrganizationSettings>) => {
    setOrganization(prev =>
      prev
        ? {
            ...prev,
            settings: { ...prev.settings, ...updates },
          }
        : null,
    );
  };

  const tabs = [
    { id: 'general', label: 'General', icon: Building },
    { id: 'reviews', label: 'Reviews', icon: Settings },
    { id: 'recovery', label: 'Recovery', icon: Shield },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'branding', label: 'Branding', icon: Palette },
  ];

  if (isLoading) {
    return (
      <div className='px-4 sm:px-6 lg:px-8'>
        <div className='animate-pulse space-y-6'>
          <div className='h-8 bg-gray-200 rounded w-1/4'></div>
          <div className='h-64 bg-gray-200 rounded'></div>
        </div>
      </div>
    );
  }

  if (!organization) {
    return (
      <div className='px-4 sm:px-6 lg:px-8'>
        <div className='text-center py-12'>
          <Settings className='h-12 w-12 text-gray-400 mx-auto mb-4' />
          <h2 className='text-lg font-medium text-gray-900 mb-2'>Settings Unavailable</h2>
          <p className='text-gray-600'>{error || 'Unable to load organization settings'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className='px-4 sm:px-6 lg:px-8'>
      {/* Header */}
      <div className='mb-8'>
        <div className='flex items-center justify-between'>
          <div>
            <h1 className='text-2xl font-bold text-gray-900'>Organization Settings</h1>
            <p className='mt-1 text-sm text-gray-500'>
              Manage your organization's configuration and preferences
            </p>
          </div>
          <Button onClick={handleSave} disabled={isSaving}>
            <Save className='h-4 w-4 mr-1' />
            {isSaving ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </div>

      <div className='grid grid-cols-1 lg:grid-cols-4 gap-8'>
        {/* Sidebar Navigation */}
        <div className='lg:col-span-1'>
          <nav className='space-y-1'>
            {tabs.map(tab => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    'w-full flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors',
                    activeTab === tab.id
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50',
                  )}
                >
                  <Icon className='h-5 w-5 mr-3' />
                  {tab.label}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Main Content */}
        <div className='lg:col-span-3'>
          {activeTab === 'general' && (
            <Card>
              <CardHeader>
                <CardTitle>General Information</CardTitle>
                <CardDescription>Basic information about your organization</CardDescription>
              </CardHeader>
              <CardContent className='space-y-6'>
                <div className='grid grid-cols-1 md:grid-cols-2 gap-6'>
                  <div>
                    <Label htmlFor='name'>Organization Name</Label>
                    <Input
                      id='name'
                      value={organization.name}
                      onChange={e => updateOrganization({ name: e.target.value })}
                    />
                  </div>

                  <div>
                    <Label htmlFor='slug'>URL Slug</Label>
                    <Input
                      id='slug'
                      value={organization.slug}
                      onChange={e => updateOrganization({ slug: e.target.value })}
                    />
                  </div>
                </div>

                <div>
                  <Label htmlFor='description'>Description</Label>
                  <textarea
                    id='description'
                    className='w-full mt-1 p-3 border border-gray-300 rounded-md resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                    rows={3}
                    value={organization.description || ''}
                    onChange={e => updateOrganization({ description: e.target.value })}
                    placeholder='Brief description of your organization...'
                  />
                </div>

                <div className='grid grid-cols-1 md:grid-cols-2 gap-6'>
                  <div>
                    <Label htmlFor='website'>Website</Label>
                    <Input
                      id='website'
                      type='url'
                      value={organization.website || ''}
                      onChange={e => updateOrganization({ website: e.target.value })}
                      placeholder='https://example.com'
                    />
                  </div>

                  <div>
                    <Label htmlFor='industry'>Industry</Label>
                    <select
                      id='industry'
                      value={organization.industry || ''}
                      onChange={e => updateOrganization({ industry: e.target.value })}
                      className='w-full mt-1 p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                    >
                      <option value=''>Select Industry</option>
                      {INDUSTRIES.map(industry => (
                        <option key={industry} value={industry}>
                          {industry}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className='grid grid-cols-1 md:grid-cols-2 gap-6'>
                  <div>
                    <Label htmlFor='size'>Company Size</Label>
                    <select
                      id='size'
                      value={organization.size || ''}
                      onChange={e => updateOrganization({ size: e.target.value as any })}
                      className='w-full mt-1 p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                    >
                      <option value=''>Select Size</option>
                      {COMPANY_SIZES.map(size => (
                        <option key={size.value} value={size.value}>
                          {size.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <Label htmlFor='timezone'>Timezone</Label>
                    <select
                      id='timezone'
                      value={organization.timezone}
                      onChange={e => updateOrganization({ timezone: e.target.value })}
                      className='w-full mt-1 p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                    >
                      {TIMEZONES.map(tz => (
                        <option key={tz} value={tz}>
                          {tz}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <Label>Logo</Label>
                  <div className='mt-1 flex items-center space-x-4'>
                    {organization.logo_url && (
                      <img
                        src={organization.logo_url}
                        alt='Organization logo'
                        className='h-12 w-12 rounded-lg object-cover'
                      />
                    )}
                    <Button variant='outline' size='sm'>
                      <Upload className='h-4 w-4 mr-1' />
                      Upload Logo
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {activeTab === 'reviews' && (
            <Card>
              <CardHeader>
                <CardTitle>Review Settings</CardTitle>
                <CardDescription>
                  Configure how reviews are processed and responded to
                </CardDescription>
              </CardHeader>
              <CardContent className='space-y-6'>
                <div className='flex items-center justify-between'>
                  <div>
                    <Label className='text-base font-medium'>Auto Response</Label>
                    <p className='text-sm text-gray-600'>
                      Automatically generate responses to reviews
                    </p>
                  </div>
                  <input
                    type='checkbox'
                    checked={organization.settings.review_settings.auto_response_enabled}
                    onChange={e =>
                      updateSettings({
                        review_settings: {
                          ...organization.settings.review_settings,
                          auto_response_enabled: e.target.checked,
                        },
                      })
                    }
                    className='h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
                  />
                </div>

                <div>
                  <Label htmlFor='response-delay'>Response Delay (minutes)</Label>
                  <Input
                    id='response-delay'
                    type='number'
                    min='0'
                    max='1440'
                    value={organization.settings.review_settings.response_delay_minutes}
                    onChange={e =>
                      updateSettings({
                        review_settings: {
                          ...organization.settings.review_settings,
                          response_delay_minutes: parseInt(e.target.value) || 0,
                        },
                      })
                    }
                  />
                  <p className='text-sm text-gray-600 mt-1'>
                    Delay before auto-responding to reviews
                  </p>
                </div>

                <div>
                  <Label htmlFor='escalation-threshold'>Escalation Threshold (rating)</Label>
                  <Input
                    id='escalation-threshold'
                    type='number'
                    min='1'
                    max='5'
                    value={organization.settings.review_settings.escalation_threshold}
                    onChange={e =>
                      updateSettings({
                        review_settings: {
                          ...organization.settings.review_settings,
                          escalation_threshold: parseInt(e.target.value) || 1,
                        },
                      })
                    }
                  />
                  <p className='text-sm text-gray-600 mt-1'>
                    Reviews with this rating or below will be escalated
                  </p>
                </div>

                <div>
                  <Label htmlFor='sentiment-threshold'>Sentiment Threshold</Label>
                  <Input
                    id='sentiment-threshold'
                    type='number'
                    min='0'
                    max='1'
                    step='0.1'
                    value={organization.settings.review_settings.sentiment_threshold}
                    onChange={e =>
                      updateSettings({
                        review_settings: {
                          ...organization.settings.review_settings,
                          sentiment_threshold: parseFloat(e.target.value) || 0,
                        },
                      })
                    }
                  />
                  <p className='text-sm text-gray-600 mt-1'>
                    Reviews below this sentiment score will be flagged (0.0 - 1.0)
                  </p>
                </div>

                <div className='flex items-center justify-between'>
                  <div>
                    <Label className='text-base font-medium'>Require Approval</Label>
                    <p className='text-sm text-gray-600'>
                      Require manual approval before publishing responses
                    </p>
                  </div>
                  <input
                    type='checkbox'
                    checked={organization.settings.review_settings.require_approval}
                    onChange={e =>
                      updateSettings({
                        review_settings: {
                          ...organization.settings.review_settings,
                          require_approval: e.target.checked,
                        },
                      })
                    }
                    className='h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
                  />
                </div>
              </CardContent>
            </Card>
          )}

          {activeTab === 'recovery' && (
            <Card>
              <CardHeader>
                <CardTitle>Customer Recovery Settings</CardTitle>
                <CardDescription>Configure automatic customer recovery actions</CardDescription>
              </CardHeader>
              <CardContent className='space-y-6'>
                <div className='flex items-center justify-between'>
                  <div>
                    <Label className='text-base font-medium'>Auto Recovery</Label>
                    <p className='text-sm text-gray-600'>
                      Automatically trigger recovery actions for at-risk customers
                    </p>
                  </div>
                  <input
                    type='checkbox'
                    checked={organization.settings.recovery_settings.auto_recovery_enabled}
                    onChange={e =>
                      updateSettings({
                        recovery_settings: {
                          ...organization.settings.recovery_settings,
                          auto_recovery_enabled: e.target.checked,
                        },
                      })
                    }
                    className='h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
                  />
                </div>

                <div>
                  <Label htmlFor='churn-threshold'>Churn Threshold</Label>
                  <Input
                    id='churn-threshold'
                    type='number'
                    min='0'
                    max='1'
                    step='0.1'
                    value={organization.settings.recovery_settings.churn_threshold}
                    onChange={e =>
                      updateSettings({
                        recovery_settings: {
                          ...organization.settings.recovery_settings,
                          churn_threshold: parseFloat(e.target.value) || 0,
                        },
                      })
                    }
                  />
                  <p className='text-sm text-gray-600 mt-1'>
                    Trigger recovery when churn probability exceeds this value (0.0 - 1.0)
                  </p>
                </div>

                <div>
                  <Label htmlFor='recovery-delay'>Recovery Delay (hours)</Label>
                  <Input
                    id='recovery-delay'
                    type='number'
                    min='0'
                    max='168'
                    value={organization.settings.recovery_settings.recovery_delay_hours}
                    onChange={e =>
                      updateSettings({
                        recovery_settings: {
                          ...organization.settings.recovery_settings,
                          recovery_delay_hours: parseInt(e.target.value) || 0,
                        },
                      })
                    }
                  />
                  <p className='text-sm text-gray-600 mt-1'>
                    Wait time before triggering recovery actions
                  </p>
                </div>

                <div>
                  <Label htmlFor='max-attempts'>Max Recovery Attempts</Label>
                  <Input
                    id='max-attempts'
                    type='number'
                    min='1'
                    max='10'
                    value={organization.settings.recovery_settings.max_recovery_attempts}
                    onChange={e =>
                      updateSettings({
                        recovery_settings: {
                          ...organization.settings.recovery_settings,
                          max_recovery_attempts: parseInt(e.target.value) || 1,
                        },
                      })
                    }
                  />
                  <p className='text-sm text-gray-600 mt-1'>
                    Maximum number of recovery attempts per customer
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {activeTab === 'notifications' && (
            <Card>
              <CardHeader>
                <CardTitle>Notification Settings</CardTitle>
                <CardDescription>Configure how and when you receive notifications</CardDescription>
              </CardHeader>
              <CardContent className='space-y-6'>
                <div className='space-y-4'>
                  <h4 className='font-medium text-gray-900'>Notification Channels</h4>

                  <div className='space-y-3'>
                    <div className='flex items-center justify-between'>
                      <div className='flex items-center space-x-3'>
                        <Bell className='h-5 w-5 text-gray-400' />
                        <div>
                          <Label className='text-base font-medium'>Email Notifications</Label>
                          <p className='text-sm text-gray-600'>Receive notifications via email</p>
                        </div>
                      </div>
                      <input
                        type='checkbox'
                        checked={organization.settings.notifications.email_enabled}
                        onChange={e =>
                          updateSettings({
                            notifications: {
                              ...organization.settings.notifications,
                              email_enabled: e.target.checked,
                            },
                          })
                        }
                        className='h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
                      />
                    </div>

                    <div className='flex items-center justify-between'>
                      <div className='flex items-center space-x-3'>
                        <Globe className='h-5 w-5 text-gray-400' />
                        <div>
                          <Label className='text-base font-medium'>Slack Notifications</Label>
                          <p className='text-sm text-gray-600'>Send notifications to Slack</p>
                        </div>
                      </div>
                      <input
                        type='checkbox'
                        checked={organization.settings.notifications.slack_enabled}
                        onChange={e =>
                          updateSettings({
                            notifications: {
                              ...organization.settings.notifications,
                              slack_enabled: e.target.checked,
                            },
                          })
                        }
                        className='h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
                      />
                    </div>
                  </div>
                </div>

                <div className='space-y-4'>
                  <h4 className='font-medium text-gray-900'>Notification Types</h4>

                  <div className='space-y-3'>
                    {Object.entries(organization.settings.notifications.notification_types).map(
                      ([key, enabled]) => (
                        <div key={key} className='flex items-center justify-between'>
                          <Label className='text-base font-medium capitalize'>
                            {key.replace('_', ' ')}
                          </Label>
                          <input
                            type='checkbox'
                            checked={enabled}
                            onChange={e =>
                              updateSettings({
                                notifications: {
                                  ...organization.settings.notifications,
                                  notification_types: {
                                    ...organization.settings.notifications.notification_types,
                                    [key]: e.target.checked,
                                  },
                                },
                              })
                            }
                            className='h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
                          />
                        </div>
                      ),
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {activeTab === 'branding' && (
            <Card>
              <CardHeader>
                <CardTitle>Branding Settings</CardTitle>
                <CardDescription>
                  Customize the appearance of your dashboard and customer-facing content
                </CardDescription>
              </CardHeader>
              <CardContent className='space-y-6'>
                <div className='grid grid-cols-1 md:grid-cols-2 gap-6'>
                  <div>
                    <Label htmlFor='primary-color'>Primary Color</Label>
                    <div className='flex items-center space-x-3 mt-1'>
                      <input
                        id='primary-color'
                        type='color'
                        value={organization.settings.branding.primary_color}
                        onChange={e =>
                          updateSettings({
                            branding: {
                              ...organization.settings.branding,
                              primary_color: e.target.value,
                            },
                          })
                        }
                        className='h-10 w-20 border border-gray-300 rounded cursor-pointer'
                      />
                      <Input
                        value={organization.settings.branding.primary_color}
                        onChange={e =>
                          updateSettings({
                            branding: {
                              ...organization.settings.branding,
                              primary_color: e.target.value,
                            },
                          })
                        }
                        className='flex-1'
                      />
                    </div>
                  </div>

                  <div>
                    <Label htmlFor='secondary-color'>Secondary Color</Label>
                    <div className='flex items-center space-x-3 mt-1'>
                      <input
                        id='secondary-color'
                        type='color'
                        value={organization.settings.branding.secondary_color}
                        onChange={e =>
                          updateSettings({
                            branding: {
                              ...organization.settings.branding,
                              secondary_color: e.target.value,
                            },
                          })
                        }
                        className='h-10 w-20 border border-gray-300 rounded cursor-pointer'
                      />
                      <Input
                        value={organization.settings.branding.secondary_color}
                        onChange={e =>
                          updateSettings({
                            branding: {
                              ...organization.settings.branding,
                              secondary_color: e.target.value,
                            },
                          })
                        }
                        className='flex-1'
                      />
                    </div>
                  </div>
                </div>

                <div>
                  <Label>Brand Logo</Label>
                  <div className='mt-1 flex items-center space-x-4'>
                    {organization.settings.branding.logo_url && (
                      <img
                        src={organization.settings.branding.logo_url}
                        alt='Brand logo'
                        className='h-12 w-12 rounded-lg object-cover'
                      />
                    )}
                    <Button variant='outline' size='sm'>
                      <Upload className='h-4 w-4 mr-1' />
                      Upload Brand Logo
                    </Button>
                  </div>
                </div>

                <div>
                  <Label htmlFor='custom-css'>Custom CSS</Label>
                  <textarea
                    id='custom-css'
                    className='w-full mt-1 p-3 border border-gray-300 rounded-md resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm'
                    rows={6}
                    value={organization.settings.branding.custom_css || ''}
                    onChange={e =>
                      updateSettings({
                        branding: {
                          ...organization.settings.branding,
                          custom_css: e.target.value,
                        },
                      })
                    }
                    placeholder='/* Custom CSS styles */&#10;.custom-class {&#10;  color: #333;&#10;}'
                  />
                  <p className='text-sm text-gray-600 mt-1'>
                    Add custom CSS to further customize the appearance
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {error && (
        <div className='mt-8 bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded-md'>
          <p className='text-sm'>{error} - Showing sample data for demonstration</p>
        </div>
      )}
    </div>
  );
}
