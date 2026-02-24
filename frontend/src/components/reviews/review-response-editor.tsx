'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Send, Save, Sparkles, RefreshCw, Eye, AlertCircle, CheckCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Review } from '@/types/review';
import api from '@/lib/api';

const responseSchema = z.object({
  content: z
    .string()
    .min(10, 'Response must be at least 10 characters')
    .max(500, 'Response must be less than 500 characters'),
});

type ResponseFormData = z.infer<typeof responseSchema>;

interface ReviewResponseEditorProps {
  review: Review;
  onSave?: (content: string) => void;
  onPublish?: (content: string) => void;
  onCancel?: () => void;
  initialContent?: string;
  isLoading?: boolean;
}

export function ReviewResponseEditor({
  review,
  onSave,
  onPublish,
  onCancel,
  initialContent = '',
  isLoading = false,
}: ReviewResponseEditorProps) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [previewMode, setPreviewMode] = useState(false);
  const [generatedSuggestions, setGeneratedSuggestions] = useState<string[]>([]);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isDirty },
  } = useForm<ResponseFormData>({
    resolver: zodResolver(responseSchema),
    defaultValues: {
      content: initialContent,
    },
  });

  const content = watch('content');
  const characterCount = content.length;
  const isOverLimit = characterCount > 500;

  const generateAIResponse = async () => {
    setIsGenerating(true);
    try {
      const response = await api.post('/reviews/generate-response', {
        review_id: review.id,
        review_content: review.content,
        rating: review.rating,
        sentiment_score: review.sentiment_score,
        issue_categories: review.issue_categories,
      });

      const suggestions = response.data.suggestions || [response.data.content];
      setGeneratedSuggestions(suggestions);

      if (suggestions.length > 0) {
        setValue('content', suggestions[0], { shouldDirty: true });
      }
    } catch (error) {
      console.error('Error generating AI response:', error);
      // Fallback to mock suggestions
      const mockSuggestions = generateMockSuggestions(review);
      setGeneratedSuggestions(mockSuggestions);
      setValue('content', mockSuggestions[0], { shouldDirty: true });
    } finally {
      setIsGenerating(false);
    }
  };

  const generateMockSuggestions = (review: Review): string[] => {
    const suggestions = [];

    if (review.rating >= 4) {
      suggestions.push(
        `Thank you so much for your wonderful ${review.rating}-star review! We're thrilled to hear about your positive experience. Your feedback means the world to us and motivates our team to continue delivering excellent service.`,
        `We're delighted by your ${review.rating}-star review! It's fantastic to know we met your expectations. Thank you for taking the time to share your experience with others.`,
      );
    } else if (review.rating === 3) {
      suggestions.push(
        `Thank you for your 3-star review and feedback. We appreciate you taking the time to share your experience. We'd love to learn more about how we can improve - please feel free to reach out to us directly.`,
        `We appreciate your honest feedback in this 3-star review. Your input helps us identify areas for improvement. We'd welcome the opportunity to discuss your experience further.`,
      );
    } else {
      suggestions.push(
        `Thank you for bringing this to our attention. We sincerely apologize that your experience didn't meet expectations. We take all feedback seriously and would appreciate the opportunity to make this right. Please contact us directly so we can address your concerns.`,
        `We're sorry to hear about your experience and appreciate you taking the time to share your feedback. This is not the standard we strive for, and we'd like to work with you to resolve any issues. Please reach out to us directly.`,
      );
    }

    return suggestions;
  };

  const handleSave = (data: ResponseFormData) => {
    onSave?.(data.content);
  };

  const handlePublish = (data: ResponseFormData) => {
    onPublish?.(data.content);
  };

  const useSuggestion = (suggestion: string) => {
    setValue('content', suggestion, { shouldDirty: true });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className='flex items-center justify-between'>
          <span>Response Editor</span>
          <div className='flex items-center space-x-2'>
            <Button variant='outline' size='sm' onClick={() => setPreviewMode(!previewMode)}>
              <Eye className='h-4 w-4 mr-1' />
              {previewMode ? 'Edit' : 'Preview'}
            </Button>
          </div>
        </CardTitle>
        <CardDescription>
          Craft a professional response to this {review.rating}-star review
        </CardDescription>
      </CardHeader>

      <CardContent className='space-y-4'>
        {/* Original Review Context */}
        <div className='bg-gray-50 p-4 rounded-lg'>
          <div className='flex items-center justify-between mb-2'>
            <span className='font-medium text-gray-900'>{review.customer_name}</span>
            <div className='flex items-center space-x-2'>
              <span className='text-yellow-500'>
                {'★'.repeat(review.rating)}
                {'☆'.repeat(5 - review.rating)}
              </span>
              <span className='text-sm text-gray-500'>{review.platform}</span>
            </div>
          </div>
          <p className='text-gray-700 text-sm'>{review.content}</p>
        </div>

        {/* AI Suggestions */}
        {generatedSuggestions.length > 0 && (
          <div className='space-y-2'>
            <Label className='text-sm font-medium'>AI Suggestions</Label>
            <div className='space-y-2'>
              {generatedSuggestions.map((suggestion, index) => (
                <div
                  key={index}
                  className='p-3 bg-blue-50 border border-blue-200 rounded-lg cursor-pointer hover:bg-blue-100 transition-colors'
                  onClick={() => useSuggestion(suggestion)}
                >
                  <p className='text-sm text-gray-700'>{suggestion}</p>
                  <Button
                    variant='ghost'
                    size='sm'
                    className='mt-2 h-6 text-xs'
                    onClick={e => {
                      e.stopPropagation();
                      useSuggestion(suggestion);
                    }}
                  >
                    Use this suggestion
                  </Button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Response Editor */}
        <div className='space-y-2'>
          <div className='flex items-center justify-between'>
            <Label htmlFor='content'>Your Response</Label>
            <Button
              variant='outline'
              size='sm'
              onClick={generateAIResponse}
              disabled={isGenerating}
            >
              {isGenerating ? (
                <RefreshCw className='h-4 w-4 mr-1 animate-spin' />
              ) : (
                <Sparkles className='h-4 w-4 mr-1' />
              )}
              {isGenerating ? 'Generating...' : 'Generate AI Response'}
            </Button>
          </div>

          {previewMode ? (
            <div className='min-h-[120px] p-3 border rounded-md bg-gray-50'>
              <p className='text-sm text-gray-700 whitespace-pre-wrap'>
                {content || 'No content to preview'}
              </p>
            </div>
          ) : (
            <textarea
              id='content'
              {...register('content')}
              className={cn(
                'w-full min-h-[120px] p-3 border rounded-md resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                errors.content ? 'border-red-500' : 'border-gray-300',
                isOverLimit ? 'border-red-500' : '',
              )}
              placeholder='Write your response here...'
              disabled={isLoading}
            />
          )}

          <div className='flex items-center justify-between text-sm'>
            <div className='flex items-center space-x-4'>
              {errors.content && (
                <span className='text-red-600 flex items-center'>
                  <AlertCircle className='h-4 w-4 mr-1' />
                  {errors.content.message}
                </span>
              )}
              {!errors.content && content && (
                <span className='text-green-600 flex items-center'>
                  <CheckCircle className='h-4 w-4 mr-1' />
                  Response looks good
                </span>
              )}
            </div>
            <span className={cn('text-sm', isOverLimit ? 'text-red-600' : 'text-gray-500')}>
              {characterCount}/500 characters
            </span>
          </div>
        </div>

        {/* Platform Integration Notice */}
        <div className='bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4'>
          <div className='flex items-start space-x-2'>
            <div className='flex-shrink-0'>
              <svg
                className='h-5 w-5 text-blue-600'
                fill='none'
                stroke='currentColor'
                viewBox='0 0 24 24'
              >
                <path
                  strokeLinecap='round'
                  strokeLinejoin='round'
                  strokeWidth='2'
                  d='M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z'
                />
              </svg>
            </div>
            <div className='flex-1'>
              <p className='text-sm text-blue-800'>
                <strong>Note:</strong> Responses are saved to your internal database. To post to{' '}
                {review.platform.charAt(0).toUpperCase() + review.platform.slice(1)}, you'll need to
                manually copy and paste this response to the platform, or enable platform
                integration in settings.
              </p>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className='flex items-center justify-between pt-4 border-t'>
          <Button variant='outline' onClick={onCancel} disabled={isLoading}>
            Cancel
          </Button>

          <div className='flex items-center space-x-2'>
            <Button
              variant='outline'
              onClick={handleSubmit(handleSave)}
              disabled={isLoading || !isDirty || !!errors.content}
            >
              <Save className='h-4 w-4 mr-1' />
              Save Draft
            </Button>

            <Button
              onClick={handleSubmit(handlePublish)}
              disabled={isLoading || !content.trim() || !!errors.content}
            >
              <Send className='h-4 w-4 mr-1' />
              Publish Response
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
