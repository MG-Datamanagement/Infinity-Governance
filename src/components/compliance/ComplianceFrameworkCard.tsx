import { ComplianceFramework } from '@/types';
import { cn } from '@/lib/utils';
import { Check, Clock, InfoIcon } from 'lucide-react';

interface ComplianceFrameworkCardProps {
  framework: ComplianceFramework;
}

export function ComplianceFrameworkCard({ framework }: ComplianceFrameworkCardProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'excellent':
        return 'border-success';
      case 'warning':
        return 'border-warning';
      case 'critical':
        return 'border-danger';
      default:
        return 'border-gray-300';
    }
  };

  const getProgressColor = (status: string) => {
    switch (status) {
      case 'excellent':
        return 'bg-success';
      case 'warning':
        return 'bg-warning';
      case 'critical':
        return 'bg-danger';
      default:
        return 'bg-gray-400';
    }
  };

  return (
    <div className={cn('card p-2 space-y-1')}>
      {/* Header */}
      <div className="flex flex-col space-y-1">
        <div className='gap-1 flex items-center'>
          <h3 className="text-sm font-semibold text-gray-900">{framework.name}</h3>
          <InfoIcon size={16} />
        </div>
        <div className="text-right flex justify-between items-center">
          <div className="text-lg font-bold text-gray-900">{framework.score}%</div>
          <div className="text-xs text-gray-500 capitalize">{framework.status}</div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="space-y-1">
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className={cn('h-2 rounded-full transition-all', getProgressColor(framework.status))}
            style={{ width: `${framework.score}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-gray-600">
          <span>
            {framework.policiesComplete} of {framework.policiesTotal} Policies
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2 text-xs text-gray-500">
        <Clock size={12} />
        <span>{framework.lastUpdated}</span>
      </div>

      {/* Items */}
      {framework.items && framework.items.length > 0 && (
        <div className="space-y-1">
          {framework.items.map((item, idx) => (
            <div key={idx} className="flex items-start gap-2 text-xs">
              {item.completed ? (
                <Check size={16} className="text-success mt-0.5 flex-shrink-0" />
              ) : (
                null
              )}
              <span className={cn(item.completed ? 'text-gray-700' : 'text-warning')}>
                {!item.count && item.label}
                {item.count && ` +${item.count} ${item.label}`}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
