'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Ticket, Search, Filter, Plus, Clock, AlertCircle } from 'lucide-react';
import { api } from '@/lib/api';

interface SupportTicket {
  id: string;
  ticket_number: string;
  subject: string;
  status: string;
  priority: string;
  category: string | null;
  sentiment_label: string;
  created_at: string;
  is_overdue: boolean;
  hours_open: number;
  customer_id: string | null;
}

export default function SupportTicketsPage() {
  const router = useRouter();
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    fetchTickets();
    fetchStats();
  }, [statusFilter, priorityFilter, search]);

  const fetchTickets = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();

      if (statusFilter !== 'all') {
        params.append('status', statusFilter);
      }
      if (priorityFilter !== 'all') {
        params.append('priority', priorityFilter);
      }
      if (search) {
        params.append('search', search);
      }

      const response = await api.get(`/support-tickets?${params.toString()}`);
      setTickets(response.data.tickets || []);
    } catch (error) {
      console.error('Failed to fetch tickets:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await api.get('/support-tickets/stats');
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
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

  return (
    <div className='space-y-6'>
      <div className='flex items-center justify-between'>
        <div>
          <h1 className='text-3xl font-bold'>Support Tickets</h1>
          <p className='text-gray-600 mt-1'>Manage customer support requests and issues</p>
        </div>
        <Button onClick={() => router.push('/dashboard/support/new')}>
          <Plus className='h-4 w-4 mr-2' />
          New Ticket
        </Button>
      </div>

      {stats && (
        <div className='grid grid-cols-1 md:grid-cols-4 gap-4'>
          <Card>
            <CardHeader className='pb-2'>
              <CardTitle className='text-sm font-medium text-gray-600'>Open Tickets</CardTitle>
            </CardHeader>
            <CardContent>
              <div className='text-2xl font-bold'>{stats.open_tickets}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className='pb-2'>
              <CardTitle className='text-sm font-medium text-gray-600'>In Progress</CardTitle>
            </CardHeader>
            <CardContent>
              <div className='text-2xl font-bold'>{stats.in_progress_tickets}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className='pb-2'>
              <CardTitle className='text-sm font-medium text-gray-600'>Overdue</CardTitle>
            </CardHeader>
            <CardContent>
              <div className='text-2xl font-bold text-red-600'>{stats.overdue_tickets}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className='pb-2'>
              <CardTitle className='text-sm font-medium text-gray-600'>
                Avg Resolution Time
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className='text-2xl font-bold'>
                {stats.avg_time_to_resolution
                  ? `${stats.avg_time_to_resolution.toFixed(1)}h`
                  : 'N/A'}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      <Card>
        <CardHeader>
          <div className='flex flex-col md:flex-row gap-4'>
            <div className='flex-1 relative'>
              <Search className='absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400' />
              <Input
                placeholder='Search tickets...'
                value={search}
                onChange={e => setSearch(e.target.value)}
                className='pl-10'
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className='w-full md:w-[180px]'>
                <SelectValue placeholder='Status' />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value='all'>All Status</SelectItem>
                <SelectItem value='open'>Open</SelectItem>
                <SelectItem value='in_progress'>In Progress</SelectItem>
                <SelectItem value='resolved'>Resolved</SelectItem>
                <SelectItem value='closed'>Closed</SelectItem>
              </SelectContent>
            </Select>
            <Select value={priorityFilter} onValueChange={setPriorityFilter}>
              <SelectTrigger className='w-full md:w-[180px]'>
                <SelectValue placeholder='Priority' />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value='all'>All Priority</SelectItem>
                <SelectItem value='critical'>Critical</SelectItem>
                <SelectItem value='high'>High</SelectItem>
                <SelectItem value='medium'>Medium</SelectItem>
                <SelectItem value='low'>Low</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className='text-center py-8 text-gray-500'>Loading tickets...</div>
          ) : tickets.length === 0 ? (
            <div className='text-center py-8 text-gray-500'>No tickets found</div>
          ) : (
            <div className='space-y-3'>
              {tickets.map(ticket => (
                <div
                  key={ticket.id}
                  onClick={() => router.push(`/dashboard/support/${ticket.id}`)}
                  className='p-4 border rounded-lg hover:bg-gray-50 cursor-pointer transition-colors'
                >
                  <div className='flex items-start justify-between'>
                    <div className='flex-1'>
                      <div className='flex items-center gap-2 mb-2'>
                        <Ticket className='h-4 w-4 text-gray-400' />
                        <span className='font-mono text-sm text-gray-600'>
                          {ticket.ticket_number}
                        </span>
                        {ticket.is_overdue && (
                          <Badge variant='destructive' className='flex items-center gap-1'>
                            <AlertCircle className='h-3 w-3' />
                            Overdue
                          </Badge>
                        )}
                      </div>
                      <h3 className='font-semibold text-lg mb-1'>{ticket.subject}</h3>
                      <div className='flex items-center gap-2 flex-wrap'>
                        <Badge className={getStatusColor(ticket.status)}>
                          {ticket.status.replace('_', ' ')}
                        </Badge>
                        <Badge className={getPriorityColor(ticket.priority)}>
                          {ticket.priority}
                        </Badge>
                        {ticket.category && <Badge variant='outline'>{ticket.category}</Badge>}
                        <span className='text-sm text-gray-500 flex items-center gap-1'>
                          <Clock className='h-3 w-3' />
                          {ticket.hours_open.toFixed(1)}h open
                        </span>
                      </div>
                    </div>
                    <div className='text-right text-sm text-gray-500'>
                      {new Date(ticket.created_at).toLocaleDateString()}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
