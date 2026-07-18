import { test, expect } from "@playwright/test";

test.describe("Navigation", () => {
  test("landing page redirects", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/login|dashboard/);
  });

  test("sidebar shows all navigation items", async ({ page }) => {
    await page.goto("/login");
    const sidebar = page.locator("nav");
    await expect(sidebar.getByText(/dashboard/i)).toBeVisible();
    await expect(sidebar.getByText(/chat/i)).toBeVisible();
    await expect(sidebar.getByText(/documents/i)).toBeVisible();
    await expect(sidebar.getByText(/history/i)).toBeVisible();
    await expect(sidebar.getByText(/settings/i)).toBeVisible();
  });

  test("404 redirects to dashboard", async ({ page }) => {
    await page.goto("/nonexistent-page-12345");
    await expect(page).toHaveURL(/login|dashboard/);
  });
});

test.describe("Responsive Design", () => {
  test("mobile viewport shows hamburger menu", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto("/login");
    const hamburger = page.getByRole("button", { name: /menu/i });
    await expect(hamburger).toBeVisible();
  });

  test("desktop viewport shows full sidebar", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto("/login");
    const sidebar = page.locator("nav");
    await expect(sidebar).toBeVisible();
  });
});
