'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { ArrowLeft, Save, Loader2 } from 'lucide-react';
import api from '@/lib/api';

const PRIORITIES = ['low', 'medium', 'high', 'urgent'];
const CATEGORIES = ['technical', 'billing', 'account', 'feature_request', 'bug_report', 'general'];

export default function NewTicketPage() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const [formData, setFormData] = useState({
    title: '',
    description: '',
    customer_name: '',
    customer_email: '',
    priority: 'medium',
    category: 'general',
    source: 'web_form',
  });

  const handleChange = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      // Validate required fields
      if (!formData.title || !formData.description) {
        throw new Error('Title and description are required');
      }

      if (!formData.customer_name || !formData.customer_email) {
        throw new Error('Customer name and email are required');
      }

      // Prepare the payload
      const payload = {
        title: formData.title,
        description: formData.description,
        customer_name: formData.customer_name,
        customer_email: formData.customer_email,
        priority: formData.priority,
        category: formData.category,
        source: formData.source,
      };

      // Submit to backend
      await api.post('/support-tickets', payload);

      setSuccess(true);

      // Redirect after short delay
      setTimeout(() => {
        router.push('/dashboard/support');
      }, 1500);
    } catch (err: any) {
      console.error('Error creating ticket:', err);
      setError(
        err.response?.data?.detail ||
          err.message ||
          'Failed to create support ticket. Please try again.',
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  if (success) {
    return (
      <div className='px-4 sm:px-6 lg:px-8'>
        <div className='max-w-3xl mx-auto'>
          <Card className='border-green-200 bg-green-50'>
            <CardContent className='pt-6'>
              <div className='text-center'>
                <div className='mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100'>
                  <svg
                    className='h-6 w-6 text-green-600'
                    fill='none'
                    stroke='currentColor'
                    viewBox='0 0 24 24'
                  >
                    <path
                      strokeLinecap='round'
                      strokeLinejoin='round'
                      strokeWidth='2'
                      d='M5 13l4 4L19 7'
                    />
                  </svg>
                </div>
                <h3 className='mt-4 text-lg font-medium text-gray-900'>Support Ticket Created!</h3>
                <p className='mt-2 text-sm text-gray-600'>
                  The ticket has been created and will be processed by the AI system.
                </p>
                <p className='mt-1 text-sm text-gray-500'>Redirecting to support tickets...</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className='px-4 sm:px-6 lg:px-8'>
      <div className='max-w-3xl mx-auto'>
        {/* Header */}
        <div className='mb-8'>
          <Button variant='ghost' onClick={() => router.back()} className='mb-4'>
            <ArrowLeft className='h-4 w-4 mr-2' />
            Back to Support
          </Button>
          <h1 className='text-2xl font-bold text-gray-900'>Create Support Ticket</h1>
          <p className='mt-1 text-sm text-gray-500'>
            Create a new support ticket for customer assistance
          </p>
        </div>

        {/* Form */}
        <Card>
          <CardHeader>
            <CardTitle>Ticket Details</CardTitle>
            <CardDescription>
              Enter the support ticket information. The AI will analyze and suggest responses.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className='space-y-6'>
              {error && (
                <div className='bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm'>
                  {error}
                </div>
              )}

              {/* Title */}
              <div>
                <Label htmlFor='title'>Ticket Title *</Label>
                <Input
                  id='title'
                  type='text'
                  value={formData.title}
                  onChange={e => handleChange('title', e.target.value)}
                  placeholder='Brief description of the issue'
                  required
                />
              </div>

              {/* Customer Name */}
              <div>
                <Label htmlFor='customer_name'>Customer Name *</Label>
                <Input
                  id='customer_name'
                  type='text'
                  value={formData.customer_name}
                  onChange={e => handleChange('customer_name', e.target.value)}
                  placeholder='John Smith'
                  required
                />
              </div>

              {/* Customer Email */}
              <div>
                <Label htmlFor='customer_email'>Customer Email *</Label>
                <Input
                  id='customer_email'
                  type='email'
                  value={formData.customer_email}
                  onChange={e => handleChange('customer_email', e.target.value)}
                  placeholder='john.smith@email.com'
                  required
                />
              </div>

              {/* Priority and Category Row */}
              <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
                {/* Priority */}
                <div>
                  <Label htmlFor='priority'>Priority *</Label>
                  <select
                    id='priority'
                    value={formData.priority}
                    onChange={e => handleChange('priority', e.target.value)}
                    className='mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500'
                    required
                  >
                    {PRIORITIES.map(priority => (
                      <option key={priority} value={priority}>
                        {priority.charAt(0).toUpperCase() + priority.slice(1)}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Category */}
                <div>
                  <Label htmlFor='category'>Category *</Label>
                  <select
                    id='category'
                    value={formData.category}
                    onChange={e => handleChange('category', e.target.value)}
                    className='mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500'
                    required
                  >
                    {CATEGORIES.map(category => (
                      <option key={category} value={category}>
                        {category
                          .split('_')
                          .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                          .join(' ')}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Description */}
              <div>
                <Label htmlFor='description'>Description *</Label>
                <Textarea
                  id='description'
                  value={formData.description}
                  onChange={e => handleChange('description', e.target.value)}
                  placeholder='Detailed description of the issue or request...'
                  rows={8}
                  className='mt-1'
                  required
                />
                <p className='mt-1 text-xs text-gray-500'>
                  Provide as much detail as possible to help resolve the issue quickly
                </p>
              </div>

              {/* Source (hidden, set to web_form) */}
              <input type='hidden' value={formData.source} />

              {/* Actions */}
              <div className='flex items-center justify-end space-x-3 pt-4 border-t'>
                <Button
                  type='button'
                  variant='outline'
                  onClick={() => router.back()}
                  disabled={isSubmitting}
                >
                  Cancel
                </Button>
                <Button type='submit' disabled={isSubmitting}>
                  {isSubmitting ? (
                    <>
                      <Loader2 className='h-4 w-4 mr-2 animate-spin' />
                      Creating...
                    </>
                  ) : (
                    <>
                      <Save className='h-4 w-4 mr-2' />
                      Create Ticket
                    </>
                  )}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Info Box */}
        <Card className='mt-6 border-blue-200 bg-blue-50'>
          <CardContent className='pt-6'>
            <h3 className='text-sm font-medium text-blue-900 mb-2'>What happens next?</h3>
            <ul className='text-sm text-blue-800 space-y-1 list-disc list-inside'>
              <li>The ticket will be analyzed by AI for urgency and sentiment</li>
              <li>Suggested responses will be generated automatically</li>
              <li>The ticket will be assigned based on category and priority</li>
              <li>Customer will receive confirmation email</li>
              <li>You'll be notified of any escalations or updates</li>
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
