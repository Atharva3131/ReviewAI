'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Users,
  Plus,
  Search,
  Filter,
  MoreHorizontal,
  Edit,
  Trash2,
  Shield,
  Mail,
  Calendar,
  CheckCircle,
  XCircle,
  Clock,
  UserPlus,
} from 'lucide-react';
import { cn, formatDateTime } from '@/lib/utils';
import type { User, UserPermissions } from '@/types/settings';
import api from '@/lib/api';

const ROLES = [
  { value: 'admin', label: 'Admin', description: 'Full access to all features' },
  { value: 'manager', label: 'Manager', description: 'Manage users and view analytics' },
  { value: 'agent', label: 'Agent', description: 'Respond to reviews and manage customers' },
  { value: 'viewer', label: 'Viewer', description: 'View-only access to data' },
];

const STATUSES = ['active', 'inactive', 'pending'];

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.get('/users');
      setUsers(response.data.users || []);
    } catch (err: any) {
      console.error('Error fetching users:', err);
      setError('Failed to load users');

      // Mock data for development
      const mockUsers: User[] = [
        {
          id: '1',
          email: 'admin@acmerestaurants.com',
          first_name: 'John',
          last_name: 'Admin',
          role: 'admin',
          status: 'active',
          avatar_url: '/avatars/admin.jpg',
          last_login: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
          created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 365).toISOString(),
          updated_at: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
          permissions: {
            can_manage_users: true,
            can_manage_settings: true,
            can_view_analytics: true,
            can_respond_to_reviews: true,
            can_manage_customers: true,
            can_access_api: true,
            can_export_data: true,
          },
        },
        {
          id: '2',
          email: 'sarah.manager@acmerestaurants.com',
          first_name: 'Sarah',
          last_name: 'Johnson',
          role: 'manager',
          status: 'active',
          avatar_url: '/avatars/sarah.jpg',
          last_login: new Date(Date.now() - 1000 * 60 * 60 * 6).toISOString(),
          created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 180).toISOString(),
          updated_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2).toISOString(),
          permissions: {
            can_manage_users: true,
            can_manage_settings: false,
            can_view_analytics: true,
            can_respond_to_reviews: true,
            can_manage_customers: true,
            can_access_api: false,
            can_export_data: true,
          },
        },
        {
          id: '3',
          email: 'mike.agent@acmerestaurants.com',
          first_name: 'Mike',
          last_name: 'Davis',
          role: 'agent',
          status: 'active',
          last_login: new Date(Date.now() - 1000 * 60 * 60 * 12).toISOString(),
          created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 90).toISOString(),
          updated_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3).toISOString(),
          permissions: {
            can_manage_users: false,
            can_manage_settings: false,
            can_view_analytics: false,
            can_respond_to_reviews: true,
            can_manage_customers: true,
            can_access_api: false,
            can_export_data: false,
          },
        },
        {
          id: '4',
          email: 'emily.viewer@acmerestaurants.com',
          first_name: 'Emily',
          last_name: 'Chen',
          role: 'viewer',
          status: 'pending',
          created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 7).toISOString(),
          updated_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 7).toISOString(),
          permissions: {
            can_manage_users: false,
            can_manage_settings: false,
            can_view_analytics: true,
            can_respond_to_reviews: false,
            can_manage_customers: false,
            can_access_api: false,
            can_export_data: false,
          },
        },
      ];
      setUsers(mockUsers);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredUsers = users.filter(user => {
    const matchesSearch =
      !searchTerm ||
      user.first_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.last_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.email.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesRole = !roleFilter || user.role === roleFilter;
    const matchesStatus = !statusFilter || user.status === statusFilter;

    return matchesSearch && matchesRole && matchesStatus;
  });

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'admin':
        return 'bg-red-100 text-red-800';
      case 'manager':
        return 'bg-blue-100 text-blue-800';
      case 'agent':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return CheckCircle;
      case 'inactive':
        return XCircle;
      default:
        return Clock;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'text-green-600';
      case 'inactive':
        return 'text-red-600';
      default:
        return 'text-yellow-600';
    }
  };

  const handleInviteUser = () => {
    setShowInviteModal(true);
  };

  const handleEditUser = (user: User) => {
    setSelectedUser(user);
  };

  const handleDeleteUser = async (userId: string) => {
    if (!confirm('Are you sure you want to delete this user?')) {
      return;
    }

    try {
      await api.delete(`/users/${userId}`);
      setUsers(prev => prev.filter(u => u.id !== userId));
    } catch (error) {
      console.error('Error deleting user:', error);
    }
  };

  const handleUpdateUserStatus = async (userId: string, status: User['status']) => {
    try {
      await api.patch(`/users/${userId}`, { status });
      setUsers(prev => prev.map(u => (u.id === userId ? { ...u, status } : u)));
    } catch (error) {
      console.error('Error updating user status:', error);
    }
  };

  if (isLoading) {
    return (
      <div className='px-4 sm:px-6 lg:px-8'>
        <div className='animate-pulse space-y-4'>
          <div className='h-8 bg-gray-200 rounded w-1/4'></div>
          <div className='h-12 bg-gray-200 rounded'></div>
          {[...Array(5)].map((_, i) => (
            <div key={i} className='h-20 bg-gray-200 rounded'></div>
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
            <h1 className='text-2xl font-bold text-gray-900'>User Management</h1>
            <p className='mt-1 text-sm text-gray-500'>Manage team members and their permissions</p>
          </div>
          <Button onClick={handleInviteUser}>
            <UserPlus className='h-4 w-4 mr-1' />
            Invite User
          </Button>
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
                  placeholder='Search users...'
                  value={searchTerm}
                  onChange={e => setSearchTerm(e.target.value)}
                  className='pl-10'
                />
              </div>
            </div>

            <div className='flex items-center space-x-2'>
              <Filter className='h-4 w-4 text-gray-400' />
              <select
                value={roleFilter}
                onChange={e => setRoleFilter(e.target.value)}
                className='text-sm border border-gray-300 rounded px-2 py-1'
              >
                <option value=''>All Roles</option>
                {ROLES.map(role => (
                  <option key={role.value} value={role.value}>
                    {role.label}
                  </option>
                ))}
              </select>

              <select
                value={statusFilter}
                onChange={e => setStatusFilter(e.target.value)}
                className='text-sm border border-gray-300 rounded px-2 py-1'
              >
                <option value=''>All Statuses</option>
                {STATUSES.map(status => (
                  <option key={status} value={status}>
                    {status.charAt(0).toUpperCase() + status.slice(1)}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Users List */}
      <div className='space-y-4'>
        {filteredUsers.length === 0 ? (
          <Card>
            <CardContent className='text-center py-12'>
              <Users className='h-12 w-12 text-gray-400 mx-auto mb-4' />
              <h3 className='text-lg font-medium text-gray-900 mb-2'>No Users Found</h3>
              <p className='text-gray-600 mb-4'>
                {searchTerm || roleFilter || statusFilter
                  ? 'No users match your current filters.'
                  : 'No users have been added to your organization yet.'}
              </p>
              {!searchTerm && !roleFilter && !statusFilter && (
                <Button onClick={handleInviteUser}>
                  <UserPlus className='h-4 w-4 mr-1' />
                  Invite First User
                </Button>
              )}
            </CardContent>
          </Card>
        ) : (
          filteredUsers.map(user => {
            const StatusIcon = getStatusIcon(user.status);

            return (
              <Card key={user.id} className='hover:shadow-md transition-shadow'>
                <CardContent className='p-6'>
                  <div className='flex items-center justify-between'>
                    <div className='flex items-center space-x-4'>
                      {/* Avatar */}
                      <div className='flex-shrink-0'>
                        {user.avatar_url ? (
                          <img
                            src={user.avatar_url}
                            alt={`${user.first_name} ${user.last_name}`}
                            className='h-12 w-12 rounded-full object-cover'
                          />
                        ) : (
                          <div className='h-12 w-12 rounded-full bg-gray-200 flex items-center justify-center'>
                            <Users className='h-6 w-6 text-gray-400' />
                          </div>
                        )}
                      </div>

                      {/* User Info */}
                      <div className='flex-1 min-w-0'>
                        <div className='flex items-center space-x-2 mb-1'>
                          <h3 className='text-lg font-medium text-gray-900'>
                            {user.first_name} {user.last_name}
                          </h3>
                          <span
                            className={cn(
                              'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium',
                              getRoleColor(user.role),
                            )}
                          >
                            {user.role}
                          </span>
                        </div>

                        <div className='flex items-center space-x-4 text-sm text-gray-600'>
                          <div className='flex items-center space-x-1'>
                            <Mail className='h-4 w-4' />
                            <span>{user.email}</span>
                          </div>

                          <div
                            className={cn(
                              'flex items-center space-x-1',
                              getStatusColor(user.status),
                            )}
                          >
                            <StatusIcon className='h-4 w-4' />
                            <span className='capitalize'>{user.status}</span>
                          </div>

                          {user.last_login && (
                            <div className='flex items-center space-x-1'>
                              <Calendar className='h-4 w-4' />
                              <span>Last login: {formatDateTime(user.last_login)}</span>
                            </div>
                          )}
                        </div>

                        {/* Permissions Summary */}
                        <div className='mt-2 flex flex-wrap gap-1'>
                          {Object.entries(user.permissions)
                            .filter(([_, enabled]) => enabled)
                            .map(([permission]) => (
                              <span
                                key={permission}
                                className='inline-flex items-center px-2 py-1 rounded text-xs bg-blue-50 text-blue-700'
                              >
                                {permission.replace('can_', '').replace('_', ' ')}
                              </span>
                            ))}
                        </div>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className='flex items-center space-x-2'>
                      {user.status === 'pending' && (
                        <Button
                          size='sm'
                          variant='outline'
                          onClick={() => handleUpdateUserStatus(user.id, 'active')}
                        >
                          Activate
                        </Button>
                      )}

                      {user.status === 'active' && (
                        <Button
                          size='sm'
                          variant='outline'
                          onClick={() => handleUpdateUserStatus(user.id, 'inactive')}
                        >
                          Deactivate
                        </Button>
                      )}

                      <Button size='sm' variant='outline' onClick={() => handleEditUser(user)}>
                        <Edit className='h-4 w-4 mr-1' />
                        Edit
                      </Button>

                      <Button
                        size='sm'
                        variant='outline'
                        onClick={() => handleDeleteUser(user.id)}
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

      {/* Invite User Modal */}
      {showInviteModal && (
        <div className='fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50'>
          <div className='bg-white rounded-lg p-6 w-full max-w-md mx-4'>
            <div className='flex items-center justify-between mb-4'>
              <h3 className='text-lg font-medium text-gray-900'>Invite User</h3>
              <Button variant='ghost' size='sm' onClick={() => setShowInviteModal(false)}>
                ×
              </Button>
            </div>

            <div className='space-y-4'>
              <div>
                <Label htmlFor='invite-email'>Email Address</Label>
                <Input id='invite-email' type='email' placeholder='user@example.com' />
              </div>

              <div>
                <Label htmlFor='invite-role'>Role</Label>
                <select
                  id='invite-role'
                  className='w-full mt-1 p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                >
                  {ROLES.map(role => (
                    <option key={role.value} value={role.value}>
                      {role.label} - {role.description}
                    </option>
                  ))}
                </select>
              </div>

              <div className='flex items-center justify-end space-x-2 pt-4'>
                <Button variant='outline' onClick={() => setShowInviteModal(false)}>
                  Cancel
                </Button>
                <Button onClick={() => setShowInviteModal(false)}>Send Invitation</Button>
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
