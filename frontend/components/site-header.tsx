import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import { Logo } from "@/components/ui/logo";
import { cn } from "@/lib/utils";

export function SiteHeader({ compact = false }: { compact?: boolean }) {
  return (
    <header className="sticky top-0 z-30 border-b border-ink-100/80 bg-parchment/85 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <div className="flex items-center gap-3">
          <Logo />
        </div>

        <nav className="hidden items-center gap-6 text-sm font-medium text-slate-600 md:flex">
          <Link href="/evaluate" className="focus-ring rounded-md hover:text-ink-900">
            Student evaluation
          </Link>
          <Link href="/login" className="focus-ring rounded-md hover:text-ink-900">
            QA insights
          </Link>
          <Link href="/#how-it-works" className="focus-ring rounded-md hover:text-ink-900">
            How it works
          </Link>
        </nav>

        <div className="flex items-center gap-2">
          <Link
            href="/login"
            className={cn(
              buttonVariants({ variant: "outline", size: "sm" }),
              "hidden sm:inline-flex"
            )}
          >
            Reviewer sign in
          </Link>
          <Link
            href="/evaluate"
            className={cn(buttonVariants({ variant: "primary", size: compact ? "sm" : "md" }))}
          >
            Start evaluation
            <ArrowUpRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </header>
  );
}
