'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent } from '@/components/ui/card';
import {
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  BrainCircuit,
  MessageSquare,
  Bot,
  BookOpen,
  X,
  Loader2,
} from 'lucide-react';
import api from '@/lib/api';

interface SimulateReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

interface DemoLifecycleResult {
  review_id: string;
  customer_name: string;
  rating: number;
  sentiment_score: number;
  urgency_level: string;
  decision_category: string;
  decision_urgency: number;
  churn_risk: number;
  ml_churn_probability: number;
  confidence: number;
  decision_provider: string;
  policy_decision: string;
  reasoning: string;
  generated_response?: string;
}

const PRESETS = [
  {
    label: '1★ Late Delivery & Cold Food',
    customer: 'David Miller',
    rating: 1,
    text: 'Extremely poor service! The delivery took 2 hours, food arrived freezing cold, and driver refused to refund.',
  },
  {
    label: '2★ Billing & Service Complaint',
    customer: 'Sarah Jenkins',
    rating: 2,
    text: 'I was overcharged on my bill and customer support was unresponsive for 3 days.',
  },
  {
    label: '5★ Excellent Experience',
    customer: 'Alex Rivera',
    rating: 5,
    text: 'Fantastic atmosphere, delicious food, and wonderful staff. Will definitely come back!',
  },
];

export function SimulateReviewModal({ isOpen, onClose, onSuccess }: SimulateReviewModalProps) {
  const [customerName, setCustomerName] = useState('David Miller');
  const [rating, setRating] = useState(1);
  const [reviewText, setReviewText] = useState(
    'Extremely poor service! The delivery took 2 hours, food arrived freezing cold, and driver refused to refund.',
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<DemoLifecycleResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleApplyPreset = (preset: (typeof PRESETS)[0]) => {
    setCustomerName(preset.customer);
    setRating(preset.rating);
    setReviewText(preset.text);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    setResult(null);

    try {
      const response = await api.post('/demo/ingest-demo-review', {
        customer_name: customerName,
        rating: Number(rating),
        review_text: reviewText,
      });

      // Also construct generated response for complete lifecycle visualization
      const data = response.data;
      if (data.rating <= 2) {
        data.generated_response = `Dear ${data.customer_name}, we are deeply sorry for your experience. This does not meet our standard of service. We have processed your feedback and our management team is reviewing this issue immediately.`;
      } else {
        data.generated_response = `Hi ${data.customer_name}, thank you so much for taking the time to share your feedback with us! We look forward to welcoming you back soon.`;
      }

      setResult(data);
      if (onSuccess) onSuccess();
    } catch (err: any) {
      console.error('Demo review simulation error:', err);
      setError(err.response?.data?.detail || 'Failed to process demo review');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getPolicyBadge = (policy: string) => {
    switch (policy) {
      case 'AUTO_EXECUTE':
        return (
          <span className='inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-800 border border-green-300'>
            <CheckCircle2 className='w-3.5 h-3.5 mr-1' /> AUTO-EXECUTE ALLOWED
          </span>
        );
      case 'APPROVAL_REQUIRED':
        return (
          <span className='inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-yellow-100 text-yellow-800 border border-yellow-300'>
            <AlertTriangle className='w-3.5 h-3.5 mr-1' /> APPROVAL REQUIRED
          </span>
        );
      default:
        return (
          <span className='inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-red-100 text-red-800 border border-red-300'>
            <ShieldCheck className='w-3.5 h-3.5 mr-1' /> ESCALATED TO MANAGEMENT
          </span>
        );
    }
  };

  return (
    <div className='fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto'>
      <div className='bg-white rounded-xl shadow-2xl border border-gray-100 w-full max-w-2xl overflow-hidden'>
        {/* Header */}
        <div className='bg-gradient-to-r from-blue-900 to-indigo-900 text-white p-5 flex items-center justify-between'>
          <div className='flex items-center space-x-2'>
            <Sparkles className='w-6 h-6 text-yellow-400' />
            <div>
              <h2 className='text-lg font-bold'>Simulate Google Review Event</h2>
              <p className='text-xs text-blue-200'>
                Full AI Customer Recovery & Decision Lifecycle Engine
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className='text-gray-300 hover:text-white transition-colors p-1 rounded-lg hover:bg-white/10'
          >
            <X className='w-5 h-5' />
          </button>
        </div>

        <div className='p-6 max-h-[80vh] overflow-y-auto space-y-6'>
          {/* Preset Buttons */}
          <div>
            <Label className='text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 block'>
              Quick Demo Presets
            </Label>
            <div className='flex flex-wrap gap-2'>
              {PRESETS.map((p, idx) => (
                <button
                  key={idx}
                  type='button'
                  onClick={() => handleApplyPreset(p)}
                  className='text-xs px-3 py-1.5 rounded-lg border border-gray-200 bg-gray-50 hover:bg-blue-50 hover:border-blue-300 hover:text-blue-700 transition-all font-medium'
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Input Form */}
          <form onSubmit={handleSubmit} className='space-y-4'>
            <div className='grid grid-cols-1 md:grid-cols-3 gap-4'>
              <div className='md:col-span-2'>
                <Label htmlFor='customerName'>Customer Name</Label>
                <Input
                  id='customerName'
                  value={customerName}
                  onChange={e => setCustomerName(e.target.value)}
                  placeholder='e.g. David Miller'
                  required
                />
              </div>
              <div>
                <Label htmlFor='rating'>Rating (1 to 5 Stars)</Label>
                <select
                  id='rating'
                  value={rating}
                  onChange={e => setRating(Number(e.target.value))}
                  className='w-full mt-1 border border-gray-300 rounded-md p-2 text-sm focus:ring-2 focus:ring-blue-500'
                >
                  <option value={1}>1 ★ (Critical)</option>
                  <option value={2}>2 ★ (Poor)</option>
                  <option value={3}>3 ★ (Average)</option>
                  <option value={4}>4 ★ (Good)</option>
                  <option value={5}>5 ★ (Excellent)</option>
                </select>
              </div>
            </div>

            <div>
              <Label htmlFor='reviewText'>Google Review Content</Label>
              <textarea
                id='reviewText'
                rows={3}
                value={reviewText}
                onChange={e => setReviewText(e.target.value)}
                className='w-full mt-1 border border-gray-300 rounded-md p-3 text-sm resize-none focus:ring-2 focus:ring-blue-500'
                placeholder='Enter review content...'
                required
              />
            </div>

            <Button
              type='submit'
              disabled={isSubmitting}
              className='w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 shadow-md transition-all'
            >
              {isSubmitting ? (
                <>
                  <Loader2 className='w-4 h-4 mr-2 animate-spin' /> Processing AI Pipeline...
                </>
              ) : (
                <>
                  <Sparkles className='w-4 h-4 mr-2' /> Run AI Analysis & Recovery Engine
                </>
              )}
            </Button>
          </form>

          {error && (
            <div className='p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm'>
              {error}
            </div>
          )}

          {/* Lifecycle Result Display */}
          {result && (
            <div className='border-t border-gray-200 pt-5 space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300'>
              <div className='flex items-center justify-between'>
                <h3 className='font-bold text-gray-900 flex items-center gap-2'>
                  <CheckCircle2 className='w-5 h-5 text-green-600' /> AI Decision Lifecycle Result
                </h3>
                {getPolicyBadge(result.policy_decision)}
              </div>

              <div className='grid grid-cols-2 md:grid-cols-4 gap-3 text-xs'>
                <Card className='bg-gray-50 border border-gray-200'>
                  <CardContent className='p-3'>
                    <span className='text-gray-500 block mb-1 font-medium'>Sentiment</span>
                    <span className='text-sm font-bold text-gray-900'>
                      {(result.sentiment_score * 100).toFixed(0)}% Positive
                    </span>
                  </CardContent>
                </Card>

                <Card className='bg-gray-50 border border-gray-200'>
                  <CardContent className='p-3'>
                    <span className='text-gray-500 block mb-1 font-medium'>Urgency Level</span>
                    <span className='text-sm font-bold text-amber-700 uppercase'>
                      {result.urgency_level}
                    </span>
                  </CardContent>
                </Card>

                <Card className='bg-gray-50 border border-gray-200'>
                  <CardContent className='p-3'>
                    <span className='text-gray-500 block mb-1 font-medium'>ML Churn Risk</span>
                    <span className='text-sm font-bold text-red-600'>
                      {(result.ml_churn_probability * 100).toFixed(1)}%
                    </span>
                  </CardContent>
                </Card>

                <Card className='bg-gray-50 border border-gray-200'>
                  <CardContent className='p-3'>
                    <span className='text-gray-500 block mb-1 font-medium'>Decision Provider</span>
                    <span className='text-xs font-semibold px-2 py-0.5 rounded bg-purple-100 text-purple-800 inline-block uppercase'>
                      {result.decision_provider}
                    </span>
                  </CardContent>
                </Card>
              </div>

              {/* Structured Decision & Policy Details */}
              <div className='bg-slate-50 border border-slate-200 rounded-lg p-4 text-xs space-y-2'>
                <div className='flex items-center justify-between text-slate-700 font-semibold border-b border-slate-200 pb-2 mb-2'>
                  <span className='flex items-center gap-1.5'>
                    <BrainCircuit className='w-4 h-4 text-indigo-600' /> Structured Decision Summary
                  </span>
                  <span>Category: {result.decision_category.toUpperCase()}</span>
                </div>
                <p className='text-slate-600'>
                  <strong>Policy Rationale:</strong> {result.reasoning}
                </p>
              </div>

              {/* Bedrock / LLM Response */}
              {result.generated_response && (
                <div className='bg-blue-50/70 border border-blue-200 rounded-lg p-4 text-xs space-y-2'>
                  <div className='flex items-center justify-between text-blue-900 font-semibold mb-1'>
                    <span className='flex items-center gap-1.5'>
                      <Bot className='w-4 h-4 text-blue-600' /> Bedrock Generated Response (Grounded)
                    </span>
                    <span className='text-blue-600 text-[10px] uppercase tracking-wide font-mono'>
                      Knowledge Grounded
                    </span>
                  </div>
                  <p className='text-blue-950 italic bg-white p-3 rounded border border-blue-100 shadow-sm leading-relaxed'>
                    "{result.generated_response}"
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
