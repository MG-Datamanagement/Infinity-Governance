"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { signOut, useSession } from "next-auth/react";
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
  FilePlus,
  FileTextIcon,
  Book,
  Bot,
} from "lucide-react";
import { MdOutlineAutoAwesome } from "react-icons/md";
import { LuMessageSquare, LuCable, LuSparkles } from "react-icons/lu";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/store/appStore";
import { BrandLogo } from "../ui/BrandLogo";

const GOVERN_ITEMS = [
  { icon: Home, label: "Home", href: "/overview" },
  { icon: Database, label: "Data Sources", href: "/data-sources" },
  { icon: Globe, label: "Domains", href: "/domains" },
  { icon: Tag, label: "Tags", href: "/tags" },
  { icon: Book, label: "Glossary", href: "/glossary" },
  { icon: Bot, label: "Agents", href: "/agents" },
];

const ADMIN_ITEMS = [
  { icon: Database, label: "Data Connectors", href: "/data-connectors" },
  { icon: BarChart3, label: "Analytics", href: "/analytics" },
];

const AI_ASSISTANT_ITEMS = [
  { icon: LuMessageSquare, label: "Ask Me Anything", href: "/ask-me-anything" },
];

// const CONTEXT_ITEMS = [
//   { icon: FilePlus, label: "New Document", href: "/documents/new" },
// ];

export function Sidebar() {
  const pathname = usePathname();
  const { data: session } = useSession();
  const { sidebarCollapsed, toggleSidebar, darkMode, toggleDarkMode } =
    useAppStore();

  const getUserInitials = (name: string) => {
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <aside
      className={cn(
        "bg-white border-r border-gray-200 flex flex-col h-screen transition-all duration-300",
        sidebarCollapsed ? "w-[70px]" : "w-60",
      )}
    >
      {/* Logo */}
      <div className="p-6 flex items-center justify-between">
        {!sidebarCollapsed && (
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 text-white bg-gray-950 rounded-lg flex items-center justify-center flex-shrink-0">
              <BrandLogo />
            </div>
            <div className="flex flex-col">
              <span className="font-medium text-gray-950 text-sm">
                Infinity
              </span>
              <span className="font-light text-gray-800 text-xs">
                Governance
              </span>
            </div>
          </div>
        )}
        {sidebarCollapsed && (
          <div className="w-8 h-8 text-white bg-gray-950 rounded-lg flex items-center justify-center flex-shrink-0">
            <BrandLogo />
          </div>
        )}
      </div>

      {/* Toggle Button */}
      <button
        onClick={toggleSidebar}
        className={cn(
          "absolute w-6 h-6 bg-white border border-gray-200 rounded-full flex items-center justify-center hover:bg-gray-50 z-20 transition-all",
          sidebarCollapsed ? "top-12 left-14" : "top-12 left-[226px]",
        )}
      >
        {sidebarCollapsed ? (
          <ChevronRight size={16} />
        ) : (
          <ChevronLeft size={16} />
        )}
      </button>

      {/* Navigation */}
      <div className="flex-1 overflow-y-auto p-3">
        <nav className="space-y-3">
          {/* Govern */}
          <div>
            {!sidebarCollapsed && (
              <h3 className="px-3 mb-1 text-xs font-medium text-gray-500 uppercase">
                Govern
              </h3>
            )}
            <div className="space-y-1">
              {GOVERN_ITEMS.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "sidebar-link",
                    pathname === item.href && "active",
                  )}
                  title={sidebarCollapsed ? item.label : ""}
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
              <h3 className="px-3 mb-1 text-xs font-medium text-gray-500 uppercase">
                Admin
              </h3>
            )}
            <div className="space-y-1">
              {ADMIN_ITEMS.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "sidebar-link",
                    pathname === item.href && "active",
                  )}
                  title={sidebarCollapsed ? item.label : ""}
                >
                  <item.icon size={16} />
                  {!sidebarCollapsed && <span>{item.label}</span>}
                </Link>
              ))}
            </div>
          </div>

          {/* AI Assistant */}
          <div>
            {!sidebarCollapsed && (
              <h3 className="px-3 mb-1 text-xs font-medium text-gray-500 uppercase">
                Ai Assistant
              </h3>
            )}
            <div className="space-y-1">
              {AI_ASSISTANT_ITEMS.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "sidebar-link",
                    pathname === item.href && "active",
                  )}
                  title={sidebarCollapsed ? item.label : ""}
                >
                  <item.icon size={16} />
                  {!sidebarCollapsed && <span>{item.label}</span>}
                </Link>
              ))}
            </div>
          </div>

          {/* Context */}
          {/* <div>
            {!sidebarCollapsed && (
              <h3 className="px-3 mb-1 text-xs font-medium text-gray-500 uppercase">
                Context
              </h3>
            )}
            <div className="space-y-1">
              {CONTEXT_ITEMS.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "sidebar-link",
                    pathname === item.href && "active",
                  )}
                  title={sidebarCollapsed ? item.label : ""}
                >
                  <item.icon size={16} />
                  {!sidebarCollapsed && <span>{item.label}</span>}
                </Link>
              ))}
            </div>
          </div> */}
        </nav>
      </div>

      {/* Bottom Section */}
      <div className="border-t border-gray-200 p-3 space-y-1">
        <div>
          <button
            className={cn("sidebar-link", sidebarCollapsed ? "" : "w-full")}
            title={sidebarCollapsed ? "Profile" : ""}
          >
            <User size={16} />
            {!sidebarCollapsed && <span>Profile</span>}
          </button>
        </div>
        <div>
          <button
            onClick={toggleDarkMode}
            className={cn("sidebar-link", sidebarCollapsed ? "" : "w-full")}
            title={sidebarCollapsed ? "Dark Theme" : ""}
          >
            <Moon size={16} />
            {!sidebarCollapsed && <span>Dark Theme</span>}
          </button>
        </div>
        <div>
          <button
            className={cn("sidebar-link", sidebarCollapsed ? "" : "w-full")}
            title={sidebarCollapsed ? "Settings" : ""}
          >
            <Settings size={16} />
            {!sidebarCollapsed && <span>Settings</span>}
          </button>
        </div>
        <div>
          <button
            onClick={() => signOut({ callbackUrl: "/login" })}
            className={cn(
              "sidebar-link",
              sidebarCollapsed ? "" : "w-full",
              // "text-red-600 hover:bg-red-50",
            )}
            title={sidebarCollapsed ? "Sign out" : ""}
          >
            <LogOut size={16} />
            {!sidebarCollapsed && <span>Sign out</span>}
          </button>
        </div>

        {/* User Info */}
        {session?.user && (
          <div className="p-2 border-t border-gray-200 hover:bg-gray-300">
            <div
              className={cn(
                "flex items-center gap-2",
                sidebarCollapsed ? "justify-center" : "px-1",
              )}
            >
              <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center flex-shrink-0 hover:bg-gray-600 hover:border hover:border-white">
                <span className="text-sm font-medium text-gray-700">
                  {getUserInitials(session.user.name || "User")}
                </span>
              </div>
              {!sidebarCollapsed && (
                <span className="text-sm font-semibold text-gray-900 truncate">
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
