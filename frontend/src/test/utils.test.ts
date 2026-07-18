import { describe, it, expect } from "vitest";

describe("formatFileSize", () => {
  function formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  it("formats bytes", () => expect(formatFileSize(500)).toBe("500 B"));
  it("formats KB", () => expect(formatFileSize(1536)).toBe("1.5 KB"));
  it("formats MB", () => expect(formatFileSize(1048576)).toBe("1.0 MB"));
});

describe("cn utility", () => {
  it("merges class names", async () => {
    const { cn } = await import("@/lib/utils");
    const result = cn("base", "extra");
    expect(result).toContain("base");
    expect(result).toContain("extra");
  });

  it("handles conditional classes", async () => {
    const { cn } = await import("@/lib/utils");
    const showHidden = false;
    const result = cn("base", showHidden && "hidden", "visible");
    expect(result).not.toContain("hidden");
    expect(result).toContain("visible");
  });
});

describe("validateEmail", () => {
  function validateEmail(email: string): boolean {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  }

  it("accepts valid email", () => expect(validateEmail("user@example.com")).toBe(true));
  it("rejects invalid email", () => expect(validateEmail("notanemail")).toBe(false));
  it("rejects empty string", () => expect(validateEmail("")).toBe(false));
});
