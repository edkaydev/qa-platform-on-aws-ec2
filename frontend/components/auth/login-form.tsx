"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  BarChart3,
  Eye,
  EyeOff,
  LineChart,
  Loader2,
  Lock,
  ShieldCheck,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
import { Logo, LogoMark } from "@/components/ui/logo";
import {
  api,
  getToken,
  setStoredReviewer,
  setToken,
} from "@/lib/api";

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [showPassword, setShowPassword] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (getToken()) router.replace("/dashboard");
  }, [router]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const result = await api.login(email.trim(), password);
      setToken(result.access_token);
      setStoredReviewer(result.reviewer);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-[1.05fr_0.95fr]">
      <aside className="relative hidden overflow-hidden bg-ink-900 p-10 text-white lg:flex lg:flex-col lg:justify-between">
        <div
          className="pointer-events-none absolute -left-24 top-1/3 h-80 w-80 rounded-full bg-ember-500/25 blur-3xl"
          aria-hidden="true"
        />
        <div
          className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 rounded-full bg-ink-500/40 blur-3xl"
          aria-hidden="true"
        />

        <Link
          href="/"
          className="focus-ring relative inline-flex w-fit items-center gap-2.5 rounded-lg"
        >
          <LogoMark />
          <span className="leading-tight">
            <span className="block text-[15px] font-bold tracking-tight text-white">
              QAAI
            </span>
            <span className="block text-[10px] font-medium uppercase tracking-[0.14em] text-ink-200">
              Quality Assurance AI
            </span>
          </span>
        </Link>

        <div className="relative max-w-md">
          <Badge variant="ember">Reviewer access</Badge>
          <h1 className="text-balance mt-4 text-3xl font-bold leading-tight tracking-tight">
            Quality assurance, grounded in what students actually said.
          </h1>
          <p className="mt-4 text-sm leading-relaxed text-ink-100">
            The reviewer workspace turns anonymous conversations into structured
            evidence: explicit ratings, recurring themes, and the original
            responses behind every insight.
          </p>

          <ul className="mt-7 space-y-3 text-sm text-ink-100">
            <li className="flex items-start gap-3">
              <span className="mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white/10">
                <BarChart3 className="h-4 w-4" />
              </span>
              Criteria-level analysis with sentiment and rating counts.
            </li>
            <li className="flex items-start gap-3">
              <span className="mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white/10">
                <LineChart className="h-4 w-4" />
              </span>
              Database-backed metrics, not hard-coded dashboard numbers.
            </li>
            <li className="flex items-start gap-3">
              <span className="mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white/10">
                <ShieldCheck className="h-4 w-4" />
              </span>
              Every response is tied to the course it was actually about.
            </li>
          </ul>
        </div>

        <p className="relative text-xs leading-relaxed text-ink-200">
          Uganda Martyrs University, Faculty of Science
        </p>
      </aside>

      <main className="flex flex-col px-4 py-8 sm:px-8">
        <div className="flex items-center justify-between">
          <div className="lg:hidden">
            <Logo subtitle={false} />
          </div>
          <Link
            href="/"
            className="focus-ring ml-auto inline-flex items-center gap-1.5 rounded-md text-xs font-medium text-slate-500 hover:text-ink-900"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to overview
          </Link>
        </div>

        <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center py-10">
          <div className="hidden lg:block">
            <Badge variant="outline">QA insights</Badge>
          </div>
          <h2 className="mt-4 text-2xl font-bold tracking-tight text-ink-950 sm:text-3xl">
            Sign in to QA insights
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-600">
            Reviewer access to the Year 3 course review analytics.
          </p>

          <form className="mt-7 space-y-4" onSubmit={handleSubmit}>
            <div>
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="reviewer@qaai.local"
                className="mt-1.5"
              />
            </div>

            <div>
              <Label htmlFor="password">Password</Label>
              <div className="relative mt-1.5">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Enter your password"
                  className="pr-11"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((value) => !value)}
                  className="focus-ring absolute right-2 top-1/2 inline-flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-lg text-slate-400 hover:bg-ink-50 hover:text-ink-700"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            {error ? (
              <div
                role="alert"
                className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2.5 text-xs leading-relaxed text-rose-700"
              >
                {error}
              </div>
            ) : null}

            <Button
              type="submit"
              variant="accent"
              size="lg"
              className="w-full"
              disabled={loading}
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Lock className="h-4 w-4" />
              )}
              {loading ? "Signing in…" : "Sign in"}
            </Button>
          </form>

          <p className="mt-5 text-center text-xs text-slate-500">
            Looking to submit a course evaluation?{" "}
            <Link
              href="/evaluate"
              className="font-semibold text-ink-800 hover:underline"
            >
              Start here
              <ArrowRight className="ml-0.5 inline h-3 w-3" />
            </Link>
          </p>
        </div>
      </main>
    </div>
  );
}
