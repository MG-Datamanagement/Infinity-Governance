import { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface StatCardProps {
  icon: LucideIcon;
  iconColor?: string;
  label: string;
  value: string | number;
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
}

export function StatCard({
  icon: Icon,
  iconColor = 'text-primary',
  label,
  value,
  change,
  changeType = 'neutral',
}: StatCardProps) {
  return (
    <div className="stat-card">
      <div className="flex items-start justify-between mb-3">
        <div className="w-full flex items-center justify-between gap-1">
          <span className="text-xs text-gray-600">{label}</span>
          <Icon size={18} className={cn(iconColor)} />
        </div>
      </div>
      <div>
        <div className="text-xl font-semibold text-gray-900 my-2">{value}</div>
        {change && (
          <div
            className={cn(
              'text-xs font-medium',
              changeType === 'positive' && 'text-success',
              changeType === 'negative' && 'text-danger',
              changeType === 'neutral' && 'text-gray-600'
            )}
          >
            {change}
          </div>
        )}
      </div>
    </div>
  );
}
