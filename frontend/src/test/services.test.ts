import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/services/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
    patch: vi.fn(),
    put: vi.fn(),
  },
}));

import { documentService, chatService, apiKeyService, healthService, notificationService } from "@/services";
import { api } from "@/services/api";

describe("documentService", () => {
  beforeEach(() => vi.clearAllMocks());

  it("list calls GET /api/v1/documents/", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [] });
    const result = await documentService.list();
    expect(api.get).toHaveBeenCalledWith("/api/v1/documents/");
    expect(result).toEqual([]);
  });

  it("delete calls DELETE endpoint", async () => {
    vi.mocked(api.delete).mockResolvedValue({ data: undefined });
    await documentService.delete("doc-1");
    expect(api.delete).toHaveBeenCalledWith("/api/v1/documents/doc-1");
  });

  it("getStatus calls correct endpoint", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { status: "completed" } });
    await documentService.getStatus("doc-1");
    expect(api.get).toHaveBeenCalledWith("/api/v1/documents/doc-1/status");
  });
});

describe("chatService", () => {
  beforeEach(() => vi.clearAllMocks());

  it("listSessions calls GET /api/v1/chat/sessions", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [] });
    await chatService.listSessions();
    expect(api.get).toHaveBeenCalledWith("/api/v1/chat/sessions");
  });

  it("createSession POSTs with title", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: { id: "s1", title: "test" } });
    await chatService.createSession("test");
    expect(api.post).toHaveBeenCalledWith("/api/v1/chat/sessions", { title: "test" });
  });

  it("deleteSession calls DELETE", async () => {
    vi.mocked(api.delete).mockResolvedValue({ data: undefined });
    await chatService.deleteSession("s1");
    expect(api.delete).toHaveBeenCalledWith("/api/v1/chat/sessions/s1");
  });

  it("renameSession calls PATCH", async () => {
    vi.mocked(api.patch).mockResolvedValue({ data: { id: "s1", title: "new" } });
    await chatService.renameSession("s1", "new");
    expect(api.patch).toHaveBeenCalledWith("/api/v1/chat/sessions/s1", { title: "new" });
  });

  it("addFeedback POSTs feedback", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: undefined });
    await chatService.addFeedback("msg1", "positive");
    expect(api.post).toHaveBeenCalledWith("/api/v1/chat/messages/msg1/feedback", { feedback: "positive" });
  });
});

describe("apiKeyService", () => {
  beforeEach(() => vi.clearAllMocks());

  it("list calls GET", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [] });
    await apiKeyService.list();
    expect(api.get).toHaveBeenCalledWith("/api/v1/api-keys/");
  });

  it("create POSTs name", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: { id: "k1", name: "test", key: "sk-xxx" } });
    await apiKeyService.create("test");
    expect(api.post).toHaveBeenCalledWith("/api/v1/api-keys/", { name: "test" });
  });

  it("revoke calls DELETE", async () => {
    vi.mocked(api.delete).mockResolvedValue({ data: undefined });
    await apiKeyService.revoke("k1");
    expect(api.delete).toHaveBeenCalledWith("/api/v1/api-keys/k1");
  });
});

describe("healthService", () => {
  beforeEach(() => vi.clearAllMocks());

  it("getHealth calls GET", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { status: "healthy" } });
    await healthService.getHealth();
    expect(api.get).toHaveBeenCalledWith("/api/v1/health");
  });

  it("getDetailedHealth calls correct endpoint", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { status: "healthy" } });
    await healthService.getDetailedHealth();
    expect(api.get).toHaveBeenCalledWith("/api/v1/health/detailed");
  });
});

describe("notificationService", () => {
  beforeEach(() => vi.clearAllMocks());

  it("list calls GET", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [] });
    await notificationService.list();
    expect(api.get).toHaveBeenCalledWith("/api/v1/notifications");
  });

  it("markRead calls PATCH", async () => {
    vi.mocked(api.patch).mockResolvedValue({ data: undefined });
    await notificationService.markRead("n1");
    expect(api.patch).toHaveBeenCalledWith("/api/v1/notifications/n1/read");
  });

  it("markAllRead calls POST", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: undefined });
    await notificationService.markAllRead();
    expect(api.post).toHaveBeenCalledWith("/api/v1/notifications/read-all");
  });
});
