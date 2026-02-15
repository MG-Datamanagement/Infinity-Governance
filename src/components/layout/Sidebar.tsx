'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { signOut, useSession } from 'next-auth/react';
import {
  Home,
  Tag,
  Database,
  Globe,
  BarChart3,
  FileText,
  Settings,
  LogOut,
  User,
  Moon,
  ChevronLeft,
  ChevronRight,
  BookOpen,
  FilePlus
} from 'lucide-react';
import { MdOutlineAutoAwesome } from "react-icons/md";
import { cn } from '@/lib/utils';
import { useAppStore } from '@/store/appStore';

const GOVERN_ITEMS = [
  { icon: BookOpen, label: 'Glossary', href: '/glossary' },
  { icon: Tag, label: 'Tags', href: '/tags' },
  { icon: FileText, label: 'Applications', href: '/applications' },
  { icon: Globe, label: 'Domains', href: '/domains' },
];

const ADMIN_ITEMS = [
  { icon: Database, label: 'Data Sources', href: '/data-sources' },
  { icon: MdOutlineAutoAwesome, label: 'Ask Me Anything', href: '/ask' },
  { icon: BarChart3, label: 'Analytics', href: '/analytics' },
];

const CONTEXT_ITEMS = [
  { icon: FilePlus, label: 'New Document', href: '/documents/new' },
];

export function Sidebar() {
  const pathname = usePathname();
  const { data: session } = useSession();
  const { sidebarCollapsed, toggleSidebar, darkMode, toggleDarkMode } = useAppStore();

  const getUserInitials = (name: string) => {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <aside className={cn(
      'bg-white border-r border-gray-200 flex flex-col h-screen transition-all duration-300',
      sidebarCollapsed ? 'w-[52px]' : 'w-52'
    )}>
      {/* Logo */}
      <div className="p-3 border-b border-gray-200 flex items-center justify-between">
        {!sidebarCollapsed && (
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center flex-shrink-0">
              <span className="text-white font-bold text-lg">∞</span>
            </div>
            <span className="font-semibold text-gray-900 text-sm">Infinity Governance</span>
          </div>
        )}
        {sidebarCollapsed && (
          <div className="w-6 h-6 bg-primary rounded-md flex items-center justify-center mx-auto">
            <span className="text-white font-bold text-lg">∞</span>
          </div>
        )}
      </div>

      {/* Toggle Button */}
      <button
        onClick={toggleSidebar}
        className={cn("absolute w-6 h-6 bg-white border border-gray-200 rounded-full flex items-center justify-center hover:bg-gray-50 z-20", sidebarCollapsed ? "top-9 left-10" : "top-11 left-[198px]" )}
      >
        {sidebarCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
      </button>

      {/* Navigation */}
      <div className="flex-1 overflow-y-auto py-2 px-1">
        <nav className="space-y-2">
          {/* Main */}
          <div>
            <Link
              href="/overview"
              className={cn(
                'sidebar-link',
                pathname === '/overview' && 'active'
              )}
              title={sidebarCollapsed ? 'Home' : ''}
            >
              <Home size={16} />
              {!sidebarCollapsed && <span>Home</span>}
            </Link>
          </div>

          {/* Govern */}
          <div>
            {!sidebarCollapsed && (
              <h3 className="px-2 mb-1 text-xs font-medium text-gray-500 uppercase">
                Govern
              </h3>
            )}
            <div className="space-y-1">
              {GOVERN_ITEMS.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    'sidebar-link',
                    pathname === item.href && 'active'
                  )}
                  title={sidebarCollapsed ? item.label : ''}
                >
                  <item.icon size={16} />
                  {!sidebarCollapsed && <span>{item.label}</span>}
                </Link>
              ))}
            </div>
          </div>

          {/* Admin */}
          <div>
            {!sidebarCollapsed && (
              <h3 className="px-2 mb-1 text-xs font-medium text-gray-500 uppercase">
                Admin
              </h3>
            )}
            <div className="space-y-1">
              {ADMIN_ITEMS.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    'sidebar-link',
                    pathname === item.href && 'active'
                  )}
                  title={sidebarCollapsed ? item.label : ''}
                >
                  <item.icon size={16} />
                  {!sidebarCollapsed && <span>{item.label}</span>}
                </Link>
              ))}
            </div>
          </div>

          {/* Context */}
          <div>
            {!sidebarCollapsed && (
              <h3 className="px-2 mb-1 text-xs font-medium text-gray-500 uppercase">
                Context
              </h3>
            )}
            <div className="space-y-1">
              {CONTEXT_ITEMS.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    'sidebar-link',
                    pathname === item.href && 'active'
                  )}
                  title={sidebarCollapsed ? item.label : ''}
                >
                  <item.icon size={16} />
                  {!sidebarCollapsed && <span>{item.label}</span>}
                </Link>
              ))}
            </div>
          </div>
        </nav>
      </div>

      {/* Bottom Section */}
      <div className="border-t border-gray-200 py-2 px-1 space-y-1">
        <div>
          <button className={cn("sidebar-link", sidebarCollapsed ? "" : "w-full")} title={sidebarCollapsed ? 'Profile' : ''}>
            <User size={16} />
            {!sidebarCollapsed && <span>Profile</span>}
          </button>
        </div>
        <div>
          <button
            onClick={toggleDarkMode}
            className={cn("sidebar-link", sidebarCollapsed ? "" : "w-full")}
            title={sidebarCollapsed ? 'Dark Theme' : ''}
          >
            <Moon size={16} />
            {!sidebarCollapsed && <span>Dark Theme</span>}
          </button>
        </div>
        <div>
          <button className={cn("sidebar-link", sidebarCollapsed ? "" : "w-full")} title={sidebarCollapsed ? 'Settings' : ''}>
            <Settings size={16} />
            {!sidebarCollapsed && <span>Settings</span>}
          </button>
        </div>
        <div>
          <button
            onClick={() => signOut({ callbackUrl: '/login' })}
            className={cn("sidebar-link", sidebarCollapsed ? "" : "w-full", "text-red-600 hover:bg-red-50")}
            title={sidebarCollapsed ? 'Sign out' : ''}
          >
            <LogOut size={16} />
            {!sidebarCollapsed && <span>Sign out</span>}
          </button>
        </div>

        {/* User Info */}
        {session?.user && (
          <div className="p-1.5 bg-gray-100 rounded-lg hover:bg-gray-300">
            <div className={cn(
              'flex items-center gap-1',
              sidebarCollapsed ? 'justify-center' : 'px-1'
            )}>
              <div className="w-7 h-7 bg-gray-200 rounded-full flex items-center justify-center flex-shrink-0 hover:bg-gray-600 hover:border hover:border-white">
                <span className="text-xs font-semibold text-gray-700">
                  {getUserInitials(session.user.name || 'User')}
                </span>
              </div>
              {!sidebarCollapsed && (
                <span className="text-xs font-semibold text-gray-700 truncate">
                  {session.user.name}
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
