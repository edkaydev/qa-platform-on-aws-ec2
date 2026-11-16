import type {
  CommentItem,
  CriterionAnalytics,
  EvaluationView,
  HealthOut,
  Mode,
  Overview,
  RecordPage,
  Review,
  Reviewer,
  SubmitResult,
  ThemeCount,
  ThemeSummary,
  TokenResponse,
  Transcription,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";
const TOKEN_KEY = "qaai_token";
const REVIEWER_KEY = "qaai_reviewer";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  token?: string | null
): Promise<T> {
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers,
      cache: "no-store",
    });
  } catch {
    throw new ApiError(
      "Cannot reach the QAAI server. Check your connection and try again.",
      0
    );
  }

  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    try {
      const data = await response.json();
      if (typeof data?.detail === "string") {
        message = data.detail;
      } else if (Array.isArray(data?.detail) && data.detail[0]?.msg) {
        message = data.detail[0].msg;
      }
    } catch {
      // Keep the fallback message when the body is not JSON.
    }
    throw new ApiError(message, response.status);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
}

export function getStoredReviewer(): Reviewer | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(REVIEWER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Reviewer;
  } catch {
    return null;
  }
}

export function setStoredReviewer(reviewer: Reviewer) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(REVIEWER_KEY, JSON.stringify(reviewer));
}

export function clearStoredReviewer() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(REVIEWER_KEY);
}

function qs(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

export const api = {
  health: () => request<HealthOut>("/api/health"),

  login: (email: string, password: string) =>
    request<TokenResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  startEvaluation: () =>
    request<EvaluationView>("/api/evaluations", {
      method: "POST",
      body: JSON.stringify({
        template_key: "umu-year3-review",
      }),
    }),

  getEvaluation: (sessionId: number) =>
    request<EvaluationView>(`/api/evaluations/${sessionId}`),

  sendMessage: (sessionId: number, content: string, source: "text" | "voice") =>
    request<EvaluationView>(`/api/evaluations/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content, source }),
    }),

  sendRating: (
    sessionId: number,
    criterionKey: string,
    rating: number | null,
    declined = false
  ) =>
    request<EvaluationView>(`/api/evaluations/${sessionId}/rating`, {
      method: "POST",
      body: JSON.stringify({
        criterion_key: criterionKey,
        rating,
        declined,
      }),
    }),

  getReview: (sessionId: number) =>
    request<Review>(`/api/evaluations/${sessionId}/review`),

  submit: (sessionId: number) =>
    request<SubmitResult>(`/api/evaluations/${sessionId}/submit`, {
      method: "POST",
    }),

  transcribe: (sessionId: number, blob: Blob, filename = "answer.webm") => {
    const form = new FormData();
    form.append("file", blob, filename);
    return request<Transcription>(`/api/evaluations/${sessionId}/transcribe`, {
      method: "POST",
      body: form,
    });
  },

  overview: (mode: Mode, token: string) =>
    request<Overview>(`/api/analytics/overview${qs({ mode })}`, {}, token),

  criteria: (mode: Mode, token: string) =>
    request<CriterionAnalytics[]>(
      `/api/analytics/criteria${qs({ mode })}`,
      {},
      token
    ),

  themes: (mode: Mode, token: string) =>
    request<ThemeCount[]>(`/api/analytics/themes${qs({ mode })}`, {}, token),

  themeSummary: (mode: Mode, token: string) =>
    request<ThemeSummary>(
      `/api/analytics/theme-summary${qs({ mode })}`,
      {},
      token
    ),

  records: (
    mode: Mode,
    page: number,
    pageSize: number,
    token: string
  ) =>
    request<RecordPage>(
      `/api/analytics/records${qs({ mode, page, page_size: pageSize })}`,
      {},
      token
    ),

  comments: (mode: Mode, limit: number, token: string) =>
    request<CommentItem[]>(
      `/api/analytics/comments${qs({ mode, limit })}`,
      {},
      token
    ),
};
