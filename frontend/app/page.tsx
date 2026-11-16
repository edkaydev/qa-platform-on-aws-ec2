import type { ComponentType, ReactNode } from "react";
import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  Building2,
  CheckCircle2,
  GraduationCap,
  Lock,
  MessageSquareText,
  Mic,
  ShieldCheck,
  Sparkles,
  Users,
} from "lucide-react";

import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

const audiences = [
  {
    icon: MessageSquareText,
    title: "For students",
    body: "Answer in your own words, by typing or voice. One question at a time, with a clear review before anything is submitted.",
  },
  {
    icon: BarChart3,
    title: "For QA reviewers",
    body: "See ratings, recurring themes, representative comments, and the original anonymous response behind every number.",
  },
  {
    icon: Building2,
    title: "For institutions",
    body: "A transparent evaluation trail: fixed criteria, deterministic coverage, and auditable records for every course.",
  },
];

const steps = [
  {
    number: "01",
    title: "Start anonymously",
    body: "No student account required. Each evaluation uses an anonymous session token, never a student identity.",
  },
  {
    number: "02",
    title: "Talk naturally",
    body: "The assistant covers every criterion in order. One answer can raise several issues; the controller keeps track so nothing is skipped.",
  },
  {
    number: "03",
    title: "Review & submit",
    body: "Check exactly what was captured, add a rating only where the template requires one, and submit once.",
  },
  {
    number: "04",
    title: "Turn talk into insight",
    body: "Reviewers get database-backed aggregates, criteria analysis, recurring themes, and the original anonymous records.",
  },
];

const criteria = [
  "Teaching clarity",
  "Lecturer preparedness",
  "Learning materials",
  "Practical learning",
  "Student engagement",
  "Lecturer accessibility",
  "Assessment feedback",
  "Overall experience",
];

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader />

      <main className="flex-1">
        <section className="relative overflow-hidden">
          <div className="grid-fade pointer-events-none absolute inset-0" aria-hidden="true" />
          <div className="relative mx-auto grid max-w-6xl gap-12 px-4 pb-20 pt-14 sm:px-6 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:pb-24 lg:pt-20">
            <div className="animate-fade-up">
              <div className="mb-5 inline-flex items-center gap-2">
                <Badge variant="outline">Year 3 review</Badge>
                <span className="text-xs font-medium text-slate-500">
                  Uganda Martyrs University · Faculty of Science
                </span>
              </div>

              <h1 className="text-balance text-4xl font-bold leading-[1.08] tracking-tight text-ink-950 sm:text-5xl lg:text-[3.4rem]">
                Course feedback that feels like a{" "}
                <span className="relative whitespace-nowrap text-ember-500">
                  conversation.
                  <svg
                    className="absolute -bottom-2 left-0 h-2 w-full text-ember-300"
                    viewBox="0 0 200 8"
                    preserveAspectRatio="none"
                    aria-hidden="true"
                  >
                    <path
                      d="M1 5.5c40-3 82-4.5 126-3.2 24 .7 48 1.7 72 3.2"
                      stroke="currentColor"
                      strokeWidth="2.5"
                      fill="none"
                      strokeLinecap="round"
                    />
                  </svg>
                </span>
              </h1>

              <p className="mt-6 max-w-xl text-[15px] leading-relaxed text-slate-600 sm:text-base">
                QAAI turns open, typed or spoken student feedback into structured,
                anonymised quality assurance insight — without inventing ratings or
                skipping the questions that matter.
              </p>

              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Link
                  href="/evaluate"
                  className={cn(buttonVariants({ variant: "accent", size: "lg" }))}
                >
                  Start your course review
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link
                  href="/login"
                  className={cn(buttonVariants({ variant: "outline", size: "lg" }))}
                >
                  Reviewer insights
                </Link>
              </div>

              <p className="mt-5 flex items-center gap-2 text-xs font-medium text-slate-500">
                <Lock className="h-3.5 w-3.5 text-ink-400" />
                Runs on the university&apos;s own server. Local AI. No third-party
                processing.
              </p>
            </div>

            <div className="animate-fade-up [animation-delay:120ms]">
              <div className="relative">
                <div
                  className="absolute -inset-3 -z-10 rounded-[2rem] bg-gradient-to-br from-ink-200/60 via-white to-ember-100/70 blur-xl"
                  aria-hidden="true"
                />
                <div className="overflow-hidden rounded-3xl border border-ink-100 bg-white shadow-lift">
                  <div className="flex items-center justify-between gap-3 border-b border-ink-100 bg-gradient-to-r from-ink-50 to-white px-5 py-4">
                    <div className="flex items-center gap-3">
                      <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-ink-900 text-white">
                        <GraduationCap className="h-4 w-4" />
                      </span>
                      <div>
                        <p className="text-sm font-semibold text-ink-900">
                          Embedded Systems
                        </p>
                        <p className="text-xs text-slate-500">
                          Course 1 of 6 · Year 3
                        </p>
                      </div>
                    </div>
                    <Badge variant="outline" className="hidden sm:inline-flex">
                      Anonymous
                    </Badge>
                  </div>

                  <div className="space-y-3 border-b border-ink-100 px-5 py-4">
                    <div className="flex items-center justify-between text-xs font-medium text-slate-500">
                      <span>Areas captured</span>
                      <span className="text-ink-800">3 of 8</span>
                    </div>
                    <Progress value={37.5} />
                  </div>

                  <div className="space-y-4 bg-parchment/60 px-5 py-6">
                    <ChatBubble role="assistant">
                      Let&apos;s start with how the lecturer explains things —
                      how clear have the lectures been for this course?
                    </ChatBubble>
                    <ChatBubble role="user">
                      Honestly solid, the lecturer uses real examples and the
                      pace is good. Could use a bit more practice time though.
                    </ChatBubble>
                    <ChatBubble role="assistant">
                      Got it, noted! What did you think of the learning
                      materials — slides, notes, anything shared online?
                    </ChatBubble>
                    <div className="flex flex-wrap gap-2 pl-11">
                      <Badge variant="positive">Teaching clarity</Badge>
                      <Badge variant="default">Practical learning</Badge>
                      <Badge variant="neutral">2 themes</Badge>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 border-t border-ink-100 bg-white px-4 py-3">
                    <div className="flex h-10 flex-1 items-center rounded-xl border border-ink-100 bg-parchment/60 px-3 text-xs text-slate-400">
                      Type your answer, or use the microphone…
                    </div>
                    <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-ink-50 text-ink-700">
                      <Mic className="h-4 w-4" />
                    </span>
                    <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-ember-500 text-white">
                      <ArrowRight className="h-4 w-4" />
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="border-y border-ink-100 bg-white/60">
          <div className="mx-auto grid max-w-6xl gap-6 px-4 py-14 sm:px-6 md:grid-cols-3">
            {audiences.map((audience) => (
              <div key={audience.title} className="rounded-2xl p-2">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-ink-50 text-ink-800">
                  <audience.icon className="h-5 w-5" />
                </span>
                <h2 className="mt-4 text-base font-semibold text-ink-900">
                  {audience.title}
                </h2>
                <p className="mt-1.5 text-sm leading-relaxed text-slate-600">
                  {audience.body}
                </p>
              </div>
            ))}
          </div>
        </section>

        <section id="how-it-works" className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
          <div className="max-w-2xl">
            <Badge variant="default">How it works</Badge>
            <h2 className="text-balance mt-4 text-3xl font-bold tracking-tight text-ink-950 sm:text-4xl">
              A guided conversation, a disciplined evaluation.
            </h2>
            <p className="mt-3 text-[15px] leading-relaxed text-slate-600">
              The AI handles wording and extraction. A deterministic controller
              handles structure: it knows which criteria are covered, what still
              needs a rating, and when the evaluation is ready to submit.
            </p>
          </div>

          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {steps.map((step) => (
              <div
                key={step.number}
                className="rounded-2xl border border-ink-100 bg-white p-5 shadow-soft"
              >
                <span className="text-xs font-bold tracking-[0.18em] text-ember-500">
                  {step.number}
                </span>
                <h3 className="mt-3 text-sm font-semibold text-ink-900">
                  {step.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">
                  {step.body}
                </p>
              </div>
            ))}
          </div>
        </section>

        <section className="border-y border-ink-100 bg-white">
          <div className="mx-auto grid max-w-6xl gap-10 px-4 py-16 sm:px-6 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
            <div>
              <Badge variant="ember">One conversation, every course</Badge>
              <h2 className="mt-4 text-2xl font-bold tracking-tight text-ink-950 sm:text-3xl">
                Uganda Martyrs University, Faculty of Science
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-slate-600">
                Year 3 Computer Science students walk through all six of their
                course units in a single sitting — same core questions each
                time, one course after another.
              </p>

              <dl className="mt-6 grid grid-cols-2 gap-4 text-sm">
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-400">
                    Programme
                  </dt>
                  <dd className="mt-1 font-semibold text-ink-900">
                    BSc Computer Science, Year 3
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-400">
                    Course units covered
                  </dt>
                  <dd className="mt-1 font-semibold text-ink-900">6 courses</dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-400">
                    Time per course
                  </dt>
                  <dd className="mt-1 font-semibold text-ink-900">
                    A few minutes each
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-400">
                    Evaluation areas
                  </dt>
                  <dd className="mt-1 font-semibold text-ink-900">8 per course</dd>
                </div>
              </dl>

              <p className="mt-5 flex items-start gap-2 text-xs leading-relaxed text-slate-500">
                <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-ink-400" />
                Every response is tied to the specific course it was about, so
                reviewers see clean, per-course feedback — never mixed up
                across subjects.
              </p>
            </div>

            <div className="rounded-3xl border border-ink-100 bg-parchment/70 p-6 sm:p-8">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-ink-900">
                  Evaluation template
                </h3>
                <Badge variant="outline">Same for every course</Badge>
              </div>
              <ul className="mt-5 grid gap-2 sm:grid-cols-2">
                {criteria.map((item) => (
                  <li
                    key={item}
                    className="flex items-center gap-2 rounded-xl border border-ink-100 bg-white px-3 py-2.5 text-sm text-slate-700"
                  >
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-ink-400" />
                    {item}
                  </li>
                ))}
              </ul>
              <p className="mt-5 flex items-start gap-2 text-xs leading-relaxed text-slate-500">
                <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-ember-500" />
                Only the overall experience asks for a numeric rating. Everything
                else is captured from what the student actually says.
              </p>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
          <div className="grid gap-4 md:grid-cols-3">
            <PrivacyCard
              icon={Lock}
              title="Anonymous by design"
              body="No student account, name, or registration number is collected. Reviewers see anonymous response records only."
            />
            <PrivacyCard
              icon={ShieldCheck}
              title="No invented ratings"
              body="Ratings come only from explicit student input. The AI can summarise wording, but it cannot manufacture a score."
            />
            <PrivacyCard
              icon={Users}
              title="One course at a time"
              body="Every response is tied to the specific course it was about, so reviewers get clean, per-course feedback."
            />
          </div>
        </section>

        <section className="pb-20">
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <div className="rounded-3xl bg-ink-900 px-6 py-10 text-white shadow-lift sm:px-10 sm:py-12">
              <div className="grid gap-8 md:grid-cols-[1.2fr_0.8fr] md:items-center">
                <div>
                  <h2 className="text-balance text-2xl font-bold tracking-tight sm:text-3xl">
                    Try the full loop: conversation, review, dashboard.
                  </h2>
                  <p className="mt-3 max-w-xl text-sm leading-relaxed text-ink-100">
                    Complete an anonymous course review, then sign in as a
                    reviewer to see how the same responses become structured QA
                    insight.
                  </p>
                </div>
                <div className="flex flex-col gap-3 sm:flex-row md:justify-end">
                  <Link
                    href="/evaluate"
                    className={cn(
                      buttonVariants({ variant: "accent", size: "lg" })
                    )}
                  >
                    Start evaluation
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                  <Link
                    href="/login"
                    className={cn(
                      "focus-ring inline-flex h-12 items-center justify-center rounded-xl border border-white/25 px-6 text-[15px] font-semibold text-white transition-colors hover:bg-white/10"
                    )}
                  >
                    Reviewer sign in
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}

function ChatBubble({
  role,
  children,
}: {
  role: "assistant" | "user";
  children: ReactNode;
}) {
  const isAssistant = role === "assistant";
  return (
    <div className={cn("flex", isAssistant ? "justify-start" : "justify-end")}>
      <div
        className={cn(
          "max-w-[85%] rounded-2xl px-4 py-3 text-[13px] leading-relaxed",
          isAssistant
            ? "rounded-tl-md border border-ink-100 bg-white text-slate-700 shadow-soft"
            : "rounded-tr-md bg-ink-900 text-ink-50"
        )}
      >
        {children}
      </div>
    </div>
  );
}

function PrivacyCard({
  icon: Icon,
  title,
  body,
}: {
  icon: ComponentType<{ className?: string }>;
  title: string;
  body: string;
}) {
  return (
    <div className="rounded-2xl border border-ink-100 bg-white p-5 shadow-soft">
      <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-ember-50 text-ember-600">
        <Icon className="h-4 w-4" />
      </span>
      <h3 className="mt-3 text-sm font-semibold text-ink-900">{title}</h3>
      <p className="mt-1.5 text-sm leading-relaxed text-slate-600">{body}</p>
    </div>
  );
}
