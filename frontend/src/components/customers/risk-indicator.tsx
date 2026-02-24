'use client';

import { AlertTriangle, Shield, TrendingDown, TrendingUp } from 'lucide-react';
import { cn } from '@/lib/utils';

interface RiskIndicatorProps {
  level: 'low' | 'medium' | 'high';
  score?: number;
  size?: 'sm' | 'md' | 'lg';
  showScore?: boolean;
  className?: string;
}

export function RiskIndicator({
  level,
  score,
  size = 'md',
  showScore = false,
  className,
}: RiskIndicatorProps) {
  const getRiskConfig = (level: string) => {
    switch (level) {
      case 'high':
        return {
          color: 'bg-red-100 text-red-800 border-red-200',
          icon: AlertTriangle,
          label: 'High Risk',
          description: 'Likely to churn soon',
        };
      case 'medium':
        return {
          color: 'bg-yellow-100 text-yellow-800 border-yellow-200',
          icon: TrendingDown,
          label: 'Medium Risk',
          description: 'Showing warning signs',
        };
      default:
        return {
          color: 'bg-green-100 text-green-800 border-green-200',
          icon: Shield,
          label: 'Low Risk',
          description: 'Stable and satisfied',
        };
    }
  };

  const config = getRiskConfig(level);
  const Icon = config.icon;

  const sizeClasses = {
    sm: 'px-2 py-1 text-xs',
    md: 'px-3 py-1 text-sm',
    lg: 'px-4 py-2 text-base',
  };

  const iconSizes = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
    lg: 'h-5 w-5',
  };

  return (
    <div className={cn('flex items-center space-x-1', className)}>
      <span
        className={cn(
          'inline-flex items-center rounded-full border font-medium',
          config.color,
          sizeClasses[size],
        )}
      >
        <Icon className={cn('mr-1', iconSizes[size])} />
        {config.label}
        {showScore && score !== undefined && (
          <span className='ml-1'>({Math.round(score * 100)}%)</span>
        )}
      </span>
    </div>
  );
}

interface ChurnProbabilityProps {
  probability: number;
  className?: string;
}

export function ChurnProbability({ probability, className }: ChurnProbabilityProps) {
  const getColor = (prob: number) => {
    if (prob >= 0.7) {
      return 'bg-red-500';
    }
    if (prob >= 0.4) {
      return 'bg-yellow-500';
    }
    return 'bg-green-500';
  };

  const getTextColor = (prob: number) => {
    if (prob >= 0.7) {
      return 'text-red-700';
    }
    if (prob >= 0.4) {
      return 'text-yellow-700';
    }
    return 'text-green-700';
  };

  return (
    <div className={cn('space-y-1', className)}>
      <div className='flex items-center justify-between text-sm'>
        <span className='font-medium text-gray-700'>Churn Risk</span>
        <span className={cn('font-medium', getTextColor(probability))}>
          {Math.round(probability * 100)}%
        </span>
      </div>
      <div className='w-full bg-gray-200 rounded-full h-2'>
        <div
          className={cn('h-2 rounded-full transition-all duration-300', getColor(probability))}
          style={{ width: `${probability * 100}%` }}
        />
      </div>
    </div>
  );
}

interface CustomerStatusBadgeProps {
  status: 'active' | 'at_risk' | 'churned' | 'recovered';
  className?: string;
}

export function CustomerStatusBadge({ status, className }: CustomerStatusBadgeProps) {
  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'active':
        return {
          color: 'bg-green-100 text-green-800 border-green-200',
          icon: Shield,
          label: 'Active',
        };
      case 'at_risk':
        return {
          color: 'bg-yellow-100 text-yellow-800 border-yellow-200',
          icon: AlertTriangle,
          label: 'At Risk',
        };
      case 'churned':
        return {
          color: 'bg-red-100 text-red-800 border-red-200',
          icon: TrendingDown,
          label: 'Churned',
        };
      case 'recovered':
        return {
          color: 'bg-blue-100 text-blue-800 border-blue-200',
          icon: TrendingUp,
          label: 'Recovered',
        };
      default:
        return {
          color: 'bg-gray-100 text-gray-800 border-gray-200',
          icon: Shield,
          label: 'Unknown',
        };
    }
  };

  const config = getStatusConfig(status);
  const Icon = config.icon;

  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border',
        config.color,
        className,
      )}
    >
      <Icon className='h-3 w-3 mr-1' />
      {config.label}
    </span>
  );
}
