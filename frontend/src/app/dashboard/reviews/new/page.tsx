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

const PLATFORMS = ['google', 'yelp', 'facebook', 'tripadvisor', 'trustpilot', 'other'];

export default function NewReviewPage() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const [formData, setFormData] = useState({
    platform: 'google',
    external_id: '',
    customer_name: '',
    customer_email: '',
    rating: 5,
    content: '',
    review_date: new Date().toISOString().split('T')[0],
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
      if (!formData.customer_name || !formData.content) {
        throw new Error('Customer name and review content are required');
      }

      if (formData.rating < 1 || formData.rating > 5) {
        throw new Error('Rating must be between 1 and 5');
      }

      // Prepare the payload
      const payload = {
        platform: formData.platform,
        external_id: formData.external_id || `manual_${Date.now()}`,
        customer_name: formData.customer_name,
        customer_email: formData.customer_email || undefined,
        rating: formData.rating,
        content: formData.content,
        review_date: formData.review_date,
      };

      // Submit to backend
      await api.post('/reviews/ingest', payload);

      setSuccess(true);

      // Redirect after short delay
      setTimeout(() => {
        router.push('/dashboard/reviews');
      }, 1500);
    } catch (err: any) {
      console.error('Error creating review:', err);
      setError(
        err.response?.data?.detail || err.message || 'Failed to create review. Please try again.',
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
                <h3 className='mt-4 text-lg font-medium text-gray-900'>
                  Review Created Successfully!
                </h3>
                <p className='mt-2 text-sm text-gray-600'>
                  The review has been ingested and will be processed by the AI system.
                </p>
                <p className='mt-1 text-sm text-gray-500'>Redirecting to reviews list...</p>
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
            Back to Reviews
          </Button>
          <h1 className='text-2xl font-bold text-gray-900'>Add New Review</h1>
          <p className='mt-1 text-sm text-gray-500'>
            Manually ingest a customer review into the system
          </p>
        </div>

        {/* Form */}
        <Card>
          <CardHeader>
            <CardTitle>Review Details</CardTitle>
            <CardDescription>
              Enter the review information. The AI will automatically analyze sentiment and urgency.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className='space-y-6'>
              {error && (
                <div className='bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm'>
                  {error}
                </div>
              )}

              {/* Platform */}
              <div>
                <Label htmlFor='platform'>Platform *</Label>
                <select
                  id='platform'
                  value={formData.platform}
                  onChange={e => handleChange('platform', e.target.value)}
                  className='mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500'
                  required
                >
                  {PLATFORMS.map(platform => (
                    <option key={platform} value={platform}>
                      {platform.charAt(0).toUpperCase() + platform.slice(1)}
                    </option>
                  ))}
                </select>
                <p className='mt-1 text-xs text-gray-500'>
                  Select the platform where this review was posted
                </p>
              </div>

              {/* External ID */}
              <div>
                <Label htmlFor='external_id'>External ID (Optional)</Label>
                <Input
                  id='external_id'
                  type='text'
                  value={formData.external_id}
                  onChange={e => handleChange('external_id', e.target.value)}
                  placeholder='e.g., google_review_123456'
                />
                <p className='mt-1 text-xs text-gray-500'>
                  The review ID from the platform (leave blank to auto-generate)
                </p>
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
                <Label htmlFor='customer_email'>Customer Email (Optional)</Label>
                <Input
                  id='customer_email'
                  type='email'
                  value={formData.customer_email}
                  onChange={e => handleChange('customer_email', e.target.value)}
                  placeholder='john.smith@email.com'
                />
                <p className='mt-1 text-xs text-gray-500'>
                  Email for customer recovery communications
                </p>
              </div>

              {/* Rating */}
              <div>
                <Label htmlFor='rating'>Rating *</Label>
                <div className='flex items-center space-x-4 mt-2'>
                  <Input
                    id='rating'
                    type='number'
                    min='1'
                    max='5'
                    value={formData.rating}
                    onChange={e => handleChange('rating', parseInt(e.target.value))}
                    className='w-20'
                    required
                  />
                  <div className='flex items-center space-x-1'>
                    {[1, 2, 3, 4, 5].map(star => (
                      <button
                        key={star}
                        type='button'
                        onClick={() => handleChange('rating', star)}
                        className='focus:outline-none'
                      >
                        <span
                          className={`text-2xl ${star <= formData.rating ? 'text-yellow-400' : 'text-gray-300'}`}
                        >
                          ★
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
                <p className='mt-1 text-xs text-gray-500'>
                  1-5 stars (click stars or enter number)
                </p>
              </div>

              {/* Review Date */}
              <div>
                <Label htmlFor='review_date'>Review Date *</Label>
                <Input
                  id='review_date'
                  type='date'
                  value={formData.review_date}
                  onChange={e => handleChange('review_date', e.target.value)}
                  max={new Date().toISOString().split('T')[0]}
                  required
                />
              </div>

              {/* Review Content */}
              <div>
                <Label htmlFor='content'>Review Content *</Label>
                <Textarea
                  id='content'
                  value={formData.content}
                  onChange={e => handleChange('content', e.target.value)}
                  placeholder='Enter the full review text here...'
                  rows={6}
                  className='mt-1'
                  required
                />
                <p className='mt-1 text-xs text-gray-500'>
                  The AI will analyze this text for sentiment, urgency, and issue categories
                </p>
              </div>

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
                      Create Review
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
              <li>The review will be analyzed by AI for sentiment and urgency</li>
              <li>Issue categories will be automatically detected</li>
              <li>Customer risk scoring will be updated</li>
              <li>Suggested responses will be generated if needed</li>
              <li>Recovery actions will be triggered for low-rated reviews</li>
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
