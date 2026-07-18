import { describe, it, expectTypeOf } from "vitest";
import type {
  User, Document, ChatMessage, HealthResponse, PaginatedResponse,
} from "@/types";

describe("TypeScript types", () => {
  it("User has required fields", () => {
    expectTypeOf<User>().toHaveProperty("id");
    expectTypeOf<User>().toHaveProperty("email");
    expectTypeOf<User>().toHaveProperty("role");
  });

  it("Document has status field", () => {
    expectTypeOf<Document["status"]>().toMatchTypeOf<"pending" | "processing" | "completed" | "failed">();
  });

  it("ChatMessage has role field", () => {
    expectTypeOf<ChatMessage["role"]>().toMatchTypeOf<"user" | "assistant" | "system">();
  });

  it("PaginatedResponse is generic", () => {
    expectTypeOf<PaginatedResponse<User>>().toHaveProperty("items");
    expectTypeOf<PaginatedResponse<User>>().toHaveProperty("total");
  });

  it("HealthResponse has services", () => {
    expectTypeOf<HealthResponse>().toHaveProperty("services");
    expectTypeOf<HealthResponse>().toHaveProperty("status");
  });
});
