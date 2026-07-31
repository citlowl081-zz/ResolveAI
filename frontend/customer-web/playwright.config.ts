import { defineConfig } from "@playwright/test";

const webPort = Number(process.env.PLAYWRIGHT_WEB_PORT || "3000");

export default defineConfig({
  testDir: "./e2e",
  timeout: 30000,
  retries: 1,
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || `http://localhost:${webPort}`,
    headless: true,
    screenshot: "only-on-failure",
  },
  webServer: {
    command: `npm run dev -- -p ${webPort}`,
    port: webPort,
    reuseExistingServer: !process.env.CI,
    timeout: 30000,
  },
});
