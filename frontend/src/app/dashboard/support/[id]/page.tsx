'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  ArrowLeft,
  Clock,
  User,
  MessageSquare,
  CheckCircle,
  XCircle,
  RotateCcw,
  Star,
} from 'lucide-react';
import { api } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

interface TicketDetails {
  id: string;
  ticket_number: string;
  subject: string;
  content: string;
  status: string;
  priority: string;
  category: string | null;
  sentiment_score: number | null;
  sentiment_label: string;
  assigned_to: string | null;
  resolution: string | null;
  created_at: string;
  updated_at: string;
  is_overdue: boolean;
  hours_open: number;
  time_to_first_response: number | null;
  time_to_resolution: number | null;
  satisfaction_rating: number | null;
  satisfaction_feedback: string | null;
  response_count: number;
}

export default function TicketDetailPage() {
  const router = useRouter();
  const params = useParams();
  const { toast } = useToast();
  const ticketId = params.id as string;

  const [ticket, setTicket] = useState<TicketDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [resolution, setResolution] = useState('');
  const [response, setResponse] = useState('');
  const [newPriority, setNewPriority] = useState('');
  const [newStatus, setNewStatus] = useState('');

  useEffect(() => {
    fetchTicket();
  }, [ticketId]);

  const fetchTicket = async () => {
    try {
      setLoading(true);
      const res = await api.get(`/support-tickets/${ticketId}`);
      setTicket(res.data);
      setNewPriority(res.data.priority);
      setNewStatus(res.data.status);
    } catch (error) {
      console.error('Failed to fetch ticket:', error);
      toast({
        title: 'Error',
        description: 'Failed to load ticket details',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleResolve = async () => {
    if (!resolution.trim()) {
      toast({
        title: 'Error',
        description: 'Please provide a resolution',
        variant: 'destructive',
      });
      return;
    }

    try {
      await api.post(`/support-tickets/${ticketId}/resolve`, {
        resolution,
        resolved_by: 'Current User',
      });
      toast({
        title: 'Success',
        description: 'Ticket resolved successfully',
      });
      fetchTicket();
      setResolution('');
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to resolve ticket',
        variant: 'destructive',
      });
    }
  };

  const handleClose = async () => {
    try {
      await api.post(`/support-tickets/${ticketId}/close`);
      toast({
        title: 'Success',
        description: 'Ticket closed successfully',
      });
      fetchTicket();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to close ticket',
        variant: 'destructive',
      });
    }
  };

  const handleReopen = async () => {
    try {
      await api.post(`/support-tickets/${ticketId}/reopen`, {
        reason: 'Reopened by user',
      });
      toast({
        title: 'Success',
        description: 'Ticket reopened successfully',
      });
      fetchTicket();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to reopen ticket',
        variant: 'destructive',
      });
    }
  };

  const handleAddResponse = async () => {
    if (!response.trim()) {
      return;
    }

    try {
      await api.post(`/support-tickets/${ticketId}/response`, {
        content: response,
        is_internal: false,
      });
      toast({
        title: 'Success',
        description: 'Response added successfully',
      });
      fetchTicket();
      setResponse('');
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to add response',
        variant: 'destructive',
      });
    }
  };

  const handleUpdateTicket = async () => {
    try {
      await api.patch(`/support-tickets/${ticketId}`, {
        priority: newPriority,
        status: newStatus,
      });
      toast({
        title: 'Success',
        description: 'Ticket updated successfully',
      });
      fetchTicket();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to update ticket',
        variant: 'destructive',
      });
    }
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      open: 'bg-blue-100 text-blue-800',
      in_progress: 'bg-yellow-100 text-yellow-800',
      resolved: 'bg-green-100 text-green-800',
      closed: 'bg-gray-100 text-gray-800',
      reopened: 'bg-red-100 text-red-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const getPriorityColor = (priority: string) => {
    const colors: Record<string, string> = {
      critical: 'bg-red-100 text-red-800',
      high: 'bg-orange-100 text-orange-800',
      medium: 'bg-yellow-100 text-yellow-800',
      low: 'bg-green-100 text-green-800',
    };
    return colors[priority] || 'bg-gray-100 text-gray-800';
  };

  if (loading) {
    return (
      <div className='flex items-center justify-center h-64'>
        <div className='text-gray-500'>Loading ticket...</div>
      </div>
    );
  }

  if (!ticket) {
    return (
      <div className='flex items-center justify-center h-64'>
        <div className='text-gray-500'>Ticket not found</div>
      </div>
    );
  }

  return (
    <div className='space-y-6'>
      <div className='flex items-center gap-4'>
        <Button variant='ghost' size='sm' onClick={() => router.push('/dashboard/support')}>
          <ArrowLeft className='h-4 w-4 mr-2' />
          Back
        </Button>
      </div>

      <div className='grid grid-cols-1 lg:grid-cols-3 gap-6'>
        <div className='lg:col-span-2 space-y-6'>
          <Card>
            <CardHeader>
              <div className='flex items-start justify-between'>
                <div>
                  <div className='text-sm text-gray-600 mb-2'>{ticket.ticket_number}</div>
                  <CardTitle className='text-2xl'>{ticket.subject}</CardTitle>
                </div>
                <div className='flex gap-2'>
                  <Badge className={getStatusColor(ticket.status)}>
                    {ticket.status.replace('_', ' ')}
                  </Badge>
                  <Badge className={getPriorityColor(ticket.priority)}>{ticket.priority}</Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent className='space-y-4'>
              <div>
                <h3 className='font-semibold mb-2'>Description</h3>
                <p className='text-gray-700 whitespace-pre-wrap'>{ticket.content}</p>
              </div>

              {ticket.sentiment_score !== null && (
                <div>
                  <h3 className='font-semibold mb-2'>Sentiment Analysis</h3>
                  <div className='flex items-center gap-2'>
                    <Badge variant='outline'>{ticket.sentiment_label}</Badge>
                    <span className='text-sm text-gray-600'>
                      Score: {(ticket.sentiment_score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              )}

              {ticket.resolution && (
                <div>
                  <h3 className='font-semibold mb-2'>Resolution</h3>
                  <p className='text-gray-700 whitespace-pre-wrap'>{ticket.resolution}</p>
                </div>
              )}

              {ticket.satisfaction_rating && (
                <div>
                  <h3 className='font-semibold mb-2'>Customer Satisfaction</h3>
                  <div className='flex items-center gap-2'>
                    <div className='flex'>
                      {[1, 2, 3, 4, 5].map(star => (
                        <Star
                          key={star}
                          className={`h-5 w-5 ${
                            star <= ticket.satisfaction_rating!
                              ? 'fill-yellow-400 text-yellow-400'
                              : 'text-gray-300'
                          }`}
                        />
                      ))}
                    </div>
                    <span className='text-sm text-gray-600'>{ticket.satisfaction_rating}/5</span>
                  </div>
                  {ticket.satisfaction_feedback && (
                    <p className='text-sm text-gray-600 mt-2'>{ticket.satisfaction_feedback}</p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {ticket.status !== 'resolved' && ticket.status !== 'closed' && (
            <Card>
              <CardHeader>
                <CardTitle>Add Response</CardTitle>
              </CardHeader>
              <CardContent className='space-y-4'>
                <Textarea
                  placeholder='Type your response...'
                  value={response}
                  onChange={e => setResponse(e.target.value)}
                  rows={4}
                />
                <Button onClick={handleAddResponse}>
                  <MessageSquare className='h-4 w-4 mr-2' />
                  Add Response
                </Button>
              </CardContent>
            </Card>
          )}

          {ticket.status !== 'resolved' && ticket.status !== 'closed' && (
            <Card>
              <CardHeader>
                <CardTitle>Resolve Ticket</CardTitle>
              </CardHeader>
              <CardContent className='space-y-4'>
                <Textarea
                  placeholder='Describe how the issue was resolved...'
                  value={resolution}
                  onChange={e => setResolution(e.target.value)}
                  rows={4}
                />
                <Button onClick={handleResolve}>
                  <CheckCircle className='h-4 w-4 mr-2' />
                  Resolve Ticket
                </Button>
              </CardContent>
            </Card>
          )}
        </div>

        <div className='space-y-6'>
          <Card>
            <CardHeader>
              <CardTitle>Ticket Details</CardTitle>
            </CardHeader>
            <CardContent className='space-y-4'>
              <div>
                <label className='text-sm font-medium text-gray-600'>Priority</label>
                <Select value={newPriority} onValueChange={setNewPriority}>
                  <SelectTrigger className='mt-1'>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value='low'>Low</SelectItem>
                    <SelectItem value='medium'>Medium</SelectItem>
                    <SelectItem value='high'>High</SelectItem>
                    <SelectItem value='critical'>Critical</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className='text-sm font-medium text-gray-600'>Status</label>
                <Select value={newStatus} onValueChange={setNewStatus}>
                  <SelectTrigger className='mt-1'>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value='open'>Open</SelectItem>
                    <SelectItem value='in_progress'>In Progress</SelectItem>
                    <SelectItem value='resolved'>Resolved</SelectItem>
                    <SelectItem value='closed'>Closed</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {(newPriority !== ticket.priority || newStatus !== ticket.status) && (
                <Button onClick={handleUpdateTicket} className='w-full'>
                  Update Ticket
                </Button>
              )}

              <div className='pt-4 border-t space-y-2'>
                <div className='flex items-center justify-between text-sm'>
                  <span className='text-gray-600'>Created</span>
                  <span>{new Date(ticket.created_at).toLocaleString()}</span>
                </div>
                <div className='flex items-center justify-between text-sm'>
                  <span className='text-gray-600'>Updated</span>
                  <span>{new Date(ticket.updated_at).toLocaleString()}</span>
                </div>
                <div className='flex items-center justify-between text-sm'>
                  <span className='text-gray-600'>Hours Open</span>
                  <span>{ticket.hours_open.toFixed(1)}h</span>
                </div>
                {ticket.time_to_first_response && (
                  <div className='flex items-center justify-between text-sm'>
                    <span className='text-gray-600'>First Response</span>
                    <span>{ticket.time_to_first_response.toFixed(1)}h</span>
                  </div>
                )}
                {ticket.time_to_resolution && (
                  <div className='flex items-center justify-between text-sm'>
                    <span className='text-gray-600'>Resolution Time</span>
                    <span>{ticket.time_to_resolution.toFixed(1)}h</span>
                  </div>
                )}
                <div className='flex items-center justify-between text-sm'>
                  <span className='text-gray-600'>Responses</span>
                  <span>{ticket.response_count}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Actions</CardTitle>
            </CardHeader>
            <CardContent className='space-y-2'>
              {ticket.status === 'resolved' && (
                <Button onClick={handleClose} className='w-full' variant='outline'>
                  <XCircle className='h-4 w-4 mr-2' />
                  Close Ticket
                </Button>
              )}
              {(ticket.status === 'resolved' || ticket.status === 'closed') && (
                <Button onClick={handleReopen} className='w-full' variant='outline'>
                  <RotateCcw className='h-4 w-4 mr-2' />
                  Reopen Ticket
                </Button>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
