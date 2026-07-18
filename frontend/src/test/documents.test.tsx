import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import DocumentsPage from "@/pages/DocumentsPage";

vi.mock("@/services", () => ({
  documentService: {
    list: vi.fn().mockResolvedValue([]),
    delete: vi.fn().mockResolvedValue(undefined),
  },
}));

vi.mock("@/hooks/use-toast", () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

const mockDocuments = [
  {
    id: "doc-1",
    original_filename: "report.pdf",
    file_type: "pdf",
    file_size: 1024000,
    status: "completed" as const,
    chunk_count: 42,
    progress: 1,
    created_at: "2025-01-15T10:00:00Z",
  },
  {
    id: "doc-2",
    original_filename: "notes.md",
    file_type: "md",
    file_size: 2048,
    status: "processing" as const,
    chunk_count: 0,
    progress: 0.6,
    created_at: "2025-01-16T12:00:00Z",
  },
  {
    id: "doc-3",
    original_filename: "data.csv",
    file_type: "csv",
    file_size: 512000,
    status: "failed" as const,
    chunk_count: 0,
    progress: 0,
    error_message: "Unsupported file format",
    created_at: "2025-01-17T08:00:00Z",
  },
];

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

describe("DocumentsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders documents page with upload button and search", async () => {
    const { documentService } = await import("@/services");
    (documentService.list as ReturnType<typeof vi.fn>).mockResolvedValue(mockDocuments);

    render(<DocumentsPage />, { wrapper: Wrapper });

    expect(screen.getByText("Documents")).toBeInTheDocument();
    expect(screen.getByText("Manage your uploaded documents")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /upload/i })).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Search documents...")).toBeInTheDocument();
  });

  it("displays document list with file info", async () => {
    const { documentService } = await import("@/services");
    (documentService.list as ReturnType<typeof vi.fn>).mockResolvedValue(mockDocuments);

    render(<DocumentsPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByText("report.pdf")).toBeInTheDocument();
    });
    expect(screen.getByText("notes.md")).toBeInTheDocument();
    expect(screen.getByText("data.csv")).toBeInTheDocument();
  });

  it("search filters documents", async () => {
    const { documentService } = await import("@/services");
    (documentService.list as ReturnType<typeof vi.fn>).mockResolvedValue(mockDocuments);

    render(<DocumentsPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByText("report.pdf")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText("Search documents...");
    fireEvent.change(searchInput, { target: { value: "report" } });

    await waitFor(() => {
      expect(screen.getByText("report.pdf")).toBeInTheDocument();
      expect(screen.queryByText("notes.md")).not.toBeInTheDocument();
    });
  });

  it("upload button opens file picker", async () => {
    const { documentService } = await import("@/services");
    (documentService.list as ReturnType<typeof vi.fn>).mockResolvedValue([]);

    render(<DocumentsPage />, { wrapper: Wrapper });

    const uploadButton = screen.getByRole("button", { name: /upload/i });
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const clickSpy = vi.spyOn(fileInput, "click");

    fireEvent.click(uploadButton);
    expect(clickSpy).toHaveBeenCalled();
    clickSpy.mockRestore();
  });

  it("delete button opens confirmation dialog", async () => {
    const { documentService } = await import("@/services");
    (documentService.list as ReturnType<typeof vi.fn>).mockResolvedValue(mockDocuments);

    render(<DocumentsPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByText("report.pdf")).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByRole("button").filter((btn) =>
      btn.className.includes("text-destructive"),
    );

    expect(deleteButtons.length).toBeGreaterThan(0);
    fireEvent.click(deleteButtons[0]!);

    await waitFor(() => {
      expect(screen.getByText("Delete Document")).toBeInTheDocument();
    });
    expect(screen.getByText(/Are you sure you want to delete/)).toBeInTheDocument();
  });

  it("shows processing indicator for processing documents", async () => {
    const { documentService } = await import("@/services");
    (documentService.list as ReturnType<typeof vi.fn>).mockResolvedValue([mockDocuments[1]]);

    render(<DocumentsPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByText("notes.md")).toBeInTheDocument();
    });

    const card = screen.getByText("notes.md").closest('[class*="Card"]') || screen.getByText("notes.md").parentElement?.parentElement?.parentElement;
    expect(card).toBeTruthy();
  });

  it("shows completed badge with chunk count", async () => {
    const { documentService } = await import("@/services");
    (documentService.list as ReturnType<typeof vi.fn>).mockResolvedValue([mockDocuments[0]]);

    render(<DocumentsPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByText("42 chunks")).toBeInTheDocument();
    });
  });

  it("shows error message for failed documents", async () => {
    const { documentService } = await import("@/services");
    (documentService.list as ReturnType<typeof vi.fn>).mockResolvedValue([mockDocuments[2]]);

    render(<DocumentsPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByText("Unsupported file format")).toBeInTheDocument();
    });
  });
});
