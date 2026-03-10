import { type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type Variant = "primary" | "outline" | "transparent";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  icon?: React.ReactNode;
};

const variants: Record<Variant, string> = {
  primary: "bg-primary text-white hover:bg-primary-dark",
  outline: "text-gray-800 border border-gray-200 bg-white hover:bg-gray-200",
  transparent: "text-gray-800 bg-white hover:bg-gray-200",
};

export function Button({
  variant = "primary",
  icon,
  children,
  className,
  ...props
}: Props) {
  return (
    <button
      className={cn(
        "px-2 py-2 text-xs font-medium rounded-md transition-colors flex items-center gap-2 whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed",
        variants[variant],
        className,
      )}
      {...props}
    >
      {icon}
      {children}
    </button>
  );
}
