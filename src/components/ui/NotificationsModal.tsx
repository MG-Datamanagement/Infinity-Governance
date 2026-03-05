import { BellIcon, Database } from "lucide-react";
import { IoClose } from "react-icons/io5";
import { Button } from "./Button";
import { RecentActivity } from "@/types";
import { cn, formatDate } from "@/lib/utils";
import { useMemo } from "react";
import { InlineState } from "./InlineState";

interface NotificationsModalProps {
  isOpen: boolean;
  notifications: RecentActivity[] | undefined;
  isLoading: boolean;
  isError: Error | null;
  onClose: () => void;
  onMarkAsRead: () => void;
}

export const NotificationsModal: React.FC<NotificationsModalProps> = ({
  isOpen,
  notifications,
  onClose,
  onMarkAsRead,
  isError,
  isLoading,
}) => {
  if (!isOpen) return null;

  const isNotificationsEmpty = useMemo(
    () => !(notifications && notifications?.length),
    [notifications],
  );

//   {
//     !isLoading && !isError && isNotificationsEmpty && (
//       <InlineState
//         type="empty"
//         message={"Ingestion events will appear here."}
//       />
//     );
//   }

  return (
    <div
      className="
      absolute right-5 top-12 mt-2 w-80 bg-white rounded-xl border border-border shadow-2xl z-50 overflow-hidden animate-in slide-in-from-top-2 fade-in duration-200"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg flex flex-col shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center px-4 py-2 rounded-tl-lg rounded-tr-lg bg-[#f9fafb] border-b border-gray-200">
          <div className="flex items-center gap-2.5 text-sm font-medium">
            <BellIcon size={12} className="font-bold" />
            <span className="text-gray-700 text-xs">Notifications</span>
          </div>
          <button
            className="text-xl opacity-60 hover:opacity-100 transition-opacity"
            onClick={onClose}
          >
            <IoClose size={16} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto max-h-64">
          {(notifications || []).map((notification) => (
            <div
              key={notification.id}
              className={`flex items-start gap-3 px-3 py-4 rounded-sm cursor-pointer transition-all border-b border-gray-200 hover:bg-gray-100`}
            >
              <div className="rounded-full p-2 bg-indigo-100">
                <Database size={12} className="font-bold text-indigo-600" />
              </div>
              <div className="flex-1 space-y-1">
                <div className={cn("text-xs font-medium text-gray-900")}>
                  {notification?.name}
                </div>
                <div className="text-[10px] text-gray-600">
                  {notification?.time ? formatDate(notification?.time) : ""}
                </div>
              </div>
            </div>
          ))}

          {isNotificationsEmpty && (
            <div className="flex flex-col justify-center items-center space-y-2 p-4">
              <BellIcon size={25} className="font-bold text-slate-200" />
              <h3 className="text-slate-600 font-medium">No notifications</h3>
              <p className="text-slate-400 text-xs">
                Ingestion events will appear here.
              </p>
            </div>
          )}
        </div>

        <div className="px-4 py-2 bg-[#f9fafb] border-t border-gray-200">
          <Button
            disabled={isNotificationsEmpty}
            onClick={onMarkAsRead}
            className="p-0 text-xs text-indigo-500 bg-transparent border-none outline-none hover:bg-transparent hover:border-none"
          >
            Mark all as read
          </Button>
        </div>
      </div>
    </div>
  );
};
