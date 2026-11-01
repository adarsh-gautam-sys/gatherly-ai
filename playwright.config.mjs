import { defineConfig } from "@playwright/test";

const python =
  process.platform === "win32"
    ? ".venv/Scripts/python.exe"
    : ".venv/bin/python";
export default defineConfig({
  testDir: "tests/browser",
  testMatch: "*.spec.mjs",
  workers: 1,
  timeout: 60000,
  reporter: "list",
  use: { baseURL: "http://127.0.0.1:8123", browserName: "chromium" },
  webServer: {
    command: `"${python}" -m uvicorn gatherly.main:create_app --factory --host 127.0.0.1 --port 8123 --no-access-log --no-proxy-headers`,
    url: "http://127.0.0.1:8123/health",
    reuseExistingServer: false,
    env: {
      GEMINI_API_KEY: "",
      GATHERLY_REQUESTS_PER_MINUTE: "600",
      GATHERLY_ENVIRONMENT: "production",
    },
  },
});
