import Link from "next/link";

import { Logo } from "@/components/ui/logo";

export function SiteFooter() {
  return (
    <footer className="border-t border-ink-100 bg-white/70">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-10 sm:px-6 md:flex-row md:items-center md:justify-between">
        <div className="space-y-3">
          <Logo subtitle={false} />
          <p className="max-w-md text-xs leading-relaxed text-slate-500">
            Built for Uganda Martyrs University, Faculty of Science. Anonymous
            by design, grounded in what students actually say.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-xs font-medium text-slate-500">
          <Link href="/evaluate" className="hover:text-ink-900">
            Student evaluation
          </Link>
          <Link href="/login" className="hover:text-ink-900">
            QA insights
          </Link>
          <Link href="/#how-it-works" className="hover:text-ink-900">
            How it works
          </Link>
          <span className="text-slate-400">QAAI · 2026</span>
        </div>
      </div>
    </footer>
  );
}
