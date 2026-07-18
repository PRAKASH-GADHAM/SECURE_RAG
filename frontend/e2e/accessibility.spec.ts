import { test, expect } from "@playwright/test";

test.describe("Accessibility", () => {
  test("login page has proper headings", async ({ page }) => {
    await page.goto("/login");
    const h1 = page.locator("h1, h2").first();
    await expect(h1).toBeVisible();
  });

  test("all form inputs have labels", async ({ page }) => {
    await page.goto("/login");
    const inputs = page.locator("input:not([type='hidden'])");
    const count = await inputs.count();
    for (let i = 0; i < count; i++) {
      const input = inputs.nth(i);
      const id = await input.getAttribute("id");
      const ariaLabel = await input.getAttribute("aria-label");
      const placeholder = await input.getAttribute("placeholder");
      const hasLabel = id ? await page.locator(`label[for="${id}"]`).count() > 0 : false;
      expect(hasLabel || !!ariaLabel || !!placeholder).toBeTruthy();
    }
  });

  test("skip to main content link exists", async ({ page }) => {
    await page.goto("/login");
    const skipLink = page.locator('a[href="#main-content"]');
    await expect(skipLink).toHaveCount(1);
  });

  test("interactive elements are keyboard accessible", async ({ page }) => {
    await page.goto("/login");
    await page.keyboard.press("Tab");
    const focused = page.locator(":focus");
    await expect(focused).toBeVisible();
  });

  test("pages have lang attribute", async ({ page }) => {
    await page.goto("/login");
    const html = page.locator("html");
    await expect(html).toHaveAttribute("lang", /[a-z]{2}/);
  });
});
