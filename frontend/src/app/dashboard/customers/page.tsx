'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  RiskIndicator,
  ChurnProbability,
  CustomerStatusBadge,
} from '@/components/customers/risk-indicator';
import {
  Search,
  Filter,
  SortAsc,
  SortDesc,
  Users,
  Star,
  Calendar,
  ExternalLink,
  RefreshCw,
  CheckSquare,
  Square,
  BarChart,
  MessageSquare,
  Phone,
  Mail,
  Tag,
  TrendingUp,
  AlertTriangle,
} from 'lucide-react';
import { cn, formatDateTime } from '@/lib/utils';
import type {
  Customer,
  CustomerFilters,
  CustomerSortOptions,
  CustomersListResponse,
} from '@/types/customer';
import api from '@/lib/api';

const RISK_LEVELS = ['low', 'medium', 'high'];
const STATUSES = ['active', 'at_risk', 'churned', 'recovered'];
const CONTACT_METHODS = ['email', 'phone', 'sms'];

export default function CustomersPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [customers, setCustomers] = useState<Customer[]>([]);
  const [totalCustomers, setTotalCustomers] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCustomers, setSelectedCustomers] = useState<Set<string>>(new Set());

  // Filters and sorting
  const [filters, setFilters] = useState<CustomerFilters>({
    search: searchParams.get('search') || '',
    risk_level: searchParams.get('risk_level')?.split(',') || undefined,
    status: searchParams.get('status')?.split(',') || undefined,
  });

  const [sortOptions, setSortOptions] = useState<CustomerSortOptions>({
    field: (searchParams.get('sort') as any) || 'last_review_date',
    direction: (searchParams.get('order') as any) || 'desc',
  });

  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    fetchCustomers();
  }, [currentPage, filters, sortOptions]);

  const fetchCustomers = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      params.set('page', currentPage.toString());
      params.set('per_page', '20');
      params.set('sort', sortOptions.field);
      params.set('order', sortOptions.direction);

      if (filters.search) {
        params.set('search', filters.search);
      }
      if (filters.risk_level?.length) {
        params.set('risk_level', filters.risk_level.join(','));
      }
      if (filters.status?.length) {
        params.set('status', filters.status.join(','));
      }

      const response = await api.get(`/customers?${params.toString()}`);
      const data: CustomersListResponse = response.data;

      setCustomers(data.customers);
      setTotalCustomers(data.total);
      setTotalPages(data.total_pages);
    } catch (err: any) {
      console.error('Error fetching customers:', err);
      setError('Failed to load customers');

      // Mock data for development
      const mockCustomers: Customer[] = [
        {
          id: '1',
          name: 'John Smith',
          email: 'john.smith@email.com',
          phone: '+1-555-0123',
          total_reviews: 8,
          average_rating: 2.1,
          last_review_date: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2).toISOString(),
          first_review_date: new Date(Date.now() - 1000 * 60 * 60 * 24 * 180).toISOString(),
          risk_score: 0.85,
          risk_level: 'high',
          churn_probability: 0.92,
          lifetime_value: 1250,
          status: 'at_risk',
          tags: ['vip', 'frequent_complainer'],
          created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 200).toISOString(),
          updated_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2).toISOString(),
          metadata: {
            location: 'New York, NY',
            preferred_contact_method: 'email',
            timezone: 'America/New_York',
          },
        },
        {
          id: '2',
          name: 'Sarah Johnson',
          email: 'sarah.j@email.com',
          total_reviews: 15,
          average_rating: 4.7,
          last_review_date: new Date(Date.now() - 1000 * 60 * 60 * 24 * 7).toISOString(),
          first_review_date: new Date(Date.now() - 1000 * 60 * 60 * 24 * 365).toISOString(),
          risk_score: 0.15,
          risk_level: 'low',
          churn_probability: 0.08,
          lifetime_value: 3200,
          status: 'active',
          tags: ['loyal', 'advocate'],
          created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 400).toISOString(),
          updated_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 7).toISOString(),
          metadata: {
            location: 'Los Angeles, CA',
            preferred_contact_method: 'phone',
            timezone: 'America/Los_Angeles',
          },
        },
        {
          id: '3',
          name: 'Mike Davis',
          email: 'mike.davis@email.com',
          phone: '+1-555-0456',
          total_reviews: 4,
          average_rating: 3.2,
          last_review_date: new Date(Date.now() - 1000 * 60 * 60 * 24 * 30).toISOString(),
          first_review_date: new Date(Date.now() - 1000 * 60 * 60 * 24 * 90).toISOString(),
          risk_score: 0.45,
          risk_level: 'medium',
          churn_probability: 0.38,
          lifetime_value: 850,
          status: 'active',
          tags: ['new_customer'],
          created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 100).toISOString(),
          updated_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 30).toISOString(),
          metadata: {
            location: 'Chicago, IL',
            preferred_contact_method: 'sms',
            timezone: 'America/Chicago',
          },
        },
        {
          id: '4',
          name: 'Emily Chen',
          email: 'emily.chen@email.com',
          total_reviews: 12,
          average_rating: 4.1,
          last_review_date: new Date(Date.now() - 1000 * 60 * 60 * 24 * 60).toISOString(),
          first_review_date: new Date(Date.now() - 1000 * 60 * 60 * 24 * 300).toISOString(),
          risk_score: 0.72,
          risk_level: 'high',
          churn_probability: 0.68,
          lifetime_value: 2100,
          status: 'recovered',
          tags: ['recovered', 'high_value'],
          created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 320).toISOString(),
          updated_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 60).toISOString(),
          metadata: {
            location: 'San Francisco, CA',
            preferred_contact_method: 'email',
            timezone: 'America/Los_Angeles',
          },
        },
      ];

      setCustomers(mockCustomers);
      setTotalCustomers(mockCustomers.length);
      setTotalPages(1);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFilterChange = (key: keyof CustomerFilters, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setCurrentPage(1);
  };

  const handleSortChange = (field: CustomerSortOptions['field']) => {
    setSortOptions(prev => ({
      field,
      direction: prev.field === field && prev.direction === 'desc' ? 'asc' : 'desc',
    }));
  };

  const handleSelectCustomer = (customerId: string) => {
    setSelectedCustomers(prev => {
      const newSet = new Set(prev);
      if (newSet.has(customerId)) {
        newSet.delete(customerId);
      } else {
        newSet.add(customerId);
      }
      return newSet;
    });
  };

  const handleSelectAll = () => {
    if (selectedCustomers.size === (customers?.length || 0)) {
      setSelectedCustomers(new Set());
    } else {
      setSelectedCustomers(new Set((customers || []).map(c => c.id)));
    }
  };

  const handleViewCustomer = (customerId: string) => {
    router.push(`/dashboard/customers/${customerId}`);
  };

  const handleBulkAction = async (action: 'tag' | 'export' | 'recovery') => {
    if (selectedCustomers.size === 0) {
      return;
    }

    setIsLoading(true);
    try {
      const customerIds = Array.from(selectedCustomers);

      switch (action) {
        case 'tag':
          // Open tag modal (would implement in real app)
          console.log('Bulk tag customers:', customerIds);
          break;

        case 'export':
          const response = await api.post('/customers/export', {
            customer_ids: customerIds,
            format: 'csv',
          });
          // Download the file
          const blob = new Blob([response.data], { type: 'text/csv' });
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `customers-export-${new Date().toISOString().split('T')[0]}.csv`;
          document.body.appendChild(a);
          a.click();
          window.URL.revokeObjectURL(url);
          document.body.removeChild(a);
          break;

        case 'recovery':
          await api.post('/customers/bulk-recovery', { customer_ids: customerIds });
          // Refresh data
          fetchCustomers();
          break;
      }

      setSelectedCustomers(new Set());
    } catch (error) {
      console.error(`Error performing bulk ${action}:`, error);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading && customers.length === 0) {
    return (
      <div className='px-4 sm:px-6 lg:px-8'>
        <div className='animate-pulse space-y-4'>
          <div className='h-8 bg-gray-200 rounded w-1/4'></div>
          <div className='h-12 bg-gray-200 rounded'></div>
          {[...Array(5)].map((_, i) => (
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
            <h1 className='text-2xl font-bold text-gray-900'>Customers</h1>
            <p className='mt-1 text-sm text-gray-500'>
              Manage customer relationships and track risk indicators
            </p>
          </div>
          <div className='flex items-center space-x-2'>
            <Button
              variant='outline'
              size='sm'
              onClick={() => router.push('/dashboard/customers/analytics')}
            >
              <BarChart className='h-4 w-4 mr-1' />
              Analytics
            </Button>
            <Button variant='outline' size='sm' onClick={fetchCustomers} disabled={isLoading}>
              <RefreshCw className={cn('h-4 w-4 mr-1', isLoading && 'animate-spin')} />
              Refresh
            </Button>
          </div>
        </div>
      </div>

      {/* Search and Filters */}
      <Card className='mb-6'>
        <CardContent className='p-4'>
          <div className='flex items-center space-x-4'>
            <div className='flex-1'>
              <div className='relative'>
                <Search className='absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400' />
                <Input
                  placeholder='Search customers...'
                  value={filters.search || ''}
                  onChange={e => handleFilterChange('search', e.target.value)}
                  className='pl-10'
                />
              </div>
            </div>
            <Button variant='outline' onClick={() => setShowFilters(!showFilters)}>
              <Filter className='h-4 w-4 mr-1' />
              Filters
            </Button>
          </div>

          {showFilters && (
            <div className='mt-4 pt-4 border-t grid grid-cols-1 md:grid-cols-3 gap-4'>
              {/* Risk Level Filter */}
              <div>
                <Label className='text-sm font-medium'>Risk Level</Label>
                <div className='mt-1 flex flex-wrap gap-1'>
                  {RISK_LEVELS.map(level => (
                    <button
                      key={level}
                      onClick={() => {
                        const currentLevels = filters.risk_level || [];
                        const newLevels = currentLevels.includes(level)
                          ? currentLevels.filter(l => l !== level)
                          : [...currentLevels, level];
                        handleFilterChange('risk_level', newLevels.length ? newLevels : undefined);
                      }}
                      className={cn(
                        'px-2 py-1 text-xs rounded border capitalize',
                        filters.risk_level?.includes(level)
                          ? 'bg-blue-100 text-blue-800 border-blue-200'
                          : 'bg-gray-100 text-gray-700 border-gray-200',
                      )}
                    >
                      {level}
                    </button>
                  ))}
                </div>
              </div>

              {/* Status Filter */}
              <div>
                <Label className='text-sm font-medium'>Status</Label>
                <div className='mt-1 flex flex-wrap gap-1'>
                  {STATUSES.map(status => (
                    <button
                      key={status}
                      onClick={() => {
                        const currentStatus = filters.status || [];
                        const newStatus = currentStatus.includes(status)
                          ? currentStatus.filter(s => s !== status)
                          : [...currentStatus, status];
                        handleFilterChange('status', newStatus.length ? newStatus : undefined);
                      }}
                      className={cn(
                        'px-2 py-1 text-xs rounded border capitalize',
                        filters.status?.includes(status)
                          ? 'bg-blue-100 text-blue-800 border-blue-200'
                          : 'bg-gray-100 text-gray-700 border-gray-200',
                      )}
                    >
                      {status.replace('_', ' ')}
                    </button>
                  ))}
                </div>
              </div>

              {/* Quick Filters */}
              <div>
                <Label className='text-sm font-medium'>Quick Filters</Label>
                <div className='mt-1 flex flex-wrap gap-1'>
                  <button
                    onClick={() => handleFilterChange('risk_level', ['high'])}
                    className='px-2 py-1 text-xs rounded border bg-red-50 text-red-700 border-red-200 hover:bg-red-100'
                  >
                    High Risk Only
                  </button>
                  <button
                    onClick={() => handleFilterChange('status', ['at_risk'])}
                    className='px-2 py-1 text-xs rounded border bg-yellow-50 text-yellow-700 border-yellow-200 hover:bg-yellow-100'
                  >
                    At Risk Only
                  </button>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Bulk Actions */}
      {selectedCustomers.size > 0 && (
        <Card className='mb-4'>
          <CardContent className='p-4'>
            <div className='flex items-center justify-between'>
              <span className='text-sm text-gray-600'>
                {selectedCustomers.size} customer{selectedCustomers.size !== 1 ? 's' : ''} selected
              </span>
              <div className='flex items-center space-x-2'>
                <Button
                  variant='outline'
                  size='sm'
                  onClick={() => handleBulkAction('tag')}
                  disabled={isLoading}
                >
                  <Tag className='h-4 w-4 mr-1' />
                  Add Tags
                </Button>
                <Button
                  variant='outline'
                  size='sm'
                  onClick={() => handleBulkAction('recovery')}
                  disabled={isLoading}
                >
                  <TrendingUp className='h-4 w-4 mr-1' />
                  Start Recovery
                </Button>
                <Button
                  variant='outline'
                  size='sm'
                  onClick={() => handleBulkAction('export')}
                  disabled={isLoading}
                >
                  Export Selected
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Customers List */}
      <div className='space-y-4'>
        {/* Table Header */}
        <div className='bg-gray-50 px-4 py-3 rounded-lg'>
          <div className='flex items-center space-x-4'>
            <button onClick={handleSelectAll} className='flex items-center'>
              {selectedCustomers.size === (customers || []).length ? (
                <CheckSquare className='h-4 w-4 text-blue-600' />
              ) : (
                <Square className='h-4 w-4 text-gray-400' />
              )}
            </button>

            <div className='flex-1 grid grid-cols-12 gap-4 text-sm font-medium text-gray-700'>
              <div className='col-span-3'>
                <button
                  onClick={() => handleSortChange('name')}
                  className='flex items-center hover:text-gray-900'
                >
                  Customer
                  {sortOptions.field === 'name' &&
                    (sortOptions.direction === 'desc' ? (
                      <SortDesc className='h-4 w-4 ml-1' />
                    ) : (
                      <SortAsc className='h-4 w-4 ml-1' />
                    ))}
                </button>
              </div>
              <div className='col-span-2'>
                <button
                  onClick={() => handleSortChange('total_reviews')}
                  className='flex items-center hover:text-gray-900'
                >
                  Reviews
                  {sortOptions.field === 'total_reviews' &&
                    (sortOptions.direction === 'desc' ? (
                      <SortDesc className='h-4 w-4 ml-1' />
                    ) : (
                      <SortAsc className='h-4 w-4 ml-1' />
                    ))}
                </button>
              </div>
              <div className='col-span-2'>
                <button
                  onClick={() => handleSortChange('average_rating')}
                  className='flex items-center hover:text-gray-900'
                >
                  Avg Rating
                  {sortOptions.field === 'average_rating' &&
                    (sortOptions.direction === 'desc' ? (
                      <SortDesc className='h-4 w-4 ml-1' />
                    ) : (
                      <SortAsc className='h-4 w-4 ml-1' />
                    ))}
                </button>
              </div>
              <div className='col-span-2'>
                <button
                  onClick={() => handleSortChange('risk_score')}
                  className='flex items-center hover:text-gray-900'
                >
                  Risk Level
                  {sortOptions.field === 'risk_score' &&
                    (sortOptions.direction === 'desc' ? (
                      <SortDesc className='h-4 w-4 ml-1' />
                    ) : (
                      <SortAsc className='h-4 w-4 ml-1' />
                    ))}
                </button>
              </div>
              <div className='col-span-2'>Status</div>
              <div className='col-span-1'>Actions</div>
            </div>
          </div>
        </div>

        {/* Customers */}
        {(customers || []).map(customer => (
          <Card key={customer.id} className='hover:shadow-md transition-shadow'>
            <CardContent className='p-4'>
              <div className='flex items-start space-x-4'>
                <button onClick={() => handleSelectCustomer(customer.id)} className='mt-1'>
                  {selectedCustomers.has(customer.id) ? (
                    <CheckSquare className='h-4 w-4 text-blue-600' />
                  ) : (
                    <Square className='h-4 w-4 text-gray-400' />
                  )}
                </button>

                <div className='flex-1 grid grid-cols-12 gap-4'>
                  {/* Customer Info */}
                  <div className='col-span-3'>
                    <div className='flex items-center space-x-2 mb-2'>
                      <Users className='h-4 w-4 text-gray-400' />
                      <span className='font-medium text-gray-900'>{customer.name}</span>
                    </div>
                    <div className='space-y-1'>
                      {customer.email && (
                        <div className='flex items-center space-x-1 text-sm text-gray-600'>
                          <Mail className='h-3 w-3' />
                          <span>{customer.email}</span>
                        </div>
                      )}
                      {customer.phone && (
                        <div className='flex items-center space-x-1 text-sm text-gray-600'>
                          <Phone className='h-3 w-3' />
                          <span>{customer.phone}</span>
                        </div>
                      )}
                      {customer.metadata?.location && (
                        <p className='text-xs text-gray-500'>{customer.metadata.location}</p>
                      )}
                    </div>
                    {customer.tags.length > 0 && (
                      <div className='flex flex-wrap gap-1 mt-2'>
                        {customer.tags.slice(0, 2).map(tag => (
                          <span
                            key={tag}
                            className='inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800'
                          >
                            {tag}
                          </span>
                        ))}
                        {customer.tags.length > 2 && (
                          <span className='text-xs text-gray-500'>+{customer.tags.length - 2}</span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Reviews */}
                  <div className='col-span-2'>
                    <div className='flex items-center space-x-1 mb-1'>
                      <MessageSquare className='h-4 w-4 text-gray-400' />
                      <span className='font-medium text-gray-900'>{customer.total_reviews}</span>
                    </div>
                    <p className='text-xs text-gray-500'>
                      Last: {formatDateTime(customer.last_review_date)}
                    </p>
                  </div>

                  {/* Average Rating */}
                  <div className='col-span-2'>
                    <div className='flex items-center space-x-1'>
                      <Star className='h-4 w-4 text-yellow-500' />
                      <span className='font-medium text-gray-900'>
                        {customer.average_rating != null
                          ? customer.average_rating.toFixed(1)
                          : 'N/A'}
                      </span>
                    </div>
                    <p className='text-xs text-gray-500'>
                      LTV: $
                      {customer.lifetime_value != null
                        ? customer.lifetime_value.toLocaleString()
                        : '0'}
                    </p>
                  </div>

                  {/* Risk Level */}
                  <div className='col-span-2'>
                    <RiskIndicator
                      level={customer.risk_level || 'low'}
                      score={customer.risk_score != null ? customer.risk_score : 0}
                      showScore
                    />
                    <div className='mt-1'>
                      <ChurnProbability
                        probability={
                          customer.churn_probability != null ? customer.churn_probability : 0
                        }
                      />
                    </div>
                  </div>

                  {/* Status */}
                  <div className='col-span-2'>
                    <CustomerStatusBadge status={customer.status} />
                  </div>

                  {/* Actions */}
                  <div className='col-span-1'>
                    <Button
                      variant='ghost'
                      size='sm'
                      onClick={() => handleViewCustomer(customer.id)}
                    >
                      <ExternalLink className='h-4 w-4' />
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}

        {/* Empty State */}
        {!isLoading && (!customers || customers.length === 0) && (
          <div className='text-center py-12'>
            <Users className='mx-auto h-12 w-12 text-gray-400' />
            <h3 className='mt-2 text-sm font-medium text-gray-900'>No customers found</h3>
            <p className='mt-1 text-sm text-gray-500'>
              {filters.search || filters.risk_level || filters.status
                ? 'Try adjusting your filters'
                : 'Customers will appear here once they are added to the system'}
            </p>
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className='mt-8 flex items-center justify-between'>
          <p className='text-sm text-gray-700'>
            Showing {(currentPage - 1) * 20 + 1} to {Math.min(currentPage * 20, totalCustomers)} of{' '}
            {totalCustomers} customers
          </p>
          <div className='flex items-center space-x-2'>
            <Button
              variant='outline'
              size='sm'
              onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
              disabled={currentPage === 1}
            >
              Previous
            </Button>
            <span className='text-sm text-gray-600'>
              Page {currentPage} of {totalPages}
            </span>
            <Button
              variant='outline'
              size='sm'
              onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
              disabled={currentPage === totalPages}
            >
              Next
            </Button>
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
