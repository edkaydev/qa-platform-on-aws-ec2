import Link from "next/link";

import { cn } from "@/lib/utils";

export function LogoMark({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "relative inline-flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-ink-900 to-ink-600 text-white shadow-soft",
        className
      )}
      aria-hidden="true"
    >
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none">
        <path
          d="M6.5 6.25h11a2.25 2.25 0 0 1 2.25 2.25v5.5a2.25 2.25 0 0 1-2.25 2.25h-4.6l-3.2 2.6v-2.6H6.5A2.25 2.25 0 0 1 4.25 14V8.5A2.25 2.25 0 0 1 6.5 6.25Z"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
        <path
          d="m9 11.4 1.7 1.7 3.4-3.4"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx="18.2" cy="6.2" r="2.2" fill="#FD6500" />
      </svg>
    </span>
  );
}

export function Logo({
  className,
  href = "/",
  subtitle = true,
}: {
  className?: string;
  href?: string;
  subtitle?: boolean;
}) {
  return (
    <Link
      href={href}
      className={cn("focus-ring inline-flex items-center gap-2.5 rounded-lg", className)}
    >
      <LogoMark />
      <span className="leading-tight">
        <span className="block text-[15px] font-bold tracking-tight text-ink-900">
          QAAI
        </span>
        {subtitle ? (
          <span className="block text-[10px] font-medium uppercase tracking-[0.14em] text-slate-500">
            Quality Assurance AI
          </span>
        ) : null}
      </span>
    </Link>
  );
}
