import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import AdminPage from "@/pages/AdminPage";

vi.mock("@/services", () => ({
  monitoringService: {
    getMetrics: vi.fn().mockResolvedValue({
      cache_hit_ratio: 0.85,
      counters: { requests: 4280, errors: 23 },
      latency: {},
    }),
    getBenchmarks: vi.fn().mockResolvedValue({}),
    getLatencyMetrics: vi.fn().mockResolvedValue({}),
  },
  adminService: {
    getStats: vi.fn().mockResolvedValue({
      total_users: 15,
      active_users: 12,
      total_documents: 48,
      total_chats: 203,
    }),
    listUsers: vi.fn().mockResolvedValue([]),
    getAuditLogs: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, total_pages: 0 }),
    getSystemConfig: vi.fn().mockResolvedValue({}),
  },
  securityService: {
    getAuditLogs: vi.fn().mockResolvedValue([]),
    getStatistics: vi.fn().mockResolvedValue({ total_events: 10, blocked: 3 }),
  },
  healthService: {
    getDetailedHealth: vi.fn().mockResolvedValue({ status: "healthy", services: {} }),
    getHealth: vi.fn().mockResolvedValue({ status: "healthy" }),
  },
  guardrailsService: {
    getStatistics: vi.fn().mockResolvedValue({}),
  },
}));

vi.mock("@/hooks/use-toast", () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

vi.mock("@/hooks", async (importOriginal) => {
  const orig = await importOriginal<typeof import("@/hooks")>();
  return { ...orig, useNotifications: () => ({ notifications: [], unreadCount: 0, isLoading: false, markRead: vi.fn(), markAllRead: vi.fn(), dismiss: vi.fn() }) };
});

function createQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={createQueryClient()}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  );
}

describe("AdminPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders admin page with tabs", async () => {
    render(<AdminPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByText("Admin Portal")).toBeInTheDocument();
    });
    expect(screen.getByText("System management and monitoring")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /overview/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /metrics/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /security/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /users/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /infrastructure/i })).toBeInTheDocument();
  });

  it("metrics tab shows stats cards", async () => {
    render(<AdminPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByText("Total Users")).toBeInTheDocument();
    });

    expect(screen.getByText("Documents")).toBeInTheDocument();
    expect(screen.getByText("System Health")).toBeInTheDocument();
  });

  it("security tab renders", async () => {
    const user = userEvent.setup();
    render(<AdminPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByText("Total Users")).toBeInTheDocument();
    });

    const securityTab = screen.getByRole("tab", { name: /security/i });
    await user.click(securityTab);

    await waitFor(() => {
      expect(screen.getByText("Security Events by Severity")).toBeInTheDocument();
    });
    expect(screen.getByText("Total Events")).toBeInTheDocument();
  });

  it("users tab renders", async () => {
    const user = userEvent.setup();
    render(<AdminPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByText("Total Users")).toBeInTheDocument();
    });

    const usersTab = screen.getByRole("tab", { name: /users/i });
    await user.click(usersTab);

    await waitFor(() => {
      expect(screen.getByText("User Management")).toBeInTheDocument();
    });
    expect(screen.getByPlaceholderText("Search users...")).toBeInTheDocument();
  });

  it("infrastructure tab renders", async () => {
    const user = userEvent.setup();
    render(<AdminPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByText("Total Users")).toBeInTheDocument();
    });

    const infraTab = screen.getByRole("tab", { name: /infrastructure/i });
    await user.click(infraTab);

    await waitFor(() => {
      expect(screen.getByText("Infrastructure")).toBeInTheDocument();
    });
  });

  it("shows loading skeletons while data loads", async () => {
    const { adminService, monitoringService } = await import("@/services");
    vi.mocked(adminService.getStats).mockReturnValue(new Promise(() => {}));
    vi.mocked(adminService.listUsers).mockReturnValue(new Promise(() => {}));
    vi.mocked(adminService.getAuditLogs).mockReturnValue(new Promise(() => {}));
    vi.mocked(monitoringService.getMetrics).mockReturnValue(new Promise(() => {}));

    render(<AdminPage />, { wrapper: Wrapper });

    await waitFor(() => {
      const skeletons = document.querySelectorAll(".animate-pulse");
      expect(skeletons.length).toBeGreaterThan(0);
    });
  });
});
