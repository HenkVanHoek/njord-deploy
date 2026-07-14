import { test, expect } from '@playwright/test';
import { MOCK_COMPONENTS_RESPONSE, MOCK_JELLYFIN_DETAILS } from './fixtures/mock_data.js';

test.describe('UI Render Utils', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/');
        await page.setContent(`
            <h2 id="editor-title"></h2>
            <div id="metadata-pane"></div>
            <div id="variables-pane"></div>
            <button id="save-changes-btn"></button>
            <button id="delete-component-btn"></button>
        `);
    });

    test.describe('renderEditor()', () => {
        test('should render basic metadata fields correctly', async ({ page }) => {
            await page.evaluate(async ({ details, componentData }) => {
                const { renderEditor } = await import('./src/editor_app/static/ui_render_utils.js');
                renderEditor(details, componentData, () => {});
            }, { details: { ...MOCK_JELLYFIN_DETAILS, id: 'jellyfin' }, componentData: MOCK_COMPONENTS_RESPONSE });
            await expect(page.locator('#comp-name')).toHaveValue('Jellyfin');
        });

        test('should render checkboxes with correct states', async ({ page }) => {
            await page.evaluate(async ({ details, componentData }) => {
                const { renderEditor } = await import('./src/editor_app/static/ui_render_utils.js');
                renderEditor(details, componentData, () => {});
            }, { details: { id: 'jellyfin', has_ui: true, has_configuration: false }, componentData: MOCK_COMPONENTS_RESPONSE });
            await expect(page.locator('#comp-has-ui')).toBeChecked();
            await expect(page.locator('#comp-has-config')).not.toBeChecked();
        });

        test('should render UI Port Variable field', async ({ page }) => {
            await page.evaluate(async ({ details, componentData }) => {
                const { renderEditor } = await import('./src/editor_app/static/ui_render_utils.js');
                renderEditor(details, componentData, () => {});
            }, { details: { id: 'jellyfin', ui_port_variable: 'JELLYFIN_WEB_PORT' }, componentData: MOCK_COMPONENTS_RESPONSE });

            await expect(page.locator('#comp-ui-port-variable')).toHaveValue('JELLYFIN_WEB_PORT');
        });

        test('should show traefik port when support is enabled', async ({ page }) => {
            await page.evaluate(async ({ details, componentData }) => {
                const { renderEditor } = await import('./src/editor_app/static/ui_render_utils.js');
                renderEditor(details, componentData, () => {});
            }, { details: { id: 'jellyfin', has_traefik_support: true }, componentData: MOCK_COMPONENTS_RESPONSE });
            await expect(page.locator('#traefik-port-wrapper')).toBeVisible();
        });
    });

    test.describe('renderVariablesPane()', () => {
        test('should render all variable cards correctly', async ({ page }) => {
            const { required_variables: variables } = MOCK_JELLYFIN_DETAILS;
            await page.evaluate(async (variables) => {
                const { renderVariablesPane } = await import('./src/editor_app/static/ui_render_utils.js');
                renderVariablesPane({ variables, renderAllRowsCallback: () => {} });
            }, variables);
            await expect(page.locator('#variables-list .card')).toHaveCount(3);
        });

        test('should render a "choice" variable as a select dropdown', async ({ page }) => {
            const { required_variables: variables } = MOCK_JELLYFIN_DETAILS;
            await page.evaluate(async (variables) => {
                const { renderVariablesPane } = await import('./src/editor_app/static/ui_render_utils.js');
                renderVariablesPane({ variables, renderAllRowsCallback: () => {} });
            }, variables);
            const defaultField = page.locator('.card[data-variable-id="JELLYFIN_MEDIA_LOCATION"] [data-field="default"]');
            await expect(defaultField).toHaveValue('nas');
        });
    });
});
