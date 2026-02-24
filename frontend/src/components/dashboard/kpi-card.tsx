import { Card, CardContent } from '@/components/ui/card';
import { LucideIcon, TrendingUp, TrendingDown } from 'lucide-react';
import { cn } from '@/lib/utils';

interface KPICardProps {
  title: string;
  value: string;
  trend?: number;
  icon: LucideIcon;
  color: 'blue' | 'green' | 'red' | 'purple' | 'yellow';
  invertTrend?: boolean;
}

const colorClasses = {
  blue: 'text-blue-600 bg-blue-100',
  green: 'text-green-600 bg-green-100',
  red: 'text-red-600 bg-red-100',
  purple: 'text-purple-600 bg-purple-100',
  yellow: 'text-yellow-600 bg-yellow-100',
};

export function KPICard({
  title,
  value,
  trend,
  icon: Icon,
  color,
  invertTrend = false,
}: KPICardProps) {
  const getTrendColor = () => {
    if (trend === undefined || trend === 0) {
      return 'text-gray-500';
    }

    const isPositive = invertTrend ? trend < 0 : trend > 0;
    return isPositive ? 'text-green-600' : 'text-red-600';
  };

  const getTrendIcon = () => {
    if (trend === undefined || trend === 0) {
      return null;
    }

    const isUp = trend > 0;
    return isUp ? TrendingUp : TrendingDown;
  };

  const TrendIcon = getTrendIcon();

  return (
    <Card>
      <CardContent className='p-6'>
        <div className='flex items-center justify-between'>
          <div className='flex-1'>
            <p className='text-sm font-medium text-gray-600'>{title}</p>
            <p className='text-2xl font-bold text-gray-900 mt-1'>{value}</p>

            {trend !== undefined && (
              <div className={cn('flex items-center mt-2', getTrendColor())}>
                {TrendIcon && <TrendIcon className='h-4 w-4 mr-1' />}
                <span className='text-sm font-medium'>
                  {Math.abs(trend)}
                  {trend !== 0 && <span className='text-gray-500 ml-1'>vs last month</span>}
                </span>
              </div>
            )}
          </div>

          <div className={cn('p-3 rounded-full', colorClasses[color])}>
            <Icon className='h-6 w-6' />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
