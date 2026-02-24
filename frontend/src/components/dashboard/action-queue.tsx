import { Button } from '@/components/ui/button';
import { formatDateTime } from '@/lib/utils';
import { MessageSquare, Users, AlertTriangle, CheckCircle, ArrowRight, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ActionItem {
  id: string;
  type: string;
  title: string;
  description: string;
  priority: 'low' | 'medium' | 'high';
  created_at: string;
}

interface ActionQueueProps {
  actions: ActionItem[];
}

const getActionIcon = (type: string) => {
  switch (type) {
    case 'review_response':
      return MessageSquare;
    case 'customer_recovery':
      return Users;
    case 'escalation':
      return AlertTriangle;
    default:
      return CheckCircle;
  }
};

const getPriorityColor = (priority: string) => {
  switch (priority) {
    case 'high':
      return 'border-red-200 bg-red-50';
    case 'medium':
      return 'border-yellow-200 bg-yellow-50';
    case 'low':
      return 'border-green-200 bg-green-50';
    default:
      return 'border-gray-200 bg-gray-50';
  }
};

const getPriorityBadgeColor = (priority: string) => {
  switch (priority) {
    case 'high':
      return 'bg-red-100 text-red-800';
    case 'medium':
      return 'bg-yellow-100 text-yellow-800';
    case 'low':
      return 'bg-green-100 text-green-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
};

export function ActionQueue({ actions }: ActionQueueProps) {
  if (actions.length === 0) {
    return (
      <div className='text-center py-8'>
        <CheckCircle className='h-12 w-12 text-green-400 mx-auto mb-4' />
        <p className='text-gray-500'>All caught up!</p>
        <p className='text-sm text-gray-400'>No pending actions</p>
      </div>
    );
  }

  return (
    <div className='space-y-3'>
      {actions.map(action => {
        const Icon = getActionIcon(action.type);

        return (
          <div
            key={action.id}
            className={cn('p-4 rounded-lg border-2', getPriorityColor(action.priority))}
          >
            <div className='flex items-start justify-between'>
              <div className='flex items-start space-x-3'>
                <div className='flex-shrink-0'>
                  <Icon className='h-5 w-5 text-gray-600' />
                </div>
                <div className='flex-1 min-w-0'>
                  <p className='text-sm font-medium text-gray-900'>{action.title}</p>
                  <p className='text-sm text-gray-600 mt-1'>{action.description}</p>
                  <div className='flex items-center mt-2 space-x-2'>
                    <span
                      className={cn(
                        'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium',
                        getPriorityBadgeColor(action.priority),
                      )}
                    >
                      {action.priority} priority
                    </span>
                    <span className='text-xs text-gray-500'>
                      <Clock className='h-3 w-3 inline mr-1' />
                      {formatDateTime(action.created_at)}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div className='mt-3 flex justify-end'>
              <Button size='sm' variant='outline'>
                Take Action
                <ArrowRight className='h-4 w-4 ml-1' />
              </Button>
            </div>
          </div>
        );
      })}

      {actions.length > 3 && (
        <div className='text-center pt-2'>
          <Button variant='ghost' size='sm'>
            View all actions ({actions.length})
          </Button>
        </div>
      )}
    </div>
  );
}
