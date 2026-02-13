'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';

export function TabNavigation() {
  const pathname = usePathname();

  const tabs = [
    { name: 'Overview', href: '/overview' },
    { name: 'Compliance', href: '/compliance' },
  ];

  return (
    <div className="border-b border-gray-200">
      <nav className="flex gap-6">
        {tabs.map((tab) => (
          <Link
            key={tab.href}
            href={tab.href}
            className={cn(
              'pb-2 px-1 text-sm font-medium transition-colors border-b-2',
              pathname === tab.href
                ? 'text-primary border-primary font-bold'
                : 'text-gray-500 border-transparent hover:text-gray-900'
            )}
          >
            {tab.name}
          </Link>
        ))}
      </nav>
    </div>
  );
}
