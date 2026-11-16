import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide",
  {
    variants: {
      variant: {
        default: "border-ink-200 bg-ink-50 text-ink-800",
        demo: "border-amber-200 bg-amber-50 text-amber-800",
        live: "border-emerald-200 bg-emerald-50 text-emerald-800",
        positive: "border-emerald-200 bg-emerald-50 text-emerald-700",
        mixed: "border-amber-200 bg-amber-50 text-amber-700",
        negative: "border-rose-200 bg-rose-50 text-rose-700",
        neutral: "border-slate-200 bg-slate-50 text-slate-600",
        ember: "border-ember-200 bg-ember-50 text-ember-700",
        outline: "border-ink-200 bg-white text-ink-700",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}
