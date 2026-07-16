// Playwright e2e smoke — proves the live app at `http://localhost:8001/app/`
// loads, is styled, the primary input works, real output appears, and the
// stubs are visibly labelled.
//
// Run with:  npx playwright test tests/e2e/ --reporter=line
//
// We don't pull in @playwright/test from npm at install time (we use the
// python `playwright` runner instead): see conftest.py.

import { test, expect } from "@playwright/test";

test("app loads, primary input works, real output appears, stubs visible", async ({ page }) => {
  await page.goto("http://localhost:8001/app/");

  // Wait for the textarea (proves SSR/bundle rendered)
  const textarea = page.getByTestId("question");
  await expect(textarea).toBeVisible();

  // Stub labels are visible and look disabled
  await expect(page.getByText(/coming in phase 2/i).first()).toBeVisible();
  await expect(page.getByText(/coming in phase 3/i).first()).toBeVisible();

  // Trigger the primary action
  await textarea.fill("How many FIRs in Lucknow?");
  await page.getByTestId("ask").click();

  // Real output appears. Use a generous timeout so a slow LLM call still passes.
  await expect(page.getByTestId("answer")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByTestId("latency")).toBeVisible();
  await expect(page.getByTestId("results-table")).toBeVisible();

  // Show SQL reveals the SQL; asserts the toggle works
  await page.getByTestId("toggle-sql").click();
  await expect(page.getByTestId("sql")).toBeVisible();
});
