export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
}

export interface Document {
  id: string;
  filename: string;
  original_filename: string;
  file_type: string;
  file_size: number;
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  chunk_count: number;
  error_message: string | null;
  user_id: string;
  created_at: string;
  updated_at: string;
}

export interface ChatSession {
  id: string;
  title: string;
  user_id: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sources: Source[];
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface Source {
  document_id: string;
  filename: string;
  chunk_text: string;
  score: number;
  page_number?: number;
}

export interface QueryRequest {
  query: string;
  session_id?: string;
  retrieval_mode?: "dense" | "bm25" | "hybrid";
  top_k?: number;
  use_reranking?: boolean;
}

export interface QueryResponse {
  response: string;
  session_id: string;
  message_id: string;
  sources: Source[];
  metadata: {
    retrieval_mode: string;
    latency_ms: number;
    tokens_used: number;
  };
}

export interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
  expires_at: string | null;
}

export interface AdminStats {
  total_users: number;
  active_users: number;
  total_documents: number;
  total_chats: number;
  total_messages: number;
}

export interface SecurityEvent {
  id: string;
  event_type: string;
  severity: "low" | "medium" | "high" | "critical";
  description: string;
  user_id: string;
  ip_address: string;
  created_at: string;
}

export interface MetricsData {
  counters: Record<string, number>;
  gauges: Record<string, number>;
  latency: Record<string, LatencyMetrics>;
  cache_hit_ratio: number;
}

export interface LatencyMetrics {
  p50: number;
  p95: number;
  p99: number;
  average: number;
  max: number;
  min: number;
  count: number;
}

export interface EvaluationResult {
  retrieval: Record<string, number>;
  reranking: Record<string, number>;
  hallucination: Record<string, number>;
  citation: Record<string, number>;
  overall_score: number;
}

export interface BenchmarkResult {
  iterations: number;
  total_time_ms: number;
  average_time_ms: number;
  min_time_ms: number;
  max_time_ms: number;
  p50_ms: number;
  p95_ms: number;
  p99_ms: number;
  success_rate: number;
  error_count: number;
}

export interface UserAdmin {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_login: string | null;
}

export interface AdminAuditLog {
  id: string;
  event_type: string;
  severity: "low" | "medium" | "high" | "critical";
  description: string;
  user_id: string;
  username?: string;
  ip_address: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  services: Record<string, { status: string; latency_ms?: number }>;
  uptime_seconds: number;
}

export interface SystemConfig {
  llm_provider: string;
  llm_model: string;
  embedding_model: string;
  vector_db: string;
  chunk_size: number;
  chunk_overlap: number;
  max_top_k: number;
  enable_reranking: boolean;
  enable_guardrails: boolean;
  cache_ttl_seconds: number;
  rate_limit_per_minute: number;
}

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  type: "info" | "success" | "warning" | "error";
  read: boolean;
  created_at: string;
  action_url?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
