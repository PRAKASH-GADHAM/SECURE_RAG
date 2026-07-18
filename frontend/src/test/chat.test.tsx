import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ChatPage from "@/pages/ChatPage";

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

describe("ChatPage", () => {
  it("renders chat interface", () => {
    render(<ChatPage />, { wrapper: Wrapper });
    expect(screen.getByText("Chat")).toBeInTheDocument();
    expect(screen.getByText("Ask anything")).toBeInTheDocument();
  });

  it("renders input field", () => {
    render(<ChatPage />, { wrapper: Wrapper });
    expect(screen.getByPlaceholderText("Ask a question about your documents...")).toBeInTheDocument();
  });

  it("renders disclaimer", () => {
    render(<ChatPage />, { wrapper: Wrapper });
    expect(screen.getByText(/SecureRAG uses AI/)).toBeInTheDocument();
  });
});
