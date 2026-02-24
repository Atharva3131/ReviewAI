'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Mail,
  Phone,
  MessageSquare,
  Search,
  Filter,
  ArrowUpRight,
  ArrowDownLeft,
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle,
  ExternalLink,
  Calendar,
} from 'lucide-react';
import { cn, formatDateTime } from '@/lib/utils';
import type { CustomerCommunication } from '@/types/customer';

interface CommunicationHistoryProps {
  customerId: string;
  communications?: CustomerCommunication[];
  onLoadMore?: () => void;
  hasMore?: boolean;
  isLoading?: boolean;
  className?: string;
}

export function CommunicationHistory({
  customerId,
  communications = [],
  onLoadMore,
  hasMore = false,
  isLoading = false,
  className,
}: CommunicationHistoryProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [directionFilter, setDirectionFilter] = useState<string>('');

  const getCommunicationIcon = (type: string) => {
    switch (type) {
      case 'email':
        return Mail;
      case 'phone':
        return Phone;
      case 'sms':
        return MessageSquare;
      case 'review_response':
        return MessageSquare;
      case 'support_ticket':
        return AlertCircle;
      default:
        return MessageSquare;
    }
  };

  const getDirectionIcon = (direction: string) => {
    return direction === 'inbound' ? ArrowDownLeft : ArrowUpRight;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'delivered':
      case 'sent':
        return CheckCircle;
      case 'read':
      case 'replied':
        return CheckCircle;
      case 'failed':
        return XCircle;
      default:
        return Clock;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'delivered':
      case 'sent':
        return 'text-blue-600';
      case 'read':
      case 'replied':
        return 'text-green-600';
      case 'failed':
        return 'text-red-600';
      default:
        return 'text-yellow-600';
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'email':
        return 'bg-blue-100 text-blue-800';
      case 'phone':
        return 'bg-green-100 text-green-800';
      case 'sms':
        return 'bg-purple-100 text-purple-800';
      case 'review_response':
        return 'bg-orange-100 text-orange-800';
      case 'support_ticket':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  // Mock data if no communications provided
  const mockCommunications: CustomerCommunication[] =
    communications.length > 0
      ? communications
      : [
          {
            id: '1',
            customer_id: customerId,
            type: 'email',
            direction: 'outbound',
            subject: 'Apology for Recent Service Issues',
            content:
              'Dear John, We sincerely apologize for the service issues you experienced during your recent visit. We take your feedback seriously and have implemented immediate improvements...',
            status: 'read',
            created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2).toISOString(),
            metadata: {
              template_used: 'apology_email_template_v2',
            },
          },
          {
            id: '2',
            customer_id: customerId,
            type: 'review_response',
            direction: 'outbound',
            content:
              'Thank you for your feedback. We apologize for the wait time and are working to improve our service. Please contact us directly so we can make this right.',
            status: 'sent',
            created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3).toISOString(),
            metadata: {
              platform: 'google',
              review_id: 'review_123',
            },
          },
          {
            id: '3',
            customer_id: customerId,
            type: 'phone',
            direction: 'inbound',
            content:
              'Customer called to express dissatisfaction with recent order. Discussed refund options and future service improvements.',
            status: 'completed',
            created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 5).toISOString(),
            metadata: {
              duration: '15 minutes',
              agent: 'Sarah Johnson',
            },
          },
          {
            id: '4',
            customer_id: customerId,
            type: 'sms',
            direction: 'outbound',
            content:
              'Hi John! We have a special 20% discount offer just for you. Use code WELCOME20 on your next order. Valid until end of month.',
            status: 'delivered',
            created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 10).toISOString(),
            metadata: {
              campaign: 'customer_recovery_sms',
            },
          },
          {
            id: '5',
            customer_id: customerId,
            type: 'support_ticket',
            direction: 'inbound',
            subject: 'Order #12345 - Missing Items',
            content:
              'My recent order was missing two items. I ordered a burger and fries but only received the burger. Please help resolve this.',
            status: 'resolved',
            created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 15).toISOString(),
            metadata: {
              ticket_id: 'TICKET-789',
              priority: 'high',
            },
          },
        ];

  // Filter communications
  const filteredCommunications = mockCommunications.filter(comm => {
    const matchesSearch =
      !searchTerm ||
      comm.content.toLowerCase().includes(searchTerm.toLowerCase()) ||
      comm.subject?.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesType = !typeFilter || comm.type === typeFilter;
    const matchesDirection = !directionFilter || comm.direction === directionFilter;

    return matchesSearch && matchesType && matchesDirection;
  });

  const communicationTypes = ['email', 'phone', 'sms', 'review_response', 'support_ticket'];
  const directions = ['inbound', 'outbound'];

  return (
    <Card className={className}>
      <CardHeader>
        <div className='flex items-center justify-between'>
          <div>
            <CardTitle>Communication History</CardTitle>
            <CardDescription>
              All interactions and communications with this customer
            </CardDescription>
          </div>
          <div className='text-sm text-gray-500'>
            {filteredCommunications.length} communication
            {filteredCommunications.length !== 1 ? 's' : ''}
          </div>
        </div>

        {/* Search and Filters */}
        <div className='space-y-4'>
          <div className='relative'>
            <Search className='absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400' />
            <Input
              placeholder='Search communications...'
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className='pl-10'
            />
          </div>

          <div className='flex items-center space-x-4'>
            <div className='flex items-center space-x-2'>
              <Filter className='h-4 w-4 text-gray-400' />
              <select
                value={typeFilter}
                onChange={e => setTypeFilter(e.target.value)}
                className='text-sm border border-gray-300 rounded px-2 py-1'
              >
                <option value=''>All Types</option>
                {communicationTypes.map(type => (
                  <option key={type} value={type}>
                    {type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </option>
                ))}
              </select>
            </div>

            <div className='flex items-center space-x-2'>
              <select
                value={directionFilter}
                onChange={e => setDirectionFilter(e.target.value)}
                className='text-sm border border-gray-300 rounded px-2 py-1'
              >
                <option value=''>All Directions</option>
                {directions.map(direction => (
                  <option key={direction} value={direction}>
                    {direction.charAt(0).toUpperCase() + direction.slice(1)}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {filteredCommunications.length === 0 ? (
          <div className='text-center py-8'>
            <MessageSquare className='h-12 w-12 text-gray-400 mx-auto mb-4' />
            <h3 className='text-lg font-medium text-gray-900 mb-2'>No Communications</h3>
            <p className='text-gray-600'>
              {searchTerm || typeFilter || directionFilter
                ? 'No communications match your current filters.'
                : 'No communications found for this customer.'}
            </p>
          </div>
        ) : (
          <div className='space-y-4'>
            {filteredCommunications.map(communication => {
              const CommunicationIcon = getCommunicationIcon(communication.type);
              const DirectionIcon = getDirectionIcon(communication.direction);
              const StatusIcon = getStatusIcon(communication.status);

              return (
                <div
                  key={communication.id}
                  className='border rounded-lg p-4 hover:bg-gray-50 transition-colors'
                >
                  <div className='flex items-start space-x-4'>
                    {/* Communication Type Icon */}
                    <div
                      className={cn(
                        'flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center',
                        getTypeColor(communication.type),
                      )}
                    >
                      <CommunicationIcon className='h-5 w-5' />
                    </div>

                    {/* Communication Content */}
                    <div className='flex-1 min-w-0'>
                      <div className='flex items-center justify-between mb-2'>
                        <div className='flex items-center space-x-2'>
                          <h4 className='text-sm font-medium text-gray-900'>
                            {communication.subject ||
                              communication.type
                                .replace('_', ' ')
                                .replace(/\b\w/g, l => l.toUpperCase())}
                          </h4>

                          <div className='flex items-center space-x-1'>
                            <DirectionIcon
                              className={cn(
                                'h-4 w-4',
                                communication.direction === 'inbound'
                                  ? 'text-green-600'
                                  : 'text-blue-600',
                              )}
                            />
                            <span
                              className={cn(
                                'text-xs font-medium',
                                communication.direction === 'inbound'
                                  ? 'text-green-600'
                                  : 'text-blue-600',
                              )}
                            >
                              {communication.direction}
                            </span>
                          </div>
                        </div>

                        <div className='flex items-center space-x-2'>
                          <div
                            className={cn(
                              'flex items-center space-x-1',
                              getStatusColor(communication.status),
                            )}
                          >
                            <StatusIcon className='h-4 w-4' />
                            <span className='text-xs font-medium capitalize'>
                              {communication.status}
                            </span>
                          </div>

                          <span className='text-xs text-gray-500'>
                            {formatDateTime(communication.created_at)}
                          </span>
                        </div>
                      </div>

                      <p className='text-sm text-gray-700 mb-3 line-clamp-3'>
                        {communication.content}
                      </p>

                      {/* Metadata */}
                      {communication.metadata && (
                        <div className='flex items-center space-x-4 text-xs text-gray-500'>
                          {communication.metadata.platform && (
                            <div className='flex items-center space-x-1'>
                              <ExternalLink className='h-3 w-3' />
                              <span>Platform: {communication.metadata.platform}</span>
                            </div>
                          )}

                          {communication.metadata.template_used && (
                            <div className='flex items-center space-x-1'>
                              <span>Template: {communication.metadata.template_used}</span>
                            </div>
                          )}

                          {communication.metadata.agent && (
                            <div className='flex items-center space-x-1'>
                              <span>Agent: {communication.metadata.agent}</span>
                            </div>
                          )}

                          {communication.metadata.duration && (
                            <div className='flex items-center space-x-1'>
                              <Clock className='h-3 w-3' />
                              <span>Duration: {communication.metadata.duration}</span>
                            </div>
                          )}

                          {communication.metadata.priority && (
                            <div className='flex items-center space-x-1'>
                              <AlertCircle className='h-3 w-3' />
                              <span>Priority: {communication.metadata.priority}</span>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Action Links */}
                      <div className='mt-3 flex items-center space-x-2'>
                        {communication.metadata?.review_id && (
                          <Button
                            variant='ghost'
                            size='sm'
                            onClick={() =>
                              window.open(
                                `/dashboard/reviews/${communication.metadata?.review_id}`,
                                '_blank',
                              )
                            }
                          >
                            <ExternalLink className='h-3 w-3 mr-1' />
                            View Review
                          </Button>
                        )}

                        {communication.metadata?.ticket_id && (
                          <Button
                            variant='ghost'
                            size='sm'
                            onClick={() =>
                              console.log('View ticket:', communication.metadata?.ticket_id)
                            }
                          >
                            <ExternalLink className='h-3 w-3 mr-1' />
                            View Ticket
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}

            {/* Load More Button */}
            {hasMore && (
              <div className='text-center pt-4'>
                <Button variant='outline' onClick={onLoadMore} disabled={isLoading}>
                  {isLoading ? 'Loading...' : 'Load More Communications'}
                </Button>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
