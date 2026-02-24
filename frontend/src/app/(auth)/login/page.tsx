'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { AuthService, type LoginCredentials } from '@/lib/auth';
import { AUTH_CONFIG } from '@/config/auth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

const loginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
});

export default function LoginPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const router = useRouter();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginCredentials>({
    resolver: zodResolver(loginSchema),
  });

  useEffect(() => {
    // Check if user is already authenticated
    const checkAuth = async () => {
      // DEMO MODE: Auto-login with demo credentials
      if (AUTH_CONFIG.DEMO_MODE) {
        try {
          await AuthService.login(AUTH_CONFIG.DEMO_CREDENTIALS);
          router.push('/dashboard');
          return;
        } catch (error) {
          console.error('Demo auto-login failed:', error);
          setCheckingAuth(false);
          return;
        }
      }

      // NORMAL MODE: Check existing token
      const token = AuthService.getToken();
      if (token) {
        // Verify the token is actually valid by checking with the backend
        try {
          const user = await AuthService.getCurrentUser();
          if (user) {
            // Token is valid, redirect to dashboard
            router.push('/dashboard');
            return;
          }
        } catch (error) {
          // Token is invalid, clear it
          await AuthService.logout();
        }
      }
      setCheckingAuth(false);
    };
    checkAuth();
  }, [router]);

  const onSubmit = async (data: LoginCredentials) => {
    setIsLoading(true);
    setError(null);

    try {
      await AuthService.login(data);
      router.push('/dashboard');
    } catch (err: any) {
      setError(
        err.response?.data?.detail || 'Login failed. Please check your credentials and try again.',
      );
    } finally {
      setIsLoading(false);
    }
  };

  if (checkingAuth) {
    return (
      <div className='min-h-screen flex items-center justify-center bg-gray-50'>
        <div className='text-center'>
          <div className='animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto'></div>
          <p className='mt-4 text-gray-600'>
            {AUTH_CONFIG.DEMO_MODE
              ? 'Logging in with demo account...'
              : 'Checking authentication...'}
          </p>
        </div>
      </div>
    );
  }

  // If DEMO_MODE is enabled but auto-login failed, show a message
  if (AUTH_CONFIG.DEMO_MODE) {
    return (
      <div className='min-h-screen flex items-center justify-center bg-gray-50'>
        <Card className='max-w-md'>
          <CardHeader>
            <CardTitle>Demo Mode Error</CardTitle>
            <CardDescription>Auto-login with demo account failed</CardDescription>
          </CardHeader>
          <CardContent>
            <p className='text-sm text-gray-600 mb-4'>
              Demo mode is enabled but automatic login failed. Please check your backend connection.
            </p>
            <Button onClick={() => window.location.reload()}>Try Again</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className='min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8'>
      <div className='max-w-md w-full space-y-8'>
        <div className='text-center'>
          <h1 className='text-3xl font-bold text-gray-900'>ReviewAI <span className='text-lg font-normal text-gray-500'>Beta</span></h1>
          <p className='mt-2 text-sm text-gray-600'>Intelligent reputation management platform</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Sign in to your account</CardTitle>
            <CardDescription>
              Enter your email and password to access your dashboard
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className='space-y-4'>
              {error && (
                <div className='bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm'>
                  {error}
                </div>
              )}

              <div className='space-y-2'>
                <Label htmlFor='email'>Email address</Label>
                <Input
                  id='email'
                  type='email'
                  autoComplete='email'
                  {...register('email')}
                  className={errors.email ? 'border-red-500' : ''}
                />
                {errors.email && <p className='text-sm text-red-600'>{errors.email.message}</p>}
              </div>

              <div className='space-y-2'>
                <Label htmlFor='password'>Password</Label>
                <Input
                  id='password'
                  type='password'
                  autoComplete='current-password'
                  {...register('password')}
                  className={errors.password ? 'border-red-500' : ''}
                />
                {errors.password && (
                  <p className='text-sm text-red-600'>{errors.password.message}</p>
                )}
              </div>

              <div className='flex items-center justify-between'>
                <Link href='/reset-password' className='text-sm text-blue-600 hover:text-blue-500'>
                  Forgot your password?
                </Link>
              </div>

              <Button type='submit' className='w-full' disabled={isLoading}>
                {isLoading ? 'Signing in...' : 'Sign in'}
              </Button>
            </form>

            <div className='mt-6 text-center'>
              <p className='text-sm text-gray-600'>
                Don't have an account?{' '}
                <Link href='/register' className='font-medium text-blue-600 hover:text-blue-500'>
                  Sign up
                </Link>
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Footer */}
        <div className='mt-8 text-center'>
          <p className='text-xs text-gray-500'>&copy; 2026 ReviewAI. All rights reserved.</p>
          <p className='text-xs text-gray-400 mt-1'>
            Powered by <span className='font-semibold text-gray-500'>Axionyx Labs</span>
          </p>
        </div>
      </div>
    </div>
  );
}
