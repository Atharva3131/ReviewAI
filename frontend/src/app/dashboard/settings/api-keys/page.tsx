'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Key,
  Plus,
  Copy,
  Eye,
  EyeOff,
  Trash2,
  Calendar,
  Shield,
  CheckCircle,
  XCircle,
  AlertTriangle,
  RotateCcw,
} from 'lucide-react';
import { cn, formatDateTime } from '@/lib/utils';
import type { APIKey } from '@/types/settings';
import api from '@/lib/api';

const PERMISSIONS = [
  { value: 'read:reviews', label: 'Read Reviews', description: 'View review data' },
  { value: 'write:reviews', label: 'Write Reviews', description: 'Create and update reviews' },
  { value: 'read:customers', label: 'Read Customers', description: 'View customer data' },
  {
    value: 'write:customers',
    label: 'Write Customers',
    description: 'Create and update customers',
  },
  { value: 'read:analytics', label: 'Read Analytics', description: 'Access analytics data' },
  {
    value: 'write:responses',
    label: 'Write Responses',
    description: 'Generate and publish responses',
  },
  { value: 'admin', label: 'Admin Access', description: 'Full administrative access' },
];

export default function APIKeysPage() {
  const [apiKeys, setApiKeys] = useState<APIKey[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [visibleKeys, setVisibleKeys] = useState<Set<string>>(new Set());
  const [newKeyData, setNewKeyData] = useState({
    name: '',
    permissions: [] as string[],
    expires_at: '',
  });

  useEffect(() => {
    fetchAPIKeys();
  }, []);

  const fetchAPIKeys = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.get('/api-keys');
      setApiKeys(response.data.keys || []);
    } catch (err: any) {
      console.error('Error fetching API keys:', err);
      setError('Failed to load API keys');

      // Mock data for development
      const mockKeys: APIKey[] = [
        {
          id: '1',
          name: 'Production API Key',
          key: 'rva_live_1234567890abcdef1234567890abcdef',
          permissions: ['read:reviews', 'write:reviews', 'read:customers', 'write:responses'],
          last_used: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
          expires_at: new Date(Date.now() + 1000 * 60 * 60 * 24 * 365).toISOString(),
          created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 30).toISOString(),
          status: 'active',
        },
        {
          id: '2',
          name: 'Development API Key',
          key: 'rva_test_abcdef1234567890abcdef1234567890',
          permissions: ['read:reviews', 'read:customers', 'read:analytics'],
          last_used: new Date(Date.now() - 1000 * 60 * 60 * 24 * 5).toISOString(),
          created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 60).toISOString(),
          status: 'active',
        },
        {
          id: '3',
          name: 'Legacy Integration',
          key: 'rva_live_fedcba0987654321fedcba0987654321',
          permissions: ['read:reviews', 'write:responses'],
          last_used: new Date(Date.now() - 1000 * 60 * 60 * 24 * 90).toISOString(),
          expires_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 10).toISOString(),
          created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 180).toISOString(),
          status: 'expired',
        },
        {
          id: '4',
          name: 'Analytics Dashboard',
          key: 'rva_live_9876543210fedcba9876543210fedcba',
          permissions: ['read:analytics', 'read:reviews', 'read:customers'],
          created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 7).toISOString(),
          status: 'inactive',
        },
      ];
      setApiKeys(mockKeys);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateKey = async () => {
    try {
      const response = await api.post('/api-keys', newKeyData);
      setApiKeys(prev => [response.data, ...prev]);
      setShowCreateModal(false);
      setNewKeyData({ name: '', permissions: [], expires_at: '' });
    } catch (error) {
      console.error('Error creating API key:', error);
    }
  };

  const handleDeleteKey = async (keyId: string) => {
    if (!confirm('Are you sure you want to delete this API key? This action cannot be undone.')) {
      return;
    }

    try {
      await api.delete(`/api-keys/${keyId}`);
      setApiKeys(prev => prev.filter(key => key.id !== keyId));
    } catch (error) {
      console.error('Error deleting API key:', error);
    }
  };

  const handleRegenerateKey = async (keyId: string) => {
    if (
      !confirm(
        'Are you sure you want to regenerate this API key? The old key will stop working immediately.',
      )
    ) {
      return;
    }

    try {
      const response = await api.post(`/api-keys/${keyId}/regenerate`);
      setApiKeys(prev =>
        prev.map(key => (key.id === keyId ? { ...key, key: response.data.key } : key)),
      );
    } catch (error) {
      console.error('Error regenerating API key:', error);
    }
  };

  const handleToggleKeyStatus = async (keyId: string, status: 'active' | 'inactive') => {
    try {
      await api.patch(`/api-keys/${keyId}`, { status });
      setApiKeys(prev => prev.map(key => (key.id === keyId ? { ...key, status } : key)));
    } catch (error) {
      console.error('Error updating API key status:', error);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    // Show success message
  };

  const toggleKeyVisibility = (keyId: string) => {
    setVisibleKeys(prev => {
      const newSet = new Set(prev);
      if (newSet.has(keyId)) {
        newSet.delete(keyId);
      } else {
        newSet.add(keyId);
      }
      return newSet;
    });
  };

  const maskKey = (key: string) => {
    const prefix = key.substring(0, 12);
    const suffix = key.substring(key.length - 4);
    return `${prefix}${'*'.repeat(key.length - 16)}${suffix}`;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return CheckCircle;
      case 'inactive':
        return XCircle;
      case 'expired':
        return AlertTriangle;
      default:
        return XCircle;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'text-green-600';
      case 'inactive':
        return 'text-gray-600';
      case 'expired':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const isExpired = (expiresAt?: string) => {
    return expiresAt && new Date(expiresAt) < new Date();
  };

  if (isLoading) {
    return (
      <div className='px-4 sm:px-6 lg:px-8'>
        <div className='animate-pulse space-y-4'>
          <div className='h-8 bg-gray-200 rounded w-1/4'></div>
          <div className='h-12 bg-gray-200 rounded'></div>
          {[...Array(3)].map((_, i) => (
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
            <h1 className='text-2xl font-bold text-gray-900'>API Keys</h1>
            <p className='mt-1 text-sm text-gray-500'>
              Manage API keys for programmatic access to your data
            </p>
          </div>
          <Button onClick={() => setShowCreateModal(true)}>
            <Plus className='h-4 w-4 mr-1' />
            Create API Key
          </Button>
        </div>
      </div>

      {/* API Keys List */}
      <div className='space-y-4'>
        {apiKeys.length === 0 ? (
          <Card>
            <CardContent className='text-center py-12'>
              <Key className='h-12 w-12 text-gray-400 mx-auto mb-4' />
              <h3 className='text-lg font-medium text-gray-900 mb-2'>No API Keys</h3>
              <p className='text-gray-600 mb-4'>
                Create your first API key to start integrating with the ReviewAI API
              </p>
              <Button onClick={() => setShowCreateModal(true)}>
                <Plus className='h-4 w-4 mr-1' />
                Create First API Key
              </Button>
            </CardContent>
          </Card>
        ) : (
          apiKeys.map(apiKey => {
            const StatusIcon = getStatusIcon(apiKey.status);
            const expired = isExpired(apiKey.expires_at);
            const actualStatus = expired ? 'expired' : apiKey.status;

            return (
              <Card
                key={apiKey.id}
                className={cn(
                  'transition-shadow',
                  actualStatus === 'active'
                    ? 'border-green-200'
                    : actualStatus === 'expired'
                      ? 'border-red-200'
                      : 'border-gray-200',
                )}
              >
                <CardContent className='p-6'>
                  <div className='flex items-start justify-between'>
                    <div className='flex-1'>
                      <div className='flex items-center space-x-3 mb-3'>
                        <div
                          className={cn(
                            'w-10 h-10 rounded-full flex items-center justify-center',
                            actualStatus === 'active'
                              ? 'bg-green-100'
                              : actualStatus === 'expired'
                                ? 'bg-red-100'
                                : 'bg-gray-100',
                          )}
                        >
                          <Key
                            className={cn(
                              'h-5 w-5',
                              actualStatus === 'active'
                                ? 'text-green-600'
                                : actualStatus === 'expired'
                                  ? 'text-red-600'
                                  : 'text-gray-400',
                            )}
                          />
                        </div>

                        <div className='flex-1'>
                          <h3 className='text-lg font-medium text-gray-900'>{apiKey.name}</h3>
                          <div className='flex items-center space-x-4 text-sm text-gray-600'>
                            <div
                              className={cn(
                                'flex items-center space-x-1',
                                getStatusColor(actualStatus),
                              )}
                            >
                              <StatusIcon className='h-4 w-4' />
                              <span className='capitalize'>{actualStatus}</span>
                            </div>

                            <div className='flex items-center space-x-1'>
                              <Calendar className='h-4 w-4' />
                              <span>Created {formatDateTime(apiKey.created_at)}</span>
                            </div>

                            {apiKey.last_used && (
                              <div className='flex items-center space-x-1'>
                                <span>Last used {formatDateTime(apiKey.last_used)}</span>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* API Key */}
                      <div className='mb-4'>
                        <Label className='text-sm font-medium text-gray-700 mb-2 block'>
                          API Key
                        </Label>
                        <div className='flex items-center space-x-2'>
                          <code className='flex-1 px-3 py-2 bg-gray-100 border rounded font-mono text-sm'>
                            {visibleKeys.has(apiKey.id) ? apiKey.key : maskKey(apiKey.key)}
                          </code>
                          <Button
                            variant='outline'
                            size='sm'
                            onClick={() => toggleKeyVisibility(apiKey.id)}
                          >
                            {visibleKeys.has(apiKey.id) ? (
                              <EyeOff className='h-4 w-4' />
                            ) : (
                              <Eye className='h-4 w-4' />
                            )}
                          </Button>
                          <Button
                            variant='outline'
                            size='sm'
                            onClick={() => copyToClipboard(apiKey.key)}
                          >
                            <Copy className='h-4 w-4' />
                          </Button>
                        </div>
                      </div>

                      {/* Permissions */}
                      <div className='mb-4'>
                        <Label className='text-sm font-medium text-gray-700 mb-2 block'>
                          Permissions
                        </Label>
                        <div className='flex flex-wrap gap-2'>
                          {apiKey.permissions.map(permission => (
                            <span
                              key={permission}
                              className='inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800'
                            >
                              <Shield className='h-3 w-3 mr-1' />
                              {permission}
                            </span>
                          ))}
                        </div>
                      </div>

                      {/* Expiration */}
                      {apiKey.expires_at && (
                        <div className='mb-4'>
                          <Label className='text-sm font-medium text-gray-700 mb-1 block'>
                            Expires
                          </Label>
                          <span
                            className={cn(
                              'text-sm',
                              expired ? 'text-red-600 font-medium' : 'text-gray-600',
                            )}
                          >
                            {formatDateTime(apiKey.expires_at)}
                            {expired && ' (Expired)'}
                          </span>
                        </div>
                      )}
                    </div>

                    {/* Actions */}
                    <div className='flex items-center space-x-2 ml-4'>
                      {actualStatus === 'active' && (
                        <Button
                          variant='outline'
                          size='sm'
                          onClick={() => handleToggleKeyStatus(apiKey.id, 'inactive')}
                        >
                          Disable
                        </Button>
                      )}

                      {actualStatus === 'inactive' && (
                        <Button
                          variant='outline'
                          size='sm'
                          onClick={() => handleToggleKeyStatus(apiKey.id, 'active')}
                        >
                          Enable
                        </Button>
                      )}

                      <Button
                        variant='outline'
                        size='sm'
                        onClick={() => handleRegenerateKey(apiKey.id)}
                      >
                        <RotateCcw className='h-4 w-4 mr-1' />
                        Regenerate
                      </Button>

                      <Button
                        variant='outline'
                        size='sm'
                        onClick={() => handleDeleteKey(apiKey.id)}
                        className='text-red-600 hover:text-red-700'
                      >
                        <Trash2 className='h-4 w-4' />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })
        )}
      </div>

      {/* Create API Key Modal */}
      {showCreateModal && (
        <div className='fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50'>
          <div className='bg-white rounded-lg p-6 w-full max-w-md mx-4'>
            <div className='flex items-center justify-between mb-4'>
              <h3 className='text-lg font-medium text-gray-900'>Create API Key</h3>
              <Button variant='ghost' size='sm' onClick={() => setShowCreateModal(false)}>
                ×
              </Button>
            </div>

            <div className='space-y-4'>
              <div>
                <Label htmlFor='key-name'>Name</Label>
                <Input
                  id='key-name'
                  placeholder='e.g., Production API Key'
                  value={newKeyData.name}
                  onChange={e => setNewKeyData(prev => ({ ...prev, name: e.target.value }))}
                />
              </div>

              <div>
                <Label>Permissions</Label>
                <div className='mt-2 space-y-2 max-h-48 overflow-y-auto'>
                  {PERMISSIONS.map(permission => (
                    <label
                      key={permission.value}
                      className='flex items-start space-x-2 p-2 border rounded cursor-pointer hover:bg-gray-50'
                    >
                      <input
                        type='checkbox'
                        checked={newKeyData.permissions.includes(permission.value)}
                        onChange={e => {
                          if (e.target.checked) {
                            setNewKeyData(prev => ({
                              ...prev,
                              permissions: [...prev.permissions, permission.value],
                            }));
                          } else {
                            setNewKeyData(prev => ({
                              ...prev,
                              permissions: prev.permissions.filter(p => p !== permission.value),
                            }));
                          }
                        }}
                        className='h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded mt-0.5'
                      />
                      <div>
                        <div className='font-medium text-sm'>{permission.label}</div>
                        <div className='text-xs text-gray-600'>{permission.description}</div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <Label htmlFor='expires-at'>Expiration Date (Optional)</Label>
                <Input
                  id='expires-at'
                  type='date'
                  value={newKeyData.expires_at}
                  onChange={e => setNewKeyData(prev => ({ ...prev, expires_at: e.target.value }))}
                  min={new Date().toISOString().split('T')[0]}
                />
              </div>

              <div className='flex items-center justify-end space-x-2 pt-4'>
                <Button variant='outline' onClick={() => setShowCreateModal(false)}>
                  Cancel
                </Button>
                <Button
                  onClick={handleCreateKey}
                  disabled={!newKeyData.name || newKeyData.permissions.length === 0}
                >
                  Create API Key
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
