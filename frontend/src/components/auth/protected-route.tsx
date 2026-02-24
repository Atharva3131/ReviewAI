'use client';

import { useAuth } from './auth-provider';

interface ProtectedRouteProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export function ProtectedRoute({ children, fallback }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className='min-h-screen flex items-center justify-center'>
        <div className='animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600'></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      fallback || (
        <div className='min-h-screen flex items-center justify-center'>
          <div className='text-center'>
            <h1 className='text-2xl font-bold text-gray-900'>Access Denied</h1>
            <p className='mt-2 text-gray-600'>Please log in to access this page.</p>
          </div>
        </div>
      )
    );
  }

  return <>{children}</>;
}
