import { describe, it, expect, beforeEach } from "vitest";
import { useAuthStore } from "@/stores/authStore";

describe("authStore", () => {
  beforeEach(() => {
    localStorage.clear();
    useAuthStore.setState({ user: null, isAuthenticated: false });
  });

  it("starts unauthenticated", () => {
    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.user).toBeNull();
  });

  it("setAuth stores user and tokens", () => {
    const user = { id: "1", email: "test@test.com", username: "test", full_name: "Test", role: "user", is_active: true, is_verified: true, created_at: "", updated_at: "" };
    useAuthStore.getState().setAuth(user, "access-token", "refresh-token");
    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(true);
    expect(state.user?.email).toBe("test@test.com");
    expect(localStorage.getItem("access_token")).toBe("access-token");
  });

  it("logout clears state", () => {
    const user = { id: "1", email: "test@test.com", username: "test", full_name: "Test", role: "user", is_active: true, is_verified: true, created_at: "", updated_at: "" };
    useAuthStore.getState().setAuth(user, "at", "rt");
    useAuthStore.getState().logout();
    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.user).toBeNull();
    expect(localStorage.getItem("access_token")).toBeNull();
  });

  it("updateUser modifies user data", () => {
    const user = { id: "1", email: "test@test.com", username: "test", full_name: "Old Name", role: "user", is_active: true, is_verified: true, created_at: "", updated_at: "" };
    useAuthStore.getState().setAuth(user, "at", "rt");
    useAuthStore.getState().updateUser({ ...user, full_name: "New Name" });
    expect(useAuthStore.getState().user?.full_name).toBe("New Name");
  });
});
