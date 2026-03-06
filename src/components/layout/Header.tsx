"use client";

import { Search, Menu, Database } from "lucide-react";
import { useState } from "react";
import { LuSlidersHorizontal } from "react-icons/lu";
import { RiRobot2Line } from "react-icons/ri";
import { LuCircleHelp } from "react-icons/lu";
import { LuBell } from "react-icons/lu";
import { cn } from "@/lib/utils";
import { NotificationsModal } from "../ui/NotificationsModal";
import { useOverviewData } from "@/hooks/useOverviewData";
import { Button } from "../ui/Button";
import { useRouter } from "next/navigation";

interface HeaderProps {
  userName: string;
}

export function Header({ userName }: HeaderProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [isNotificationsOpen, setIsNotificationsOpen] =
    useState<boolean>(false);
  const [markAllAsRead, setMarkAllAsRead] = useState<boolean>(false);

  const router = useRouter();
  const { activity } = useOverviewData();

  const {
    data: notifications,
    isFetching: isNotificationsLoading,
    error: isNotificationsError,
  } = activity;

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
            <div className="">
              <Button
                variant="transparent"
                className="p-1 transition-colors hidden md:block"
                onClick={() => router.push("/ask-me-anything")}
              >
                <RiRobot2Line size={20} className="text-slate-500" />
              </Button>
            </div>
            {/* <div>
              <Button
                variant="transparent"
                className="p-1 transition-colors hidden md:block"
              >
                <LuCircleHelp size={20} className="text-slate-500" />
              </Button>
            </div> */}
            <div>
              <Button
                variant="transparent"
                onClick={() => setIsNotificationsOpen(!isNotificationsOpen)}
                className="p-1 transition-colors hidden md:block hover:bg-gray-200"
              >
                <LuBell size={20} className="text-slate-500" />
              </Button>
            </div>
          </div>

          {/* Notifications Tray */}
          {isNotificationsOpen && (
            <NotificationsModal
              isOpen={isNotificationsOpen}
              notifications={markAllAsRead ? [] : notifications}
              onClose={() => {
                setIsNotificationsOpen(!isNotificationsOpen);
              }}
              onMarkAsRead={() => setMarkAllAsRead(true)}
              isLoading={isNotificationsLoading}
              isError={isNotificationsError}
            />
          )}
        </div>
      </div>
    </header>
  );
}
