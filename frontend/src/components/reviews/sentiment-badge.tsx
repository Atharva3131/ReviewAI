import { cn } from '@/lib/utils';

interface SentimentBadgeProps {
  score: number;
  size?: 'sm' | 'md' | 'lg';
  showScore?: boolean;
}

export function SentimentBadge({ score, size = 'md', showScore = true }: SentimentBadgeProps) {
  const getSentimentLabel = (score: number): string => {
    if (score >= 0.7) {
      return 'Positive';
    }
    if (score >= 0.4) {
      return 'Neutral';
    }
    return 'Negative';
  };

  const getSentimentColor = (score: number): string => {
    if (score >= 0.7) {
      return 'bg-green-100 text-green-800 border-green-200';
    }
    if (score >= 0.4) {
      return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    }
    return 'bg-red-100 text-red-800 border-red-200';
  };

  const getSizeClasses = (size: string): string => {
    switch (size) {
      case 'sm':
        return 'px-2 py-1 text-xs';
      case 'lg':
        return 'px-4 py-2 text-sm';
      default:
        return 'px-3 py-1 text-sm';
    }
  };

  const label = getSentimentLabel(score);
  const colorClasses = getSentimentColor(score);
  const sizeClasses = getSizeClasses(size);

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border font-medium',
        colorClasses,
        sizeClasses,
      )}
    >
      {label}
      {showScore && <span className='ml-1 opacity-75'>({Math.round(score * 100)}%)</span>}
    </span>
  );
}
