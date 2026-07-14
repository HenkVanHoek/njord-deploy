import { test, expect } from '@playwright/test';
import {
    MOCK_COMPONENTS_RESPONSE,
    MOCK_JELLYFIN_DETAILS,
    MOCK_TRAEFIK_DETAILS,
    MOCK_TRAEFIK_TEMPLATE,
    MOCK_VALIDATION_FAILURE
} from './fixtures/mock_data.js';

async function loadComponent(page, componentId, details, template) {
    await page.route(`**/api/components/${componentId}`, r => r.fulfill({ status: 200, json: details }));
    await page.route(`**/api/components/${componentId}/template`, r => r.fulfill({ status: 200, body: template }));

    const responsePromise = page.waitForResponse(`**/api/components/${componentId}`);
    await page.locator(`.component-list-item[data-component-id="${componentId}"]`).click();
    await responsePromise;
    await expect(page.locator('#editorTabs button[data-bs-target="#metadata-pane"]')).toBeEnabled();
}

test.describe('NjordDeploy Editor E2E', () => {
    test.beforeEach(async ({ page }) => {
        // Transform the mock components response into the raw dictionary format expected by the API
        const rawComponents = {};
        MOCK_COMPONENTS_RESPONSE.groups.forEach(g => {
            g.components.forEach(c => {
                rawComponents[c.id] = { id: c.id, name: c.name, group: g.id };
            });
        });

        await page.route('**/api/components', r => r.fulfill({ status: 200, json: rawComponents }));
        await page.route('**/api/groups', r => r.fulfill({
            status: 200,
            json: {
                network: { name: 'Network Services', is_exclusive: false },
                media: { name: 'Media Servers', is_exclusive: true }
            }
        }));
        await page.route('**/api/packages', r => r.fulfill({ status: 200, json: {} }));

        await page.goto('/tests/editor_app/playwright/fixtures/editor.html');

        // Wait for the group headers to load and render
        const firstHeader = page.locator('.group-header').first();
        await firstHeader.waitFor({ state: 'visible' });

        // Expand all collapsed sidebar groups to make components visible
        const collapsedCount = await page.locator('.group-header.collapsed').count();
        for (let i = 0; i < collapsedCount; i++) {
            await page.locator('.group-header.collapsed').first().click();
        }

        await expect(page.locator('.component-list-item').first()).toBeVisible();
    });

    test('should load and display the component list on startup', async ({ page }) => {
        await expect(page.getByText('Network Services')).toBeVisible();
        await expect(page.locator('.component-list-item[data-component-id="pi-hole"]')).toBeVisible();
    });

    test('should load component details when a component is clicked', async ({ page }) => {
        await loadComponent(page, 'traefik', MOCK_TRAEFIK_DETAILS, MOCK_TRAEFIK_TEMPLATE);
        await expect(page.locator('#editor-title')).toHaveText('Traefik');
    });

    test('should mark tabs as dirty and manage save button state', async ({ page }) => {
        await loadComponent(page, 'traefik', MOCK_TRAEFIK_DETAILS, MOCK_TRAEFIK_TEMPLATE);
        await page.locator('#comp-name').fill('New Name');
        await expect(page.locator('#save-changes-btn')).toBeEnabled();
    });

    test('should successfully save all changes', async ({ page }) => {
        // THIS LINE CONTAINS THE CORRECTION
        await loadComponent(page, 'traefik', MOCK_TRAEFIK_DETAILS, MOCK_TRAEFIK_TEMPLATE);
        await page.route('**/*', r => r.fulfill({ status: 200, json: { message: 'Success' } }));
        const finalResponse = page.waitForResponse('**/api/components');
        await page.locator('#comp-name').fill('Updated Name');
        await page.locator('#save-changes-btn').click();
        await finalResponse;
        await expect(page.getByText('All changes saved successfully!')).toBeVisible();
    });

    test('should stop save if conflict gatekeeper fails', async ({ page }) => {
        await loadComponent(page, 'traefik', MOCK_TRAEFIK_DETAILS, MOCK_TRAEFIK_TEMPLATE);
        await page.route('**/validate_metadata_conflicts', r => r.fulfill({ status: 400, json: MOCK_VALIDATION_FAILURE }));
        await page.locator('#comp-conflicts').fill('traefik');
        await page.locator('#save-changes-btn').click();
        await expect(page.getByText(/Conflict Validation Failed/)).toBeVisible();
    });

    test('should handle unsaved changes when switching tabs', async ({ page }) => {
        await loadComponent(page, 'traefik', MOCK_TRAEFIK_DETAILS, MOCK_TRAEFIK_TEMPLATE);
        await page.locator('#comp-name').fill('A Dirty Name');
        await page.locator('button[data-bs-target="#variables-pane"]').click();
        await expect(page.locator('#unsavedChangesModal')).toBeVisible();
    });

    test('should toggle dependent variable visibility', async ({ page }) => {
        await loadComponent(page, 'jellyfin', MOCK_JELLYFIN_DETAILS, '');
        await page.locator('button[data-bs-target="#variables-pane"]').click();
        const controller = page.locator('.card[data-variable-id="JELLYFIN_MEDIA_LOCATION"] [data-field="default"]');
        const dependent = page.locator('.card[data-variable-id="JELLYFIN_NAS_PATH"]');
        await expect(dependent).toBeVisible();
        await controller.selectOption('usb');
        await expect(dependent).toBeHidden();
    });
});
