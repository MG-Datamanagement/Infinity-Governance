'use client';

import { Search, Menu } from 'lucide-react';
import { useState } from 'react';
import { LuSlidersHorizontal } from "react-icons/lu";

interface HeaderProps {
  userName: string;
}

export function Header({ userName }: HeaderProps) {
  const [searchQuery, setSearchQuery] = useState('');


  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    console.log('Searching for:', searchQuery);
    // Implement search functionality
  };

  return (
    <header className="bg-white border-b border-gray-200 px-4 py-3 sticky top-0 z-10">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-md font-semibold text-gray-900 hidden md:block">
            Good evening, {userName}!
          </h1>
        </div>

        <div className="flex items-center gap-4 flex-1 md:flex-initial justify-end">
          {/* Search */}
          <form onSubmit={handleSearch} className="relative flex-1 md:flex-initial">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Find tasks, dashboards, people, and more"
              className="pl-10 pr-16 md:pr-24 py-1.5 w-full md:w-96 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            />
            <kbd className="absolute right-3 top-1/2 -translate-y-1/2 px-2 py-0.5 text-xs bg-gray-100 border border-gray-300 rounded hidden md:inline-block">
              ⌘ K
            </kbd>
          </form>

          {/* Quick Actions */}
          <div className="relative">
            <button
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors px-2 py-1 text-xs bg-gray-50 border border-gray-300"
            >
              <LuSlidersHorizontal size={20} className="text-gray-600" />
            </button>

            
          </div>

          <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors md:hidden">
            <Menu size={20} className="text-gray-600" />
          </button>
        </div>
      </div>
    </header>
  );
}
