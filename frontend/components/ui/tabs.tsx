"use client";

import { cn } from "@/lib/utils";

type TabsProps = {
  tabs: Array<{ key: string; label: string }>;
  value: string;
  onChange: (value: string) => void;
};

export function Tabs({ tabs, value, onChange }: TabsProps) {
  return (
    <div className="flex gap-2 border-b px-4 pt-4">
      {tabs.map((t) => (
        <button
          key={t.key}
          onClick={() => onChange(t.key)}
          className={cn(
            "rounded-t-md px-3 py-2 text-sm font-medium",
            value === t.key ? "bg-primary text-primary-foreground" : "bg-muted text-foreground"
          )}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}
