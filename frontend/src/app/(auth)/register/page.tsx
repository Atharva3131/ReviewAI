'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { AuthService, type RegisterData } from '@/lib/auth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

const registerSchema = z
  .object({
    email: z.string().email('Please enter a valid email address'),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string(),
    organization_name: z.string().min(2, 'Organization name must be at least 2 characters'),
  })
  .refine(data => data.password === data.confirmPassword, {
    message: "Passwords don't match",
    path: ['confirmPassword'],
  });

type RegisterFormData = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterFormData) => {
    setIsLoading(true);
    setError(null);

    try {
      const registerData: RegisterData = {
        email: data.email,
        password: data.password,
        organization_name: data.organization_name,
      };

      await AuthService.register(registerData);
      router.push('/onboarding');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className='min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8'>
      <div className='max-w-md w-full space-y-8'>
        <div className='text-center'>
          <h1 className='text-3xl font-bold text-gray-900'>ReviewAI <span className='text-lg font-normal text-gray-500'>Beta</span></h1>
          <p className='mt-2 text-sm text-gray-600'>Intelligent reputation management platform</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Create your account</CardTitle>
            <CardDescription>
              Get started with ReviewAI to manage your online reputation
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
                <Label htmlFor='organization_name'>Organization Name</Label>
                <Input
                  id='organization_name'
                  type='text'
                  {...register('organization_name')}
                  className={errors.organization_name ? 'border-red-500' : ''}
                />
                {errors.organization_name && (
                  <p className='text-sm text-red-600'>{errors.organization_name.message}</p>
                )}
              </div>

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
                  autoComplete='new-password'
                  {...register('password')}
                  className={errors.password ? 'border-red-500' : ''}
                />
                {errors.password && (
                  <p className='text-sm text-red-600'>{errors.password.message}</p>
                )}
              </div>

              <div className='space-y-2'>
                <Label htmlFor='confirmPassword'>Confirm Password</Label>
                <Input
                  id='confirmPassword'
                  type='password'
                  autoComplete='new-password'
                  {...register('confirmPassword')}
                  className={errors.confirmPassword ? 'border-red-500' : ''}
                />
                {errors.confirmPassword && (
                  <p className='text-sm text-red-600'>{errors.confirmPassword.message}</p>
                )}
              </div>

              <Button type='submit' className='w-full' disabled={isLoading}>
                {isLoading ? 'Creating account...' : 'Create account'}
              </Button>
            </form>

            <div className='mt-6 text-center'>
              <p className='text-sm text-gray-600'>
                Already have an account?{' '}
                <Link href='/login' className='font-medium text-blue-600 hover:text-blue-500'>
                  Sign in
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
