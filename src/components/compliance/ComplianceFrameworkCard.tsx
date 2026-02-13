import { ComplianceFramework } from '@/types';
import { cn } from '@/lib/utils';
import { Check, Clock } from 'lucide-react';

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
    <div className={cn('card p-4 border-l-4', getStatusColor(framework.status))}>
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="font-semibold text-gray-900 mb-1">{framework.name}</h3>
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <Clock size={12} />
            <span>{framework.lastUpdated}</span>
          </div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-gray-900">{framework.score}%</div>
          <div className="text-xs text-gray-500 capitalize">{framework.status}</div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-4">
        <div className="flex justify-between text-xs text-gray-600 mb-1">
          <span>
            {framework.policiesComplete} of {framework.policiesTotal} Policies
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className={cn('h-2 rounded-full transition-all', getProgressColor(framework.status))}
            style={{ width: `${framework.score}%` }}
          />
        </div>
      </div>

      {/* Items */}
      {framework.items && framework.items.length > 0 && (
        <div className="space-y-2">
          {framework.items.map((item, idx) => (
            <div key={idx} className="flex items-start gap-2 text-sm">
              {item.completed ? (
                <Check size={16} className="text-success mt-0.5 flex-shrink-0" />
              ) : (
                <div className="w-4 h-4 border-2 border-warning rounded mt-0.5 flex-shrink-0" />
              )}
              <span className={cn(item.completed ? 'text-gray-700' : 'text-warning')}>
                {item.label}
                {item.count && ` +${item.count} more`}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
