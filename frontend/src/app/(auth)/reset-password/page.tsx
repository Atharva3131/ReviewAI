'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { AuthService } from '@/lib/auth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

const resetSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
});

type ResetFormData = z.infer<typeof resetSchema>;

export default function ResetPasswordPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetFormData>({
    resolver: zodResolver(resetSchema),
  });

  const onSubmit = async (data: ResetFormData) => {
    setIsLoading(true);
    setError(null);

    try {
      await AuthService.resetPassword(data.email);
      setSuccess(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to send reset email. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  if (success) {
    return (
      <div className='min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8'>
        <div className='max-w-md w-full space-y-8'>
          <div className='text-center'>
            <h1 className='text-3xl font-bold text-gray-900'>ReviewAI <span className='text-lg font-normal text-gray-500'>Beta</span></h1>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Check your email</CardTitle>
              <CardDescription>
                We've sent a password reset link to your email address
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className='text-center space-y-4'>
                <div className='bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-md text-sm'>
                  Password reset email sent successfully!
                </div>
                <p className='text-sm text-gray-600'>
                  Didn't receive the email? Check your spam folder or{' '}
                  <button
                    onClick={() => setSuccess(false)}
                    className='text-blue-600 hover:text-blue-500 underline'
                  >
                    try again
                  </button>
                </p>
                <Link
                  href='/login'
                  className='inline-block text-sm text-blue-600 hover:text-blue-500'
                >
                  Back to sign in
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>
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
            <CardTitle>Reset your password</CardTitle>
            <CardDescription>
              Enter your email address and we'll send you a link to reset your password
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

              <Button type='submit' className='w-full' disabled={isLoading}>
                {isLoading ? 'Sending...' : 'Send reset link'}
              </Button>
            </form>

            <div className='mt-6 text-center'>
              <Link href='/login' className='text-sm text-blue-600 hover:text-blue-500'>
                Back to sign in
              </Link>
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
