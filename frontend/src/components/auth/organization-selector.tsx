'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import api from '@/lib/api';

interface Organization {
  id: string;
  name: string;
  domain?: string;
}

interface OrganizationSelectorProps {
  user: {
    id: string;
    email: string;
    organizations?: Organization[];
  };
  onSelect: (organizationId: string) => void;
}

export function OrganizationSelector({ user, onSelect }: OrganizationSelectorProps) {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const fetchOrganizations = async () => {
      try {
        const response = await api.get('/users/organizations');
        setOrganizations(response.data);
      } catch (err: any) {
        setError('Failed to load organizations');
        console.error('Error fetching organizations:', err);
      } finally {
        setIsLoading(false);
      }
    };

    // If user already has organizations data, use it
    if (user.organizations && user.organizations.length > 0) {
      setOrganizations(user.organizations);
      setIsLoading(false);
    } else {
      fetchOrganizations();
    }
  }, [user]);

  const handleSelectOrganization = async (organizationId: string) => {
    try {
      // Update user's active organization
      await api.post('/users/select-organization', { organization_id: organizationId });
      onSelect(organizationId);
      router.push('/dashboard');
    } catch (err: any) {
      setError('Failed to select organization');
      console.error('Error selecting organization:', err);
    }
  };

  if (isLoading) {
    return (
      <div className='min-h-screen flex items-center justify-center bg-gray-50'>
        <div className='animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600'></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className='min-h-screen flex items-center justify-center bg-gray-50'>
        <Card className='w-full max-w-md'>
          <CardHeader>
            <CardTitle className='text-red-600'>Error</CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => window.location.reload()} className='w-full'>
              Try Again
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (organizations.length === 0) {
    return (
      <div className='min-h-screen flex items-center justify-center bg-gray-50'>
        <Card className='w-full max-w-md'>
          <CardHeader>
            <CardTitle>No Organizations Found</CardTitle>
            <CardDescription>
              You don't have access to any organizations. Please contact your administrator.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => router.push('/login')} className='w-full'>
              Back to Login
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (organizations.length === 1) {
    // Auto-select if only one organization
    handleSelectOrganization(organizations[0].id);
    return (
      <div className='min-h-screen flex items-center justify-center bg-gray-50'>
        <div className='animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600'></div>
      </div>
    );
  }

  return (
    <div className='min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8'>
      <div className='max-w-md w-full space-y-8'>
        <div className='text-center'>
          <h1 className='text-3xl font-bold text-gray-900'>ReviewAI <span className='text-lg font-normal text-gray-500'>Beta</span></h1>
          <p className='mt-2 text-sm text-gray-600'>Welcome back, {user.email}</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Select Organization</CardTitle>
            <CardDescription>Choose which organization you'd like to access</CardDescription>
          </CardHeader>
          <CardContent>
            <div className='space-y-3'>
              {organizations.map(org => (
                <Button
                  key={org.id}
                  variant='outline'
                  className='w-full justify-start h-auto p-4'
                  onClick={() => handleSelectOrganization(org.id)}
                >
                  <div className='text-left'>
                    <div className='font-medium'>{org.name}</div>
                    {org.domain && <div className='text-sm text-gray-500'>{org.domain}</div>}
                  </div>
                </Button>
              ))}
            </div>

            <div className='mt-6 text-center'>
              <Button variant='ghost' onClick={() => router.push('/login')} className='text-sm'>
                Sign in as different user
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
