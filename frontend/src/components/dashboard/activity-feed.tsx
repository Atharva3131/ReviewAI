import { formatDateTime } from '@/lib/utils';
import { MessageSquare, Users, Star, AlertTriangle, CheckCircle, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ActivityItem {
  id: string;
  type: string;
  title: string;
  description: string;
  timestamp: string;
  priority?: 'low' | 'medium' | 'high';
}

interface ActivityFeedProps {
  activities: ActivityItem[];
}

const getActivityIcon = (type: string) => {
  switch (type) {
    case 'review':
      return MessageSquare;
    case 'recovery':
      return Users;
    case 'response':
      return Star;
    case 'escalation':
      return AlertTriangle;
    default:
      return CheckCircle;
  }
};

const getPriorityColor = (priority?: string) => {
  switch (priority) {
    case 'high':
      return 'text-red-600 bg-red-100';
    case 'medium':
      return 'text-yellow-600 bg-yellow-100';
    case 'low':
      return 'text-green-600 bg-green-100';
    default:
      return 'text-gray-600 bg-gray-100';
  }
};

export function ActivityFeed({ activities }: ActivityFeedProps) {
  if (activities.length === 0) {
    return (
      <div className='text-center py-8'>
        <Clock className='h-12 w-12 text-gray-400 mx-auto mb-4' />
        <p className='text-gray-500'>No recent activity</p>
      </div>
    );
  }

  return (
    <div className='flow-root'>
      <ul className='-mb-8'>
        {activities.map((activity, index) => {
          const Icon = getActivityIcon(activity.type);
          const isLast = index === activities.length - 1;

          return (
            <li key={activity.id}>
              <div className='relative pb-8'>
                {!isLast && (
                  <span
                    className='absolute top-4 left-4 -ml-px h-full w-0.5 bg-gray-200'
                    aria-hidden='true'
                  />
                )}
                <div className='relative flex space-x-3'>
                  <div>
                    <span
                      className={cn(
                        'h-8 w-8 rounded-full flex items-center justify-center ring-8 ring-white',
                        getPriorityColor(activity.priority),
                      )}
                    >
                      <Icon className='h-4 w-4' />
                    </span>
                  </div>
                  <div className='flex-1 min-w-0'>
                    <div>
                      <p className='text-sm font-medium text-gray-900'>{activity.title}</p>
                      <p className='text-sm text-gray-500'>{activity.description}</p>
                    </div>
                    <div className='mt-2 text-xs text-gray-500'>
                      {formatDateTime(activity.timestamp)}
                    </div>
                  </div>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
