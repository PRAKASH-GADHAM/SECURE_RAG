import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";

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

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders login form", () => {
    render(<LoginPage />, { wrapper: Wrapper });
    expect(screen.getByText("Welcome back")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });

  it("shows link to register", () => {
    render(<LoginPage />, { wrapper: Wrapper });
    expect(screen.getByText("Sign up")).toHaveAttribute("href", "/register");
  });

  it("shows link to forgot password", () => {
    render(<LoginPage />, { wrapper: Wrapper });
    expect(screen.getByText("Forgot password?")).toHaveAttribute("href", "/forgot-password");
  });

  it("validates required fields", async () => {
    render(<LoginPage />, { wrapper: Wrapper });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => {
      expect(screen.getByText("Invalid email address")).toBeInTheDocument();
    });
  });
});

describe("RegisterPage", () => {
  it("renders register form", () => {
    render(<RegisterPage />, { wrapper: Wrapper });
    expect(screen.getByText("Create account")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Username")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.getByLabelText("Confirm Password")).toBeInTheDocument();
  });

  it("shows link to login", () => {
    render(<RegisterPage />, { wrapper: Wrapper });
    expect(screen.getByText("Sign in")).toHaveAttribute("href", "/login");
  });
});
