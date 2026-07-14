import { test, expect } from '@playwright/test';

test.describe('NjordDeploy Configurator E2E', () => {
    test.beforeEach(async ({ page }) => {
        // Target the configurator app started on port 5001
        await page.goto('http://127.0.0.1:5001/');
    });

    test('should display Network Discovery page on startup', async ({ page }) => {
        await expect(page.locator('h2')).toHaveText('Network Discovery');
        await expect(page.locator('#autoDetectRadio')).toBeChecked();
        await expect(page.locator('#begin-scan-btn')).toBeVisible();
    });

    test('should show direct IP input when that option is selected', async ({ page }) => {
        const directRadio = page.locator('#method_direct_ip');
        await directRadio.click();

        const container = page.locator('#direct_ip_input_container');
        await expect(container).toBeVisible();
        await expect(container).not.toHaveClass(/d-none/);
        await expect(page.locator('#direct_target_ip')).toBeVisible();
    });

    test('should show manual subnet input when that option is selected', async ({ page }) => {
        const manualRadio = page.locator('#manualScanRadio');
        await manualRadio.click();

        await expect(page.locator('#manualSubnetInput')).toBeEnabled();
    });
});
