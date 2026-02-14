import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  fullyParallel: false,
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://127.0.0.1:19006',
    headless: true,
  },
  webServer: {
    command: 'cd mobile && CI=1 npx expo start --web --port 19006',
    url: 'http://127.0.0.1:19006',
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
