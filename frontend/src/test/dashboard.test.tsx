import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import DashboardPage from "@/pages/DashboardPage";

vi.mock("@/services", () => ({
  documentService: { list: vi.fn().mockResolvedValue([]) },
  chatService: { listSessions: vi.fn().mockResolvedValue([]) },
  monitoringService: { getMetrics: vi.fn().mockResolvedValue({ cache_hit_ratio: 0, counters: {}, latency: {} }) },
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  );
}

describe("DashboardPage", () => {
  it("renders dashboard title", () => {
    render(<DashboardPage />, { wrapper: Wrapper });
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
  });

  it("renders stat cards", () => {
    render(<DashboardPage />, { wrapper: Wrapper });
    expect(screen.getByText("Documents")).toBeInTheDocument();
    expect(screen.getByText("Chat Sessions")).toBeInTheDocument();
    expect(screen.getByText("Avg Latency")).toBeInTheDocument();
    expect(screen.getByText("Cache Hit")).toBeInTheDocument();
  });

  it("renders chart sections", () => {
    render(<DashboardPage />, { wrapper: Wrapper });
    expect(screen.getByText("Latency Over Time")).toBeInTheDocument();
    expect(screen.getByText("Token Usage")).toBeInTheDocument();
  });

  it("renders recent chats section", () => {
    render(<DashboardPage />, { wrapper: Wrapper });
    expect(screen.getByText("Recent Chats")).toBeInTheDocument();
  });
});
