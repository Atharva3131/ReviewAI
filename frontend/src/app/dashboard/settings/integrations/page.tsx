'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Plug,
  Mail,
  MessageSquare,
  Users,
  Slack,
  Webhook,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Settings,
  Trash2,
  RefreshCw,
  Plus,
  ExternalLink,
} from 'lucide-react';
import { cn, formatDateTime } from '@/lib/utils';
import type { Integration } from '@/types/settings';
import api from '@/lib/api';

const INTEGRATION_TYPES = [
  {
    type: 'email',
    name: 'Email Service',
    icon: Mail,
    description: 'Send emails via SendGrid, AWS SES, or SMTP',
    color: 'bg-blue-100 text-blue-600',
    fields: [
      {
        key: 'provider',
        label: 'Provider',
        type: 'select',
        options: ['sendgrid', 'aws-ses', 'smtp'],
      },
      { key: 'api_key', label: 'API Key', type: 'password' },
      { key: 'from_email', label: 'From Email', type: 'email' },
      { key: 'from_name', label: 'From Name', type: 'text' },
    ],
  },
  {
    type: 'whatsapp',
    name: 'WhatsApp Business',
    icon: MessageSquare,
    description: 'Send WhatsApp messages via WhatsApp Business API',
    color: 'bg-green-100 text-green-600',
    fields: [
      { key: 'phone_number_id', label: 'Phone Number ID', type: 'text' },
      { key: 'access_token', label: 'Access Token', type: 'password' },
      { key: 'webhook_verify_token', label: 'Webhook Verify Token', type: 'password' },
    ],
  },
  {
    type: 'crm',
    name: 'CRM System',
    icon: Users,
    description: 'Integrate with Salesforce, HubSpot, or other CRM systems',
    color: 'bg-purple-100 text-purple-600',
    fields: [
      {
        key: 'provider',
        label: 'CRM Provider',
        type: 'select',
        options: ['salesforce', 'hubspot', 'pipedrive'],
      },
      { key: 'api_key', label: 'API Key', type: 'password' },
      { key: 'instance_url', label: 'Instance URL', type: 'url' },
    ],
  },
  {
    type: 'slack',
    name: 'Slack',
    icon: Slack,
    description: 'Send notifications to Slack channels',
    color: 'bg-indigo-100 text-indigo-600',
    fields: [
      { key: 'webhook_url', label: 'Webhook URL', type: 'url' },
      { key: 'channel', label: 'Default Channel', type: 'text' },
      { key: 'username', label: 'Bot Username', type: 'text' },
    ],
  },
  {
    type: 'webhook',
    name: 'Custom Webhook',
    icon: Webhook,
    description: 'Send data to custom webhook endpoints',
    color: 'bg-gray-100 text-gray-600',
    fields: [
      { key: 'url', label: 'Webhook URL', type: 'url' },
      { key: 'secret', label: 'Secret Key', type: 'password' },
      {
        key: 'events',
        label: 'Events',
        type: 'multiselect',
        options: ['review.created', 'review.responded', 'customer.at_risk', 'recovery.completed'],
      },
    ],
  },
];

export default function IntegrationsPage() {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedType, setSelectedType] = useState<string>('');
  const [editingIntegration, setEditingIntegration] = useState<Integration | null>(null);

  useEffect(() => {
    fetchIntegrations();
  }, []);

  const fetchIntegrations = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.get('/integrations');
      setIntegrations(response.data.integrations || []);
    } catch (err: any) {
      console.error('Error fetching integrations:', err);
      setError('Failed to load integrations');

      // Mock data for development
      const mockIntegrations: Integration[] = [
        {
          id: '1',
          type: 'email',
          name: 'SendGrid Email Service',
          enabled: true,
          configuration: {
            provider: 'sendgrid',
            api_key: 'SG.*********************',
            from_email: 'noreply@acmerestaurants.com',
            from_name: 'Acme Restaurants',
          },
          status: 'connected',
          last_sync: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
          created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 30).toISOString(),
          updated_at: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
        },
        {
          id: '2',
          type: 'slack',
          name: 'Team Notifications',
          enabled: true,
          configuration: {
            webhook_url: 'https://hooks.slack.com/services/***',
            channel: '#customer-alerts',
            username: 'ReviewAI Bot',
          },
          status: 'connected',
          last_sync: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
          created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 15).toISOString(),
          updated_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2).toISOString(),
        },
        {
          id: '3',
          type: 'whatsapp',
          name: 'WhatsApp Business',
          enabled: false,
          configuration: {
            phone_number_id: '1234567890',
            access_token: 'EAA*********************',
            webhook_verify_token: 'verify_token_123',
          },
          status: 'disconnected',
          created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 7).toISOString(),
          updated_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 7).toISOString(),
        },
        {
          id: '4',
          type: 'crm',
          name: 'Salesforce CRM',
          enabled: true,
          configuration: {
            provider: 'salesforce',
            api_key: 'sf_*********************',
            instance_url: 'https://acme.salesforce.com',
          },
          status: 'error',
          last_sync: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3).toISOString(),
          created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 45).toISOString(),
          updated_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3).toISOString(),
        },
      ];
      setIntegrations(mockIntegrations);
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleIntegration = async (integrationId: string, enabled: boolean) => {
    try {
      await api.patch(`/integrations/${integrationId}`, { enabled });
      setIntegrations(prev =>
        prev.map(integration =>
          integration.id === integrationId ? { ...integration, enabled } : integration,
        ),
      );
    } catch (error) {
      console.error('Error toggling integration:', error);
    }
  };

  const handleTestIntegration = async (integrationId: string) => {
    try {
      await api.post(`/integrations/${integrationId}/test`);
      // Show success message
    } catch (error) {
      console.error('Error testing integration:', error);
    }
  };

  const handleDeleteIntegration = async (integrationId: string) => {
    if (!confirm('Are you sure you want to delete this integration?')) {
      return;
    }

    try {
      await api.delete(`/integrations/${integrationId}`);
      setIntegrations(prev => prev.filter(integration => integration.id !== integrationId));
    } catch (error) {
      console.error('Error deleting integration:', error);
    }
  };

  const getIntegrationType = (type: string) => {
    return INTEGRATION_TYPES.find(t => t.type === type) || INTEGRATION_TYPES[0];
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected':
        return CheckCircle;
      case 'error':
        return AlertTriangle;
      default:
        return XCircle;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected':
        return 'text-green-600';
      case 'error':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const maskSensitiveValue = (value: string) => {
    if (value.length <= 8) {
      return '*'.repeat(value.length);
    }
    return value.substring(0, 4) + '*'.repeat(value.length - 8) + value.substring(value.length - 4);
  };

  if (isLoading) {
    return (
      <div className='px-4 sm:px-6 lg:px-8'>
        <div className='animate-pulse space-y-4'>
          <div className='h-8 bg-gray-200 rounded w-1/4'></div>
          <div className='h-12 bg-gray-200 rounded'></div>
          {[...Array(4)].map((_, i) => (
            <div key={i} className='h-32 bg-gray-200 rounded'></div>
          ))}
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
            <h1 className='text-2xl font-bold text-gray-900'>Integrations</h1>
            <p className='mt-1 text-sm text-gray-500'>
              Connect external services to enhance your workflow
            </p>
          </div>
          <Button onClick={() => setShowAddModal(true)}>
            <Plus className='h-4 w-4 mr-1' />
            Add Integration
          </Button>
        </div>
      </div>

      {/* Available Integrations */}
      <div className='mb-8'>
        <h2 className='text-lg font-medium text-gray-900 mb-4'>Available Integrations</h2>
        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'>
          {INTEGRATION_TYPES.map(type => {
            const Icon = type.icon;
            const existingIntegration = integrations.find(i => i.type === type.type);

            return (
              <Card
                key={type.type}
                className={cn(
                  'cursor-pointer transition-all hover:shadow-md',
                  existingIntegration ? 'border-blue-200 bg-blue-50' : 'hover:border-gray-300',
                )}
                onClick={() => {
                  if (existingIntegration) {
                    setEditingIntegration(existingIntegration);
                  } else {
                    setSelectedType(type.type);
                    setShowAddModal(true);
                  }
                }}
              >
                <CardContent className='p-4'>
                  <div className='flex items-center space-x-3'>
                    <div
                      className={cn(
                        'w-10 h-10 rounded-full flex items-center justify-center',
                        type.color,
                      )}
                    >
                      <Icon className='h-5 w-5' />
                    </div>
                    <div className='flex-1'>
                      <h3 className='font-medium text-gray-900'>{type.name}</h3>
                      <p className='text-sm text-gray-600'>{type.description}</p>
                      {existingIntegration && (
                        <div className='flex items-center space-x-2 mt-1'>
                          <span className='text-xs text-blue-600 font-medium'>Configured</span>
                          <span
                            className={cn('text-xs', getStatusColor(existingIntegration.status))}
                          >
                            • {existingIntegration.status}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Configured Integrations */}
      {integrations.length > 0 && (
        <div>
          <h2 className='text-lg font-medium text-gray-900 mb-4'>Configured Integrations</h2>
          <div className='space-y-4'>
            {integrations.map(integration => {
              const typeConfig = getIntegrationType(integration.type);
              const Icon = typeConfig.icon;
              const StatusIcon = getStatusIcon(integration.status);

              return (
                <Card key={integration.id}>
                  <CardContent className='p-6'>
                    <div className='flex items-start justify-between'>
                      <div className='flex items-start space-x-4'>
                        <div
                          className={cn(
                            'w-12 h-12 rounded-full flex items-center justify-center',
                            typeConfig.color,
                          )}
                        >
                          <Icon className='h-6 w-6' />
                        </div>

                        <div className='flex-1'>
                          <div className='flex items-center space-x-2 mb-2'>
                            <h3 className='text-lg font-medium text-gray-900'>
                              {integration.name}
                            </h3>
                            <div
                              className={cn(
                                'flex items-center space-x-1',
                                getStatusColor(integration.status),
                              )}
                            >
                              <StatusIcon className='h-4 w-4' />
                              <span className='text-sm capitalize'>{integration.status}</span>
                            </div>
                          </div>

                          <p className='text-sm text-gray-600 mb-3'>{typeConfig.description}</p>

                          {/* Configuration Preview */}
                          <div className='space-y-2'>
                            {Object.entries(integration.configuration)
                              .slice(0, 3)
                              .map(([key, value]) => (
                                <div key={key} className='flex items-center space-x-2 text-sm'>
                                  <span className='text-gray-500 capitalize w-24'>
                                    {key.replace('_', ' ')}:
                                  </span>
                                  <span className='text-gray-900 font-mono'>
                                    {key.includes('key') ||
                                    key.includes('token') ||
                                    key.includes('secret')
                                      ? maskSensitiveValue(value as string)
                                      : (value as string)}
                                  </span>
                                </div>
                              ))}
                          </div>

                          {integration.last_sync && (
                            <p className='text-xs text-gray-500 mt-3'>
                              Last sync: {formatDateTime(integration.last_sync)}
                            </p>
                          )}
                        </div>
                      </div>

                      {/* Actions */}
                      <div className='flex items-center space-x-2'>
                        <Button
                          variant='outline'
                          size='sm'
                          onClick={() => handleTestIntegration(integration.id)}
                        >
                          <RefreshCw className='h-4 w-4 mr-1' />
                          Test
                        </Button>

                        <Button
                          variant='outline'
                          size='sm'
                          onClick={() => setEditingIntegration(integration)}
                        >
                          <Settings className='h-4 w-4 mr-1' />
                          Configure
                        </Button>

                        <Button
                          variant='outline'
                          size='sm'
                          onClick={() =>
                            handleToggleIntegration(integration.id, !integration.enabled)
                          }
                        >
                          {integration.enabled ? 'Disable' : 'Enable'}
                        </Button>

                        <Button
                          variant='outline'
                          size='sm'
                          onClick={() => handleDeleteIntegration(integration.id)}
                          className='text-red-600 hover:text-red-700'
                        >
                          <Trash2 className='h-4 w-4' />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {/* Add/Edit Integration Modal */}
      {(showAddModal || editingIntegration) && (
        <div className='fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50'>
          <div className='bg-white rounded-lg p-6 w-full max-w-md mx-4 max-h-[90vh] overflow-y-auto'>
            <div className='flex items-center justify-between mb-4'>
              <h3 className='text-lg font-medium text-gray-900'>
                {editingIntegration ? 'Edit Integration' : 'Add Integration'}
              </h3>
              <Button
                variant='ghost'
                size='sm'
                onClick={() => {
                  setShowAddModal(false);
                  setEditingIntegration(null);
                  setSelectedType('');
                }}
              >
                ×
              </Button>
            </div>

            <div className='space-y-4'>
              {!editingIntegration && (
                <div>
                  <Label>Integration Type</Label>
                  <select
                    value={selectedType}
                    onChange={e => setSelectedType(e.target.value)}
                    className='w-full mt-1 p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                  >
                    <option value=''>Select Integration Type</option>
                    {INTEGRATION_TYPES.map(type => (
                      <option key={type.type} value={type.type}>
                        {type.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {(selectedType || editingIntegration) && (
                <>
                  <div>
                    <Label htmlFor='integration-name'>Name</Label>
                    <Input
                      id='integration-name'
                      placeholder='e.g., Production Email Service'
                      defaultValue={editingIntegration?.name || ''}
                    />
                  </div>

                  {getIntegrationType(selectedType || editingIntegration?.type || '').fields.map(
                    field => (
                      <div key={field.key}>
                        <Label htmlFor={field.key}>{field.label}</Label>
                        {field.type === 'select' ? (
                          <select
                            id={field.key}
                            className='w-full mt-1 p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                            defaultValue={editingIntegration?.configuration[field.key] || ''}
                          >
                            <option value=''>Select {field.label}</option>
                            {field.options?.map(option => (
                              <option key={option} value={option}>
                                {option}
                              </option>
                            ))}
                          </select>
                        ) : field.type === 'multiselect' ? (
                          <div className='mt-1 space-y-1'>
                            {field.options?.map(option => (
                              <label key={option} className='flex items-center space-x-2'>
                                <input
                                  type='checkbox'
                                  defaultChecked={editingIntegration?.configuration[
                                    field.key
                                  ]?.includes(option)}
                                  className='h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
                                />
                                <span className='text-sm'>{option}</span>
                              </label>
                            ))}
                          </div>
                        ) : (
                          <Input
                            id={field.key}
                            type={field.type}
                            placeholder={`Enter ${field.label.toLowerCase()}`}
                            defaultValue={editingIntegration?.configuration[field.key] || ''}
                          />
                        )}
                      </div>
                    ),
                  )}
                </>
              )}

              <div className='flex items-center justify-end space-x-2 pt-4'>
                <Button
                  variant='outline'
                  onClick={() => {
                    setShowAddModal(false);
                    setEditingIntegration(null);
                    setSelectedType('');
                  }}
                >
                  Cancel
                </Button>
                <Button disabled={!selectedType && !editingIntegration}>
                  {editingIntegration ? 'Update Integration' : 'Add Integration'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className='mt-4 bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded-md'>
          <p className='text-sm'>{error} - Showing sample data for demonstration</p>
        </div>
      )}
    </div>
  );
}
