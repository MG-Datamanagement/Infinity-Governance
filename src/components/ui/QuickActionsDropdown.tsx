import { useState, useRef, useEffect } from "react";
import { Plus, FileText, Search, Sparkles, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

type ActionItem = {
  id: string;
  title: string;
  description: string;
  icon: React.ElementType;
  iconBg: string;
  iconColor: string;
};

const ACTIONS: ActionItem[] = [
  {
    id: "domain",
    title: "Add Domain",
    description: "Create a new governance domain",
    icon: Plus,
    iconBg: "bg-blue-100",
    iconColor: "text-blue-600",
  },
  {
    id: "policy",
    title: "Create Policy",
    description: "Define new compliance policy",
    icon: FileText,
    iconBg: "bg-indigo-100",
    iconColor: "text-indigo-600",
  },
  {
    id: "compliance",
    title: "Run Compliance Check",
    description: "Scan assets for compliance",
    icon: Search,
    iconBg: "bg-purple-100",
    iconColor: "text-purple-600",
  },
  {
    id: "ai",
    title: "AI Classifier",
    description: "Auto-classify data assets",
    icon: Sparkles,
    iconBg: "bg-amber-100",
    iconColor: "text-amber-600",
  },
];

export default function QuickActionsDropdown() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="relative inline-block" ref={ref}>
      {/* Trigger Button */}
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          "flex items-center gap-2 h-9 px-4 rounded-lg",
          "border border-gray-300 bg-white",
          "text-gray-700 font-medium text-sm",
          "hover:bg-gray-50 transition-colors",
        )}
      >
        Quick actions
        <ChevronDown
          size={16}
          className={cn("transition-transform ml-auto", open && "rotate-180")}
        />
      </button>

      {/* Dropdown */}
      {open && (
        <div
          className={cn(
            "absolute right-0 mt-3 w-[260px] max-w-[90vw]",
            "rounded-2xl border border-gray-200",
            "bg-white shadow-xl",
            "z-50",
          )}
        >
          <div className="space-y-1">
            {ACTIONS.map(
              ({ id, title, description, icon: Icon, iconBg, iconColor }) => (
                <button
                  key={id}
                  className={cn(
                    "w-full flex items-start gap-4",
                    "p-3 rounded-md",
                    "hover:bg-gray-50 transition-colors text-left",
                  )}
                >
                  <div
                    className={cn(
                      "w-8 h-8 rounded-full flex items-center justify-center shrink-0",
                      iconBg,
                    )}
                  >
                    <Icon size={16} className={iconColor} />
                  </div>

                  <div>
                    <div className="text-sm font-semibold text-gray-900">
                      {title}
                    </div>
                    <div className="text-[10px] text-gray-500 mt-0.5">
                      {description}
                    </div>
                  </div>
                </button>
              ),
            )}
          </div>
        </div>
      )}
    </div>
  );
}
