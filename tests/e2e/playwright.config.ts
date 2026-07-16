import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: ".",
  testMatch: "tests/e2e/**/*.spec.ts",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: process.env.CI ? "line" : "list",
  use: {
    baseURL: "http://localhost:8001",
    headless: true,
    trace: "off",
  },
  projects: [
    {
      name: "chromium",
      use: { browserName: "chromium" },
    },
  ],
});
