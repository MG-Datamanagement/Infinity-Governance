import { create } from "zustand";

export type DashboardTabType = "Overview" | "Compliance";
export type ActivityTabType = "recent" | "viewed";

interface AppState {
  sidebarCollapsed: boolean;
  darkMode: boolean;
  activityTab: ActivityTabType;
  dashboardTab: DashboardTabType;

  setDashboardTab: (tab: DashboardTabType) => void;
  setActivityTab: (tab: ActivityTabType) => void;
  toggleSidebar: () => void;
  toggleDarkMode: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  sidebarCollapsed: false,
  darkMode: false,
  dashboardTab: "Overview",
  activityTab: "recent",

  setDashboardTab: (tab) => set({ dashboardTab: tab }),
  setActivityTab: (tab) => set({ activityTab: tab }),
  toggleSidebar: () =>
    set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  toggleDarkMode: () => set((state) => ({ darkMode: !state.darkMode })),
}));
