'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Bell,
  Mail,
  MessageSquare,
  Smartphone,
  Slack,
  Clock,
  Volume2,
  VolumeX,
  Save,
  TestTube,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { NotificationPreference } from '@/types/settings';
import api from '@/lib/api';

const NOTIFICATION_TYPES = [
  { value: 'email', label: 'Email', icon: Mail, description: 'Receive notifications via email' },
  {
    value: 'sms',
    label: 'SMS',
    icon: MessageSquare,
    description: 'Receive text message notifications',
  },
  {
    value: 'push',
    label: 'Push',
    icon: Smartphone,
    description: 'Browser and mobile push notifications',
  },
  {
    value: 'slack',
    label: 'Slack',
    icon: Slack,
    description: 'Send notifications to Slack channels',
  },
];

const FREQUENCIES = [
  { value: 'immediate', label: 'Immediate', description: 'Send notifications right away' },
  { value: 'hourly', label: 'Hourly', description: 'Bundle notifications every hour' },
  { value: 'daily', label: 'Daily', description: 'Send daily digest at 9 AM' },
  { value: 'weekly', label: 'Weekly', description: 'Send weekly summary on Mondays' },
];

const CATEGORIES = [
  { key: 'reviews', label: 'Reviews', description: 'New reviews and review responses' },
  {
    key: 'customers',
    label: 'Customers',
    description: 'Customer risk alerts and recovery actions',
  },
  { key: 'system', label: 'System', description: 'System alerts and maintenance notifications' },
  { key: 'recovery', label: 'Recovery', description: 'Customer recovery action updates' },
];

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

export default function NotificationPreferencesPage() {
  const [preferences, setPreferences] = useState<NotificationPreference[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchNotificationPreferences();
  }, []);

  const fetchNotificationPreferences = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.get('/notification-preferences');
      setPreferences(response.data.preferences || []);
    } catch (err: any) {
      console.error('Error fetching notification preferences:', err);
      setError('Failed to load notification preferences');

      // Mock data for development
      const mockPreferences: NotificationPreference[] = [
        {
          id: '1',
          user_id: 'user_1',
          type: 'email',
          enabled: true,
          settings: {
            frequency: 'immediate',
            quiet_hours: {
              enabled: true,
              start: '22:00',
              end: '08:00',
              timezone: 'America/New_York',
            },
            categories: {
              reviews: true,
              customers: true,
              system: true,
              recovery: true,
            },
          },
          created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 30).toISOString(),
          updated_at: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
        },
        {
          id: '2',
          user_id: 'user_1',
          type: 'slack',
          enabled: true,
          settings: {
            frequency: 'hourly',
            quiet_hours: {
              enabled: false,
              start: '18:00',
              end: '09:00',
              timezone: 'America/New_York',
            },
            categories: {
              reviews: true,
              customers: true,
              system: false,
              recovery: true,
            },
          },
          created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 20).toISOString(),
          updated_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 5).toISOString(),
        },
        {
          id: '3',
          user_id: 'user_1',
          type: 'sms',
          enabled: false,
          settings: {
            frequency: 'immediate',
            quiet_hours: {
              enabled: true,
              start: '21:00',
              end: '09:00',
              timezone: 'America/New_York',
            },
            categories: {
              reviews: false,
              customers: true,
              system: true,
              recovery: false,
            },
          },
          created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 10).toISOString(),
          updated_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2).toISOString(),
        },
      ];
      setPreferences(mockPreferences);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await api.put('/notification-preferences', { preferences });
      // Show success message
    } catch (error) {
      console.error('Error saving notification preferences:', error);
      setError('Failed to save preferences');
    } finally {
      setIsSaving(false);
    }
  };

  const updatePreference = (id: string, updates: Partial<NotificationPreference>) => {
    setPreferences(prev => prev.map(pref => (pref.id === id ? { ...pref, ...updates } : pref)));
  };

  const updatePreferenceSettings = (
    id: string,
    settingUpdates: Partial<NotificationPreference['settings']>,
  ) => {
    setPreferences(prev =>
      prev.map(pref =>
        pref.id === id
          ? {
              ...pref,
              settings: { ...pref.settings, ...settingUpdates },
            }
          : pref,
      ),
    );
  };

  const sendTestNotification = async (type: string) => {
    try {
      await api.post('/notification-preferences/test', { type });
      // Show success message
    } catch (error) {
      console.error('Error sending test notification:', error);
    }
  };

  const getNotificationTypeConfig = (type: string) => {
    return NOTIFICATION_TYPES.find(nt => nt.value === type) || NOTIFICATION_TYPES[0];
  };

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

  return (
    <div className='px-4 sm:px-6 lg:px-8'>
      {/* Header */}
      <div className='mb-8'>
        <div className='flex items-center justify-between'>
          <div>
            <h1 className='text-2xl font-bold text-gray-900'>Notification Preferences</h1>
            <p className='mt-1 text-sm text-gray-500'>
              Configure how and when you receive notifications
            </p>
          </div>
          <Button onClick={handleSave} disabled={isSaving}>
            <Save className='h-4 w-4 mr-1' />
            {isSaving ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </div>

      <div className='space-y-6'>
        {preferences.map(preference => {
          const typeConfig = getNotificationTypeConfig(preference.type);
          const Icon = typeConfig.icon;

          return (
            <Card key={preference.id}>
              <CardHeader>
                <div className='flex items-center justify-between'>
                  <div className='flex items-center space-x-3'>
                    <div
                      className={cn(
                        'w-10 h-10 rounded-full flex items-center justify-center',
                        preference.enabled ? 'bg-blue-100' : 'bg-gray-100',
                      )}
                    >
                      <Icon
                        className={cn(
                          'h-5 w-5',
                          preference.enabled ? 'text-blue-600' : 'text-gray-400',
                        )}
                      />
                    </div>
                    <div>
                      <CardTitle className='flex items-center space-x-2'>
                        <span>{typeConfig.label} Notifications</span>
                        {preference.enabled ? (
                          <Volume2 className='h-4 w-4 text-green-600' />
                        ) : (
                          <VolumeX className='h-4 w-4 text-gray-400' />
                        )}
                      </CardTitle>
                      <CardDescription>{typeConfig.description}</CardDescription>
                    </div>
                  </div>

                  <div className='flex items-center space-x-2'>
                    <Button
                      variant='outline'
                      size='sm'
                      onClick={() => sendTestNotification(preference.type)}
                    >
                      <TestTube className='h-4 w-4 mr-1' />
                      Test
                    </Button>
                    <input
                      type='checkbox'
                      checked={preference.enabled}
                      onChange={e => updatePreference(preference.id, { enabled: e.target.checked })}
                      className='h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
                    />
                  </div>
                </div>
              </CardHeader>

              {preference.enabled && (
                <CardContent className='space-y-6'>
                  {/* Frequency Settings */}
                  <div>
                    <Label className='text-base font-medium mb-3 block'>Frequency</Label>
                    <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3'>
                      {FREQUENCIES.map(freq => (
                        <label
                          key={freq.value}
                          className={cn(
                            'flex items-center space-x-2 p-3 border rounded-lg cursor-pointer transition-colors',
                            preference.settings.frequency === freq.value
                              ? 'border-blue-500 bg-blue-50'
                              : 'border-gray-200 hover:border-gray-300',
                          )}
                        >
                          <input
                            type='radio'
                            name={`frequency-${preference.id}`}
                            value={freq.value}
                            checked={preference.settings.frequency === freq.value}
                            onChange={e =>
                              updatePreferenceSettings(preference.id, {
                                frequency: e.target.value as any,
                              })
                            }
                            className='h-4 w-4 text-blue-600 focus:ring-blue-500'
                          />
                          <div>
                            <div className='font-medium text-sm'>{freq.label}</div>
                            <div className='text-xs text-gray-600'>{freq.description}</div>
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* Quiet Hours */}
                  <div>
                    <div className='flex items-center justify-between mb-3'>
                      <Label className='text-base font-medium'>Quiet Hours</Label>
                      <input
                        type='checkbox'
                        checked={preference.settings.quiet_hours.enabled}
                        onChange={e =>
                          updatePreferenceSettings(preference.id, {
                            quiet_hours: {
                              ...preference.settings.quiet_hours,
                              enabled: e.target.checked,
                            },
                          })
                        }
                        className='h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
                      />
                    </div>

                    {preference.settings.quiet_hours.enabled && (
                      <div className='grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-gray-50 rounded-lg'>
                        <div>
                          <Label htmlFor={`quiet-start-${preference.id}`}>Start Time</Label>
                          <Input
                            id={`quiet-start-${preference.id}`}
                            type='time'
                            value={preference.settings.quiet_hours.start}
                            onChange={e =>
                              updatePreferenceSettings(preference.id, {
                                quiet_hours: {
                                  ...preference.settings.quiet_hours,
                                  start: e.target.value,
                                },
                              })
                            }
                          />
                        </div>

                        <div>
                          <Label htmlFor={`quiet-end-${preference.id}`}>End Time</Label>
                          <Input
                            id={`quiet-end-${preference.id}`}
                            type='time'
                            value={preference.settings.quiet_hours.end}
                            onChange={e =>
                              updatePreferenceSettings(preference.id, {
                                quiet_hours: {
                                  ...preference.settings.quiet_hours,
                                  end: e.target.value,
                                },
                              })
                            }
                          />
                        </div>

                        <div>
                          <Label htmlFor={`quiet-timezone-${preference.id}`}>Timezone</Label>
                          <select
                            id={`quiet-timezone-${preference.id}`}
                            value={preference.settings.quiet_hours.timezone}
                            onChange={e =>
                              updatePreferenceSettings(preference.id, {
                                quiet_hours: {
                                  ...preference.settings.quiet_hours,
                                  timezone: e.target.value,
                                },
                              })
                            }
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
                    )}
                  </div>

                  {/* Categories */}
                  <div>
                    <Label className='text-base font-medium mb-3 block'>
                      Notification Categories
                    </Label>
                    <div className='space-y-3'>
                      {CATEGORIES.map(category => (
                        <div
                          key={category.key}
                          className='flex items-center justify-between p-3 border rounded-lg'
                        >
                          <div>
                            <div className='font-medium text-sm'>{category.label}</div>
                            <div className='text-xs text-gray-600'>{category.description}</div>
                          </div>
                          <input
                            type='checkbox'
                            checked={
                              preference.settings.categories[
                                category.key as keyof typeof preference.settings.categories
                              ]
                            }
                            onChange={e =>
                              updatePreferenceSettings(preference.id, {
                                categories: {
                                  ...preference.settings.categories,
                                  [category.key]: e.target.checked,
                                },
                              })
                            }
                            className='h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                </CardContent>
              )}
            </Card>
          );
        })}
      </div>

      {error && (
        <div className='mt-8 bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded-md'>
          <p className='text-sm'>{error} - Showing sample data for demonstration</p>
        </div>
      )}
    </div>
  );
}
