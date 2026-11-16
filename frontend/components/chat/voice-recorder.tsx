"use client";

import * as React from "react";
import { Loader2, Mic, Square } from "lucide-react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { Transcription } from "@/lib/types";

type RecorderState = "idle" | "recording" | "processing";

export function VoiceRecorder({
  sessionId,
  disabled = false,
  onTranscribed,
  onError,
  onBusyChange,
}: {
  sessionId: number;
  disabled?: boolean;
  onTranscribed: (transcription: Transcription) => void;
  onError: (message: string) => void;
  onBusyChange?: (busy: boolean) => void;
}) {
  const [state, setState] = React.useState<RecorderState>("idle");
  const recorderRef = React.useRef<MediaRecorder | null>(null);
  const streamRef = React.useRef<MediaStream | null>(null);
  const chunksRef = React.useRef<Blob[]>([]);

  React.useEffect(() => {
    return () => {
      try {
        if (recorderRef.current?.state === "recording") {
          recorderRef.current.stop();
        }
      } catch {
        // Recorder may already be stopped.
      }
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  async function startRecording() {
    onError("");
    if (
      typeof navigator === "undefined" ||
      !navigator.mediaDevices?.getUserMedia
    ) {
      onError("Voice recording is not supported in this browser. Please type your answer.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];

      const candidates = [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/mp4",
      ];
      const mimeType = candidates.find(
        (type) =>
          typeof MediaRecorder !== "undefined" &&
          MediaRecorder.isTypeSupported(type)
      );

      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        streamRef.current = null;

        const type = recorder.mimeType || "audio/webm";
        const blob = new Blob(chunksRef.current, { type });
        if (blob.size === 0) {
          setState("idle");
          onError("No audio was captured. Please try again.");
          return;
        }

        setState("processing");
        onBusyChange?.(true);
        try {
          const result = await api.transcribe(
            sessionId,
            blob,
            type.includes("mp4") ? "answer.m4a" : "answer.webm"
          );
          if (!result.text?.trim()) {
            onError("We could not hear any speech in that recording. Please try again or type your answer.");
          } else {
            onTranscribed(result);
          }
        } catch (error) {
          onError(
            error instanceof Error
              ? error.message
              : "Voice transcription failed. You can still type your answer."
          );
        } finally {
          setState("idle");
          onBusyChange?.(false);
        }
      };

      recorder.start();
      recorderRef.current = recorder;
      setState("recording");
    } catch {
      onError(
        "Microphone access was blocked. Allow microphone access or type your answer instead."
      );
      setState("idle");
    }
  }

  function stopRecording() {
    try {
      recorderRef.current?.stop();
    } catch {
      setState("idle");
    }
    recorderRef.current = null;
  }

  if (state === "processing") {
    return (
      <span className="inline-flex h-10 items-center gap-2 rounded-xl bg-ink-50 px-3 text-xs font-medium text-ink-800">
        <Loader2 className="h-4 w-4 animate-spin" />
        Transcribing…
      </span>
    );
  }

  if (state === "recording") {
    return (
      <div className="flex items-center gap-2">
        <span className="inline-flex items-center gap-2 rounded-xl bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-700">
          <span className="h-2 w-2 animate-pulse rounded-full bg-rose-500" />
          Recording
        </span>
        <Button
          variant="accent"
          size="icon"
          onClick={stopRecording}
          aria-label="Stop recording"
          title="Stop recording"
        >
          <Square className="h-3.5 w-3.5 fill-current" />
        </Button>
      </div>
    );
  }

  return (
    <Button
      variant="outline"
      size="icon"
      onClick={startRecording}
      disabled={disabled}
      aria-label="Record a voice answer"
      title="Record a voice answer"
    >
      <Mic className="h-4 w-4" />
    </Button>
  );
}
