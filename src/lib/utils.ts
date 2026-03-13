import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPercentage(value: number): string {
  return `${value}%`;
}

export function formatDate(date: string | Date): string {
  return new Date(date).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "numeric",
  });
}

export function formatDateTime(date: string | Date | null | undefined): string {
  if (!date) return "—";
  const d = new Date(date);
  if (isNaN(d.getTime())) return "—";

  const pad = (n: number) => n.toString().padStart(2, "0");

  const day = pad(d.getUTCDate());
  const month = pad(d.getUTCMonth() + 1);
  const year = d.getUTCFullYear();
  const hours = pad(d.getUTCHours());
  const minutes = pad(d.getUTCMinutes());
  const seconds = pad(d.getUTCSeconds());

  return `${day}/${month}/${year} ${hours}:${minutes}:${seconds}`;
}

export function getStatusColor(status: string): string {
  switch (status.toLowerCase()) {
    case "excellent":
      return "text-success";
    case "warning":
      return "text-warning";
    case "critical":
      return "text-danger";
    default:
      return "text-gray-600";
  }
}

export function getSeverityColor(severity: string): string {
  switch (severity) {
    case "CRITICAL":
      return "bg-red-200 text-red-900 border border-red-300 font-bold";
    case "HIGH":
      return "bg-red-100 text-red-800";
    case "MEDIUM":
      return "bg-yellow-100 text-yellow-800";
    case "LOW":
      return "bg-blue-100 text-blue-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
}

/**
 * Converts ISO time string into:
 *  - "Just now"
 *  - "5 mins ago"
 *  - "1 hr ago"
 *  - "2 hrs ago"
 *  - "3 days ago"
 */
export function formatTimeAgo(timeString: string): string {
  const past = new Date(timeString);

  if (isNaN(past.getTime())) {
    return timeString;
  }

  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - past.getTime()) / 1000);

  if (diffInSeconds < 60) {
    return "Just now";
  }

  const diffInMinutes = Math.floor(diffInSeconds / 60);
  if (diffInMinutes < 60) {
    return `${diffInMinutes} min${diffInMinutes > 1 ? "s" : ""} ago`;
  }

  const diffInHours = Math.floor(diffInMinutes / 60);
  if (diffInHours < 24) {
    return `${diffInHours} hr${diffInHours > 1 ? "s" : ""} ago`;
  }

  const diffInDays = Math.floor(diffInHours / 24);
  return `${diffInDays} day${diffInDays > 1 ? "s" : ""} ago`;
}

const platformColors = [
  "#3B82F6", // blue
  "#22C55E", // green
  "#A855F7", // purple
  "#EC4899", // pink
  "#6366F1", // indigo
  "#F97316", // orange
  "#14B8A6", // teal
];

export function getPlatformColor(name: string) {
  let hash = 5381;

  for (let i = 0; i < name.length; i++) {
    hash = (hash * 33) ^ name.charCodeAt(i);
  }

  const index = Math.abs(hash) % platformColors.length;
  return platformColors[index];
}

export const downloadCSV = (csv: string, filename: string): void => {
  if (!csv) {
    console.error("CSV is empty");
    return;
  }

  const blob = new Blob(["\uFEFF" + csv], {
    type: "text/csv;charset=utf-8;",
  });

  const url = window.URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = url;
  a.download = filename;

  document.body.appendChild(a);
  a.click();

  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
};

export const downloadFileFromResponse = async (response: Response) => {
  if (!response.ok) {
    throw new Error("Download failed");
  }

  const blob = await response.blob();

  // extract filename from header
  const disposition = response.headers.get("content-disposition");
  let fileName = "my_db_datasets";

  if (disposition && disposition.includes("filename=")) {
    fileName = disposition.split("filename=")[1].replace(/"/g, "");
  }

  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;

  document.body.appendChild(link);
  link.click();
  link.remove();

  URL.revokeObjectURL(url);
};
