'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Mail,
  Phone,
  MessageSquare,
  Gift,
  User,
  Calendar,
  Plus,
  MoreHorizontal,
} from 'lucide-react';
import { cn, formatDateTime } from '@/lib/utils';
import type { RecoveryAction } from '@/types/customer';

interface RecoveryActionsTimelineProps {
  customerId: string;
  actions?: RecoveryAction[];
  onAddAction?: () => void;
  onUpdateAction?: (actionId: string, updates: Partial<RecoveryAction>) => void;
  className?: string;
}

export function RecoveryActionsTimeline({
  customerId,
  actions = [],
  onAddAction,
  onUpdateAction,
  className,
}: RecoveryActionsTimelineProps) {
  const [isLoading, setIsLoading] = useState(false);

  const getActionIcon = (type: string) => {
    switch (type) {
      case 'email':
        return Mail;
      case 'phone_call':
        return Phone;
      case 'sms':
        return MessageSquare;
      case 'discount_offer':
        return Gift;
      case 'personal_outreach':
        return User;
      default:
        return AlertCircle;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return CheckCircle;
      case 'failed':
        return XCircle;
      case 'in_progress':
        return Clock;
      default:
        return Clock;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-600 bg-green-100';
      case 'failed':
        return 'text-red-600 bg-red-100';
      case 'in_progress':
        return 'text-blue-600 bg-blue-100';
      default:
        return 'text-yellow-600 bg-yellow-100';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'border-red-200 bg-red-50';
      case 'medium':
        return 'border-yellow-200 bg-yellow-50';
      default:
        return 'border-green-200 bg-green-50';
    }
  };

  const handleActionUpdate = async (actionId: string, status: string) => {
    setIsLoading(true);
    try {
      onUpdateAction?.(actionId, {
        status: status as any,
        completed_at: status === 'completed' ? new Date().toISOString() : undefined,
      });
    } catch (error) {
      console.error('Error updating action:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Mock data if no actions provided
  const mockActions: RecoveryAction[] =
    actions.length > 0
      ? actions
      : [
          {
            id: '1',
            customer_id: customerId,
            type: 'email',
            status: 'completed',
            priority: 'high',
            title: 'Apology Email Sent',
            description:
              'Personalized apology email addressing service issues mentioned in recent review',
            completed_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2).toISOString(),
            created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3).toISOString(),
            updated_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2).toISOString(),
            metadata: {
              template_id: 'apology_template_v2',
              notes: 'Customer responded positively to the email',
            },
          },
          {
            id: '2',
            customer_id: customerId,
            type: 'discount_offer',
            status: 'in_progress',
            priority: 'medium',
            title: '20% Discount Offer',
            description: 'Exclusive discount code sent to encourage return visit',
            scheduled_at: new Date(Date.now() + 1000 * 60 * 60 * 24).toISOString(),
            created_at: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
            updated_at: new Date(Date.now() - 1000 * 60 * 60 * 12).toISOString(),
            metadata: {
              discount_amount: 20,
              template_id: 'discount_offer_template',
            },
          },
          {
            id: '3',
            customer_id: customerId,
            type: 'phone_call',
            status: 'pending',
            priority: 'high',
            title: 'Personal Follow-up Call',
            description: 'Direct call from manager to discuss concerns and ensure satisfaction',
            scheduled_at: new Date(Date.now() + 1000 * 60 * 60 * 48).toISOString(),
            created_at: new Date(Date.now() - 1000 * 60 * 60 * 6).toISOString(),
            updated_at: new Date(Date.now() - 1000 * 60 * 60 * 6).toISOString(),
            metadata: {
              contact_person: 'Sarah Johnson - Customer Success Manager',
              notes: 'Customer prefers calls after 2 PM EST',
            },
          },
        ];

  const sortedActions = mockActions.sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );

  return (
    <Card className={className}>
      <CardHeader>
        <div className='flex items-center justify-between'>
          <div>
            <CardTitle>Recovery Actions</CardTitle>
            <CardDescription>Timeline of customer recovery efforts and outreach</CardDescription>
          </div>
          {onAddAction && (
            <Button size='sm' onClick={onAddAction}>
              <Plus className='h-4 w-4 mr-1' />
              Add Action
            </Button>
          )}
        </div>
      </CardHeader>

      <CardContent>
        {sortedActions.length === 0 ? (
          <div className='text-center py-8'>
            <AlertCircle className='h-12 w-12 text-gray-400 mx-auto mb-4' />
            <h3 className='text-lg font-medium text-gray-900 mb-2'>No Recovery Actions</h3>
            <p className='text-gray-600 mb-4'>
              No recovery actions have been initiated for this customer yet.
            </p>
            {onAddAction && (
              <Button onClick={onAddAction}>
                <Plus className='h-4 w-4 mr-1' />
                Create First Action
              </Button>
            )}
          </div>
        ) : (
          <div className='space-y-4'>
            {sortedActions.map((action, index) => {
              const ActionIcon = getActionIcon(action.type);
              const StatusIcon = getStatusIcon(action.status);
              const isLast = index === sortedActions.length - 1;

              return (
                <div key={action.id} className='relative'>
                  {/* Timeline line */}
                  {!isLast && <div className='absolute left-6 top-12 w-0.5 h-16 bg-gray-200' />}

                  <div
                    className={cn(
                      'flex items-start space-x-4 p-4 rounded-lg border',
                      getPriorityColor(action.priority),
                    )}
                  >
                    {/* Action Icon */}
                    <div
                      className={cn(
                        'flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center',
                        getStatusColor(action.status),
                      )}
                    >
                      <ActionIcon className='h-6 w-6' />
                    </div>

                    {/* Action Content */}
                    <div className='flex-1 min-w-0'>
                      <div className='flex items-center justify-between mb-2'>
                        <div className='flex items-center space-x-2'>
                          <h4 className='text-sm font-medium text-gray-900'>{action.title}</h4>
                          <span
                            className={cn(
                              'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium',
                              action.priority === 'high'
                                ? 'bg-red-100 text-red-800'
                                : action.priority === 'medium'
                                  ? 'bg-yellow-100 text-yellow-800'
                                  : 'bg-green-100 text-green-800',
                            )}
                          >
                            {action.priority} priority
                          </span>
                        </div>

                        <div className='flex items-center space-x-2'>
                          <div
                            className={cn(
                              'flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium',
                              getStatusColor(action.status),
                            )}
                          >
                            <StatusIcon className='h-3 w-3' />
                            <span className='capitalize'>{action.status.replace('_', ' ')}</span>
                          </div>

                          {action.status === 'pending' && onUpdateAction && (
                            <div className='flex items-center space-x-1'>
                              <Button
                                size='sm'
                                variant='outline'
                                onClick={() => handleActionUpdate(action.id, 'in_progress')}
                                disabled={isLoading}
                              >
                                Start
                              </Button>
                              <Button
                                size='sm'
                                variant='outline'
                                onClick={() => handleActionUpdate(action.id, 'completed')}
                                disabled={isLoading}
                              >
                                Complete
                              </Button>
                            </div>
                          )}

                          {action.status === 'in_progress' && onUpdateAction && (
                            <Button
                              size='sm'
                              variant='outline'
                              onClick={() => handleActionUpdate(action.id, 'completed')}
                              disabled={isLoading}
                            >
                              Complete
                            </Button>
                          )}
                        </div>
                      </div>

                      <p className='text-sm text-gray-700 mb-3'>{action.description}</p>

                      {/* Metadata */}
                      <div className='space-y-2'>
                        <div className='flex items-center space-x-4 text-xs text-gray-500'>
                          <div className='flex items-center space-x-1'>
                            <Calendar className='h-3 w-3' />
                            <span>Created: {formatDateTime(action.created_at)}</span>
                          </div>

                          {action.scheduled_at && (
                            <div className='flex items-center space-x-1'>
                              <Clock className='h-3 w-3' />
                              <span>Scheduled: {formatDateTime(action.scheduled_at)}</span>
                            </div>
                          )}

                          {action.completed_at && (
                            <div className='flex items-center space-x-1'>
                              <CheckCircle className='h-3 w-3' />
                              <span>Completed: {formatDateTime(action.completed_at)}</span>
                            </div>
                          )}
                        </div>

                        {/* Additional metadata */}
                        {action.metadata && (
                          <div className='space-y-1'>
                            {action.metadata.contact_person && (
                              <div className='flex items-center space-x-1 text-xs text-gray-600'>
                                <User className='h-3 w-3' />
                                <span>Contact: {action.metadata.contact_person}</span>
                              </div>
                            )}

                            {action.metadata.discount_amount && (
                              <div className='flex items-center space-x-1 text-xs text-gray-600'>
                                <Gift className='h-3 w-3' />
                                <span>Discount: {action.metadata.discount_amount}%</span>
                              </div>
                            )}

                            {action.metadata.notes && (
                              <div className='text-xs text-gray-600 bg-gray-50 p-2 rounded'>
                                <strong>Notes:</strong> {action.metadata.notes}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
