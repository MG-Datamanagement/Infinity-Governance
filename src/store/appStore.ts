import { create } from "zustand";

export type DashboardTabType = "Overview" | "Compliance";
export type ActivityTabType = "recent" | "viewed";

interface AppState {
  sidebarCollapsed: boolean;
  darkMode: boolean;

  dashboardTab: DashboardTabType;
  setDashboardTab: (tab: DashboardTabType) => void;

  activityTab: ActivityTabType;
  setActivityTab: (tab: ActivityTabType) => void;

  toggleSidebar: () => void;
  toggleDarkMode: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  sidebarCollapsed: false,
  darkMode: false,

  dashboardTab: "Overview",
  setDashboardTab: (tab) => set({ dashboardTab: tab }),

  activityTab: "recent",
  setActivityTab: (tab) => set({ activityTab: tab }),

  toggleSidebar: () =>
    set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

  toggleDarkMode: () => set((state) => ({ darkMode: !state.darkMode })),
}));
