import { test, expect } from "@playwright/test";

test.describe("Authentication", () => {
  test("shows login page", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: /sign in|log in|login/i })).toBeVisible();
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByLabel(/password/i)).toBeVisible();
  });

  test("shows register page", async ({ page }) => {
    await page.goto("/register");
    await expect(page.getByRole("heading", { name: /create account|sign up|register/i })).toBeVisible();
  });

  test("validates empty form submission", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("button", { name: /sign in|log in|login/i }).click();
    await expect(page.getByText(/required|enter/i)).toBeVisible();
  });

  test("validates invalid email format", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel(/email/i).fill("notanemail");
    await page.getByRole("button", { name: /sign in|log in|login/i }).click();
    await expect(page.getByText(/valid email|invalid/i)).toBeVisible();
  });

  test("shows forgot password link", async ({ page }) => {
    await page.goto("/login");
    const link = page.getByRole("link", { name: /forgot|reset/i });
    await expect(link).toBeVisible();
    await link.click();
    await expect(page).toHaveURL(/forgot-password/);
  });

  test("navigates between login and register", async ({ page }) => {
    await page.goto("/login");
    const registerLink = page.getByRole("link", { name: /sign up|create account|register/i });
    await registerLink.click();
    await expect(page).toHaveURL(/register/);
  });
});

test.describe("Protected Routes", () => {
  test("redirects to login when not authenticated", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/login/);
  });

  test("redirects to login for chat when not authenticated", async ({ page }) => {
    await page.goto("/chat");
    await expect(page).toHaveURL(/login/);
  });

  test("redirects to login for documents when not authenticated", async ({ page }) => {
    await page.goto("/documents");
    await expect(page).toHaveURL(/login/);
  });
});
