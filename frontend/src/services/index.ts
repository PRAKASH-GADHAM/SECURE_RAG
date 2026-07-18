import { api } from "./api";
import type {
  Document,
  ChatSession,
  ChatMessage,
  QueryResponse,
  ApiKey,
  AdminStats,
  SecurityEvent,
  MetricsData,
  BenchmarkResult,
  EvaluationResult,
  UserAdmin,
  AdminAuditLog,
  HealthResponse,
  SystemConfig,
  NotificationItem,
  PaginatedResponse,
} from "@/types";

export const documentService = {
  async list(): Promise<Document[]> {
    const res = await api.get<Document[]>("/api/v1/documents/");
    return res.data;
  },
  async get(id: string): Promise<Document> {
    const res = await api.get<Document>(`/api/v1/documents/${id}`);
    return res.data;
  },
  async upload(file: File, onProgress?: (p: number) => void): Promise<Document> {
    const formData = new FormData();
    formData.append("file", file);
    const res = await api.post<Document>("/api/v1/documents/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (e) => {
        if (e.total && onProgress) onProgress(Math.round((e.loaded * 100) / e.total));
      },
    });
    return res.data;
  },
  async delete(id: string): Promise<void> {
    await api.delete(`/api/v1/documents/${id}`);
  },
  async getStatus(id: string): Promise<Document> {
    const res = await api.get<Document>(`/api/v1/documents/${id}/status`);
    return res.data;
  },
};

export const chatService = {
  async listSessions(): Promise<ChatSession[]> {
    const res = await api.get<ChatSession[]>("/api/v1/chat/sessions");
    return res.data;
  },
  async createSession(title?: string): Promise<ChatSession> {
    const res = await api.post<ChatSession>("/api/v1/chat/sessions", { title });
    return res.data;
  },
  async getSession(id: string): Promise<ChatSession> {
    const res = await api.get<ChatSession>(`/api/v1/chat/sessions/${id}`);
    return res.data;
  },
  async deleteSession(id: string): Promise<void> {
    await api.delete(`/api/v1/chat/sessions/${id}`);
  },
  async renameSession(id: string, title: string): Promise<ChatSession> {
    const res = await api.patch<ChatSession>(`/api/v1/chat/sessions/${id}`, { title });
    return res.data;
  },
  async getMessages(sessionId: string): Promise<ChatMessage[]> {
    const res = await api.get<ChatMessage[]>(`/api/v1/chat/sessions/${sessionId}/messages`);
    return res.data;
  },
  async query(params: {
    query: string;
    session_id?: string;
    retrieval_mode?: string;
    top_k?: number;
    use_reranking?: boolean;
  }): Promise<QueryResponse> {
    const res = await api.post<QueryResponse>("/api/v1/chat/query", params);
    return res.data;
  },
  async* queryStream(params: {
    query: string;
    session_id?: string;
    retrieval_mode?: string;
    top_k?: number;
  }): AsyncGenerator<string> {
    const token = localStorage.getItem("access_token");
    const res = await fetch("/api/v1/chat/query/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(params),
    });
    const reader = res.body?.getReader();
    if (!reader) return;
    const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const text = decoder.decode(value);
      const lines = text.split("\n");
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6);
          if (data === "[DONE]") return;
          try {
            const parsed = JSON.parse(data);
            if (parsed.content) yield parsed.content;
          } catch {
            yield data;
          }
        }
      }
    }
  },
  async addFeedback(
    messageId: string,
    feedback: "positive" | "negative",
  ): Promise<void> {
    await api.post(`/api/v1/chat/messages/${messageId}/feedback`, { feedback });
  },
};

export const apiKeyService = {
  async list(): Promise<ApiKey[]> {
    const res = await api.get<ApiKey[]>("/api/v1/api-keys/");
    return res.data;
  },
  async create(name: string): Promise<ApiKey & { key: string }> {
    const res = await api.post<ApiKey & { key: string }>("/api/v1/api-keys/", { name });
    return res.data;
  },
  async revoke(id: string): Promise<void> {
    await api.delete(`/api/v1/api-keys/${id}`);
  },
};

export const adminService = {
  async getStats(): Promise<AdminStats> {
    const res = await api.get<AdminStats>("/api/v1/admin/stats");
    return res.data;
  },
  async listUsers(): Promise<UserAdmin[]> {
    const res = await api.get<UserAdmin[]>("/api/v1/admin/users");
    return res.data;
  },
  async getUser(id: string): Promise<UserAdmin> {
    const res = await api.get<UserAdmin>(`/api/v1/admin/users/${id}`);
    return res.data;
  },
  async updateUserRole(id: string, role: string): Promise<UserAdmin> {
    const res = await api.patch<UserAdmin>(`/api/v1/admin/users/${id}/role`, { role });
    return res.data;
  },
  async toggleUserActive(id: string, active: boolean): Promise<UserAdmin> {
    const res = await api.patch<UserAdmin>(`/api/v1/admin/users/${id}/active`, { is_active: active });
    return res.data;
  },
  async deleteUser(id: string): Promise<void> {
    await api.delete(`/api/v1/admin/users/${id}`);
  },
  async getAuditLogs(params?: { page?: number; page_size?: number; severity?: string }): Promise<PaginatedResponse<AdminAuditLog>> {
    const res = await api.get<PaginatedResponse<AdminAuditLog>>("/api/v1/admin/audit-logs", { params });
    return res.data;
  },
  async getSystemConfig(): Promise<SystemConfig> {
    const res = await api.get<SystemConfig>("/api/v1/admin/config");
    return res.data;
  },
  async updateSystemConfig(config: Partial<SystemConfig>): Promise<SystemConfig> {
    const res = await api.put<SystemConfig>("/api/v1/admin/config", config);
    return res.data;
  },
};

export const securityService = {
  async getStatistics(): Promise<Record<string, unknown>> {
    const res = await api.get("/api/v1/security/statistics");
    return res.data;
  },
  async getAuditLogs(): Promise<SecurityEvent[]> {
    const res = await api.get<SecurityEvent[]>("/api/v1/security/audit-logs");
    return res.data;
  },
  async checkInput(text: string): Promise<{ safe: boolean; issues: string[] }> {
    const res = await api.post("/api/v1/security/check", { text });
    return res.data;
  },
  async scanOutput(text: string): Promise<{ safe: boolean; redacted_text: string; issues: string[] }> {
    const res = await api.post("/api/v1/security/scan-output", { text });
    return res.data;
  },
};

export const healthService = {
  async getHealth(): Promise<HealthResponse> {
    const res = await api.get<HealthResponse>("/api/v1/health");
    return res.data;
  },
  async getDetailedHealth(): Promise<HealthResponse> {
    const res = await api.get<HealthResponse>("/api/v1/health/detailed");
    return res.data;
  },
};

export const guardrailsService = {
  async checkContent(text: string): Promise<{ safe: boolean; categories: Record<string, number>; flagged: string[] }> {
    const res = await api.post("/api/v1/guardrails/check", { text });
    return res.data;
  },
  async getStatistics(): Promise<Record<string, unknown>> {
    const res = await api.get("/api/v1/guardrails/statistics");
    return res.data;
  },
};

export const notificationService = {
  async list(): Promise<NotificationItem[]> {
    const res = await api.get<NotificationItem[]>("/api/v1/notifications");
    return res.data;
  },
  async markRead(id: string): Promise<void> {
    await api.patch(`/api/v1/notifications/${id}/read`);
  },
  async markAllRead(): Promise<void> {
    await api.post("/api/v1/notifications/read-all");
  },
  async dismiss(id: string): Promise<void> {
    await api.delete(`/api/v1/notifications/${id}`);
  },
};

export const monitoringService = {
  async getMetrics(): Promise<MetricsData> {
    const res = await api.get<MetricsData>("/api/v1/monitoring/metrics");
    return res.data;
  },
  async getLatencyMetrics(): Promise<Record<string, unknown>> {
    const res = await api.get("/api/v1/monitoring/metrics/latency");
    return res.data;
  },
  async getBenchmarks(): Promise<Record<string, BenchmarkResult>> {
    const res = await api.get<Record<string, BenchmarkResult>>("/api/v1/monitoring/benchmark");
    return res.data;
  },
  async getDashboard(): Promise<Record<string, unknown>> {
    const res = await api.get("/api/v1/monitoring/dashboard");
    return res.data;
  },
  async evaluateRetrieval(
    retrieved: string[],
    relevant: string[],
    k: number,
  ): Promise<EvaluationResult> {
    const res = await api.post<EvaluationResult>(
      "/api/v1/monitoring/evaluation/retrieval",
      { retrieved, relevant, k },
    );
    return res.data;
  },
};
