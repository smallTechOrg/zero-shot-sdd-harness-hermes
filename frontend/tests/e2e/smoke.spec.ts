import { test, expect } from "@playwright/test";

test("dashboard loads, shows funnel + KPIs, and refreshes", async ({ page }) => {
  const errors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });
  page.on("pageerror", (err) => errors.push(err.message));

  await page.goto("/app/");
  await page.waitForLoadState("networkidle");

  // Styled: heading is present and the funnel section rendered
  await expect(page.getByRole("heading", { name: "#local Analytics" })).toBeVisible();
  await expect(page.getByText("Acquisition + Retention Funnel")).toBeVisible();

  // Primary output: funnel stages render with counts
  await expect(page.getByText("Visit / Install")).toBeVisible();
  await expect(
    page.locator("div.text-sm span").filter({ hasText: "Revenue" }).first()
  ).toBeVisible();

  // KPI tiles
  await expect(page.getByText("Signups").first()).toBeVisible();
  await expect(page.getByText("Retention").first()).toBeVisible();

  // Connectors panel + a setup affordance
  await expect(page.getByText("Connectors")).toBeVisible();
  await expect(page.getByText("NOT CONFIGURED").first()).toBeVisible();

  // Refresh updates without errors
  await page.getByRole("button", { name: "Refresh" }).click();
  await page.waitForLoadState("networkidle");

  // No console errors on the tested path
  expect(errors, `console errors: ${errors.join(" | ")}`).toHaveLength(0);
});
