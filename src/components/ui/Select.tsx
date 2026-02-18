import { type SelectHTMLAttributes } from "react";
import { cn } from "@/lib/utils";
import { Option } from "@/types";

type Props = SelectHTMLAttributes<HTMLSelectElement> & {
  options: Option[];
  placeholder?: string;
};

export function Select({
  options,
  placeholder = "Select",
  className,
  ...props
}: Props) {
  return (
    <select
      className={cn(
        "px-2 py-2 text-gray-800 text-xs font-medium rounded-md border-2 border-gray-200 bg-white transition-colors whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed",
        className,
      )}
      {...props}
    >
      <option disabled selected hidden value="">
        {placeholder}
      </option>
      {options.map(({ value, label }) => (
        <option key={value} value={value}>
          {label}
        </option>
      ))}
    </select>
  );
}
