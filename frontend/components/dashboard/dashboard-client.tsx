"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Info,
  Loader2,
  LogOut,
  MessageSquareQuote,
  RefreshCw,
  ShieldCheck,
  Star,
  Users,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Logo } from "@/components/ui/logo";
import {
  ApiError,
  api,
  clearStoredReviewer,
  clearToken,
  getStoredReviewer,
  getToken,
} from "@/lib/api";
import type {
  CommentItem,
  CriterionAnalytics,
  Mode,
  Overview,
  RecordItem,
  RecordPage,
  Reviewer,
  ThemeCount,
  ThemeSummary,
} from "@/lib/types";
import { cn, formatDate, percent } from "@/lib/utils";

const MODES: { value: Mode; label: string }[] = [
  { value: "all", label: "All data" },
  { value: "demo", label: "Demo" },
  { value: "live", label: "Live" },
];

const PAGE_SIZE = 15;

export function DashboardClient() {
  const router = useRouter();
  const [token, setToken] = React.useState<string | null>(null);
  const [reviewer, setReviewer] = React.useState<Reviewer | null>(null);
  const [mode, setMode] = React.useState<Mode>("all");
  const [page, setPage] = React.useState(1);

  const [overview, setOverview] = React.useState<Overview | null>(null);
  const [criteria, setCriteria] = React.useState<CriterionAnalytics[]>([]);
  const [themes, setThemes] = React.useState<ThemeSummary | null>(null);
  const [comments, setComments] = React.useState<CommentItem[]>([]);
  const [records, setRecords] = React.useState<RecordPage | null>(null);

  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [reloadKey, setReloadKey] = React.useState(0);

  const signOut = React.useCallback(() => {
    clearToken();
    clearStoredReviewer();
    router.replace("/login");
  }, [router]);

  React.useEffect(() => {
    const stored = getToken();
    if (!stored) {
      router.replace("/login");
      return;
    }
    setToken(stored);
    setReviewer(getStoredReviewer());
  }, [router]);

  React.useEffect(() => {
    if (!token) return;
    let active = true;
    setLoading(true);
    setError(null);

    Promise.all([
      api.overview(mode, token),
      api.criteria(mode, token),
      api.themeSummary(mode, token),
      api.comments(mode, 8, token),
      api.records(mode, page, PAGE_SIZE, token),
    ])
      .then(([nextOverview, nextCriteria, nextThemes, nextComments, nextRecords]) => {
        if (!active) return;
        setOverview(nextOverview);
        setCriteria(nextCriteria);
        setThemes(nextThemes);
        setComments(nextComments);
        setRecords(nextRecords);
      })
      .catch((err: unknown) => {
        if (!active) return;
        if (err instanceof ApiError && err.status === 401) {
          signOut();
          return;
        }
        setError(
          err instanceof Error ? err.message : "Could not load dashboard data."
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [token, mode, page, reloadKey, signOut]);

  function changeMode(nextMode: Mode) {
    setMode(nextMode);
    setPage(1);
  }

  const totalPages = records
    ? Math.max(1, Math.ceil(records.total / records.page_size))
    : 1;

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-ink-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-parchment">
      <header className="sticky top-0 z-30 border-b border-ink-100 bg-white/85 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-3 px-4 sm:px-6">
          <div className="flex items-center gap-3">
            <Logo />
            <Badge variant="default" className="hidden sm:inline-flex">
              Reviewer
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href="/evaluate"
              className={cn(
                buttonVariants({ variant: "outline", size: "sm" }),
                "hidden sm:inline-flex"
              )}
            >
              <MessageSquareQuote className="h-3.5 w-3.5" />
              Student view
            </Link>
            <span className="hidden text-xs font-medium text-slate-500 md:block">
              {reviewer?.name ?? "QA reviewer"}
            </span>
            <Button variant="ghost" size="sm" onClick={signOut}>
              <LogOut className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Sign out</span>
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:py-8">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-ember-600">
              Quality assurance
            </p>
            <h1 className="mt-1 text-2xl font-bold tracking-tight text-ink-950 sm:text-3xl">
              Evaluation insights
            </h1>
            <p className="mt-1 text-sm text-slate-600">
              BSc Computer Science · Year 3 · All six course units
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <ModeFilter mode={mode} onChange={changeMode} />
            <Button
              variant="outline"
              size="sm"
              onClick={() => setReloadKey((value) => value + 1)}
              disabled={loading}
            >
              <RefreshCw
                className={cn("h-3.5 w-3.5", loading && "animate-spin")}
              />
              Refresh
            </Button>
          </div>
        </div>

        <div className="mt-6">
          {error ? (
            <ErrorState
              message={error}
              onRetry={() => setReloadKey((value) => value + 1)}
            />
          ) : loading || !overview ? (
            <DashboardSkeleton />
          ) : (
            <div className="space-y-5">
              {overview.demo_evaluations > 0 ? (
                <div className="flex flex-col gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-amber-900 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-start gap-2.5">
                    <Info className="mt-0.5 h-4 w-4 shrink-0" />
                    <div>
                      <p className="text-xs font-semibold">
                        Demonstration data is included
                      </p>
                      <p className="mt-0.5 text-[11px] leading-relaxed text-amber-800/90">
                        {overview.demo_evaluations} demo sessions are labelled in
                        the database and can be filtered out. Live evaluations:{" "}
                        {overview.live_evaluations}.
                      </p>
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <Badge variant="demo">
                      Demo {overview.demo_evaluations}
                    </Badge>
                    <Badge variant="live">Live {overview.live_evaluations}</Badge>
                  </div>
                </div>
              ) : null}

              <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <StatCard
                  icon={ClipboardList}
                  label="Evaluations"
                  value={overview.total_evaluations.toLocaleString()}
                  sub={`${overview.completed_evaluations} completed · ${overview.in_progress_evaluations} in progress`}
                />
                <StatCard
                  icon={Star}
                  label="Average rating"
                  value={
                    overview.average_rating !== null
                      ? overview.average_rating.toFixed(1)
                      : "—"
                  }
                  suffix={
                    overview.average_rating !== null ? "/ 5" : undefined
                  }
                  sub="Explicit ratings only"
                />
                <StatCard
                  icon={CheckCircle2}
                  label="Completion rate"
                  value={`${overview.completion_rate.toFixed(1)}%`}
                  sub={`${overview.completed_evaluations} of ${overview.total_evaluations} submitted`}
                />
                <StatCard
                  icon={MessageSquareQuote}
                  label="Captured responses"
                  value={overview.total_responses.toLocaleString()}
                  sub="Structured response records"
                />
              </section>

              {overview.total_evaluations === 0 ? (
                <EmptyDashboard mode={mode} />
              ) : (
                <>
                  <section className="grid gap-4 lg:grid-cols-2">
                    <Card>
                      <CardHeader>
                        <CardTitle>Rating distribution</CardTitle>
                        <CardDescription>
                          How explicit overall ratings are spread.
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <RatingDistribution
                          data={overview.rating_distribution}
                        />
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader>
                        <CardTitle>Submissions, last 14 days</CardTitle>
                        <CardDescription>
                          Completed evaluations by day.
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <TrendChart data={overview.trend} />
                      </CardContent>
                    </Card>
                  </section>

                  <Card>
                    <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3">
                      <div>
                        <CardTitle>Criteria analysis</CardTitle>
                        <CardDescription>
                          Response volume, explicit ratings, and sentiment by
                          evaluation area.
                        </CardDescription>
                      </div>
                      <Badge variant="outline">
                        {criteria
                          .reduce((sum, item) => sum + item.response_count, 0)
                          .toLocaleString()}{" "}
                        responses
                      </Badge>
                    </CardHeader>
                    <CardContent>
                      <div className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] font-medium text-slate-500">
                        <LegendDot className="bg-emerald-500" label="Positive" />
                        <LegendDot className="bg-amber-400" label="Mixed" />
                        <LegendDot className="bg-rose-500" label="Negative" />
                        <LegendDot className="bg-slate-300" label="Neutral" />
                      </div>
                      <div className="divide-y divide-ink-100">
                        {criteria.map((item) => (
                          <CriteriaRow key={item.key} item={item} />
                        ))}
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>Qualitative intelligence</CardTitle>
                      <CardDescription>
                        Recurring themes extracted from anonymous responses.
                        Following the active filter: {modeLabel(mode)}.
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="grid gap-3 lg:grid-cols-3">
                      <ThemeColumn
                        title="Common positives"
                        tone="positive"
                        items={themes?.positives ?? []}
                        empty="No positive themes in this view."
                      />
                      <ThemeColumn
                        title="Improvement areas"
                        tone="improvement"
                        items={themes?.improvements ?? []}
                        empty="No improvement themes in this view."
                      />
                      <ThemeColumn
                        title="Recurring concerns"
                        tone="negative"
                        items={themes?.concerns ?? []}
                        empty="No concern themes in this view."
                      />
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3">
                      <div>
                        <CardTitle>Representative comments</CardTitle>
                        <CardDescription>
                          Short summaries of anonymous responses. Original text
                          is available in the records table.
                        </CardDescription>
                      </div>
                      <Badge variant="outline">{comments.length} shown</Badge>
                    </CardHeader>
                    <CardContent>
                      {comments.length > 0 ? (
                        <div className="grid gap-3 md:grid-cols-2">
                          {comments.map((comment, index) => (
                            <CommentCard
                              key={`${comment.evaluation_id}-${index}`}
                              comment={comment}
                            />
                          ))}
                        </div>
                      ) : (
                        <EmptyInline message="No summary comments in this view." />
                      )}
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3">
                      <div>
                        <CardTitle>Response records</CardTitle>
                        <CardDescription>
                          Anonymous original responses with structured capture.
                          Expand a row for the full text and summary.
                        </CardDescription>
                      </div>
                      <Badge variant="outline">
                        {(records?.total ?? 0).toLocaleString()} records
                      </Badge>
                    </CardHeader>
                    <CardContent className="p-0">
                      {!records || records.items.length === 0 ? (
                        <div className="p-5">
                          <EmptyInline message="No response records in this view." />
                        </div>
                      ) : (
                        <>
                          <div className="overflow-x-auto">
                            <table className="w-full min-w-[860px] border-collapse text-left text-xs">
                              <thead>
                                <tr className="border-y border-ink-100 bg-parchment/60 text-[10px] uppercase tracking-wide text-slate-400">
                                  <th className="px-4 py-2.5 font-semibold">
                                    Reference
                                  </th>
                                  <th className="px-4 py-2.5 font-semibold">
                                    Criterion
                                  </th>
                                  <th className="px-4 py-2.5 font-semibold">
                                    Rating
                                  </th>
                                  <th className="px-4 py-2.5 font-semibold">
                                    Captured response
                                  </th>
                                  <th className="px-4 py-2.5 font-semibold">
                                    Source
                                  </th>
                                  <th className="px-4 py-2.5 font-semibold">
                                    Submitted
                                  </th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-ink-100">
                                {records.items.map((item, index) => (
                                  <RecordRow
                                    key={`${item.evaluation_id}-${item.criterion_key}-${index}`}
                                    item={item}
                                  />
                                ))}
                              </tbody>
                            </table>
                          </div>

                          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-ink-100 px-4 py-3">
                            <p className="text-[11px] text-slate-500">
                              {records.total.toLocaleString()} records · page{" "}
                              {records.page} of {totalPages}
                            </p>
                            <div className="flex gap-2">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() =>
                                  setPage((value) => Math.max(1, value - 1))
                                }
                                disabled={page <= 1 || loading}
                              >
                                <ChevronLeft className="h-3.5 w-3.5" />
                                Previous
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() =>
                                  setPage((value) =>
                                    Math.min(totalPages, value + 1)
                                  )
                                }
                                disabled={page >= totalPages || loading}
                              >
                                Next
                                <ChevronRight className="h-3.5 w-3.5" />
                              </Button>
                            </div>
                          </div>
                        </>
                      )}
                    </CardContent>
                  </Card>
                </>
              )}

              <p className="flex items-center justify-center gap-1.5 pb-4 text-center text-[10px] leading-relaxed text-slate-400">
                <ShieldCheck className="h-3 w-3 shrink-0" />
                Figures are computed straight from the database at request
                time, not cached or hard-coded.
              </p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

function ModeFilter({
  mode,
  onChange,
}: {
  mode: Mode;
  onChange: (mode: Mode) => void;
}) {
  return (
    <div
      role="tablist"
      aria-label="Data filter"
      className="inline-flex rounded-xl border border-ink-200 bg-white p-1"
    >
      {MODES.map((item) => (
        <button
          key={item.value}
          type="button"
          role="tab"
          aria-selected={mode === item.value}
          onClick={() => onChange(item.value)}
          className={cn(
            "focus-ring rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors",
            mode === item.value
              ? "bg-ink-900 text-white"
              : "text-slate-600 hover:bg-ink-50"
          )}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  suffix,
  sub,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  suffix?: string;
  sub: string;
}) {
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-medium text-slate-500">{label}</p>
        <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-ink-50 text-ink-700">
          <Icon className="h-4 w-4" />
        </span>
      </div>
      <p className="mt-2 text-2xl font-bold tracking-tight text-ink-950">
        {value}
        {suffix ? (
          <span className="ml-1 text-sm font-medium text-slate-400">
            {suffix}
          </span>
        ) : null}
      </p>
      <p className="mt-1 text-[11px] leading-relaxed text-slate-500">{sub}</p>
    </Card>
  );
}

function RatingDistribution({
  data,
}: {
  data: Overview["rating_distribution"];
}) {
  const max = Math.max(1, ...data.map((item) => item.count));
  const total = data.reduce((sum, item) => sum + item.count, 0);
  const ordered = [...data].sort((a, b) => b.rating - a.rating);

  return (
    <div className="space-y-2.5">
      {ordered.map((item) => (
        <div key={item.rating} className="flex items-center gap-3">
          <span className="flex w-8 items-center gap-1 text-xs font-semibold text-ink-800">
            {item.rating}
            <Star className="h-3 w-3 text-ember-400" />
          </span>
          <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-ink-50">
            <div
              className="h-full rounded-full bg-gradient-to-r from-ink-700 to-ember-500"
              style={{ width: `${percent(item.count, max)}%` }}
            />
          </div>
          <span className="w-10 text-right text-xs tabular-nums text-slate-500">
            {item.count}
          </span>
        </div>
      ))}
      <p className="pt-1 text-[10px] text-slate-400">
        {total.toLocaleString()} ratings recorded
      </p>
    </div>
  );
}

function TrendChart({ data }: { data: Overview["trend"] }) {
  const max = Math.max(1, ...data.map((item) => item.count));
  const total = data.reduce((sum, item) => sum + item.count, 0);

  if (total === 0) {
    return <EmptyInline message="No completed submissions in the last 14 days." />;
  }

  return (
    <div>
      <div className="flex h-32 items-end gap-1.5">
        {data.map((item) => (
          <div
            key={item.date}
            className="group flex h-full flex-1 flex-col justify-end"
            title={`${formatDate(item.date)}: ${item.count} submitted`}
          >
            <div
              className={cn(
                "w-full rounded-t-md transition-colors",
                item.count > 0
                  ? "bg-ink-200 group-hover:bg-ink-500"
                  : "bg-ink-50"
              )}
              style={{
                height:
                  item.count > 0
                    ? `${Math.max(10, (item.count / max) * 100)}%`
                    : "4px",
              }}
            />
          </div>
        ))}
      </div>
      <div className="mt-2 flex justify-between text-[10px] text-slate-400">
        <span>{formatDate(data[0]?.date)}</span>
        <span>{formatDate(data[data.length - 1]?.date)}</span>
      </div>
    </div>
  );
}

function LegendDot({
  className,
  label,
}: {
  className: string;
  label: string;
}) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={cn("h-2 w-2 rounded-full", className)} />
      {label}
    </span>
  );
}

function CriteriaRow({ item }: { item: CriterionAnalytics }) {
  const total =
    item.positive_count +
    item.mixed_count +
    item.negative_count +
    item.neutral_count;
  const segments = [
    { key: "positive", count: item.positive_count, className: "bg-emerald-500" },
    { key: "mixed", count: item.mixed_count, className: "bg-amber-400" },
    { key: "negative", count: item.negative_count, className: "bg-rose-500" },
    { key: "neutral", count: item.neutral_count, className: "bg-slate-300" },
  ];

  return (
    <div className="grid gap-2 py-3 first:pt-0 last:pb-0 lg:grid-cols-[1.2fr_0.45fr_1.6fr] lg:items-center lg:gap-6">
      <div>
        <p className="text-sm font-semibold text-ink-900">{item.label}</p>
        <p className="text-[11px] text-slate-500">
          {item.response_count.toLocaleString()} responses ·{" "}
          {item.rating_count.toLocaleString()} ratings
        </p>
      </div>

      <div className="flex items-baseline gap-1">
        <span className="text-lg font-bold text-ink-900">
          {item.average_rating !== null ? item.average_rating.toFixed(1) : "—"}
        </span>
        <span className="text-[10px] text-slate-400">/ 5</span>
      </div>

      <div>
        <div className="flex h-2 overflow-hidden rounded-full bg-slate-100">
          {segments.map((segment) =>
            segment.count > 0 ? (
              <div
                key={segment.key}
                className={segment.className}
                style={{ width: `${percent(segment.count, total)}%` }}
                title={`${segment.key}: ${segment.count}`}
              />
            ) : null
          )}
        </div>
        <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-[10px] text-slate-500">
          <span>{item.positive_count} positive</span>
          <span>{item.mixed_count} mixed</span>
          <span>{item.negative_count} negative</span>
          <span>{item.neutral_count} neutral</span>
        </div>
      </div>
    </div>
  );
}

function ThemeColumn({
  title,
  tone,
  items,
  empty,
}: {
  title: string;
  tone: "positive" | "improvement" | "negative";
  items: ThemeCount[];
  empty: string;
}) {
  const styles = {
    positive: { dot: "bg-emerald-500", badge: "positive" as const },
    improvement: { dot: "bg-ember-500", badge: "ember" as const },
    negative: { dot: "bg-rose-500", badge: "negative" as const },
  }[tone];

  return (
    <div className="rounded-2xl border border-ink-100 bg-parchment/60 p-4">
      <div className="flex items-center justify-between gap-2">
        <p className="flex items-center gap-2 text-xs font-semibold text-ink-900">
          <span className={cn("h-2 w-2 rounded-full", styles.dot)} />
          {title}
        </p>
        <span className="text-[10px] text-slate-400">{items.length}</span>
      </div>
      {items.length > 0 ? (
        <ul className="mt-3 space-y-2">
          {items.slice(0, 8).map((item) => (
            <li
              key={`${item.polarity}-${item.label}`}
              className="flex items-start justify-between gap-3 text-[12px] leading-snug text-slate-600"
            >
              <span>{item.label}</span>
              <Badge
                variant={styles.badge}
                className="shrink-0 normal-case tracking-normal"
              >
                {item.count}
              </Badge>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-xs leading-relaxed text-slate-400">{empty}</p>
      )}
    </div>
  );
}

function CommentCard({ comment }: { comment: CommentItem }) {
  return (
    <div className="rounded-2xl border border-ink-100 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Badge variant={sentimentVariant(comment.sentiment)}>
          {comment.sentiment ?? "unrated"}
        </Badge>
        <div className="flex items-center gap-2">
          <Badge variant={comment.is_demo ? "demo" : "live"}>
            {comment.is_demo ? "Demo" : "Live"}
          </Badge>
          <span className="font-mono text-[10px] text-slate-400">
            {comment.evaluation_id}
          </span>
        </div>
      </div>
      <blockquote className="mt-3 text-[13px] leading-relaxed text-slate-700">
        “{comment.summary}”
      </blockquote>
      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        {comment.themes.slice(0, 3).map((theme) => (
          <Badge
            key={theme}
            variant="outline"
            className="normal-case tracking-normal"
          >
            {theme}
          </Badge>
        ))}
        <span className="ml-auto text-[10px] text-slate-400">
          {comment.criterion_label}
        </span>
      </div>
    </div>
  );
}

function RecordRow({ item }: { item: RecordItem }) {
  const [open, setOpen] = React.useState(false);

  return (
    <>
      <tr className="align-top transition-colors hover:bg-parchment/40">
        <td className="whitespace-nowrap px-4 py-3 font-mono text-[11px] font-semibold text-ink-800">
          {item.evaluation_id}
        </td>
        <td className="px-4 py-3">
          <p className="font-medium text-ink-900">{item.criterion_label}</p>
          <p className="text-[10px] text-slate-400">{item.course_unit}</p>
        </td>
        <td className="whitespace-nowrap px-4 py-3">
          {item.rating ? (
            <Badge variant="ember">{item.rating} / 5</Badge>
          ) : (
            <span className="text-slate-400">—</span>
          )}
        </td>
        <td className="max-w-[360px] px-4 py-3">
          <p
            className={cn(
              "text-[12px] leading-relaxed text-slate-600",
              !open && "line-clamp-2"
            )}
          >
            {item.original_text}
          </p>
          <button
            type="button"
            onClick={() => setOpen((value) => !value)}
            className="focus-ring mt-1 inline-flex items-center gap-1 rounded text-[10px] font-semibold text-ink-700 hover:text-ember-600"
          >
            {open ? "Show less" : "Show more"}
            <ChevronDown
              className={cn(
                "h-3 w-3 transition-transform",
                open && "rotate-180"
              )}
            />
          </button>
          {!open && item.themes.length > 0 ? (
            <div className="mt-1.5 flex flex-wrap gap-1">
              {item.themes.slice(0, 3).map((theme) => (
                <span
                  key={theme}
                  className="rounded-full bg-ink-50 px-2 py-0.5 text-[9px] font-medium text-ink-700"
                >
                  {theme}
                </span>
              ))}
            </div>
          ) : null}
        </td>
        <td className="whitespace-nowrap px-4 py-3">
          <Badge variant={item.is_demo ? "demo" : "live"}>
            {item.is_demo ? "Demo" : "Live"}
          </Badge>
        </td>
        <td className="whitespace-nowrap px-4 py-3 text-[11px] text-slate-500">
          {formatDate(item.submitted_at)}
        </td>
      </tr>

      {open ? (
        <tr className="bg-parchment/70">
          <td colSpan={6} className="px-4 py-4">
            <div className="grid gap-4 md:grid-cols-[1.4fr_1fr]">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                  Original response
                </p>
                <p className="mt-1 whitespace-pre-wrap text-[12px] leading-relaxed text-slate-700">
                  {item.original_text}
                </p>
              </div>
              <div className="space-y-3">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                      Structured summary
                    </p>
                    {item.sentiment ? (
                      <Badge variant={sentimentVariant(item.sentiment)}>
                        {item.sentiment}
                      </Badge>
                    ) : null}
                  </div>
                  <p className="mt-1 text-[12px] leading-relaxed text-slate-600">
                    {item.summary ?? "No summary captured."}
                  </p>
                </div>
                {item.themes.length > 0 ? (
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                      Themes
                    </p>
                    <div className="mt-1 flex flex-wrap gap-1.5">
                      {item.themes.map((theme) => (
                        <Badge
                          key={theme}
                          variant="outline"
                          className="normal-case tracking-normal"
                        >
                          {theme}
                        </Badge>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
          </td>
        </tr>
      ) : null}
    </>
  );
}

function EmptyDashboard({ mode }: { mode: Mode }) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center py-12 text-center">
        <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-ink-50 text-ink-700">
          <Users className="h-6 w-6" />
        </span>
        <h2 className="mt-4 text-base font-semibold text-ink-900">
          No evaluations in this view
        </h2>
        <p className="mt-1.5 max-w-md text-sm leading-relaxed text-slate-600">
          {mode === "demo"
            ? "No demo-flagged sessions yet."
            : "Evaluations will appear here once students complete a course review."}
        </p>
        {mode !== "live" ? (
          <Link
            href="/evaluate"
            className={cn(
              buttonVariants({ variant: "accent" }),
              "mt-5"
            )}
          >
            Try the student flow
            <ArrowRight className="h-4 w-4" />
          </Link>
        ) : null}
      </CardContent>
    </Card>
  );
}

function EmptyInline({ message }: { message: string }) {
  return (
    <p className="rounded-xl border border-dashed border-ink-200 bg-parchment/50 px-4 py-6 text-center text-xs text-slate-400">
      {message}
    </p>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-5">
      <div className="h-14 animate-pulse rounded-2xl border border-amber-100 bg-amber-50/60" />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[0, 1, 2, 3].map((item) => (
          <div
            key={item}
            className="h-32 animate-pulse rounded-2xl border border-ink-100 bg-white"
          />
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        {[0, 1].map((item) => (
          <div
            key={item}
            className="h-64 animate-pulse rounded-2xl border border-ink-100 bg-white"
          />
        ))}
      </div>
      <div className="h-80 animate-pulse rounded-2xl border border-ink-100 bg-white" />
    </div>
  );
}

function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <Card className="border-rose-200">
      <CardContent className="flex flex-col items-center py-12 text-center">
        <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-rose-50 text-rose-600">
          <AlertCircle className="h-6 w-6" />
        </span>
        <h2 className="mt-4 text-base font-semibold text-ink-900">
          Could not load insights
        </h2>
        <p className="mt-1.5 max-w-md text-sm leading-relaxed text-slate-600">
          {message}
        </p>
        <Button variant="accent" className="mt-5" onClick={onRetry}>
          <RefreshCw className="h-4 w-4" />
          Try again
        </Button>
      </CardContent>
    </Card>
  );
}

function sentimentVariant(
  sentiment: string | null
): "positive" | "mixed" | "negative" | "neutral" {
  if (sentiment === "positive") return "positive";
  if (sentiment === "mixed") return "mixed";
  if (sentiment === "negative") return "negative";
  return "neutral";
}

function modeLabel(mode: Mode): string {
  if (mode === "demo") return "demo only";
  if (mode === "live") return "live only";
  return "all data";
}
