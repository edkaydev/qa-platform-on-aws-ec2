"use client";

import * as React from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Circle,
  ClipboardCheck,
  Loader2,
  Lock,
  Mic,
  RefreshCw,
  Send,
  ShieldCheck,
  Sparkles,
  Star,
} from "lucide-react";

import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { VoiceRecorder } from "@/components/chat/voice-recorder";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { LogoMark } from "@/components/ui/logo";
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/input";
import { api } from "@/lib/api";
import type {
  ChatMessage,
  EvaluationView,
  HealthOut,
  Review,
  SubmitResult,
  Transcription,
} from "@/lib/types";
import { cn, formatDateTime } from "@/lib/utils";

function errorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "Something went wrong. Please try again.";
}

export function ChatShell() {
  const [view, setView] = React.useState<EvaluationView | null>(null);
  const [review, setReview] = React.useState<Review | null>(null);
  const [submitted, setSubmitted] = React.useState<SubmitResult | null>(null);
  const [health, setHealth] = React.useState<HealthOut | null>(null);

  const [input, setInput] = React.useState("");
  const [source, setSource] = React.useState<"text" | "voice">("text");
  const [preview, setPreview] = React.useState<Transcription | null>(null);
  const [previewText, setPreviewText] = React.useState("");

  const [starting, setStarting] = React.useState(true);
  const [bootError, setBootError] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [sending, setSending] = React.useState(false);
  const [voiceBusy, setVoiceBusy] = React.useState(false);
  const [ratingBusy, setRatingBusy] = React.useState(false);
  const [reviewLoading, setReviewLoading] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);

  const startedRef = React.useRef(false);
  const bottomRef = React.useRef<HTMLDivElement | null>(null);
  const inputRef = React.useRef<HTMLTextAreaElement | null>(null);

  const start = React.useCallback(async () => {
    setStarting(true);
    setBootError(null);
    setError(null);
    setView(null);
    setReview(null);
    setSubmitted(null);
    setInput("");
    setPreview(null);
    setSource("text");
    try {
      const data = await api.startEvaluation();
      setView(data);
    } catch (err) {
      setBootError(errorMessage(err));
    } finally {
      setStarting(false);
    }
  }, []);

  React.useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    void start();
  }, [start]);

  React.useEffect(() => {
    let active = true;
    api
      .health()
      .then((data) => {
        if (active) setHealth(data);
      })
      .catch(() => {
        if (active) setHealth(null);
      });
    return () => {
      active = false;
    };
  }, []);

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [view?.messages.length, view?.expecting, review, sending, reviewLoading]);

  async function loadReview(sessionId: number) {
    setReviewLoading(true);
    try {
      const data = await api.getReview(sessionId);
      setReview(data);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setReviewLoading(false);
    }
  }

  async function handleSend() {
    if (!view || sending || voiceBusy) return;
    const content = input.trim();
    if (!content) return;

    setSending(true);
    setError(null);
    try {
      const next = await api.sendMessage(view.session_id, content, source);
      setView(next);
      setInput("");
      setPreview(null);
      setSource("text");
      if (next.expecting === "review") {
        await loadReview(next.session_id);
      }
      inputRef.current?.focus();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSending(false);
    }
  }

  async function handleRate(rating: number | null, declined = false) {
    if (!view?.rating_criterion) return;
    setRatingBusy(true);
    setError(null);
    try {
      const next = await api.sendRating(
        view.session_id,
        view.rating_criterion,
        rating,
        declined
      );
      setView(next);
      if (next.expecting === "review") {
        await loadReview(next.session_id);
      }
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setRatingBusy(false);
    }
  }

  async function handleSubmit() {
    if (!view) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await api.submit(view.session_id);
      setSubmitted(result);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  function handleTranscribed(transcription: Transcription) {
    setPreview(transcription);
    setPreviewText(transcription.text);
    setError(null);
  }

  function useTranscription() {
    const text = previewText.trim();
    if (!text) return;
    setInput(text);
    setSource("voice");
    setPreview(null);
    setPreviewText("");
    window.setTimeout(() => inputRef.current?.focus(), 0);
  }

  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader compact />

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6 lg:py-8">
        <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-ember-600">
              Student evaluation
            </p>
            <h1 className="mt-1 text-2xl font-bold tracking-tight text-ink-950 sm:text-3xl">
              Share your course experience
            </h1>
            <p className="mt-1 text-sm text-slate-600">
              A short, anonymous conversation. About 5–8 minutes.
            </p>
          </div>
          <Link
            href="/"
            className={cn(buttonVariants({ variant: "ghost", size: "sm" }))}
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to overview
          </Link>
        </div>

        <div className="grid gap-5 lg:grid-cols-[320px_minmax(0,1fr)]">
          <aside className="space-y-4">
            <ContextCard view={view} health={health} />
            {view && !submitted ? <ProgressPanel view={view} /> : null}
          </aside>

          <section className="min-w-0">
            {starting ? (
              <LoadingCard />
            ) : bootError ? (
              <BootErrorCard message={bootError} onRetry={start} />
            ) : submitted ? (
              <SuccessPanel result={submitted} onRestart={start} />
            ) : view ? (
              <ChatCard
                view={view}
                review={review}
                reviewLoading={reviewLoading}
                sending={sending}
                voiceBusy={voiceBusy}
                ratingBusy={ratingBusy}
                submitting={submitting}
                input={input}
                error={error}
                bottomRef={bottomRef}
                inputRef={inputRef}
                preview={preview}
                previewText={previewText}
                onInputChange={(value) => {
                  setInput(value);
                  setSource("text");
                }}
                onSend={handleSend}
                onRate={handleRate}
                onSubmit={handleSubmit}
                onRetryReview={() => void loadReview(view.session_id)}
                onTranscribed={handleTranscribed}
                onTranscriptionError={setError}
                onVoiceBusyChange={setVoiceBusy}
                onPreviewChange={setPreviewText}
                onUseTranscription={useTranscription}
                onDiscardTranscription={() => {
                  setPreview(null);
                  setPreviewText("");
                }}
              />
            ) : (
              <LoadingCard />
            )}
          </section>
        </div>
      </main>

      <SiteFooter />
    </div>
  );
}

function ContextCard({
  view,
  health,
}: {
  view: EvaluationView | null;
  health: HealthOut | null;
}) {
  return (
    <Card>
      <CardContent className="space-y-4 p-5">
        <div className="flex items-center justify-between gap-2">
          <Badge variant="outline">Year 3 review</Badge>
          <span className="inline-flex items-center gap-1 text-[10px] font-medium text-slate-500">
            <Lock className="h-3 w-3" />
            Anonymous
          </span>
        </div>

        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">
            Institution
          </p>
          <p className="mt-0.5 text-sm font-semibold text-ink-900">
            {view?.institution ?? "Uganda Martyrs University"}
          </p>
          <p className="text-xs text-slate-500">
            {view?.faculty ?? "Faculty of Science"}
          </p>
        </div>

        <div className="rounded-xl bg-parchment/80 p-3">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-ember-600">
            Right now
          </p>
          <p className="mt-1 text-sm font-semibold text-ink-900">
            {view?.course_unit ?? "Loading your courses…"}
          </p>
          <p className="mt-0.5 text-xs text-slate-500">
            {view?.course_code}
            {view?.lecturer ? ` · ${view.lecturer}` : ""}
          </p>
        </div>

        {view && view.course_units.length > 1 ? (
          <ul className="space-y-1">
            {view.course_units.map((course) => (
              <li
                key={course.course_code}
                className={cn(
                  "flex items-center gap-2 rounded-lg px-2 py-1.5 text-xs",
                  course.status === "current"
                    ? "bg-ink-50 font-semibold text-ink-900"
                    : "text-slate-600"
                )}
              >
                {course.status === "done" ? (
                  <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-500" />
                ) : course.status === "current" ? (
                  <span className="flex h-3.5 w-3.5 shrink-0 items-center justify-center">
                    <span className="h-2 w-2 rounded-full bg-ember-500" />
                  </span>
                ) : (
                  <Circle className="h-3.5 w-3.5 shrink-0 text-slate-300" />
                )}
                <span className="truncate">{course.course_unit}</span>
              </li>
            ))}
          </ul>
        ) : null}

        <div className="space-y-2 text-[11px] leading-relaxed text-slate-500">
          <p className="flex items-start gap-2">
            <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ink-400" />
            No name, registration number, or student account is attached to this
            evaluation.
          </p>
          <p className="flex items-start gap-2">
            <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ember-500" />
            You can review every captured response before submitting.
          </p>
        </div>

        <div className="flex items-center gap-2 rounded-xl bg-ink-50 px-3 py-2 text-[10px] font-medium text-ink-700">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
          </span>
          {health
            ? health.ai_engine.startsWith("ollama")
              ? `Local AI · ${health.ai_model}`
              : "On-server extraction · AI model offline"
            : "Checking local AI…"}
        </div>
      </CardContent>
    </Card>
  );
}

function ProgressPanel({ view }: { view: EvaluationView }) {
  const { progress, criteria } = view;
  const currentIndex = progress.current_criterion
    ? criteria.findIndex((item) => item.key === progress.current_criterion)
    : -1;
  const allDone =
    progress.ready_to_submit ||
    progress.completed >= progress.total ||
    currentIndex === -1;

  return (
    <Card>
      <CardContent className="space-y-3 p-5">
        <div className="flex items-center justify-between text-xs font-medium">
          <span className="text-slate-500">
            Course {progress.course_index} of {progress.course_count}
          </span>
          <span className="text-ink-900">
            {progress.completed} of {progress.total} areas
          </span>
        </div>
        <Progress value={progress.percent} />
        {progress.course_count > 1 ? (
          <p className="text-[10px] text-slate-400">
            {progress.overall_percent}% of the whole review done
          </p>
        ) : null}

        <ul className="space-y-1.5 pt-1">
          {criteria.map((criterion, index) => {
            const done = allDone || (currentIndex >= 0 && index < currentIndex);
            const current = !allDone && index === currentIndex;
            const awaitingRating =
              current &&
              view.expecting === "rating" &&
              criterion.key === view.rating_criterion;
            return (
              <li
                key={criterion.key}
                className={cn(
                  "flex items-center gap-2 rounded-lg px-2 py-1.5 text-xs",
                  current
                    ? "bg-ink-50 font-semibold text-ink-900"
                    : "text-slate-600"
                )}
              >
                {done ? (
                  <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-500" />
                ) : awaitingRating ? (
                  <Star className="h-3.5 w-3.5 shrink-0 text-ember-500" />
                ) : current ? (
                  <span className="flex h-3.5 w-3.5 shrink-0 items-center justify-center">
                    <span className="h-2 w-2 rounded-full bg-ember-500" />
                  </span>
                ) : (
                  <Circle className="h-3.5 w-3.5 shrink-0 text-slate-300" />
                )}
                <span className="truncate">{criterion.label}</span>
                {current && awaitingRating ? (
                  <span className="ml-auto text-[9px] font-semibold uppercase tracking-wide text-ember-600">
                    Rating
                  </span>
                ) : null}
              </li>
            );
          })}
        </ul>
      </CardContent>
    </Card>
  );
}

function ChatCard({
  view,
  review,
  reviewLoading,
  sending,
  voiceBusy,
  ratingBusy,
  submitting,
  input,
  error,
  bottomRef,
  inputRef,
  preview,
  previewText,
  onInputChange,
  onSend,
  onRate,
  onSubmit,
  onRetryReview,
  onTranscribed,
  onTranscriptionError,
  onVoiceBusyChange,
  onPreviewChange,
  onUseTranscription,
  onDiscardTranscription,
}: {
  view: EvaluationView;
  review: Review | null;
  reviewLoading: boolean;
  sending: boolean;
  voiceBusy: boolean;
  ratingBusy: boolean;
  submitting: boolean;
  input: string;
  error: string | null;
  bottomRef: React.RefObject<HTMLDivElement | null>;
  inputRef: React.RefObject<HTMLTextAreaElement | null>;
  preview: Transcription | null;
  previewText: string;
  onInputChange: (value: string) => void;
  onSend: () => void;
  onRate: (rating: number | null, declined?: boolean) => void;
  onSubmit: () => void;
  onRetryReview: () => void;
  onTranscribed: (transcription: Transcription) => void;
  onTranscriptionError: (message: string) => void;
  onVoiceBusyChange: (busy: boolean) => void;
  onPreviewChange: (value: string) => void;
  onUseTranscription: () => void;
  onDiscardTranscription: () => void;
}) {
  const reviewing = view.expecting === "review";

  return (
    <div className="flex h-[calc(100dvh-12rem)] min-h-[560px] flex-col overflow-hidden rounded-3xl border border-ink-100 bg-white shadow-lift">
      <div className="flex items-center justify-between gap-3 border-b border-ink-100 bg-gradient-to-r from-ink-50/80 to-white px-4 py-3 sm:px-5">
        <div className="flex items-center gap-3">
          <LogoMark className="h-8 w-8" />
          <div>
            <p className="text-sm font-semibold text-ink-900">
              Evaluation assistant
            </p>
            <p className="text-[11px] text-slate-500">
              Covers each area in a fixed order
            </p>
          </div>
        </div>
        <Badge variant="outline">
          <Lock className="h-3 w-3" />
          Anonymous
        </Badge>
      </div>

      <div className="scrollbar-thin flex-1 space-y-4 overflow-y-auto bg-parchment/50 px-4 py-5 sm:px-5">
        {view.messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {sending ? <TypingIndicator /> : null}

        {reviewing ? (
          <ReviewPanel
            review={review}
            loading={reviewLoading}
            onRetry={onRetryReview}
          />
        ) : null}

        <div ref={bottomRef} />
      </div>

      {error ? (
        <div className="flex items-start gap-2 border-t border-rose-100 bg-rose-50 px-4 py-2.5 text-xs leading-relaxed text-rose-700 sm:px-5">
          <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>{error}</span>
        </div>
      ) : null}

      <div className="border-t border-ink-100 bg-white p-3 sm:p-4">
        {preview ? (
          <TranscriptionPreview
            preview={preview}
            value={previewText}
            onChange={onPreviewChange}
            onUse={onUseTranscription}
            onDiscard={onDiscardTranscription}
          />
        ) : null}

        {view.expecting === "rating" ? (
          <RatingPanel
            label={view.rating_label ?? "Overall experience"}
            busy={ratingBusy}
            onRate={onRate}
          />
        ) : reviewing ? (
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="flex items-center gap-1.5 text-[11px] leading-relaxed text-slate-500">
              <Lock className="h-3.5 w-3.5 shrink-0" />
              Submitted anonymously. No name or student number is attached.
            </p>
            <Button
              variant="accent"
              size="lg"
              onClick={onSubmit}
              disabled={
                submitting ||
                reviewLoading ||
                !review ||
                !review.ready_to_submit
              }
            >
              {submitting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <CheckCircle2 className="h-4 w-4" />
              )}
              Submit evaluation
            </Button>
          </div>
        ) : (
          <>
            <div className="flex items-end gap-2">
              <Textarea
                ref={inputRef}
                rows={2}
                value={input}
                maxLength={4000}
                disabled={sending || voiceBusy}
                placeholder="Type your answer, or use the microphone…"
                className="min-h-[52px] max-h-36"
                onChange={(event) => onInputChange(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    onSend();
                  }
                }}
              />
              <div className="shrink-0">
                <VoiceRecorder
                  sessionId={view.session_id}
                  disabled={sending}
                  onTranscribed={onTranscribed}
                  onError={onTranscriptionError}
                  onBusyChange={onVoiceBusyChange}
                />
              </div>
              <Button
                variant="accent"
                size="icon"
                onClick={onSend}
                disabled={!input.trim() || sending || voiceBusy}
                aria-label="Send answer"
                title="Send answer"
                className="shrink-0"
              >
                {sending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
            <div className="mt-2 flex items-center justify-between px-1 text-[10px] text-slate-400">
              <span>Enter to send · Shift+Enter for a new line</span>
              <span>{input.length}/4000</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isAssistant = message.role === "assistant";
  return (
    <div
      className={cn(
        "flex items-end gap-2.5",
        isAssistant ? "justify-start" : "justify-end"
      )}
    >
      {isAssistant ? <LogoMark className="h-8 w-8 shrink-0" /> : null}
      <div
        className={cn(
          "max-w-[86%] rounded-2xl px-4 py-3 text-[13px] leading-relaxed shadow-soft sm:max-w-[78%]",
          isAssistant
            ? "rounded-bl-md border border-ink-100 bg-white text-slate-700"
            : "rounded-br-md bg-ink-900 text-ink-50"
        )}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {message.source === "voice" ? (
          <span
            className={cn(
              "mt-2 inline-flex items-center gap-1 text-[10px] font-medium",
              isAssistant ? "text-slate-400" : "text-ink-200"
            )}
          >
            <Mic className="h-3 w-3" />
            Voice answer
          </span>
        ) : null}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex items-end gap-2.5">
      <LogoMark className="h-8 w-8 shrink-0" />
      <div className="flex items-center gap-1.5 rounded-2xl rounded-bl-md border border-ink-100 bg-white px-4 py-3.5 shadow-soft">
        <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-ink-400" />
        <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-ink-400 [animation-delay:150ms]" />
        <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-ink-400 [animation-delay:300ms]" />
      </div>
    </div>
  );
}

function TranscriptionPreview({
  preview,
  value,
  onChange,
  onUse,
  onDiscard,
}: {
  preview: Transcription;
  value: string;
  onChange: (value: string) => void;
  onUse: () => void;
  onDiscard: () => void;
}) {
  return (
    <div className="mb-3 rounded-xl border border-ember-200 bg-ember-50/60 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-ember-700">
          <Mic className="h-3.5 w-3.5" />
          Transcription preview
        </p>
        <span className="text-[10px] text-ember-700/70">
          {preview.language ? `${preview.language} · ` : ""}
          {preview.duration
            ? `${Math.round(preview.duration)}s · `
            : ""}
          Audio is not stored
        </span>
      </div>
      <Textarea
        rows={3}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-2 min-h-[72px] bg-white"
        placeholder="Your transcribed answer will appear here."
      />
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <Button
          size="sm"
          variant="accent"
          onClick={onUse}
          disabled={!value.trim()}
        >
          Use this answer
        </Button>
        <Button size="sm" variant="ghost" onClick={onDiscard}>
          Discard
        </Button>
        <span className="text-[10px] text-ember-700/70">
          Edit before sending if anything was misheard.
        </span>
      </div>
    </div>
  );
}

function RatingPanel({
  label,
  busy,
  onRate,
}: {
  label: string;
  busy: boolean;
  onRate: (rating: number | null, declined?: boolean) => void;
}) {
  return (
    <div className="rounded-xl border border-ink-100 bg-parchment/70 p-3 sm:p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-semibold text-ink-900">
          {label} — required rating
        </p>
        <span className="text-[10px] text-slate-500">
          Only your explicit choice is recorded
        </span>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {[1, 2, 3, 4, 5].map((value) => (
          <button
            key={value}
            type="button"
            onClick={() => onRate(value)}
            disabled={busy}
            className="focus-ring flex h-10 w-10 items-center justify-center rounded-xl border border-ink-200 bg-white text-sm font-semibold text-ink-900 transition-colors hover:border-ember-400 hover:bg-ember-50 hover:text-ember-700 disabled:opacity-50"
            aria-label={`Rate ${value} out of 5`}
          >
            {value}
          </button>
        ))}
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onRate(null, true)}
          disabled={busy}
        >
          Prefer not to say
        </Button>
        {busy ? <Loader2 className="h-4 w-4 animate-spin text-ink-500" /> : null}
      </div>
      <p className="mt-2 text-[10px] text-slate-400">
        1 = very poor · 5 = excellent
      </p>
    </div>
  );
}

function ReviewPanel({
  review,
  loading,
  onRetry,
}: {
  review: Review | null;
  loading: boolean;
  onRetry: () => void;
}) {
  return (
    <div className="animate-fade-up rounded-2xl border border-ink-200 bg-white p-4 shadow-soft sm:p-5">
      <div className="flex items-center gap-2">
        <span className="inline-flex h-8 w-8 items-center justify-center rounded-xl bg-ink-50 text-ink-800">
          <ClipboardCheck className="h-4 w-4" />
        </span>
        <div>
          <h3 className="text-sm font-semibold text-ink-900">
            Review your responses
          </h3>
          <p className="text-[11px] text-slate-500">
            Check the anonymous capture below before submitting.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="mt-4 flex items-center gap-2 text-xs text-slate-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading your responses…
        </div>
      ) : !review ? (
        <div className="mt-4 flex items-center gap-3 text-xs text-slate-500">
          Could not load the review.
          <Button size="sm" variant="outline" onClick={onRetry}>
            <RefreshCw className="h-3 w-3" />
            Retry
          </Button>
        </div>
      ) : (
        <ul className="mt-4 space-y-3">
          {review.responses.map((response, index) => (
            <li
              key={`${response.course_code}-${response.criterion_key}`}
              className="rounded-xl border border-ink-100 bg-parchment/50 p-3"
            >
              {index === 0 ||
              review.responses[index - 1].course_unit !== response.course_unit ? (
                <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-ember-600">
                  {response.course_unit}
                </p>
              ) : null}
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-xs font-semibold text-ink-900">
                  {response.criterion_label}
                </p>
                {response.rating ? (
                  <Badge variant="ember">{response.rating} / 5</Badge>
                ) : (
                  <Badge variant="neutral">No numeric rating</Badge>
                )}
              </div>
              <p className="mt-1.5 whitespace-pre-wrap text-[12px] leading-relaxed text-slate-600">
                {response.original_text}
              </p>
              {response.improvements.length > 0 ? (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {response.improvements.slice(0, 4).map((item) => (
                    <Badge
                      key={item}
                      variant="outline"
                      className="normal-case tracking-normal"
                    >
                      {item}
                    </Badge>
                  ))}
                </div>
              ) : null}
            </li>
          ))}
        </ul>
      )}

      <p className="mt-3 flex items-start gap-1.5 text-[10px] leading-relaxed text-slate-400">
        <Lock className="mt-0.5 h-3 w-3 shrink-0" />
        Once submitted, responses cannot be edited. Reviewers see the anonymous
        text and structured summary, never your identity.
      </p>
    </div>
  );
}

function LoadingCard() {
  return (
    <div className="flex h-[calc(100dvh-12rem)] min-h-[560px] flex-col items-center justify-center gap-4 rounded-3xl border border-ink-100 bg-white shadow-lift">
      <div className="relative">
        <LogoMark className="h-12 w-12" />
        <span className="absolute -right-1 -top-1 h-3.5 w-3.5 animate-pulse rounded-full border-2 border-white bg-ember-500" />
      </div>
      <div className="text-center">
        <p className="text-sm font-semibold text-ink-900">
          Preparing your evaluation…
        </p>
        <p className="mt-1 text-xs text-slate-500">
          Setting up an anonymous session covering all your Year 3 courses.
        </p>
      </div>
    </div>
  );
}

function BootErrorCard({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <Card className="flex h-[calc(100dvh-12rem)] min-h-[420px] items-center justify-center">
      <CardContent className="max-w-md text-center">
        <span className="mx-auto inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-rose-50 text-rose-600">
          <AlertCircle className="h-6 w-6" />
        </span>
        <h2 className="mt-4 text-base font-semibold text-ink-900">
          We could not start the evaluation
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-slate-600">{message}</p>
        <div className="mt-5 flex flex-wrap justify-center gap-2">
          <Button variant="accent" onClick={onRetry}>
            <RefreshCw className="h-4 w-4" />
            Try again
          </Button>
          <Link
            href="/"
            className={cn(buttonVariants({ variant: "outline" }))}
          >
            Back to overview
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}

function SuccessPanel({
  result,
  onRestart,
}: {
  result: SubmitResult;
  onRestart: () => void;
}) {
  const reference = `EV-${result.anon_token
    .replace(/[-_]/g, "")
    .slice(0, 8)
    .toUpperCase()}`;

  return (
    <Card className="flex h-[calc(100dvh-12rem)] min-h-[560px] items-center justify-center">
      <CardContent className="w-full max-w-lg p-8 text-center">
        <span className="mx-auto inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600">
          <CheckCircle2 className="h-7 w-7" />
        </span>
        <h2 className="mt-5 text-2xl font-bold tracking-tight text-ink-950">
          Evaluation submitted
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-slate-600">
          Thank you. Your anonymous responses have been recorded and will appear
          in the quality assurance dashboard.
        </p>

        <dl className="mx-auto mt-6 grid max-w-sm grid-cols-2 gap-3 text-left">
          <div className="rounded-xl border border-ink-100 bg-parchment/60 p-3">
            <dt className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
              Anonymous reference
            </dt>
            <dd className="mt-1 font-mono text-sm font-semibold text-ink-900">
              {reference}
            </dd>
          </div>
          <div className="rounded-xl border border-ink-100 bg-parchment/60 p-3">
            <dt className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
              Responses recorded
            </dt>
            <dd className="mt-1 text-sm font-semibold text-ink-900">
              {result.responses_recorded}
            </dd>
          </div>
          <div className="col-span-2 rounded-xl border border-ink-100 bg-parchment/60 p-3">
            <dt className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
              Submitted
            </dt>
            <dd className="mt-1 text-sm font-semibold text-ink-900">
              {formatDateTime(result.submitted_at)}
            </dd>
          </div>
        </dl>

        <div className="mt-6 flex flex-col justify-center gap-2 sm:flex-row">
          <Button variant="accent" size="lg" onClick={onRestart}>
            Start another evaluation
            <ArrowRight className="h-4 w-4" />
          </Button>
          <Link
            href="/"
            className={cn(buttonVariants({ variant: "outline", size: "lg" }))}
          >
            Back to overview
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
