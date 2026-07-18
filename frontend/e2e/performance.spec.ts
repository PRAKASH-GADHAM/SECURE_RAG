import { test, expect } from "@playwright/test";

test.describe("Performance", () => {
  test("login page loads within 3 seconds", async ({ page }) => {
    const start = Date.now();
    await page.goto("/login", { waitUntil: "networkidle" });
    const loadTime = Date.now() - start;
    expect(loadTime).toBeLessThan(3000);
  });

  test("no console errors on login page", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });
    await page.goto("/login");
    await page.waitForTimeout(1000);
    const criticalErrors = errors.filter(
      (e) => !e.includes("favicon") && !e.includes("404") && !e.includes("net::"),
    );
    expect(criticalErrors).toHaveLength(0);
  });

  test("static assets are cached", async ({ page }) => {
    const responses: { url: string; status: number; headers: Record<string, string> }[] = [];
    page.on("response", (res) => {
      responses.push({
        url: res.url(),
        status: res.status(),
        headers: res.headers(),
      });
    });
    await page.goto("/login");
    await page.waitForTimeout(1000);
    const jsResponses = responses.filter((r) => r.url.endsWith(".js"));
    for (const res of jsResponses) {
      if (res.headers["cache-control"]) {
        expect(res.headers["cache-control"]).toContain("public");
      }
    }
  });

  test("no layout shift on page load", async ({ page }) => {
    await page.goto("/login");
    await page.waitForLoadState("networkidle");
    const cls = await page.evaluate(() => {
      return new Promise<number>((resolve) => {
        let clsValue = 0;
        const observer = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if ((entry as any).hadRecentInput) continue;
            clsValue += (entry as any).value;
          }
        });
        observer.observe({ type: "layout-shift", buffered: true });
        setTimeout(() => {
          observer.disconnect();
          resolve(clsValue);
        }, 1000);
      });
    });
    expect(cls).toBeLessThan(0.1);
  });
});
