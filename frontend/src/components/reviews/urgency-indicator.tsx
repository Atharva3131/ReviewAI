import { cn } from '@/lib/utils';
import { AlertTriangle, Clock, CheckCircle } from 'lucide-react';

interface UrgencyIndicatorProps {
  level: 'low' | 'medium' | 'high';
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
  showLabel?: boolean;
}

export function UrgencyIndicator({
  level,
  size = 'md',
  showIcon = true,
  showLabel = true,
}: UrgencyIndicatorProps) {
  const getUrgencyConfig = (level: string) => {
    switch (level) {
      case 'high':
        return {
          label: 'High Priority',
          color: 'bg-red-100 text-red-800 border-red-200',
          icon: AlertTriangle,
          iconColor: 'text-red-600',
        };
      case 'medium':
        return {
          label: 'Medium Priority',
          color: 'bg-yellow-100 text-yellow-800 border-yellow-200',
          icon: Clock,
          iconColor: 'text-yellow-600',
        };
      case 'low':
        return {
          label: 'Low Priority',
          color: 'bg-green-100 text-green-800 border-green-200',
          icon: CheckCircle,
          iconColor: 'text-green-600',
        };
      default:
        return {
          label: 'Unknown',
          color: 'bg-gray-100 text-gray-800 border-gray-200',
          icon: Clock,
          iconColor: 'text-gray-600',
        };
    }
  };

  const getSizeClasses = (size: string) => {
    switch (size) {
      case 'sm':
        return {
          container: 'px-2 py-1 text-xs',
          icon: 'h-3 w-3',
        };
      case 'lg':
        return {
          container: 'px-4 py-2 text-sm',
          icon: 'h-5 w-5',
        };
      default:
        return {
          container: 'px-3 py-1 text-sm',
          icon: 'h-4 w-4',
        };
    }
  };

  const config = getUrgencyConfig(level);
  const sizeClasses = getSizeClasses(size);
  const Icon = config.icon;

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border font-medium',
        config.color,
        sizeClasses.container,
      )}
    >
      {showIcon && <Icon className={cn('mr-1', config.iconColor, sizeClasses.icon)} />}
      {showLabel && config.label}
    </span>
  );
}
