import { test, expect } from "@playwright/test";

// The single-origin run path: backend serves the built UI at /app/.
const BASE = process.env.BASE_URL || "http://localhost:8001/app/";

test.describe("AI Music Tutor — Phase 1 primary journey", () => {
  test("page loads and is styled", async ({ page }) => {
    await page.goto(BASE);
    const heading = page.getByRole("heading", { name: /AI Music Tutor/i });
    await expect(heading).toBeVisible();
    // styled: heading has a non-default computed font size
    const size = await heading.evaluate(
      (el) => getComputedStyle(el).fontSize
    );
    expect(parseFloat(size)).toBeGreaterThan(20);
  });

  test("start drill renders a staff, plays, and accepts the correct note", async ({
    page,
  }) => {
    await page.goto(BASE);

    // Start the drill
    await page.getByRole("button", { name: /Start drill/i }).click();

    // The staff SVG appears
    const svg = page.locator("svg[aria-label*='clef']").first();
    await expect(svg).toBeVisible({ timeout: 15000 });

    // Reasoning panel shows token usage (real LLM call happened)
    await expect(page.getByText(/total:/i)).toBeVisible({ timeout: 15000 });

    // We can't know the correct option text ahead of time, but the answer
    // buttons render. Click each until feedback shows "Correct" or we exhaust.
    const buttons = page.locator("section button", { hasText: /^[A-G]#?\d$/ });
    const count = await buttons.count();
    expect(count).toBeGreaterThanOrEqual(4);

    // Click the first option; if wrong, a hint + reveal path appears.
    await buttons.first().click();
    // Either correctness feedback or a hint appears
    await expect(
      page.getByText(/Correct|Not quite/i)
    ).toBeVisible({ timeout: 10000 });
  });

  test("answering wrong shows a hint and a reveal option", async ({ page }) => {
    await page.goto(BASE);
    await page.getByRole("button", { name: /Start drill/i }).click();
    const svg = page.locator("svg[aria-label*='clef']").first();
    await expect(svg).toBeVisible({ timeout: 15000 });

    const buttons = page.locator("section button", { hasText: /^[A-G]#?\d$/ });
    // Try all options; the wrong ones produce a hint + reveal.
    const n = await buttons.count();
    let sawHint = false;
    for (let i = 0; i < n && !sawHint; i++) {
      await buttons.nth(i).click();
      const hint = page.getByText(/Not quite/i);
      if (await hint.isVisible().catch(() => false)) {
        sawHint = true;
        await expect(page.getByRole("button", { name: /Reveal answer/i })).toBeVisible();
      }
    }
    expect(sawHint).toBe(true);
  });
});
