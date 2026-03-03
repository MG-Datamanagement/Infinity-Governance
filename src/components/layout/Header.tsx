"use client";

import { Search, Menu } from "lucide-react";
import { useState } from "react";
import { LuSlidersHorizontal } from "react-icons/lu";
import { RiRobot2Line } from "react-icons/ri";
import { LuCircleHelp } from "react-icons/lu";
import { LuBell } from "react-icons/lu";

interface HeaderProps {
  userName: string;
}

export function Header({ userName }: HeaderProps) {
  const [searchQuery, setSearchQuery] = useState("");

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    console.log("Searching for:", searchQuery);
    // Implement search functionality
  };

  return (
    <header className="h-16 flex items-center bg-white border-b border-gray-200 px-6 py-2 sticky top-0 z-10">
      <div className="flex items-center justify-between gap-4 w-full">
        <div>
          <h1 className="text-lg font-semibold text-gray-900 hidden md:block">
            Good evening, {userName}!
          </h1>
        </div>

        <div className="flex justify-end items-center flex-1 gap-4">
          {/* Search */}
          <form
            onSubmit={handleSearch}
            className="relative flex-1 md:flex-initial"
          >
            <Search
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
              size={16}
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Find tasks, dashboards, people, and more"
              className="h-10 pl-10 pr-16 md:pr-24 py-1 w-full md:w-96 border border-gray-300 rounded-md text-xs focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            />
            <kbd className="absolute right-3 top-1/2 -translate-y-1/2 px-1 py-0.5 text-xs bg-gray-50 border border-gray-300 rounded hidden md:inline-block">
              ⌘ K
            </kbd>
          </form>

          {/* Quick Actions */}
          <div className="border-l border-gray-200 pl-4 flex gap-4">
            {/* <div>
            <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors px-2 py-1 text-xs bg-gray-50 border border-gray-300">
            <LuSlidersHorizontal size={20} className="text-gray-600" />
            </button>
            </div> */}

            <div className="">
              <button className="p-1 rounded-lg transition-colors hidden md:block">
                <RiRobot2Line size={20} className="text-slate-500" />
              </button>
            </div>
            <div>
              <button className="p-1 rounded-lg transition-colors hidden md:block">
                <LuCircleHelp size={20} className="text-slate-500" />
              </button>
            </div>
            <div>
              <button className="p-1 rounded-lg transition-colors hidden md:block">
                <LuBell size={20} className="text-slate-500" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
