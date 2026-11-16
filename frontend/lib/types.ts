export type Mode = "all" | "demo" | "live";
export type Sentiment = "positive" | "mixed" | "negative" | "neutral";

export interface Reviewer {
  id: number;
  email: string;
  name: string;
  role: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  reviewer: Reviewer;
}

export interface HealthOut {
  status: string;
  app: string;
  environment: string;
  database: string;
  ai_engine: string;
  ai_model: string;
}

export interface Criterion {
  id: number;
  key: string;
  label: string;
  description: string | null;
  question: string;
  position: number;
  is_mandatory: boolean;
  requires_rating: boolean;
}

export interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  source: string;
  meta: Record<string, unknown>;
  created_at: string;
}

export interface Progress {
  completed: number;
  total: number;
  percent: number;
  status: string;
  current_criterion: string | null;
  current_label: string | null;
  ready_to_submit: boolean;
  course_index: number;
  course_count: number;
  overall_percent: number;
}

export type CourseStatus = "done" | "current" | "upcoming";

export interface CourseProgress {
  course_unit: string;
  course_code: string;
  lecturer: string | null;
  status: CourseStatus;
}

export type Expecting = "message" | "rating" | "review" | "complete";

export interface EvaluationView {
  session_id: number;
  anon_token: string;
  status: string;
  is_demo: boolean;
  institution: string;
  faculty: string;
  course_unit: string;
  course_code: string;
  lecturer: string | null;
  template_name: string;
  course_units: CourseProgress[];
  criteria: Criterion[];
  messages: ChatMessage[];
  progress: Progress;
  expecting: Expecting;
  rating_criterion: string | null;
  rating_label: string | null;
  options: number[] | null;
}

export interface ResponseReview {
  criterion_key: string;
  criterion_label: string;
  course_unit: string;
  course_code: string;
  original_text: string;
  rating: number | null;
  sentiment: string | null;
  summary: string | null;
  strengths: string[];
  improvements: string[];
  themes: string[];
}

export interface Review {
  session_id: number;
  anon_token: string;
  is_demo: boolean;
  course_units: string[];
  responses: ResponseReview[];
  progress: Progress;
  ready_to_submit: boolean;
}

export interface SubmitResult {
  session_id: number;
  anon_token: string;
  status: string;
  submitted_at: string;
  responses_recorded: number;
}

export interface Transcription {
  text: string;
  language: string | null;
  duration: number | null;
}

export interface RatingBucket {
  rating: number;
  count: number;
}

export interface TrendPoint {
  date: string;
  count: number;
}

export interface Overview {
  total_evaluations: number;
  completed_evaluations: number;
  in_progress_evaluations: number;
  demo_evaluations: number;
  live_evaluations: number;
  total_responses: number;
  average_rating: number | null;
  completion_rate: number;
  rating_distribution: RatingBucket[];
  trend: TrendPoint[];
}

export interface CriterionAnalytics {
  key: string;
  label: string;
  response_count: number;
  average_rating: number | null;
  rating_count: number;
  positive_count: number;
  mixed_count: number;
  negative_count: number;
  neutral_count: number;
}

export interface ThemeCount {
  label: string;
  polarity: string;
  count: number;
}

export interface ThemeSummary {
  positives: ThemeCount[];
  improvements: ThemeCount[];
  concerns: ThemeCount[];
}

export interface RecordItem {
  evaluation_id: string;
  course_unit: string;
  criterion_key: string;
  criterion_label: string;
  rating: number | null;
  original_text: string;
  summary: string | null;
  themes: string[];
  sentiment: string | null;
  submitted_at: string | null;
  is_demo: boolean;
}

export interface RecordPage {
  total: number;
  page: number;
  page_size: number;
  items: RecordItem[];
}

export interface CommentItem {
  evaluation_id: string;
  criterion_label: string;
  summary: string;
  sentiment: string | null;
  themes: string[];
  is_demo: boolean;
}
