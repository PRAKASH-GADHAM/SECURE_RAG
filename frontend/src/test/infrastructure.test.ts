import { describe, it, expect } from "vitest";

describe("Theme Provider", () => {
  it("exports useTheme hook", async () => {
    const { useTheme } = await import("@/lib/theme-provider");
    expect(useTheme).toBeDefined();
  });
});

describe("API Service", () => {
  it("exports api instance", async () => {
    const { api } = await import("@/services/api");
    expect(api).toBeDefined();
    expect(api.defaults.baseURL).toBeDefined();
  });
});

describe("Auth Store", () => {
  it("exports useAuthStore", async () => {
    const { useAuthStore } = await import("@/stores/authStore");
    expect(useAuthStore).toBeDefined();
  });
});

describe("Types", () => {
  it("exports type interfaces", async () => {
    const types = await import("@/types");
    expect(types).toBeDefined();
  });
});
