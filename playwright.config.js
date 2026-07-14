// playwright.config.js
/* eslint-env node */
/* global require, module, process */
// noinspection NpmUsedModulesInstalled
const { defineConfig, devices } = require('@playwright/test');

/**
 * @see https://playwright.dev/docs/test-configuration
 */
module.exports = defineConfig({
  // Directory where the test files are located.
  testDir: './tests',

  /* Run tests in files in parallel */
  fullyParallel: true,

  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env["CI"],

  /* Retry on CI only */
  retries: process.env["CI"] ? 2 : 0,

  /* Opt out of parallel tests on CI. */
  workers: process.env["CI"] ? 1 : undefined,

  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: 'html',

  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: 'http://127.0.0.1:8080',

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // This starts local web servers before running the tests.
  webServer: [
    {
      command: 'npx http-server . -p 8080 --cors',
      url: 'http://127.0.0.1:8080',
      reuseExistingServer: !process.env["CI"],
      stdout: 'ignore',
      stderr: 'pipe',
    },
    {
      command: 'PYTHONPATH=src python src/configurator_app/app.py',
      url: 'http://127.0.0.1:5001',
      reuseExistingServer: !process.env["CI"],
      stdout: 'ignore',
      stderr: 'pipe',
    }
  ],
});
