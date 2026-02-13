"use client";

import Image from "next/image";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type Menu = "editor" | "assets";

export function AppSidebar({ menu, onMenuChange }: { menu: Menu; onMenuChange: (m: Menu) => void }) {
  return (
    <aside data-sidebar="sidebar" className="w-full max-w-[260px] border-r border-border bg-background">
      <div data-sidebar="content" className="flex h-full flex-col px-3 py-4">
        <div className="mb-4 px-2">
          <Image src="/bossgolf.svg" alt="BOSS Golf" width={120} height={40} className="h-10 w-auto" priority />
        </div>
        <nav data-sidebar="group" className="space-y-1">
          <button
            onClick={() => onMenuChange("editor")}
            className={cn(
              buttonVariants({ variant: menu === "editor" ? "default" : "outline", size: "sm" }),
              "w-full justify-start"
            )}
          >
            슬라이드 제작
          </button>
          <button
            onClick={() => onMenuChange("assets")}
            className={cn(
              buttonVariants({ variant: menu === "assets" ? "default" : "outline", size: "sm" }),
              "w-full justify-start"
            )}
          >
            로고&아트워크 관리
          </button>
        </nav>
      </div>
    </aside>
  );
}
