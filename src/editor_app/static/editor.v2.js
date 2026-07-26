// src/editor_app/static/editor.v2.js

/* noinspection JSUnusedGlobalSymbols,JSUnresolvedFunction,JSCheckFunctionSignatures */

import { renderEditor, renderVariablesPane } from './ui_render_utils.js';

document.addEventListener('DOMContentLoaded', () => {
    const componentList = document.getElementById('component-list');
    const editorPane = document.getElementById('editor-pane');
    const placeholder = document.getElementById('placeholder-text');
    const editorContent = document.getElementById('editor-content');
    const saveChangesBtn = document.getElementById('save-changes-btn');
    const discardChangesBtn = document.getElementById('discard-changes-btn');
    const editorTabs = document.querySelectorAll(
        '#editorTabs button[data-bs-toggle="tab"]'
    );

    let codeEditor = null;
    let currentVariables = [];
    let internalRenderVariablesRows = null;

    /**
     * @typedef {object} ComponentSummary
     * @property {string} id
     * @property {string} name
     */
    /**
     * @typedef {object} Group
     * @property {string} id
     * @property {string} name
     * @property {boolean} is_exclusive
     * @property {ComponentSummary[]} components
     */
    /**
     * @typedef {object} PackageDetails
     * @property {string} id
     * @property {string} name
     * @property {string} [description]
     */
    /**
     * @typedef {object} ComponentData
     * @property {Group[]} groups
     * @property {Object.<string, PackageDetails>} packages
     */
    /** @type {ComponentData | null} */
    let componentData = null;

    /**
     * @typedef {object} ComponentVariable
     * @property {string} id
     * @property {string} [label]
     * @property {string} description
     * @property {string} type
     * @property {string} [default]
     * @property {'always'|'clean-install'|''} [required]
     * @property {'dotenv'} [source]
     */

    /** @type {Set<string>} */
    const dirtyTabs = new Set();
    let nextTabTarget = null;

    const unsavedChangesModalEl = document.getElementById('unsavedChangesModal');
    const unsavedChangesModal = unsavedChangesModalEl
        ? new bootstrap.Modal(
            /** @type {HTMLElement} */ (unsavedChangesModalEl)
          )
        : null;

    const updateUiForDirtyState = () => {
        const isDirty = dirtyTabs.size > 0;
        if (saveChangesBtn) saveChangesBtn.disabled = !isDirty;
        if (discardChangesBtn) {
            if (isDirty) {
                discardChangesBtn.classList.remove('d-none');
            } else {
                discardChangesBtn.classList.add('d-none');
            }
        }
        editorTabs.forEach(tabButton => {
            const paneId = tabButton.getAttribute('data-bs-target').substring(1);
            if (dirtyTabs.has(paneId)) {
                tabButton.classList.add('tab-dirty');
            } else {
                tabButton.classList.remove('tab-dirty');
            }
        });
    };

    const markTabAsDirty = (paneId) => {
        dirtyTabs.add(paneId);
        updateUiForDirtyState();
    };

    const clearAllDirtyState = () => {
        dirtyTabs.clear();
        updateUiForDirtyState();
    };

    const collectVariablesFromDOM = () => {
        const newVariables = [];
        const rows = document.querySelectorAll('#variables-list .card');
        rows.forEach(row => {
            const idEl = row.querySelector('[data-field="id"]');
            const labelEl = row.querySelector('[data-field="label"]');
            const descEl = row.querySelector('[data-field="description"]');
            const typeEl = row.querySelector('[data-field="type"]');
            const sourceEl = row.querySelector('[data-field="source"]');
            const defaultEl = row.querySelector('[data-field="default"]');
            const requiredEl = row.querySelector('[data-field="required"]');

            if (idEl && idEl.value) {
                newVariables.push({
                    id: idEl.value,
                    label: labelEl ? labelEl.value : '',
                    description: descEl ? descEl.value : '',
                    type: typeEl ? typeEl.value : 'text',
                    source: sourceEl ? sourceEl.value : '',
                    default: defaultEl ? defaultEl.value : '',
                    required: requiredEl ? requiredEl.value : ''
                });
            }
        });
        return newVariables;
    };

    // --- Utility Functions ---

    async function fetchJson(url, options = {}) {
        const response = await fetch(url, options);
        if (!response.ok) {
            let errorMsg = `Request failed with status ${response.status}`;
            try {
                const errorData = await response.json();
                errorMsg = errorData.error || errorMsg;
            } catch (e) {
                // Ignore non-JSON errors
            }
            throw new Error(errorMsg);
        }
        return response.json();
    }

    async function fetchText(url, options = {}) {
        const response = await fetch(url, options);
        if (!response.ok) {
            throw new Error(`Request failed with status ${response.status}`);
        }
        return response.text();
    }

    // Mitigation for DOM text reinterpreted as HTML (DOM-XSS)
    const showAlert = (message, type = 'success') => {
        let alertEl = document.getElementById('feedback-alert');
        if (!alertEl) {
            alertEl = document.createElement('div');
            alertEl.id = 'feedback-alert';
            alertEl.setAttribute('role', 'alert');
            const mainContainer = document.querySelector('.main-container');
            if (mainContainer) {
                document.body.insertBefore(alertEl, mainContainer);
            } else {
                document.body.appendChild(alertEl);
            }
        }
        alertEl.className = `alert alert-${type} alert-dismissible fade show`;
        alertEl.textContent = message;

        const closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'btn-close';
        closeBtn.setAttribute('data-bs-dismiss', 'alert');
        closeBtn.setAttribute('aria-label', 'Close');
        alertEl.appendChild(closeBtn);

        setTimeout(() => {
            const currentAlert = document.getElementById('feedback-alert');
            if (currentAlert && currentAlert === alertEl) {
                const alertInstance = bootstrap.Alert.getOrCreateInstance(currentAlert);
                if (alertInstance) alertInstance.close();
            }
        }, 5000);
    };

    const refreshSyncStatusBadge = async () => {
        try {
            const statusData = await fetchJson("/api/sync/status");
            const badge = document.getElementById("git-sync-badge");
            if (badge) {
                if (statusData.global_metadata_out_of_sync) {
                    badge.classList.remove("d-none");
                } else {
                    badge.classList.add("d-none");
                }
            }
            const globalAlert = document.getElementById("git-global-warning-alert");
            if (globalAlert) {
                if (statusData.global_metadata_out_of_sync) {
                    globalAlert.classList.remove("d-none");
                } else {
                    globalAlert.classList.add("d-none");
                }
            }
        } catch (err) {
            console.error("Failed to refresh sync status badge:", err);
        }
    };

    // --- Save Handlers ---

    const saveMetadata = async (componentId) => {
        const portInput = document.getElementById('comp-traefik-port');
        const uiPortInput = document.getElementById('comp-ui-port-variable');

        const payload = {
            name: document.getElementById('comp-name').value,
            description: document.getElementById('comp-desc').value,
            group: document.getElementById('comp-group').value || null,
            package_id: document.getElementById('comp-package-id').value || null,
            tags: document.getElementById('comp-tags').value
                .split(',').map(s => s.trim()).filter(Boolean),
            resource_profile: {
                cpu: document.getElementById('comp-cpu').value,
                ram: document.getElementById('comp-ram').value,
                storage_type: document.getElementById('comp-storage').value,
                recommended_cores: parseInt(document.getElementById('comp-lxc-cores').value) || null,
                recommended_ram_mb: parseInt(document.getElementById('comp-lxc-ram').value) || null,
                recommended_storage_gb: parseInt(document.getElementById('comp-lxc-storage').value) || null
            },
            depends_on: document.getElementById('comp-deps').value
                .split(',').map(s => s.trim()).filter(Boolean),
            conflicts_with: document.getElementById('comp-conflicts').value
                .split(',').map(s => s.trim()).filter(Boolean),
            has_ui: document.getElementById('comp-has-ui').checked,
            has_configuration: document.getElementById('comp-has-config').checked,
            has_traefik_support: document.getElementById('comp-has-traefik').checked,
            ui_port_variable: uiPortInput
                ? (uiPortInput.value.trim() || null)
                : null,
            traefik_internal_port: portInput.disabled
                ? null
                : parseInt(portInput.value) || null
        };

        await fetchJson(`/api/components/${componentId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    };

    const saveVariables = async (componentId) => {
        const payload = { variables: collectVariablesFromDOM() };
        await fetchJson(`/api/components/${componentId}/variables`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    };

    const saveTemplate = async (componentId) => {
        if (!codeEditor) return;
        const content = codeEditor.getValue();
        await fetchText(`/api/components/${componentId}/template`, {
            method: 'PUT',
            headers: { 'Content-Type': 'text/plain' },
            body: content
        });
    };

    const runConflictGatekeeper = async (componentId) => {
        const conflictsWithList = document.getElementById('comp-conflicts').value
            .split(',')
            .map(s => s.trim())
            .filter(Boolean);

        try {
            await fetchJson(`/api/components/${componentId}/validate_metadata_conflicts`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ conflicts_with: conflictsWithList })
            });
            return true;
        } catch (error) {
            showAlert(`Conflict Validation Failed: ${error.message}`, 'danger');
            return false;
        }
    };

    const handleSaveChanges = async (componentId) => {
        saveChangesBtn.disabled = true;
        saveChangesBtn.innerHTML =
            `<span class="spinner-border spinner-border-sm"></span> Saving...`;

        try {
            if (!(await runConflictGatekeeper(componentId))) {
                return;
            }

            await Promise.all([
                saveMetadata(componentId),
                saveVariables(componentId),
                saveTemplate(componentId)
            ]);
            showAlert('All changes saved successfully!', 'success');
            clearAllDirtyState();
            await loadComponents();
            await refreshSyncStatusBadge();
            const selector = `.component-list-item[data-component-id="${componentId}"]`;
            const activeLink = document.querySelector(selector);
            if (activeLink && activeLink.classList) {
                activeLink.classList.add('active');
            }
        } catch (error) {
            console.error('Error saving changes:', error);
            showAlert(`Error: ${error.message}`, 'danger');
        } finally {
            saveChangesBtn.innerHTML = '<i class="bi bi-save"></i> Save All Changes';
            updateUiForDirtyState();
        }
    };

    const runValidation = async (componentId) => {
        const validateBtn = document.getElementById('validate-template-btn');
        if (validateBtn) {
            validateBtn.disabled = true;
            validateBtn.innerHTML =
                `<span class="spinner-border spinner-border-sm me-1"></span> Validating...`;
        }

        const variablesFromDOM = collectVariablesFromDOM();
        const validVariables = variablesFromDOM.filter(v => v.id && v.id.trim() !== '');

        const payload = {
            template_content: codeEditor ? codeEditor.getValue() : "",
            variables: validVariables
        };

        try {
            const response = await fetchJson(`/api/components/${componentId}/validate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            showAlert(response.message, 'success');
            return true;
        } catch (error) {
            showAlert(error.message, 'danger');
            return false;
        } finally {
            if (validateBtn) {
                validateBtn.disabled = false;
                validateBtn.innerHTML =
                    `<i class="bi bi-check-circle"></i> Validate Template`;
            }
        }
    };

    const handleDeleteComponent = async (componentId) => {
        if (confirm(`Are you sure you want to delete the component '${componentId}'?`)) {
            try {
                await fetch(`/api/components/${componentId}`, { method: 'DELETE' });
                showAlert(`Component '${componentId}' deleted successfully!`, 'success');
                if (editorContent) editorContent.classList.add('d-none');
                if (placeholder) placeholder.classList.remove('d-none');
                await loadComponents();
                await refreshSyncStatusBadge();
            } catch (error) {
                showAlert(`Error deleting component: ${error.message}`, 'danger');
            }
        }
    };

    // --- Variables Pane Handlers ---

    const handleVariablesStateAndRender = (indexToRemove) => {
        if (indexToRemove !== undefined) {
            currentVariables.splice(indexToRemove, 1);
        }
        if (internalRenderVariablesRows) {
            internalRenderVariablesRows();
        }
    };

    const handleAddVariable = () => {
        currentVariables.push({
            id: '', label: '', description: '', type: 'text',
            source: '', default: '', required: ''
        });
        handleVariablesStateAndRender();
        markTabAsDirty('variables-pane');
    };

    // --- Component Loading & Rendering ---

    const applicationRenderEditor = async (details) => {
        const componentId = details.id;
        currentVariables = details.required_variables || [];

        renderEditor(
            details,
            componentData,
            markTabAsDirty,
            handleSaveChanges,
            handleDeleteComponent
        );

        internalRenderVariablesRows = renderVariablesPane({
            variables: currentVariables,
            renderAllRowsCallback: handleVariablesStateAndRender,
            markTabDirtyCallback: () => markTabAsDirty('variables-pane'),
            onAddVariable: handleAddVariable,
        });

        const addVariableBtn = document.getElementById('add-variable-btn');
        if (addVariableBtn) {
            addVariableBtn.onclick = handleAddVariable;
        }

        if (!codeEditor) {
            const themeSelector = /** @type {HTMLSelectElement} */ (
                document.getElementById('theme-selector')
            );
            const selectedTheme = themeSelector ? themeSelector.value : 'default';
            codeEditor = CodeMirror.fromTextArea(
                document.getElementById('template-editor'),
                {
                    lineNumbers: true, mode: 'yaml', theme: selectedTheme, tabSize: 2
                }
            );
        }
        if (codeEditor.dirtyMarker) codeEditor.off('change', codeEditor.dirtyMarker);
        const dirtyMarker = () => markTabAsDirty('template-pane');
        codeEditor.on('change', dirtyMarker);
        codeEditor.dirtyMarker = dirtyMarker;

        setupEditorImportFeatures();

        const validateBtn = document.getElementById('validate-template-btn');
        if (validateBtn) {
            validateBtn.onclick = () => runValidation(componentId);
        }

        const addHeaderBtn = document.getElementById('add-header-btn');
        if (addHeaderBtn) {
            addHeaderBtn.onclick = () => {
                if (!codeEditor) return;
                const currentVal = codeEditor.getValue();
                if (currentVal.startsWith('# status:')) {
                    showAlert("Metadata header is already present in this template.", "info");
                    return;
                }
                const defaultHeader =
                    '# status: "untested"\n' +
                    '# last_tested_version: "none"\n' +
                    '# platform_notes: "None"\n' +
                    '# breaking_changes: "None"\n';
                codeEditor.setValue(defaultHeader + currentVal);
                markTabAsDirty('template-pane');
                showAlert("Metadata header added successfully!", "success");
            };
        }

        if (placeholder) placeholder.classList.add('d-none');
        if (editorContent) editorContent.classList.remove('d-none');
        setTimeout(() => { if (codeEditor) codeEditor.setSize("100%", "100%"); }, 50);
        await loadTemplateContent(componentId);
    };

    const loadTemplateContent = async (componentId) => {
        if (!codeEditor) return;
        if (codeEditor.dirtyMarker) codeEditor.off('change', codeEditor.dirtyMarker);
        try {
            const templateText = await fetchText(`/api/components/${componentId}/template`);
            codeEditor.setValue(templateText);
        } catch (error) {
            console.error(`Failed to load template for ${componentId}:`, error);
            codeEditor.setValue(`# Error: Failed to load template.\n# ${error.message}`);
        } finally {
            if (codeEditor.dirtyMarker) codeEditor.on('change', codeEditor.dirtyMarker);
        }
    };

    const loadComponentDetails = async (componentId, force = false) => {
        if (dirtyTabs.size > 0 && !force) {
            if (!confirm('You have unsaved changes that will be lost. Are you sure?')) {
                return;
            }
        }
        clearAllDirtyState();

        const sidebarItems = document.querySelectorAll('.component-list-item');
        sidebarItems.forEach(item => item.classList.remove('active'));
        const selector = `.component-list-item[data-component-id="${componentId}"]`;
        const activeLink = document.querySelector(selector);
        if (activeLink) {
            if (activeLink.classList) {
                activeLink.classList.add('active');
            }
            const wrapper = activeLink.closest('.component-list-wrapper');
            if (wrapper && !wrapper.classList.contains('show')) {
                const bsCollapse = bootstrap.Collapse.getOrCreateInstance(wrapper);
                if (bsCollapse) bsCollapse.show();
            }
        }

        if (placeholder) placeholder.classList.add('d-none');
        if (editorContent) editorContent.classList.add('d-none');

        if (!document.getElementById('loading-indicator')) {
            const loader = document.createElement('div');
            loader.id = 'loading-indicator';
            loader.className = 'text-center text-muted';
            loader.textContent = 'Loading...';
            if (editorPane) editorPane.appendChild(loader);
        }

        try {
            const details = await fetchJson(`/api/components/${componentId}`);
            details.id = componentId;
            await applicationRenderEditor(details);
        } catch (error) {
            console.error('Error loading component details:', error);
            if (editorContent) editorContent.classList.add('d-none');
            if (placeholder) {
                placeholder.classList.remove('d-none');
                placeholder.textContent = '';
                const failHeader = document.createElement('h4');
                failHeader.className = 'text-danger';
                failHeader.textContent = `Failed to load details: ${error.message}`;
                placeholder.appendChild(failHeader);
            }
        } finally {
            const loader = document.getElementById('loading-indicator');
            if (loader) loader.remove();
            clearAllDirtyState();
        }
    };

    const setupResizableSidebar = () => {
        const sidebar = document.getElementById('sidebar');
        const handle = document.getElementById('drag-handle');
        if (!sidebar || !handle) return;
        const savedWidth = localStorage.getItem('sidebarWidth');
        if (savedWidth) {
            sidebar.style.width = `${savedWidth}px`;
        }
        let isResizing = false;
        handle.addEventListener('mousedown', () => {
            isResizing = true;
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });
        const onMouseMove = (e) => {
            if (!isResizing) return;
            const minWidth = parseInt(getComputedStyle(sidebar).minWidth, 10);
            const maxWidth = parseInt(getComputedStyle(sidebar).maxWidth, 10);
            let newWidth = e.clientX;
            if (newWidth < minWidth) newWidth = minWidth;
            if (newWidth > maxWidth) newWidth = maxWidth;
            sidebar.style.width = newWidth.toString() + 'px';
        };
        const onMouseUp = () => {
            isResizing = false;
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
            localStorage.setItem('sidebarWidth', sidebar.offsetWidth.toString());
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
        };
    };

    const setupSidebarCollapseActions = () => {
        const expandAllBtn = document.getElementById("expand-all-btn");
        const collapseAllBtn = document.getElementById("collapse-all-btn");
        if (!expandAllBtn || !collapseAllBtn) return;

        expandAllBtn.addEventListener("click", () => {
            const wrappers = document.querySelectorAll(".component-list-wrapper");
            wrappers.forEach(wrapper => {
                const bsCollapse = bootstrap.Collapse.getOrCreateInstance(wrapper);
                if (bsCollapse) bsCollapse.show();
            });
        });

        collapseAllBtn.addEventListener("click", () => {
            const wrappers = document.querySelectorAll(".component-list-wrapper");
            wrappers.forEach(wrapper => {
                const bsCollapse = bootstrap.Collapse.getOrCreateInstance(wrapper);
                if (bsCollapse) bsCollapse.hide();
            });
        });
    };

    const setupEditorImportFeatures = () => {
        const editorWrapper = document.getElementById('editor-wrapper');
        const importBtn = document.getElementById('import-template-btn');
        const fileInput = document.getElementById('template-file-input');
        if (!editorWrapper || !importBtn || !fileInput || !codeEditor) return;
        importBtn.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', (event) => {
            const file = event.target.files[0];
            if (file) handleFile(file);
        });
        editorWrapper.addEventListener('dragover', (e) => {
            e.preventDefault();
            editorWrapper.classList.add('drag-over');
        });
        editorWrapper.addEventListener('dragleave', () =>
            editorWrapper.classList.remove('drag-over')
        );
        editorWrapper.addEventListener('drop', (e) => {
            e.preventDefault();
            editorWrapper.classList.remove('drag-over');
            const file = e.dataTransfer.files[0];
            if (file) handleFile(file);
        });
        const handleFile = (file) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                if (codeEditor) {
                    codeEditor.setValue(e.target.result);
                    markTabAsDirty('template-pane');
                    showAlert('Template imported successfully!');
                }
            };
            reader.onerror = () => showAlert('Error reading the file.', 'danger');
            reader.readAsText(file);
        };
    };

    const setupThemeSelector = () => {
        const themeSelector = document.getElementById('theme-selector');
        if (!themeSelector) return;
        const savedTheme = localStorage.getItem('editorTheme');
        if (savedTheme) themeSelector.value = savedTheme;
        themeSelector.addEventListener('change', (event) => {
            const newTheme = event.target.value;
            localStorage.setItem('editorTheme', newTheme);
            if (codeEditor) codeEditor.setOption('theme', newTheme);
        });
    };

    const setupCreateComponentModal = () => {
        const createBtn = document.getElementById('create-new-btn');
        const modalElement = document.getElementById('create-component-modal');
        if (!createBtn || !modalElement) return;
        const modal = new bootstrap.Modal(
            /** @type {HTMLElement} */ (modalElement)
        );
        const form = document.getElementById('create-component-form');

        if (!form) {
            console.error('Create component form not found in the DOM.');
            return;
        }

        const compIdInput = document.getElementById('new-component-id-input');
        const compNameInput = document.getElementById('new-component-name');
        createBtn.addEventListener('click', () => {
            form.reset();
            modal["show"]();
        });
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const componentId = compIdInput.value.trim();
            const componentName = compNameInput.value.trim();
            const validIdPattern = /^[a-z0-9-]+$/;
            if (!validIdPattern.test(componentId)) {
                showAlert(
                    'Invalid ID. Use only lowercase letters, numbers, and hyphens.',
                    'warning'
                );
                compIdInput.classList.add('is-invalid');
                return;
            }
            compIdInput.classList.remove('is-invalid');
            if (!componentName) {
                showAlert('Component Name is required.', 'warning');
                return;
            }
            try {
                await fetchJson('/api/components', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        id: componentId,
                        meta: { name: componentName }
                    })
                });
                showAlert(`Component '${componentName}' created successfully!`, 'success');
                modal["hide"]();
                await loadComponents();
                await loadComponentDetails(componentId, false);
                await refreshSyncStatusBadge();
            } catch (error) {
                showAlert(`Error creating component: ${error.message}`, 'danger');
            }
        });
    };

    const setupAIComponentModal = () => {
        const createAiBtn = document.getElementById('create-new-ai-btn');
        const modalElement = document.getElementById('ai-component-modal');
        if (!createAiBtn || !modalElement) return;

        const modal = new bootstrap.Modal(modalElement);
        const form = document.getElementById('ai-generator-form');
        const repoUrlInput = document.getElementById('ai-repo-url');
        const instructionsInput = document.getElementById('ai-instructions');
        const apiKeyInput = document.getElementById('ai-api-key');

        const inputStep = document.getElementById('ai-input-step');
        const loadingStep = document.getElementById('ai-loading-step');
        const previewStep = document.getElementById('ai-preview-step');

        const backBtn = document.getElementById('ai-back-btn');
        const saveBtn = document.getElementById('ai-save-btn');

        // Preview fields
        const previewName = document.getElementById('ai-preview-name');
        const previewGroup = document.getElementById('ai-preview-group');
        const previewDesc = document.getElementById('ai-preview-desc');
        const previewImage = document.getElementById('ai-preview-image');
        const previewConflicts = document.getElementById('ai-preview-conflicts');
        const previewCompose = document.getElementById('ai-preview-compose');
        const previewVarsBody = document.getElementById('ai-preview-vars-body');
        const previewConfigSelector = document.getElementById('ai-preview-config-selector');
        const previewConfigContent = document.getElementById('ai-preview-config-content');

        let generatedData = null;



        createAiBtn.addEventListener('click', () => {
            form.reset();
            inputStep.classList.remove('d-none');
            loadingStep.classList.add('d-none');
            previewStep.classList.add('d-none');
            generatedData = null;
            modal.show();
        });

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const repoUrl = repoUrlInput.value.trim();
            const instructions = instructionsInput.value.trim();
            const apiKey = apiKeyInput.value.trim();
            const saveKeyCheckbox = document.getElementById('ai-save-key');
            const saveKey = saveKeyCheckbox ? saveKeyCheckbox.checked : false;

            inputStep.classList.add('d-none');
            loadingStep.classList.remove('d-none');
            const warningsContainer = document.getElementById('ai-warnings-container');
            if (warningsContainer) warningsContainer.classList.add('d-none');

            try {
                const response = await fetch('/api/ai/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        repo_url: repoUrl,
                        custom_instructions: instructions,
                        api_key: apiKey,
                        save_key: saveKey
                    })
                });

                if (!response.ok) {
                    let errorTitle = 'AI Generation Failed';
                    let errorMsg = `Request failed with status ${response.status}`;

                    try {
                        const errorData = await response.json();
                        if (errorData.error) {
                            errorTitle = errorData.error;
                        }
                        errorMsg = errorData.details || errorData.error || errorMsg;
                    } catch (e) {
                        // ignore non-json errors
                    }

                    loadingStep.classList.add('d-none');
                    const errorStep = document.getElementById('ai-error-step');
                    const errorTitleEl = document.getElementById('ai-error-title');
                    const errorMsgEl = document.getElementById('ai-error-msg');

                    if (errorStep && errorTitleEl && errorMsgEl) {
                        errorTitleEl.textContent = errorTitle;
                        errorMsgEl.textContent = errorMsg;

                        const retryBtn = document.getElementById('ai-error-retry-btn');
                        const cancelBtn = document.getElementById('ai-error-cancel-btn');

                        const newRetryBtn = retryBtn.cloneNode(true);
                        retryBtn.parentNode.replaceChild(newRetryBtn, retryBtn);

                        const newCancelBtn = cancelBtn.cloneNode(true);
                        cancelBtn.parentNode.replaceChild(newCancelBtn, cancelBtn);

                        newRetryBtn.addEventListener('click', () => {
                            errorStep.classList.add('d-none');
                            form.requestSubmit();
                        });

                        newCancelBtn.addEventListener('click', () => {
                            errorStep.classList.add('d-none');
                            inputStep.classList.remove('d-none');
                        });

                        errorStep.classList.remove('d-none');
                    } else {
                        showAlert(`${errorTitle}: ${errorMsg}`, 'danger');
                        inputStep.classList.remove('d-none');
                    }
                    return;
                }

                const result = await response.json();
                generatedData = result.data;

                // Update input placeholder dynamically if a key was entered and saved
                if (apiKey) {
                    apiKeyInput.value = '';
                    apiKeyInput.placeholder = 'Gemini API key is configured (leave blank to keep)';
                    const formText = apiKeyInput.nextElementSibling;
                    if (formText) {
                        formText.textContent = 'The configured GEMINI_API_KEY from the .env file will be used if this is left blank.';
                    }
                    if (result.key_saved) {
                        showAlert('Gemini API key successfully saved to .env file.', 'success');
                    }
                }

                // Populate preview UI
                previewName.value = generatedData.metadata.name || '';
                previewGroup.value = generatedData.metadata.group || '';
                previewDesc.value = generatedData.metadata.description || '';
                previewImage.value = generatedData.metadata.image_name || '';
                previewConflicts.value = (generatedData.metadata.conflicts_with || []).join(', ');
                previewCompose.value = generatedData.docker_compose || '';

                // Render security/validation warnings
                const warningsContainer = document.getElementById('ai-warnings-container');
                const warningsList = document.getElementById('ai-warnings-list');
                if (warningsContainer && warningsList) {
                    warningsList.innerHTML = '';
                    /** @type {string[]} */
                    const warnings = generatedData.security_warnings || [];
                    if (warnings.length > 0) {
                        warnings.forEach(warning => {
                            const li = document.createElement('li');
                            li.textContent = String(warning);
                            warningsList.appendChild(li);
                        });
                        warningsContainer.classList.remove('d-none');
                    } else {
                        warningsContainer.classList.add('d-none');
                    }
                }

                // Populate variables table
                previewVarsBody.innerHTML = '';
                (generatedData.variables || []).forEach(v => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${v.id || ''}</td>
                        <td>${v.label || ''}</td>
                        <td>${v.type || ''}</td>
                        <td>${v.default || ''}</td>
                        <td>${v.description || ''}</td>
                    `;
                    previewVarsBody.appendChild(tr);
                });

                // Populate other configs selector
                previewConfigSelector.innerHTML = '';
                const configs = generatedData.config_templates || {};
                const configNames = Object.keys(configs);
                if (configNames.length > 0) {
                    configNames.forEach(name => {
                        const opt = document.createElement('option');
                        opt.value = name;
                        opt.textContent = name;
                        previewConfigSelector.appendChild(opt);
                    });
                    previewConfigContent.value = configs[configNames[0]];
                } else {
                    const opt = document.createElement('option');
                    opt.textContent = 'No configuration templates generated';
                    previewConfigSelector.appendChild(opt);
                    previewConfigContent.value = '';
                }

                loadingStep.classList.add('d-none');
                previewStep.classList.remove('d-none');

            } catch (err) {
                showAlert(`AI Generation failed: ${err.message}`, 'danger');
                loadingStep.classList.add('d-none');
                inputStep.classList.remove('d-none');
            }
        });

        previewConfigSelector.addEventListener('change', () => {
            const selectedName = previewConfigSelector.value;
            const configs = (generatedData && generatedData.config_templates) || {};
            previewConfigContent.value = configs[selectedName] || '';
        });

        backBtn.addEventListener('click', () => {
            previewStep.classList.add('d-none');
            inputStep.classList.remove('d-none');
            const warningsContainer = document.getElementById('ai-warnings-container');
            if (warningsContainer) warningsContainer.classList.add('d-none');
        });

        saveBtn.addEventListener('click', async () => {
            if (!generatedData) return;
            try {
                await fetchJson('/api/components/ai', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(generatedData)
                });

                showAlert(`Component '${generatedData.metadata.name}' created successfully!`, 'success');
                modal.hide();
                await loadComponents();
                await loadComponentDetails(generatedData.id, false);
                await refreshSyncStatusBadge();
            } catch (err) {
                showAlert(`Error saving component: ${err.message}`, 'danger');
            }
        });
    };

    const setupManageGroupsModal = () => {
        const manageBtn = document.getElementById('manage-groups-btn');
        const modalElement = document.getElementById('manage-groups-modal');
        if (!manageBtn || !modalElement) return;
        const modal = new bootstrap.Modal(
            /** @type {HTMLElement} */ (modalElement)
        );
        const groupsList = document.getElementById('manage-groups-list');
        if (!groupsList) {
            console.error('Manage groups list not found in the DOM.');
            return;
        }
        manageBtn.addEventListener('click', () => {
            groupsList.innerHTML = '';
            if (!componentData || !componentData.groups) return;
            componentData.groups.forEach(group => {
                const isUsed = group.components.length > 0;
                const listItem = document.createElement('li');
                listItem.className =
                    'list-group-item d-flex justify-content-between align-items-center';

                const textDiv = document.createElement('div');
                textDiv.className = 'flex-grow-1 me-2';

                const nameSpan = document.createElement('span');
                nameSpan.className = 'group-name-display';
                nameSpan.textContent = group.name;

                const nameInput = document.createElement('input');
                nameInput.type = 'text';
                nameInput.className = 'form-control d-none group-name-input';
                nameInput.value = group.name;

                textDiv.appendChild(nameSpan);
                textDiv.appendChild(nameInput);

                const btnDiv = document.createElement('div');

                const editBtn = document.createElement('button');
                editBtn.className = 'btn btn-sm btn-outline-primary me-1';
                editBtn.dataset.action = 'edit';
                const editIcon = document.createElement('i');
                editIcon.className = 'bi bi-pencil';
                editBtn.appendChild(editIcon);

                const saveBtn = document.createElement('button');
                saveBtn.className = 'btn btn-sm btn-outline-success d-none me-1';
                saveBtn.dataset.action = 'save';
                const checkIcon = document.createElement('i');
                checkIcon.className = 'bi bi-check-lg';
                saveBtn.appendChild(checkIcon);

                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'btn btn-sm btn-outline-danger';
                deleteBtn.dataset.action = 'delete';
                deleteBtn.dataset.groupId = group.id;
                if (isUsed) {
                    deleteBtn.disabled = true;
                    deleteBtn.title = 'Cannot delete a group containing components';
                }
                const trashIcon = document.createElement('i');
                trashIcon.className = 'bi bi-trash';
                deleteBtn.appendChild(trashIcon);

                btnDiv.appendChild(editBtn);
                btnDiv.appendChild(saveBtn);
                btnDiv.appendChild(deleteBtn);

                listItem.appendChild(textDiv);
                listItem.appendChild(btnDiv);
                groupsList.appendChild(listItem);
            });
            modal["show"]();
        });
        groupsList.addEventListener('click', async (e) => {
            const button = e.target.closest('button');
            if (!button) return;
            const action = button.dataset.action;
            const listItem = button.closest('li');
            const groupNameDisplay = listItem.querySelector('.group-name-display');
            const groupNameInput = listItem.querySelector('.group-name-input');
            const editBtn = listItem.querySelector('[data-action="edit"]');
            const saveBtn = listItem.querySelector('[data-action="save"]');
            const deleteBtn = listItem.querySelector('[data-action="delete"]');
            const groupId = deleteBtn.dataset.groupId;

            if (action === 'edit') {
                groupNameDisplay.classList.add('d-none');
                groupNameInput.classList.remove('d-none');
                editBtn.classList.add('d-none');
                saveBtn.classList.remove('d-none');
                groupNameInput.focus();
            } else if (action === 'save') {
                const newName = groupNameInput.value.trim();
                if (newName && newName !== groupNameDisplay.textContent) {
                    try {
                        await fetchJson(`/api/groups/${groupId}/rename`, {
                            method: 'PUT',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ name: newName })
                        });
                        showAlert(`Group renamed to '${newName}'!`, 'success');
                        modal["hide"]();
                        await loadComponents();
                        await refreshSyncStatusBadge();
                    } catch (error) {
                        showAlert(`Error renaming group: ${error.message}`, 'danger');
                    }
                } else {
                    groupNameDisplay.classList.remove('d-none');
                    groupNameInput.classList.add('d-none');
                    editBtn.classList.remove('d-none');
                    saveBtn.classList.add('d-none');
                }
            } else if (action === 'delete') {
                if (button.disabled) return;
                if (confirm(`Are you sure you want to delete group '${groupId}'?`)) {
                    try {
                        await fetchJson(`/api/groups/${groupId}`, { method: 'DELETE' });
                        showAlert(`Group '${groupId}' deleted!`, 'success');
                        modal["hide"]();
                        await loadComponents();
                        await refreshSyncStatusBadge();
                    } catch (error) {
                        showAlert(`Error deleting group: ${error.message}`, 'danger');
                    }
                }
            }
        });
    };

    const setupHashGenerator = () => {
        const hashGeneratorModalEl = document.getElementById('hashGeneratorModal');
        const hashGeneratorForm = document.getElementById('hash-generator-form');
        const hashUsernameInput = document.getElementById('hash-username');
        const hashPasswordInput = document.getElementById('hash-password');
        const hashPasswordConfirmInput =
            document.getElementById('hash-password-confirm');
        const passwordMatchFeedback =
            document.getElementById('password-match-feedback');
        const generateHashSubmitBtn =
            document.getElementById('generate-hash-submit-btn');
        const hashResultArea = document.getElementById('hash-result-area');
        const hashOutputInput = document.getElementById('hash-output');
        const copyHashBtn = document.getElementById('copy-hash-btn');
        const generateHashBtn = document.getElementById('generate-hash-btn');

        if (!hashGeneratorModalEl || !generateHashBtn) return;

        const hashGeneratorModal = new bootstrap.Modal(
            /** @type {HTMLElement} */ (hashGeneratorModalEl)
        );

        generateHashBtn.addEventListener('click', () => {
            hashGeneratorForm.reset();
            hashPasswordInput.classList.remove('is-invalid');
            hashPasswordConfirmInput.classList.remove('is-invalid');
            hashResultArea.style.display = 'none';
            hashGeneratorModal["show"]();
        });

        hashGeneratorForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const username = hashUsernameInput.value.trim();
            const password = hashPasswordInput.value;
            const passwordConfirm = hashPasswordConfirmInput.value;

            if (password !== passwordConfirm) {
                hashPasswordInput.classList.add('is-invalid');
                hashPasswordConfirmInput.classList.add('is-invalid');
                passwordMatchFeedback.style.display = 'block';
                showAlert('Passwords do not match.', 'danger');
                return;
            }
            hashPasswordInput.classList.remove('is-invalid');
            hashPasswordConfirmInput.classList.remove('is-invalid');
            passwordMatchFeedback.style.display = 'none';

            if (!username || !password) {
                showAlert('Username and Password cannot be empty.', 'danger');
                return;
            }

            generateHashSubmitBtn.disabled = true;
            generateHashSubmitBtn.innerHTML =
                `<span class="spinner-border spinner-border-sm me-1"></span> Generating...`;

            try {
                const payload = { username, password };
                const response = await fetchJson('/api/generate_auth_hash', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                hashOutputInput.value = response.hashed_user_string;
                hashResultArea.style.display = 'block';
                showAlert('Secure hash generated successfully!', 'success');
            } catch (error) {
                showAlert(`Error generating hash: ${error.message}`, 'danger');
                hashResultArea.style.display = 'none';
            } finally {
                generateHashSubmitBtn.disabled = false;
                generateHashSubmitBtn.innerHTML = `Generate Hash`;
            }
        });

        copyHashBtn.addEventListener('click', async () => {
            const textToCopy = hashOutputInput.value;
            try {
                await navigator.clipboard.writeText(textToCopy);
                showAlert('Hash string copied to clipboard!', 'success');
            } catch (err) {
                hashOutputInput.select();
                document["execCommand"]('copy');
                showAlert('Hash string copied (Legacy fallback)!', 'success');
            }
        });
    };

    const setupSortableGroups = () => {
        if (typeof Sortable === 'undefined') {
            console.error('Sortable.js library not loaded. Cannot set up sorting.');
            return;
        }
        if (!componentList) return;
        new Sortable(componentList, {
            animation: 150,
            handle: '.group-drag-handle',
            onEnd: async () => {
                const newOrder = Array.from(
                    componentList.querySelectorAll('.group-header')
                ).map(header => header.dataset.groupId);
                try {
                    await fetchJson('/api/groups/order', {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(newOrder)
                    });
                    showAlert('Group order saved!');
                    await refreshSyncStatusBadge();
                } catch (error) {
                    showAlert(`Error saving group order: ${error.message}`, 'danger');
                }
            }
        });
    };

    const setupSortableComponents = () => {
        if (typeof Sortable === 'undefined') {
            console.error('Sortable.js not loaded. Cannot set up component sorting.');
            return;
        }

        const wrappers = document.querySelectorAll('.component-list-wrapper');
        wrappers.forEach(element => {
            const wrapper = /** @type {HTMLElement} */ (element);
            new Sortable(wrapper, {
                group: 'shared-components', // Allows dragging between different groups!
                animation: 150,
                ghostClass: 'sortable-ghost',
                onEnd: async (evt) => {
                    const compId = evt.item.dataset.componentId;
                    const fromGroupId = evt.from.dataset.groupId;
                    const toGroupId = evt.to.dataset.groupId;

                    if (!compId) return;

                    // 1. If moved to a different group, update group in backend
                    if (fromGroupId !== toGroupId) {
                        try {
                            await fetchJson(`/api/components/${compId}/group`, {
                                method: 'PUT',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ group: toGroupId })
                            });
                            showAlert(`Moved component to group '${toGroupId}'`);
                        } catch (error) {
                            showAlert(`Failed to move component: ${error.message}`, 'danger');
                            await loadComponents();
                            return;
                        }
                    }

                    // 2. Save the new global order of all components
                    const newOrder = Array.from(
                        document.querySelectorAll('.component-list-item')
                    ).map(item => item.dataset.componentId).filter(Boolean);

                    try {
                        await fetchJson('/api/components/order', {
                            method: 'PUT',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(newOrder)
                        });
                        await refreshSyncStatusBadge();
                    } catch (error) {
                        showAlert(`Failed to save components order: ${error.message}`, 'danger');
                    }
                }
            });
        });
    };

    const loadComponents = async () => {
        try {
            const [rawData, groupRules, packagesData] = await Promise.all([
                  fetchJson('/api/components'),
                fetchJson('/api/groups').catch(() => ({})),
                fetchJson('/api/packages').catch(() => ({}))
            ]);

            const groupsMap = new Map();
            const packagesMap = new Map();

            Object.entries(packagesData).forEach(([pkgId, pkg]) => {
                packagesMap.set(pkgId, { id: pkgId, name: pkg.name || pkgId });
            });

            Object.entries(rawData).forEach(([compId, comp]) => {
                if (!comp || typeof comp !== 'object') {
                    throw new Error(`Data corruption: Entry for '${compId}' is null.`);
                }
                comp.id = compId;
                const gId = comp.group || 'general';
                const pId = comp.package_id || 'general-stack';

                if (!groupsMap.has(gId)) {
                    const customName = (groupRules[gId] && groupRules[gId].name)
                        ? groupRules[gId].name
                        : gId.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

                    groupsMap.set(gId, {
                        id: gId,
                        name: customName,
                        is_exclusive: groupRules[gId]
                            ? !!groupRules[gId].is_exclusive
                            : false,
                        components: []
                    });
                }
                groupsMap.get(gId).components.push(comp);

                if (!packagesMap.has(pId)) {
                    packagesMap.set(pId, { id: pId, name: pId });
                }
            });

            componentData = {
                groups: Array.from(groupsMap.values()),
                packages: Object.fromEntries(packagesMap)
            };

            const sidebarControls = document.getElementById('sidebar-controls');
            const viewTabs = document.getElementById('view-tabs');

            if (!window.currentView) window.currentView = 'groups';

            if (sidebarControls && !document.getElementById('component-search')) {
                const searchInput = document.createElement('div');
                const searchBox = document.createElement('input');
                searchBox.type = 'text';
                searchBox.id = 'component-search';
                searchBox.className = 'form-control';
                searchBox.placeholder = 'Search components...';
                searchInput.appendChild(searchBox);
                sidebarControls.appendChild(searchInput);
                searchBox.addEventListener('input', (e) => {
                    const searchTerm = e.target.value.toLowerCase();
                    document.querySelectorAll('.group-container').forEach(container => {
                        const headerText = container.querySelector('.group-header')
                            .dataset.groupId.toLowerCase();
                        const itemsText = Array.from(
                            container.querySelectorAll('.component-list-item')
                        ).map(item => item.textContent.toLowerCase()).join(' ');
                        const isVisible = headerText.includes(searchTerm)
                            || itemsText.includes(searchTerm);
                        container.style.display = isVisible ? '' : 'none';
                    });
                });
            }

            if (viewTabs && !viewTabs.dataset.init) {
                viewTabs.dataset.init = "true";
                viewTabs.addEventListener('click', async (e) => {
                    const btn = e.target.closest('button');
                    if (!btn) return;
                    viewTabs.querySelectorAll('.nav-link')
                        .forEach(t => t.classList.remove('active'));
                    btn.classList.add('active');
                    window.currentView = btn.dataset.view;
                    await loadComponents();
                });
            }

            if (componentList) componentList.innerHTML = '';
            const createComponentLink = (component) => {
                const link = document.createElement('a');
                link.href = '#';
                link.className =
                    'list-group-item list-group-item-action component-list-item';
                link.textContent = component.name || component.id;
                link.dataset.componentId = component.id;
                link.addEventListener('click', async (e) => {
                    e.preventDefault();
                    await loadComponentDetails(component.id, false);
                });
                return link;
            };

            if (window.currentView === 'groups') {
                renderGroupsView(createComponentLink);
            } else {
                renderPackagesView(createComponentLink);
            }
            setupSortableComponents();

        } catch (error) {
            console.error('Error loading components:', error);
            if (componentList) {
                componentList.innerHTML = '';
                const errLi = document.createElement('li');
                errLi.className = 'list-group-item list-group-item-danger';
                errLi.textContent = 'Error loading components.';
                componentList.appendChild(errLi);
            }
        }
    };

    const renderGroupsView = (createLinkFn) => {
        if (!componentData || !componentData.groups) return;
        componentData.groups.forEach(group => {
            renderSection(
                group.id, group.name, group.is_exclusive,
                group.components, createLinkFn
            );
        });
    };

    const renderPackagesView = (createLinkFn) => {
        if (!componentData || !componentData.packages) return;
        const packageMembers = {};

        Object.keys(componentData.packages).forEach(pkgId => {
            packageMembers[pkgId] = [];
        });

        componentData.groups.forEach(group => {
            group.components.forEach(comp => {
                const pkgId = comp.package_id;
                if (pkgId && packageMembers[pkgId] !== undefined) {
                    packageMembers[pkgId].push(comp);
                }
            });
        });

        Object.keys(componentData.packages).forEach(pkgId => {
            const pkg = componentData.packages[pkgId];
            const components = packageMembers[pkgId];
            if (components && components.length > 0) {
                renderSection(
                    `pkg-${pkgId}`, pkg.name, false, components, createLinkFn
                );
            }
        });
    };

    const renderSection = (id, name, isExclusive, components, createLinkFn) => {
        const container = document.createElement('div');
        container.className = 'group-container mb-2';

        // Sanitize the collapse ID (replace spaces, ampersands, etc. with hyphens)
        // to make it a valid CSS selector for querySelector / Bootstrap
        const sanitizedId = id.replace(/[^a-zA-Z0-9_-]/g, '-');
        const collapseId = `collapse-${sanitizedId}`;

        const header = document.createElement('a');
        header.className = 'list-group-item list-group-item-secondary group-header d-flex ' +
            'justify-content-between align-items-center';
        header.href = `#${collapseId}`;
        header.dataset.bsToggle = 'collapse';
        header.dataset.groupId = id; // Keep original id for the API sorting logic
        header.setAttribute('role', 'button');
        header.setAttribute('aria-expanded', 'false');
        header.classList.add('collapsed');

        const leftDiv = document.createElement('div');
        leftDiv.className = 'd-flex align-items-center';

        const dragHandle = document.createElement('i');
        dragHandle.className = 'fa-solid fa-grip-vertical group-drag-handle me-2 text-muted';
        dragHandle.style.cursor = 'grab';
        leftDiv.appendChild(dragHandle);

        const strongEl = document.createElement('strong');
        strongEl.textContent = name;
        leftDiv.appendChild(strongEl);

        header.appendChild(leftDiv);

        const iconEl = document.createElement('i');
        iconEl.className = 'bi bi-chevron-down ms-2';
        header.appendChild(iconEl);

        if (isExclusive) header.classList.add('group-header-exclusive');

        container.appendChild(header);
        const wrapper = document.createElement('div');
        wrapper.id = collapseId; // HTML id uses the sanitized, safe ID
        wrapper.className = 'collapse component-list-wrapper';
        wrapper.dataset.groupId = id; // Keep original id for the API sorting logic

        if (components.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'list-group-item small text-muted italic';
            empty.textContent = 'No components assigned';
            wrapper.appendChild(empty);
        } else {
            components.forEach(comp => wrapper.appendChild(createLinkFn(comp)));
        }

        container.appendChild(wrapper);
        if (componentList) componentList.appendChild(container);
    };

    const setupManagePackagesModal = () => {
        const manageBtn = document.getElementById('manage-packages-btn');
        const modalElement = document.getElementById('manage-packages-modal');
        if (!manageBtn || !modalElement) return;
        const modal = new bootstrap.Modal(
            /** @type {HTMLElement} */ (modalElement)
        );
        const listContainer = document.getElementById('manage-packages-list');

        const newPkgIdInput = document.getElementById('new-pkg-id');
        const newPkgNameInput = document.getElementById('new-pkg-name');
        const createPkgSubmitBtn = document.getElementById('create-pkg-submit');

        manageBtn.addEventListener('click', async () => {
            await renderPackagesList();
            modal["show"]();
        });

        const renderPackagesList = async () => {
            const packages = await fetchJson('/api/packages');
            if (listContainer) {
                listContainer.innerHTML = '';
                Object.keys(packages).forEach(id => {
                    const pkg = packages[id];
                    const div = document.createElement('div');
                    div.className = 'card mb-2 p-2';

                    const topDiv = document.createElement('div');
                    topDiv.className = 'd-flex justify-content-between';

                    const strongId = document.createElement('strong');
                    strongId.textContent = id;
                    topDiv.appendChild(strongId);

                    const delBtn = document.createElement('button');
                    delBtn.className = 'btn btn-sm btn-outline-danger';
                    delBtn.textContent = 'Delete';
                    delBtn.addEventListener('click', () => deletePackage(id));
                    topDiv.appendChild(delBtn);

                    const botDiv = document.createElement('div');
                    botDiv.className = 'mt-2';

                    const nameInp = document.createElement('input');
                    nameInp.type = 'text';
                    nameInp.className = 'form-control form-control-sm mb-1';
                    nameInp.value = pkg.name;
                    nameInp.addEventListener('change', (e) =>
                        updatePackage(id, { name: e.target.value })
                    );
                    botDiv.appendChild(nameInp);

                    const descText = document.createElement('textarea');
                    descText.className = 'form-control form-control-sm';
                    descText.placeholder = 'Description';
                    descText.textContent = pkg.description || '';
                    descText.addEventListener('change', (e) =>
                        updatePackage(id, { description: e.target.value })
                    );
                    botDiv.appendChild(descText);

                    div.appendChild(topDiv);
                    div.appendChild(botDiv);
                    listContainer.appendChild(div);
                });
            }
        };

        if (createPkgSubmitBtn && newPkgIdInput && newPkgNameInput) {
            createPkgSubmitBtn.addEventListener('click', async () => {
                const pkgId = newPkgIdInput.value.trim();
                const pkgName = newPkgNameInput.value.trim();
                const validIdPattern = /^[a-z0-9-]+$/;

                if (!pkgId || !validIdPattern.test(pkgId)) {
                    showAlert('Invalid ID string.', 'warning');
                    newPkgIdInput.classList.add('is-invalid');
                    return;
                }
                newPkgIdInput.classList.remove('is-invalid');

                if (!pkgName) {
                    showAlert('Package Display Name is required.', 'warning');
                    newPkgNameInput.classList.add('is-invalid');
                    return;
                }
                newPkgNameInput.classList.remove('is-invalid');

                try {
                    await fetchJson(`/api/packages/${pkgId}`, {
                        method: 'PUT',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ name: pkgName })
                    });
                    showAlert(`Package '${pkgName}' created!`, 'success');
                    newPkgIdInput.value = '';
                    newPkgNameInput.value = '';
                    await renderPackagesList();
                    await loadComponents();
                    await refreshSyncStatusBadge();
                } catch (error) {
                    showAlert(`Error creating package: ${error.message}`, 'danger');
                }
            });
        }

        window.updatePackage = async (id, data) => {
            await fetchJson(`/api/packages/${id}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            showAlert('Package updated');
            await refreshSyncStatusBadge();
        };

        window.deletePackage = async (id) => {
            if (!confirm('Delete package?')) return;
            try {
                await fetchJson(`/api/packages/${id}`, { method: 'DELETE' });
                await renderPackagesList();
                await loadComponents();
                showAlert('Package deleted');
                await refreshSyncStatusBadge();
            } catch (e) { showAlert(e.message, 'danger'); }
        };
    };

    const setupDirtyFormHandling = () => {
        editorTabs.forEach(tab => {
            tab.addEventListener('show.bs.tab', (event) => {
                if (dirtyTabs.size > 0) {
                    event.preventDefault();
                    nextTabTarget = event.target;
                    if (unsavedChangesModal) unsavedChangesModal["show"]();
                }
            });
        });

        const discardBtn = document.getElementById('discard-and-continue-btn');
        if (discardBtn) {
            discardBtn.addEventListener('click', () => {
                clearAllDirtyState();
                if (unsavedChangesModal) unsavedChangesModal["hide"]();
                if (nextTabTarget) {
                    new bootstrap.Tab(nextTabTarget).show();
                    nextTabTarget = null;
                }
            });
        }

        const saveContinueBtn = document.getElementById('save-and-continue-btn');
        if (saveContinueBtn) {
            saveContinueBtn.addEventListener('click', async () => {
                const componentId = document.getElementById('comp-id').value;
                await handleSaveChanges(componentId);
                if (unsavedChangesModal) unsavedChangesModal["hide"]();
                if (dirtyTabs.size === 0 && nextTabTarget) {
                    new bootstrap.Tab(nextTabTarget).show();
                    nextTabTarget = null;
                }
            });
        }

        if (discardChangesBtn) {
            discardChangesBtn.addEventListener('click', async () => {
                const componentId = document.getElementById('comp-id').value;
                if (componentId) {
                    await loadComponentDetails(componentId, true);
                }
            });
        }
    };

    const setupOnboardingGuide = () => {
        const guideCheckbox = document.getElementById('hide-onboarding-checkbox');
        const showGuideLink = document.getElementById('show-onboarding-link');
        const detailedGuide = document.getElementById('welcome-detailed-guide');
        const minimalGuide = document.getElementById('welcome-minimal');

        const startTourBtn = document.getElementById('start-tour-btn');
        const startTourMinimalBtn = document.getElementById('start-tour-minimal-btn');
        const navStartTourBtn = document.getElementById('nav-start-tour-btn');

        if (!guideCheckbox || !showGuideLink || !detailedGuide || !minimalGuide) return;

        const startInteractiveTour = (e) => {
            if (e) e.preventDefault();
            localStorage.setItem('editor_tour_shown', 'true');
            if (window.introJs) {
                window.introJs().setOptions({
                    steps: [
                        {
                            title: "Welcome",
                            intro: "Welcome to the NjordDeploy Component Editor! Let us take a quick tour of the workspace."
                        },
                        {
                            element: document.getElementById("sidebar"),
                            title: "Sidebar Panel",
                            intro: "This panel contains all your configured components and software packages. Use the tabs above to toggle between Views.",
                            position: "right"
                        },
                        {
                            element: document.getElementById("create-new-btn"),
                            title: "Create Component",
                            intro: "Click here to create a new component manually by entering its ID and Display Name.",
                            position: "bottom"
                        },
                        {
                            element: document.getElementById("create-new-ai-btn"),
                            title: "Bootstrap with AI",
                            intro: "Click here to generate a component automatically using Google Gemini AI! Just provide a GitHub repository URL.",
                            position: "bottom"
                        },
                        {
                            element: document.getElementById("git-sync-btn"),
                            title: "Git Sync Manager",
                            intro: "Check the synchronization status, pull updates from the repository, or upload your local changes.",
                            position: "bottom"
                        },
                        {
                            element: document.getElementById("help-link"),
                            title: "Online Help",
                            intro: "Access the official online Wiki for in-depth documentation and design guidelines.",
                            position: "bottom"
                        }
                    ],
                    showProgress: true,
                    showBullets: false,
                    disableInteraction: true
                }).start();
            }
        };

        const updateGuideVisibility = () => {
            const isHidden = localStorage.getItem('editor_hide_welcome_guide') === 'true';
            if (isHidden) {
                detailedGuide.classList.add('d-none');
                minimalGuide.classList.remove('d-none');
                guideCheckbox.checked = true;
            } else {
                detailedGuide.classList.remove('d-none');
                minimalGuide.classList.add('d-none');
                guideCheckbox.checked = false;

                // Auto-start tour on first load if never shown before
                const tourShown = localStorage.getItem('editor_tour_shown') === 'true';
                if (!tourShown) {
                    setTimeout(() => {
                        startInteractiveTour();
                    }, 500);
                }
            }
        };

        guideCheckbox.addEventListener('change', (e) => {
            if (e.target.checked) {
                localStorage.setItem('editor_hide_welcome_guide', 'true');
            } else {
                localStorage.removeItem('editor_hide_welcome_guide');
            }
            updateGuideVisibility();
        });

        showGuideLink.addEventListener('click', (e) => {
            e.preventDefault();
            localStorage.removeItem('editor_hide_welcome_guide');
            updateGuideVisibility();
        });

        if (startTourBtn) startTourBtn.addEventListener('click', startInteractiveTour);
        if (startTourMinimalBtn) startTourMinimalBtn.addEventListener('click', startInteractiveTour);
        if (navStartTourBtn) navStartTourBtn.addEventListener('click', startInteractiveTour);

        updateGuideVisibility();
    };

    const setupGitSyncFeatures = async () => {
        const gitSyncModalEl = document.getElementById('git-sync-modal');
        const gitDiffModalEl = document.getElementById('git-diff-modal');
        const gitSyncBtn = document.getElementById('git-sync-btn');
        const componentSyncBtn = document.getElementById('component-sync-btn');

        if (!gitSyncModalEl || !gitDiffModalEl || !gitSyncBtn || !componentSyncBtn) return;

        const gitSyncModal = new bootstrap.Modal(gitSyncModalEl);
        const gitDiffModal = new bootstrap.Modal(gitDiffModalEl);

        const gitFetchBtn = document.getElementById('git-fetch-btn');
        const gitSyncAllBtn = document.getElementById('git-sync-all-btn');
        const gitSyncList = document.getElementById('git-sync-list');
        const gitSyncInfoAlert = document.getElementById('git-sync-info-alert');
        const diffMetaComparison = document.getElementById('diff-meta-comparison');
        const diffViewContainer = document.getElementById('diff-view-container');
        const diffSyncActionBtn = document.getElementById('diff-sync-action-btn');

        const renderSyncList = (statusData) => {
            if (!gitSyncList) return;
            gitSyncList.innerHTML = '';
            const components = statusData.components || {};
            const keys = Object.keys(components);
            if (keys.length === 0) {
                gitSyncList.innerHTML = '<tr><td colspan="3" class="text-center py-3">No components found.</td></tr>';
                if (gitSyncAllBtn) gitSyncAllBtn.disabled = true;
                return;
            }

            let canSyncAll = false;

            keys.forEach(compId => {
                const status = components[compId];
                const tr = document.createElement('tr');

                const tdId = document.createElement('td');
                tdId.textContent = compId;
                tr.appendChild(tdId);

                const tdStatus = document.createElement('td');
                let badgeClass = 'bg-secondary';
                let statusText = status;

                if (status === 'synced') {
                    badgeClass = 'bg-success';
                    statusText = 'Synced';
                } else if (status === 'modified') {
                    badgeClass = 'bg-warning text-dark';
                    statusText = 'Modified';
                    canSyncAll = true;
                } else if (status === 'remote_only') {
                    badgeClass = 'bg-info text-dark';
                    statusText = 'New in Repo';
                    canSyncAll = true;
                } else if (status === 'local_only') {
                    badgeClass = 'bg-secondary';
                    statusText = 'Local Only';
                }

                const badge = document.createElement('span');
                badge.className = `badge ${badgeClass}`;
                badge.textContent = statusText;
                tdStatus.appendChild(badge);
                tr.appendChild(tdStatus);

                const tdActions = document.createElement('td');
                tdActions.className = 'text-end';

                if (status === 'modified' || status === 'remote_only') {
                    const diffBtn = document.createElement('button');
                    diffBtn.className = 'btn btn-xs btn-outline-primary me-1 py-0 px-2';
                    diffBtn.textContent = 'Diff & Sync';
                    diffBtn.addEventListener('click', async () => {
                        gitSyncModal.hide();
                        await showDiffForComponent(compId);
                    });
                    tdActions.appendChild(diffBtn);
                }

                tr.appendChild(tdActions);
                gitSyncList.appendChild(tr);
            });

            if (gitSyncAllBtn) gitSyncAllBtn.disabled = !canSyncAll;
        };

        const renderMetadataDiff = (localMeta, remoteMeta, differingFiles) => {
            if (!diffMetaComparison) return;
            const keys = new Set([...Object.keys(localMeta || {}), ...Object.keys(remoteMeta || {})]);
            let rowsHtml = '';

            keys.forEach(key => {
                const valLoc = localMeta ? localMeta[key] : undefined;
                const valRem = remoteMeta ? remoteMeta[key] : undefined;

                const strLoc = typeof valLoc === 'object' ? JSON.stringify(valLoc) : String(valLoc || '');
                const strRem = typeof valRem === 'object' ? JSON.stringify(valRem) : String(valRem || '');

                if (strLoc !== strRem) {
                    rowsHtml += `
                        <tr>
                            <td><strong>${key}</strong></td>
                            <td class="text-danger">${strLoc || '<em>None</em>'}</td>
                            <td class="text-success">${strRem || '<em>None</em>'}</td>
                        </tr>
                    `;
                }
            });

            if (rowsHtml) {
                diffMetaComparison.innerHTML = `
                    <div class="card mb-3">
                        <div class="card-header bg-light py-1"><strong>Metadata Differences</strong></div>
                        <table class="table table-sm table-bordered mb-0 small">
                            <thead>
                                <tr>
                                    <th>Field</th>
                                    <th>Local</th>
                                    <th>Remote (Git)</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${rowsHtml}
                            </tbody>
                        </table>
                    </div>
                `;
            } else {
                if (differingFiles && differingFiles.length > 0) {
                    diffMetaComparison.innerHTML = '<div class="alert alert-warning small py-1 mb-3">Metadata is identical. Only template differs.</div>';
                } else {
                    diffMetaComparison.innerHTML = '<div class="alert alert-success small py-1 mb-3">Metadata and templates are fully synchronized!</div>';
                }
            }
        };

        const renderFilesDiff = (differingFiles) => {
            let fileAlert = document.getElementById('diff-files-list-alert');
            if (!fileAlert) {
                fileAlert = document.createElement('div');
                fileAlert.id = 'diff-files-list-alert';
                diffMetaComparison.parentNode.insertBefore(
                    fileAlert,
                    diffViewContainer
                );
            }
            fileAlert.innerHTML = '';

            if (differingFiles && differingFiles.length > 0) {
                fileAlert.className = 'alert alert-warning small py-2 mb-2';
                const fileList = differingFiles
                    .map(f => `<li><code>${f}</code></li>`)
                    .join('');
                fileAlert.innerHTML = `
                    <i class="bi bi-exclamation-triangle-fill"></i>
                    <strong>Verschillen gedetecteerd in de bestanden:</strong>
                    <ul class="mb-0 mt-1">${fileList}</ul>
                `;
            } else {
                fileAlert.className = 'd-none';
            }
        };

        const showDiffForComponent = async (compId) => {
            if (!diffViewContainer) return;
            diffViewContainer.innerHTML = '<div class="text-center text-muted p-5"><span class="spinner-border spinner-border-sm me-1"></span>Loading diff...</div>';
            if (diffMetaComparison) diffMetaComparison.innerHTML = '';
            gitDiffModal.show();

            try {
                const diffData = await fetchJson(`/api/sync/diff/${compId}`);
                renderMetadataDiff(diffData.local_meta, diffData.remote_meta, diffData.differing_files || []);
                renderFilesDiff(diffData.differing_files || []);

                setTimeout(() => {
                    diffViewContainer.innerHTML = '';
                    const mv = CodeMirror.MergeView(diffViewContainer, {
                        value: diffData.local_template || '',
                        origLeft: null,
                        orig: diffData.remote_template || '',
                        lineNumbers: true,
                        mode: 'yaml',
                        theme: 'material-darker',
                        readOnly: true,
                        revertButtons: false,
                        connect: 'align',
                        collapseIdentical: false
                    });

                    if (window.ResizeObserver) {
                        const ro = new ResizeObserver(() => {
                            mv.edit.refresh();
                            if (mv.right) mv.right.orig.refresh();
                        });
                        ro.observe(diffViewContainer);
                        diffViewContainer.resizeObserver = ro;
                    }
                }, 200);

                if (diffSyncActionBtn) {
                    diffSyncActionBtn.onclick = async () => {
                        diffSyncActionBtn.disabled = true;
                        diffSyncActionBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Syncing...';
                        try {
                            await fetchJson(`/api/sync/component/${compId}`, { method: 'POST' });
                            showAlert(`Component ${compId} successfully synchronized!`, 'success');
                            gitDiffModal.hide();
                            await loadComponents();
                            const currentId = document.getElementById('comp-id');
                            if (currentId && currentId.value === compId) {
                                await loadComponentDetails(compId, true);
                            }
                        } catch (err) {
                            showAlert(`Sync failed: ${err.message}`, 'danger');
                        } finally {
                            diffSyncActionBtn.disabled = false;
                            diffSyncActionBtn.innerHTML = '<i class="bi bi-cloud-arrow-down"></i> Sync This Component';
                        }
                    };
                }
            } catch (err) {
                diffViewContainer.innerHTML = `<div class="alert alert-danger m-3">Error loading diff: ${err.message}</div>`;
            }
        };

        const loadSyncStatus = async () => {
            try {
                const statusData = await fetchJson('/api/sync/status');
                renderSyncList(statusData);
                if (statusData.remote_fetched && gitSyncInfoAlert) {
                    gitSyncInfoAlert.className = 'alert alert-info small py-2 mb-3';
                    gitSyncInfoAlert.textContent = 'Remote cache loaded. Check status below.';
                }
                const badge = document.getElementById('git-sync-badge');
                if (badge) {
                    if (statusData.global_metadata_out_of_sync) {
                        badge.classList.remove('d-none');
                    } else {
                        badge.classList.add('d-none');
                    }
                }
                const globalAlert = document.getElementById('git-global-warning-alert');
                if (globalAlert) {
                    if (statusData.global_metadata_out_of_sync) {
                        globalAlert.classList.remove('d-none');
                    } else {
                        globalAlert.classList.add('d-none');
                    }
                }
            } catch (err) {
                showAlert(`Failed to load sync status: ${err.message}`, 'danger');
            }
        };

        if (gitFetchBtn) {
            gitFetchBtn.addEventListener('click', async () => {
                gitFetchBtn.disabled = true;
                gitFetchBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Fetching...';
                try {
                    await fetchJson('/api/sync/fetch', { method: 'POST' });
                    showAlert('Successfully fetched latest templates from Git repository', 'success');
                    await loadSyncStatus();
                } catch (err) {
                    showAlert(`Failed to fetch from remote: ${err.message}`, 'danger');
                } finally {
                    gitFetchBtn.disabled = false;
                    gitFetchBtn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> Fetch / Check Status';
                }
            });
        }

        if (gitSyncAllBtn) {
            gitSyncAllBtn.addEventListener('click', async () => {
                if (!confirm('Are you sure you want to synchronize all components from remote repository? This will overwrite your local changes.')) {
                    return;
                }
                gitSyncAllBtn.disabled = true;
                gitSyncAllBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Syncing all...';
                try {
                    await fetchJson('/api/sync/all', { method: 'POST' });
                    showAlert('All components successfully synchronized!', 'success');
                    gitSyncModal.hide();
                    await loadComponents();
                    const currentCompIdEl = document.getElementById('comp-id');
                    if (currentCompIdEl && currentCompIdEl.value) {
                        await loadComponentDetails(currentCompIdEl.value, true);
                    }
                } catch (err) {
                    showAlert(`Failed to sync all: ${err.message}`, 'danger');
                } finally {
                    gitSyncAllBtn.disabled = false;
                    gitSyncAllBtn.innerHTML = '<i class="bi bi-check-all"></i> Sync All to Local';
                }
            });
        }

        gitSyncBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            gitSyncModal.show();
            await loadSyncStatus();
        });

        componentSyncBtn.addEventListener('click', async () => {
            const compIdEl = document.getElementById('comp-id');
            if (compIdEl && compIdEl.value) {
                await showDiffForComponent(compIdEl.value);
            }
        });

        const gitUploadBtn = document.getElementById('git-upload-btn');
        const gitUploadSidebarBtn = document.getElementById('git-upload-sidebar-btn');
        const gitUploadAllBtn = document.getElementById('git-upload-all-btn');

        const checkGitPermissions = async () => {
            try {
                const data = await fetchJson('/api/git/check_permission');
                if (data.has_write_access) {
                    if (gitUploadBtn) {
                        gitUploadBtn.classList.remove('disabled');
                        gitUploadBtn.removeAttribute('style');
                        gitUploadBtn.setAttribute('title', 'Upload active component to repository');
                        new bootstrap.Tooltip(gitUploadBtn);
                    }
                    if (gitUploadSidebarBtn) {
                        gitUploadSidebarBtn.disabled = false;
                        gitUploadSidebarBtn.setAttribute('title', 'Upload active component to repository');
                        new bootstrap.Tooltip(gitUploadSidebarBtn);
                    }
                    if (gitUploadAllBtn) {
                        gitUploadAllBtn.disabled = false;
                        gitUploadAllBtn.setAttribute('title', 'Upload all local components to repository');
                        new bootstrap.Tooltip(gitUploadAllBtn);
                    }
                } else {
                    const readOnlyMsg = "Read-only: No write permissions for this repository.";
                    if (gitUploadBtn) {
                        gitUploadBtn.classList.add('disabled');
                        gitUploadBtn.style.pointerEvents = 'none';
                        gitUploadBtn.style.opacity = '0.5';
                        gitUploadBtn.setAttribute('title', readOnlyMsg);
                        new bootstrap.Tooltip(gitUploadBtn);
                    }
                    if (gitUploadSidebarBtn) {
                        gitUploadSidebarBtn.disabled = true;
                        gitUploadSidebarBtn.setAttribute('title', readOnlyMsg);
                        new bootstrap.Tooltip(gitUploadSidebarBtn);
                    }
                    if (gitUploadAllBtn) {
                        gitUploadAllBtn.disabled = true;
                        gitUploadAllBtn.setAttribute('title', readOnlyMsg);
                        new bootstrap.Tooltip(gitUploadAllBtn);
                    }
                }
            } catch (err) {
                console.error("Failed to check git write permissions:", err);
                const readOnlyMsg = "Read-only: No write permissions for this repository.";
                if (gitUploadBtn) {
                    gitUploadBtn.classList.add('disabled');
                    gitUploadBtn.style.pointerEvents = 'none';
                    gitUploadBtn.style.opacity = '0.5';
                    gitUploadBtn.setAttribute('title', readOnlyMsg);
                }
                if (gitUploadSidebarBtn) {
                    gitUploadSidebarBtn.disabled = true;
                    gitUploadSidebarBtn.setAttribute('title', readOnlyMsg);
                }
                if (gitUploadAllBtn) {
                    gitUploadAllBtn.disabled = true;
                    gitUploadAllBtn.setAttribute('title', readOnlyMsg);
                }
            }
        };

        const handleUploadAction = async (e) => {
            if (e) e.preventDefault();
            const compIdEl = document.getElementById('comp-id');
            if (!compIdEl || !compIdEl.value) {
                showAlert("Please select a component first.", "warning");
                return;
            }
            const compId = compIdEl.value;

            // Show loading / upload state
            const origHtmlNavbar = gitUploadBtn ? gitUploadBtn.innerHTML : "";
            const origHtmlSidebar = gitUploadSidebarBtn ? gitUploadSidebarBtn.innerHTML : "";

            if (gitUploadBtn) {
                gitUploadBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Uploading...';
                gitUploadBtn.style.pointerEvents = 'none';
            }
            if (gitUploadSidebarBtn) {
                gitUploadSidebarBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Uploading...';
                gitUploadSidebarBtn.disabled = true;
            }

            try {
                const response = await fetch(`/api/git/upload/${compId}`, { method: 'POST' });
                const resJson = await response.json();
                if (response.ok) {
                    showAlert(resJson.message || `Component ${compId} successfully uploaded!`, 'success');
                    await fetchJson('/api/sync/fetch', { method: 'POST' }).catch(() => {});
                    await refreshSyncStatusBadge();
                } else {
                    showAlert(resJson.error || "Upload failed.", 'danger');
                }
            } catch (err) {
                showAlert(`Upload failed: ${err.message}`, 'danger');
            } finally {
                if (gitUploadBtn) {
                    gitUploadBtn.innerHTML = origHtmlNavbar;
                    gitUploadBtn.style.pointerEvents = '';
                }
                if (gitUploadSidebarBtn) {
                    gitUploadSidebarBtn.innerHTML = origHtmlSidebar;
                    gitUploadSidebarBtn.disabled = false;
                }
            }
        };

        const handleUploadAllAction = async (e) => {
            if (e) e.preventDefault();
            if (!confirm("Are you sure you want to upload all local components and metadata to the remote repository?")) {
                return;
            }

            const origHtml = gitUploadAllBtn ? gitUploadAllBtn.innerHTML : "";
            if (gitUploadAllBtn) {
                gitUploadAllBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Uploading all...';
                gitUploadAllBtn.disabled = true;
            }

            try {
                const response = await fetch('/api/git/upload_all', { method: 'POST' });
                const resJson = await response.json();
                if (response.ok) {
                    showAlert(resJson.message || "All components successfully uploaded!", 'success');
                    gitSyncModal.hide();
                    await fetchJson('/api/sync/fetch', { method: 'POST' }).catch(() => {});
                    await refreshSyncStatusBadge();
                } else {
                    showAlert(resJson.error || "Bulk upload failed.", 'danger');
                }
            } catch (err) {
                showAlert(`Bulk upload failed: ${err.message}`, 'danger');
            } finally {
                if (gitUploadAllBtn) {
                    gitUploadAllBtn.innerHTML = origHtml;
                    gitUploadAllBtn.disabled = false;
                }
            }
        };

        if (gitUploadBtn) {
            gitUploadBtn.addEventListener('click', handleUploadAction);
        }
        if (gitUploadSidebarBtn) {
            gitUploadSidebarBtn.addEventListener('click', handleUploadAction);
        }
        if (gitUploadAllBtn) {
            gitUploadAllBtn.addEventListener('click', handleUploadAllAction);
        }

        await checkGitPermissions();
    };

    // --- Main Initialization ---

    (async () => {
        await loadComponents();
        setupThemeSelector();
        setupResizableSidebar();
        setupSidebarCollapseActions();
        setupSortableGroups();
        setupCreateComponentModal();
        setupAIComponentModal();
        setupManageGroupsModal();
        setupManagePackagesModal();
        setupDirtyFormHandling();
        setupHashGenerator();
        setupOnboardingGuide();
        await setupGitSyncFeatures();
        updateUiForDirtyState();
        await refreshSyncStatusBadge();
    })();
});
