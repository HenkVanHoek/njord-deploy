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
    let configCodeEditor = null;
    let currentConfigs = {};
    let activeConfigFile = null;
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

        if (type !== 'danger') {
            setTimeout(() => {
                const currentAlert = document.getElementById('feedback-alert');
                if (currentAlert && currentAlert === alertEl) {
                    const alertInstance = bootstrap.Alert.getOrCreateInstance(currentAlert);
                    if (alertInstance) alertInstance.close();
                }
            }, 5000);
        }
    };

    const refreshSyncStatusBadge = async () => {
        try {
            const statusData = await fetchJson("/api/sync/check-updates", { method: "POST" });
            if (statusData.initial_seed_info && statusData.initial_seed_info.status !== "already_seeded") {
                const seedInfo = statusData.initial_seed_info;
                if (seedInfo.status === "downloaded") {
                    showAlert(seedInfo.message || "De nieuwste componentpakketten zijn automatisch gedownload van GitHub.", "success");
                } else if (seedInfo.status === "fallback") {
                    showAlert(seedInfo.message || "Geen netwerkverbinding. Ingebouwde pakketten geïnstalleerd als fallback.", "warning");
                }
                statusData.initial_seed_info.status = "already_seeded";
            }
            const badge = document.getElementById("git-sync-badge");
            if (badge) {
                badge.classList.remove("d-none");
                if (statusData.is_offline) {
                    badge.className = "badge bg-secondary ms-1";
                    badge.textContent = "Offline";
                    badge.title = "Geen internetverbinding - Lokale modus actief";
                } else if (statusData.remote_updates_available > 0) {
                    badge.className = "badge bg-warning text-dark ms-1";
                    badge.textContent = `${statusData.remote_updates_available} Update(s)`;
                    badge.title = `${statusData.remote_updates_available} component(en) bijgewerkt in remote repository`;
                } else if (statusData.global_metadata_out_of_sync) {
                    badge.className = "badge bg-danger ms-1";
                    badge.textContent = "Unsynced!";
                    badge.title = "Globale metadata niet gepusht";
                } else {
                    badge.className = "badge bg-success ms-1";
                    badge.textContent = "Synced";
                    badge.title = "Alle componenten up-to-date";
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
            const badge = document.getElementById("git-sync-badge");
            if (badge) {
                badge.classList.remove("d-none");
                badge.className = "badge bg-secondary ms-1";
                badge.textContent = "Offline";
                badge.title = "Geen netwerkverbinding";
            }
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
            test_status: document.getElementById('comp-test-status')
                ? document.getElementById('comp-test-status').value
                : 'untested',
            ui_port_variable: uiPortInput
                ? (uiPortInput.value.trim() || null)
                : null,
            traefik_internal_port: portInput.disabled
                ? null
                : parseInt(portInput.value) || null,
            ai_instructions: document.getElementById('comp-ai-instructions')
                ? (document.getElementById('comp-ai-instructions').value.trim() || null)
                : null
        };

        if (payload.has_ui && !payload.ui_port_variable) {
            showAlert("Validation Error: 'UI Port Variable' (or port number) is required when 'Has Web UI' is checked.", "danger");
            throw new Error("UI Port Variable is required when Has Web UI is checked.");
        }

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

    const saveConfigs = async (componentId) => {
        if (!dirtyTabs.has('configs-pane')) return;
        if (configCodeEditor && activeConfigFile) {
            currentConfigs[activeConfigFile] = configCodeEditor.getValue();
        }
        for (const [filename, content] of Object.entries(currentConfigs)) {
            await fetchText(`/api/components/${componentId}/configs/${encodeURIComponent(filename)}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'text/plain' },
                body: content
            });
        }
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
                saveTemplate(componentId),
                saveConfigs(componentId)
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
            const currentAppTheme = document.documentElement.getAttribute('data-theme') || 'futuristic-dark';
            const isLightTheme = currentAppTheme === 'light' || currentAppTheme === 'high-contrast-light';
            const selectedTheme = isLightTheme ? 'default' : 'material-darker';
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

        const markTestedBtn = document.getElementById('btn-mark-component-tested');
        if (markTestedBtn) {
            markTestedBtn.onclick = async () => {
                try {
                    const testStatusInput = document.getElementById('comp-test-status');
                    const testStatus = testStatusInput ? testStatusInput.value : 'stable';
                    const res = await fetchJson(`/api/components/${componentId}/mark-tested`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ test_status: testStatus })
                    });
                    if (res && res.status === 'success') {
                        const nowFormatted = new Date().toLocaleString('nl-NL');
                        const label = document.getElementById('comp-tested-date-label');
                        if (label) label.textContent = nowFormatted;
                        showAlert(`Component '${componentId}' succesvol gemarkeerd als getest (${testStatus})!`, "success");
                        refreshSyncStatusBadge();
                    } else {
                        showAlert(`Fout bij markeren van component '${componentId}' als getest.`, "danger");
                    }
                } catch (err) {
                    console.error("Error marking component as tested:", err);
                    showAlert("Fout bij markeren als getest: " + err.message, "danger");
                }
            };
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
        await setupConfigsPane(componentId);
    };

    const setupConfigsPane = async (componentId) => {
        const fileSelect = document.getElementById('config-file-select');
        const tabCount = document.getElementById('configs-tab-count');
        const noConfigsMsg = document.getElementById('no-configs-msg');
        const editorWrapper = document.getElementById('config-editor-wrapper');
        const addBtn = document.getElementById('btn-add-config-file');
        const deleteBtn = document.getElementById('btn-delete-config-file');
        const mountHint = document.getElementById('config-mount-hint');

        if (!fileSelect) return;

        fileSelect.innerHTML = '';
        currentConfigs = {};
        activeConfigFile = null;

        try {
            const data = await fetchJson(`/api/components/${componentId}/configs`);
            currentConfigs = (data && data.configs) || {};
        } catch (e) {
            console.error('Error fetching component configs:', e);
            currentConfigs = {};
        }

        const filenames = Object.keys(currentConfigs);
        if (tabCount) tabCount.textContent = String(filenames.length);

        if (filenames.length === 0) {
            if (noConfigsMsg) noConfigsMsg.classList.remove('d-none');
            if (editorWrapper) editorWrapper.classList.add('d-none');
            if (deleteBtn) deleteBtn.disabled = true;
            if (mountHint) mountHint.textContent = `{{ DATA_ROOT }}/${componentId}/...`;
        } else {
            if (noConfigsMsg) noConfigsMsg.classList.add('d-none');
            if (editorWrapper) editorWrapper.classList.remove('d-none');
            if (deleteBtn) deleteBtn.disabled = false;

            filenames.forEach((fn, idx) => {
                const opt = document.createElement('option');
                opt.value = fn;
                opt.textContent = fn;
                if (idx === 0) opt.selected = true;
                fileSelect.appendChild(opt);
            });

            activeConfigFile = filenames[0];
            fileSelect.value = activeConfigFile;
            if (mountHint) mountHint.textContent = `{{ DATA_ROOT }}/${componentId}/${activeConfigFile}`;
        }

        if (!configCodeEditor) {
            const currentAppTheme = document.documentElement.getAttribute('data-theme') || 'futuristic-dark';
            const isLightTheme = currentAppTheme === 'light' || currentAppTheme === 'high-contrast-light';
            const selectedTheme = isLightTheme ? 'default' : 'material-darker';
            const textarea = document.getElementById('config-editor-textarea');
            if (textarea) {
                configCodeEditor = CodeMirror.fromTextArea(textarea, {
                    lineNumbers: true,
                    mode: 'yaml',
                    theme: selectedTheme,
                    tabSize: 2
                });
            }
        }

        if (configCodeEditor) {
            if (configCodeEditor.dirtyMarker) {
                configCodeEditor.off('change', configCodeEditor.dirtyMarker);
            }
            if (activeConfigFile && currentConfigs[activeConfigFile] !== undefined) {
                configCodeEditor.setValue(currentConfigs[activeConfigFile]);
                const ext = activeConfigFile.split('.').pop().toLowerCase();
                const modeMap = {
                    'yaml': 'yaml',
                    'yml': 'yaml',
                    'json': 'javascript',
                    'xml': 'xml',
                    'conf': 'yaml',
                    'caddyfile': 'yaml',
                    'sh': 'shell'
                };
                configCodeEditor.setOption('mode', modeMap[ext] || 'yaml');
            } else {
                configCodeEditor.setValue('');
            }
            const configDirtyMarker = () => {
                if (activeConfigFile) {
                    currentConfigs[activeConfigFile] = configCodeEditor.getValue();
                    markTabAsDirty('configs-pane');
                }
            };
            configCodeEditor.on('change', configDirtyMarker);
            configCodeEditor.dirtyMarker = configDirtyMarker;
            setTimeout(() => {
                if (configCodeEditor) {
                    configCodeEditor.refresh();
                    configCodeEditor.setSize("100%", "100%");
                }
            }, 50);
        }

        const configsTabBtn = document.getElementById('configs-tab');
        if (configsTabBtn && !configsTabBtn.dataset.listenerAttached) {
            configsTabBtn.dataset.listenerAttached = 'true';
            configsTabBtn.addEventListener('shown.bs.tab', () => {
                if (configCodeEditor) {
                    configCodeEditor.refresh();
                    configCodeEditor.setSize("100%", "100%");
                }
            });
        }

        fileSelect.onchange = () => {
            if (configCodeEditor && activeConfigFile) {
                currentConfigs[activeConfigFile] = configCodeEditor.getValue();
            }
            const newFile = fileSelect.value;
            if (newFile && currentConfigs[newFile] !== undefined) {
                activeConfigFile = newFile;
                if (configCodeEditor) {
                    if (configCodeEditor.dirtyMarker) {
                        configCodeEditor.off('change', configCodeEditor.dirtyMarker);
                    }
                    configCodeEditor.setValue(currentConfigs[newFile]);
                    const ext = newFile.split('.').pop().toLowerCase();
                    const modeMap = {
                        'yaml': 'yaml',
                        'yml': 'yaml',
                        'json': 'javascript',
                        'xml': 'xml',
                        'conf': 'yaml',
                        'caddyfile': 'yaml',
                        'sh': 'shell'
                    };
                    configCodeEditor.setOption('mode', modeMap[ext] || 'yaml');
                    if (configCodeEditor.dirtyMarker) {
                        configCodeEditor.on('change', configCodeEditor.dirtyMarker);
                    }
                    setTimeout(() => {
                        if (configCodeEditor) {
                            configCodeEditor.refresh();
                            configCodeEditor.setSize("100%", "100%");
                        }
                    }, 50);
                }
                if (mountHint) mountHint.textContent = `{{ DATA_ROOT }}/${componentId}/${newFile}`;
            }
        };

        if (addBtn) {
            addBtn.onclick = () => {
                const name = prompt('Enter configuration file name (e.g., config.yaml, Caddyfile, settings.json):');
                if (!name || !name.trim()) return;
                const cleanName = name.trim();
                if (currentConfigs[cleanName] !== undefined) {
                    showAlert(`File '${cleanName}' already exists.`, 'warning');
                    return;
                }
                currentConfigs[cleanName] = `# Configuration file for ${componentId}\n`;
                const opt = document.createElement('option');
                opt.value = cleanName;
                opt.textContent = cleanName;
                opt.selected = true;
                fileSelect.appendChild(opt);
                fileSelect.value = cleanName;
                activeConfigFile = cleanName;
                if (noConfigsMsg) noConfigsMsg.classList.add('d-none');
                if (editorWrapper) editorWrapper.classList.remove('d-none');
                if (deleteBtn) deleteBtn.disabled = false;
                if (configCodeEditor) {
                    if (configCodeEditor.dirtyMarker) {
                        configCodeEditor.off('change', configCodeEditor.dirtyMarker);
                    }
                    configCodeEditor.setValue(currentConfigs[cleanName]);
                    if (configCodeEditor.dirtyMarker) {
                        configCodeEditor.on('change', configCodeEditor.dirtyMarker);
                    }
                    setTimeout(() => { if (configCodeEditor) configCodeEditor.setSize("100%", "100%"); }, 50);
                }
                if (tabCount) tabCount.textContent = String(Object.keys(currentConfigs).length);
                if (mountHint) mountHint.textContent = `{{ DATA_ROOT }}/${componentId}/${cleanName}`;
                markTabAsDirty('configs-pane');
            };
        }

        if (deleteBtn) {
            deleteBtn.onclick = async () => {
                if (!activeConfigFile) return;
                if (!confirm(`Are you sure you want to delete '${activeConfigFile}'?`)) return;
                try {
                    await fetchJson(`/api/components/${componentId}/configs/${encodeURIComponent(activeConfigFile)}`, {
                        method: 'DELETE'
                    });
                    delete currentConfigs[activeConfigFile];
                    showAlert(`Configuration file '${activeConfigFile}' deleted.`, 'success');
                    await setupConfigsPane(componentId);
                    markTabAsDirty('configs-pane');
                } catch (err) {
                    console.error('Failed to delete config file:', err);
                    showAlert('Error deleting configuration file: ' + err.message, 'danger');
                }
            };
        }
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
        const themeSelector = /** @type {HTMLSelectElement | null} */ (
            document.getElementById('theme-selector')
        );

        const syncAllThemeControls = (themeName) => {
            if (themeSelector) {
                themeSelector.value = themeName;
            }
            const isLight = themeName === 'light' || themeName === 'high-contrast-light';
            if (codeEditor) {
                codeEditor.setOption('theme', isLight ? 'default' : 'material-darker');
            }
            if (configCodeEditor) {
                configCodeEditor.setOption('theme', isLight ? 'default' : 'material-darker');
            }
        };

        if (themeSelector) {
            themeSelector.addEventListener('change', (event) => {
                const newTheme = /** @type {HTMLSelectElement} */ (event.target).value;
                document.documentElement.setAttribute('data-theme', newTheme);
                localStorage.setItem('user-theme-preference', newTheme);
                document.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: newTheme } }));
            });
        }

        document.addEventListener('themeChanged', (e) => {
            const themeName = (e.detail && e.detail.theme) || document.documentElement.getAttribute('data-theme') || 'futuristic-dark';
            syncAllThemeControls(themeName);
        });

        const initialTheme = document.documentElement.getAttribute('data-theme') || 'futuristic-dark';
        syncAllThemeControls(initialTheme);
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
        const packageSelect = document.getElementById('ai-package-id');
        const apiKeyInput = document.getElementById('ai-api-key');

        const providerSelect = document.getElementById('ai-provider');
        const apiKeyGroup = document.getElementById('ai-api-key-group');
        const baseUrlGroup = document.getElementById('ai-base-url-group');
        const modelSelectGroup = document.getElementById('ai-model-select-group');
        const modelSelect = document.getElementById('ai-model-select');
        const modelCustomGroup = document.getElementById('ai-model-custom-group');
        const modelCustomInput = document.getElementById('ai-model-custom');
        const providerHelpGroup = document.getElementById('ai-provider-help');
        const providerHelpLink = document.getElementById('ai-provider-help-link');
        const providerHelpText = document.getElementById('ai-provider-help-text');
        const statusContainer = document.getElementById('ai-status-container');
        const statusBadge = document.getElementById('ai-status-badge');
        const statusDetails = document.getElementById('ai-status-details');
        const baseUrlInput = document.getElementById('ai-base-url');

        const inputStep = document.getElementById('ai-input-step');
        const loadingStep = document.getElementById('ai-loading-step');
        const previewStep = document.getElementById('ai-preview-step');

        const backBtn = document.getElementById('ai-back-btn');
        const saveBtn = document.getElementById('ai-save-btn');

        // Preview fields
        const previewName = document.getElementById('ai-preview-name');
        const previewGroup = document.getElementById('ai-preview-group');
        const previewPackage = document.getElementById('ai-preview-package');
        const previewDesc = document.getElementById('ai-preview-desc');
        const previewImage = document.getElementById('ai-preview-image');
        const previewConflicts = document.getElementById('ai-preview-conflicts');
        const previewCompose = document.getElementById('ai-preview-compose');
        const previewVarsBody = document.getElementById('ai-preview-vars-body');
        const previewConfigSelector = document.getElementById('ai-preview-config-selector');
        const previewConfigContent = document.getElementById('ai-preview-config-content');

        let generatedData = null;
        let installedOllamaModels = [];
        let aiProvidersRegistry = {};

        const fetchAiProviders = async () => {
            try {
                const response = await fetch('/api/ai/providers');
                if (response.ok) {
                    const data = await response.json();
                    aiProvidersRegistry = data.providers || {};
                    populateProviderDropdown();
                }
            } catch (e) {
                console.error('Failed to fetch AI providers registry:', e);
            }
        };

        const populateProviderDropdown = () => {
            if (!providerSelect || Object.keys(aiProvidersRegistry).length === 0) return;
            const savedProvider = localStorage.getItem('njord_ai_provider') || providerSelect.value;
            providerSelect.innerHTML = '';

            for (const [key, p] of Object.entries(aiProvidersRegistry)) {
                const option = document.createElement('option');
                option.value = key;
                option.textContent = p.name || key;
                if (key === savedProvider) {
                    option.selected = true;
                    option.setAttribute('selected', 'selected');
                }
                providerSelect.appendChild(option);
            }
            if (savedProvider && providerSelect.value !== savedProvider) {
                providerSelect.value = savedProvider;
            }
        };

        const checkStatus = async () => {
            const provider = providerSelect.value;
            const baseUrl = baseUrlInput.value.trim();

            statusContainer.classList.remove('d-none');
            statusBadge.className = 'badge bg-secondary';
            statusBadge.textContent = 'Checking status...';
            statusDetails.textContent = '';

            try {
                const response = await fetch('/api/ai/status', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ provider, base_url: baseUrl })
                });

                if (response.ok) {
                    const data = await response.json();
                    if (data.status === 'online') {
                        statusBadge.className = 'badge bg-success';
                        statusBadge.textContent = 'Online';
                        if (provider === 'ollama' && data.models) {
                            installedOllamaModels = data.models;
                            populateModels('ollama', installedOllamaModels);
                        }
                    } else if (data.status === 'configured_locally_only') {
                        statusBadge.className = 'badge bg-info';
                        statusBadge.textContent = 'Configured locally';
                    } else if (data.status === 'missing_key') {
                        statusBadge.className = 'badge bg-warning text-dark';
                        statusBadge.textContent = 'Key missing';
                    } else {
                        statusBadge.className = 'badge bg-danger';
                        statusBadge.textContent = 'Offline';
                    }
                    statusDetails.textContent = data.details || '';
                } else {
                    statusBadge.className = 'badge bg-danger';
                    statusBadge.textContent = 'Error';
                    statusDetails.textContent = `Status endpoint returned ${response.status}`;
                }
            } catch (e) {
                statusBadge.className = 'badge bg-danger';
                statusBadge.textContent = 'Error';
                statusDetails.textContent = e.message || 'Network error checking status';
            }
        };

        const populateModels = (provider, modelsList = []) => {
            modelSelect.innerHTML = '';
            if (providerHelpGroup) {
                providerHelpGroup.classList.add('d-none');
            }

            const pInfo = aiProvidersRegistry[provider] || {};
            let options = [];

            if (provider === 'ollama' && modelsList.length > 0) {
                modelsList.forEach(m => options.push({ value: m, text: m }));
                options.push({ value: 'custom', text: 'Handmatig model invoeren...' });
            } else if (pInfo.models && pInfo.models.length > 0) {
                options = [...pInfo.models];
            } else {
                options = [{ value: 'custom', text: 'Handmatig model invoeren...' }];
            }

            options.forEach(opt => {
                const el = document.createElement('option');
                el.value = opt.value;
                el.textContent = opt.text;
                modelSelect.appendChild(el);
            });

            // Set default model
            if (provider === 'ollama' && modelsList.length > 0) {
                const qwenModel = modelsList.find(m => m.includes('qwen2.5-coder'));
                modelSelect.value = qwenModel || modelsList[0];
            } else if (pInfo.default_model) {
                modelSelect.value = pInfo.default_model;
            }

            if (pInfo.help_url && pInfo.help_text && providerHelpGroup && providerHelpLink && providerHelpText) {
                providerHelpLink.href = pInfo.help_url;
                providerHelpText.textContent = pInfo.help_text;
                providerHelpGroup.classList.remove('d-none');
            }

            handleModelSelectChange();
        };

        const handleModelSelectChange = () => {
            if (modelSelect.value === 'custom') {
                modelCustomGroup.classList.remove('d-none');
                modelCustomInput.required = true;
            } else {
                modelCustomGroup.classList.add('d-none');
                modelCustomInput.required = false;
            }
        };

        modelSelect.addEventListener('change', handleModelSelectChange);

        const updateProviderFields = () => {
            const provider = providerSelect.value;
            const pInfo = aiProvidersRegistry[provider] || {};

            apiKeyGroup.classList.add('d-none');
            baseUrlGroup.classList.add('d-none');
            modelSelectGroup.classList.add('d-none');
            modelCustomGroup.classList.add('d-none');
            if (providerHelpGroup) {
                providerHelpGroup.classList.add('d-none');
            }

            const requiresKey = pInfo.requires_api_key !== false;
            if (requiresKey || pInfo.env_var) {
                apiKeyGroup.classList.remove('d-none');
                const helpText = document.getElementById('ai-api-key-help');
                if (helpText && pInfo.env_var) {
                    helpText.textContent = `The ${pInfo.env_var} from your .env file will be used if left blank.`;
                    apiKeyInput.placeholder = `Enter API key (leave blank to use ${pInfo.env_var})`;
                } else if (helpText) {
                    helpText.textContent = 'API Key or Token for custom endpoint.';
                    apiKeyInput.placeholder = 'Enter API Key / Token';
                }
            }

            if (pInfo.allow_custom_base_url) {
                baseUrlGroup.classList.remove('d-none');
                baseUrlInput.placeholder = pInfo.default_base_url || 'http://localhost:11434/v1';
                if (!baseUrlInput.value) {
                    baseUrlInput.value = pInfo.default_base_url || '';
                }
            }

            if (provider === 'custom') {
                modelCustomGroup.classList.remove('d-none');
                modelCustomInput.placeholder = 'e.g., custom-model-name';
            } else {
                modelSelectGroup.classList.remove('d-none');
                populateModels(provider, provider === 'ollama' ? installedOllamaModels : []);
            }

            checkStatus();
        };

        // Fetch registry on modal initialization
        fetchAiProviders();

        providerSelect.addEventListener('change', () => {
            if (providerSelect.value) {
                localStorage.setItem('njord_ai_provider', providerSelect.value);
            }
            updateProviderFields();
        });
        baseUrlInput.addEventListener('change', checkStatus);

        createAiBtn.addEventListener('click', async () => {
            const savedProvider = localStorage.getItem('njord_ai_provider') || providerSelect.value;
            form.reset();
            if (savedProvider && providerSelect.querySelector(`option[value="${savedProvider}"]`)) {
                providerSelect.value = savedProvider;
            }
            inputStep.classList.remove('d-none');
            loadingStep.classList.add('d-none');
            previewStep.classList.add('d-none');
            generatedData = null;
            installedOllamaModels = [];

            // Populate packages dropdown dynamically
            if (packageSelect) {
                packageSelect.innerHTML = '<option value="">None (General)</option>';
                try {
                    const packages = await fetchJson('/api/packages').catch(() => ({}));
                    Object.entries(packages).forEach(([pkgId, pkgData]) => {
                        const opt = document.createElement('option');
                        opt.value = pkgId;
                        opt.textContent = pkgData.name || pkgId;
                        packageSelect.appendChild(opt);
                    });
                } catch (err) {
                    console.error('Failed to populate packages for AI creator:', err);
                }
            }

            updateProviderFields();
            modal.show();
        });

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const repoUrl = repoUrlInput.value.trim();
            const instructions = instructionsInput.value.trim();
            const apiKey = apiKeyInput.value.trim();
            const saveKeyCheckbox = document.getElementById('ai-save-key');
            const saveKey = saveKeyCheckbox ? saveKeyCheckbox.checked : false;

            const provider = providerSelect.value;
            const baseUrl = baseUrlInput.value.trim();
            let modelOverride = modelSelect.value;
            if (provider === 'custom' || modelSelect.value === 'custom') {
                modelOverride = modelCustomInput.value.trim();
            }

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
                        save_key: saveKey,
                        provider: provider,
                        base_url: baseUrl,
                        model: modelOverride
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

                // Inject the selected package ID into the generated metadata
                // Inject the selected package ID into the generated metadata
                if (generatedData && packageSelect) {
                    if (!generatedData.metadata) {
                        generatedData.metadata = {};
                    }
                    generatedData.metadata.package_id = packageSelect.value || null;
                }

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
                const meta = (generatedData && generatedData.metadata) || generatedData || {};
                previewName.value = meta.name || '';
                previewGroup.value = meta.group || '';
                if (previewPackage) {
                    previewPackage.value = meta.package_id || 'None (General)';
                }
                previewDesc.value = meta.description || '';
                previewImage.value = meta.image_name || '';
                previewConflicts.value = (meta.conflicts_with || []).join(', ');
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
                // Ensure a clean metadata structure exists before saving
                if (!generatedData.metadata || Object.keys(generatedData.metadata).length === 0) {
                    generatedData.metadata = {
                        name: generatedData.name || '',
                        description: generatedData.description || '',
                        group: generatedData.group || '',
                        image_name: generatedData.image_name || '',
                        package_id: generatedData.package_id || null,
                        tags: generatedData.tags || [],
                        resource_profile: generatedData.resource_profile || {},
                        depends_on: generatedData.depends_on || [],
                        conflicts_with: generatedData.conflicts_with || [],
                        has_ui: generatedData.has_ui || false,
                        has_configuration: generatedData.has_configuration || false,
                        has_traefik_support: generatedData.has_traefik_support || false,
                        ui_port_variable: generatedData.ui_port_variable || null,
                        traefik_internal_port: generatedData.traefik_internal_port || null
                    };
                }

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

            const sortedGroups = Array.from(groupsMap.values()).sort((a, b) =>
                a.name.localeCompare(b.name, undefined, { sensitivity: 'base' })
            );
            sortedGroups.forEach(g => {
                g.components.sort((a, b) =>
                    (a.name || a.id).localeCompare(b.name || b.id, undefined, { sensitivity: 'base' })
                );
            });

            componentData = {
                groups: sortedGroups,
                packages: Object.fromEntries(packagesMap)
            };

            // Update Header and Tab counts
            const totalComponents = Object.keys(rawData).length;
            const totalGroups = groupsMap.size;
            const totalPackages = Object.keys(packagesData).length;

            const compHeaderCount = document.getElementById('components-header-count');
            if (compHeaderCount) compHeaderCount.textContent = `(${totalComponents})`;

            const groupsTabCount = document.getElementById('groups-tab-count');
            if (groupsTabCount) groupsTabCount.textContent = `(${totalGroups})`;

            const packagesTabCount = document.getElementById('packages-tab-count');
            if (packagesTabCount) packagesTabCount.textContent = `(${totalPackages})`;

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
                    'list-group-item list-group-item-action component-list-item d-flex align-items-center';

                const icon = document.createElement('i');
                icon.className = 'bi bi-hdd-network me-2 text-info opacity-75';
                icon.style.fontSize = '0.75rem';
                link.appendChild(icon);

                const span = document.createElement('span');
                span.className = 'text-truncate';
                span.textContent = component.name || component.id;
                link.appendChild(span);

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
        leftDiv.className = 'd-flex align-items-center text-truncate';

        const dragHandle = document.createElement('i');
        dragHandle.className = 'fa-solid fa-grip-vertical group-drag-handle me-2 text-muted opacity-75';
        dragHandle.style.cursor = 'grab';
        leftDiv.appendChild(dragHandle);

        const strongEl = document.createElement('span');
        strongEl.className = 'group-title text-truncate';
        strongEl.textContent = name;
        leftDiv.appendChild(strongEl);

        header.appendChild(leftDiv);

        const rightDiv = document.createElement('div');
        rightDiv.className = 'd-flex align-items-center flex-shrink-0 ms-2';

        const countBadge = document.createElement('span');
        countBadge.className = 'badge group-count-badge rounded-pill me-1 px-2';
        countBadge.style.fontSize = '0.7rem';
        countBadge.textContent = components.length;
        rightDiv.appendChild(countBadge);

        const iconEl = document.createElement('i');
        iconEl.className = 'bi bi-chevron-down';
        rightDiv.appendChild(iconEl);

        header.appendChild(rightDiv);

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
                            intro: "Click here to generate a component automatically using AI (Ollama, Gemini, OpenAI, HostYourAI)! Just provide a Git repository URL.",
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

        const gitSyncModal = gitSyncModalEl ? new bootstrap.Modal(gitSyncModalEl) : null;
        const gitDiffModal = gitDiffModalEl ? new bootstrap.Modal(gitDiffModalEl) : null;

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

        if (gitSyncBtn && gitSyncModal) {
            gitSyncBtn.addEventListener('click', async (e) => {
                e.preventDefault();
                gitSyncModal.show();
                await loadSyncStatus();
            });
        }

        if (componentSyncBtn) {
            componentSyncBtn.addEventListener('click', async () => {
                const compIdEl = document.getElementById('comp-id');
                if (compIdEl && compIdEl.value) {
                    await showDiffForComponent(compIdEl.value);
                }
            });
        }

        const gitUploadBtn = document.getElementById('git-upload-btn');
        const gitUploadSidebarBtn = document.getElementById('git-upload-sidebar-btn');
        const gitUploadAllBtn = document.getElementById('git-upload-all-btn');

        const updateBtnTooltip = (el, titleText, isWritable) => {
            if (!el) return;
            if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
                const inst = bootstrap.Tooltip.getInstance(el);
                if (inst) {
                    inst.dispose();
                }
            }
            el.setAttribute('title', titleText);
            el.removeAttribute('data-bs-original-title');
            if (isWritable) {
                el.classList.remove('disabled');
                el.removeAttribute('style');
                el.disabled = false;
            } else {
                el.classList.add('disabled');
                el.style.pointerEvents = 'none';
                el.style.opacity = '0.5';
                el.disabled = true;
            }
            if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
                new bootstrap.Tooltip(el);
            }
        };

        const checkGitPermissions = async () => {
            try {
                const data = await fetchJson('/api/git/check_permission');
                if (data.has_write_access) {
                    updateBtnTooltip(gitUploadBtn, 'Upload active component to repository', true);
                    updateBtnTooltip(gitUploadSidebarBtn, 'Upload active component to repository', true);
                    updateBtnTooltip(gitUploadAllBtn, 'Upload all local components to repository', true);
                } else {
                    const readOnlyMsg = data.details
                        ? `Read-only: ${data.details}`
                        : "Read-only: No write permissions for this repository.";
                    updateBtnTooltip(gitUploadBtn, readOnlyMsg, false);
                    updateBtnTooltip(gitUploadSidebarBtn, readOnlyMsg, false);
                    updateBtnTooltip(gitUploadAllBtn, readOnlyMsg, false);
                }
            } catch (err) {
                console.error("Failed to check git write permissions:", err);
                const readOnlyMsg = `Read-only: Permission check failed (${err.message || 'Network error'})`;
                updateBtnTooltip(gitUploadBtn, readOnlyMsg, false);
                updateBtnTooltip(gitUploadSidebarBtn, readOnlyMsg, false);
                updateBtnTooltip(gitUploadAllBtn, readOnlyMsg, false);
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

    const renderEcosystemStats = async () => {
        const modalBody = document.getElementById('stats-modal-body');
        if (!modalBody) return;

        try {
            const [rawData, groupsData, packagesData] = await Promise.all([
                fetchJson('/api/components'),
                fetchJson('/api/groups').catch(() => ({})),
                fetchJson('/api/packages').catch(() => ({}))
            ]);

            const components = Object.values(rawData || {});
            const totalComponents = components.length;
            const totalGroups = Object.keys(groupsData || {}).length;
            const totalPackages = Object.keys(packagesData || {}).length;

            let testedCount = 0;
            let inProgressCount = 0;
            let untestedCount = 0;

            let missingDescCount = 0;
            let missingUiPortCount = 0;
            let missingTraefikPortCount = 0;

            components.forEach(comp => {
                const status = (comp.test_status || 'untested').toLowerCase();
                if (status === 'tested') {
                    testedCount++;
                } else if (status === 'in_progress' || status === 'beta' || status === 'testing') {
                    inProgressCount++;
                } else {
                    untestedCount++;
                }

                if (!comp.description || !comp.description.trim()) {
                    missingDescCount++;
                }
                if (comp.has_ui && !comp.ui_port_variable) {
                    missingUiPortCount++;
                }
                if (comp.has_traefik_support && !comp.traefik_internal_port) {
                    missingTraefikPortCount++;
                }
            });

            const testedPercent = totalComponents > 0
                ? Math.round((testedCount / totalComponents) * 100)
                : 0;

            modalBody.innerHTML = `
                <div class="row text-center mb-3">
                    <div class="col-md-3 col-6 mb-3">
                        <div class="p-3 border rounded bg-glass shadow-sm stat-filter-card" data-filter="all" style="cursor: pointer;" title="Click to view all components">
                            <div class="fs-3 fw-bold text-primary">${totalComponents}</div>
                            <div class="text-muted small">Total Components</div>
                        </div>
                    </div>
                    <div class="col-md-3 col-6 mb-3">
                        <div class="p-3 border rounded bg-glass shadow-sm stat-filter-card" data-filter="tested" style="cursor: pointer;" title="Click to view tested components">
                            <div class="fs-3 fw-bold text-success">${testedCount}</div>
                            <div class="text-muted small">Tested &amp; Verified</div>
                        </div>
                    </div>
                    <div class="col-md-3 col-6 mb-3">
                        <div class="p-3 border rounded bg-glass shadow-sm stat-filter-card" data-filter="in_progress" style="cursor: pointer;" title="Click to view components in progress">
                            <div class="fs-3 fw-bold text-warning">${inProgressCount}</div>
                            <div class="text-muted small">In Testing / Progress</div>
                        </div>
                    </div>
                    <div class="col-md-3 col-6 mb-3">
                        <div class="p-3 border rounded bg-glass shadow-sm stat-filter-card" data-filter="untested" style="cursor: pointer;" title="Click to view untested components">
                            <div class="fs-3 fw-bold text-danger">${untestedCount}</div>
                            <div class="text-muted small">Untested / Pending</div>
                        </div>
                    </div>
                </div>

                <h6 class="fw-bold mb-2"><i class="bi bi-shield-check me-1 text-success"></i> Test Coverage Progress (${testedPercent}%)</h6>
                <div class="progress mb-3" style="height: 20px;">
                    <div class="progress-bar bg-success" role="progressbar" style="width: ${testedPercent}%" aria-valuenow="${testedPercent}" aria-valuemin="0" aria-valuemax="100">
                        ${testedPercent}%
                    </div>
                </div>

                <div id="stats-drilldown-section" class="mb-3 d-none">
                    <div class="card bg-transparent border">
                        <div class="card-header fw-bold bg-transparent d-flex justify-content-between align-items-center py-2">
                            <span id="drilldown-title"><i class="bi bi-list-task me-1"></i> Filtered Components</span>
                            <button type="button" class="btn-close btn-close-sm" id="close-drilldown-btn" aria-label="Close Drilldown"></button>
                        </div>
                        <div class="card-body p-0" style="max-height: 250px; overflow-y: auto;">
                            <div class="list-group list-group-flush" id="drilldown-list"></div>
                        </div>
                    </div>
                </div>

                <div class="row">
                    <div class="col-md-6 mb-3">
                        <div class="card bg-transparent border shadow-sm">
                            <div class="card-header fw-bold bg-transparent">
                                <i class="bi bi-layers me-1 text-info"></i> Architecture Totals
                            </div>
                            <ul class="list-group list-group-flush">
                                <li class="list-group-item d-flex justify-content-between align-items-center">
                                    Service Groups
                                    <span class="badge bg-info rounded-pill">${totalGroups}</span>
                                </li>
                                <li class="list-group-item d-flex justify-content-between align-items-center">
                                    Service Packages
                                    <span class="badge bg-primary rounded-pill">${totalPackages}</span>
                                </li>
                            </ul>
                        </div>
                    </div>

                    <div class="col-md-6 mb-3">
                        <div class="card bg-transparent border shadow-sm">
                            <div class="card-header fw-bold bg-transparent">
                                <i class="bi bi-clipboard-data me-1 text-warning"></i> Metadata Quality
                            </div>
                            <ul class="list-group list-group-flush">
                                <li class="list-group-item d-flex justify-content-between align-items-center stat-quality-card" data-filter="missing_desc" style="cursor: pointer;" title="Click to view components missing a description">
                                    <span><i class="bi bi-file-earmark-text me-2 text-warning"></i>Missing Description</span>
                                    <span class="badge ${missingDescCount > 0 ? 'bg-warning text-dark' : 'bg-secondary'} rounded-pill">${missingDescCount}</span>
                                </li>
                                <li class="list-group-item d-flex justify-content-between align-items-center stat-quality-card" data-filter="missing_ui_port" style="cursor: pointer;" title="Click to view components with UI enabled but missing port variable">
                                    <span><i class="bi bi-window-sidebar me-2 text-danger"></i>UI Enabled (Missing Port Var)</span>
                                    <span class="badge ${missingUiPortCount > 0 ? 'bg-danger' : 'bg-secondary'} rounded-pill">${missingUiPortCount}</span>
                                </li>
                                <li class="list-group-item d-flex justify-content-between align-items-center stat-quality-card" data-filter="missing_traefik_port" style="cursor: pointer;" title="Click to view components with Traefik enabled but missing internal port">
                                    <span><i class="bi bi-diagram-3 me-2 text-info"></i>Traefik Enabled (Missing Port)</span>
                                    <span class="badge ${missingTraefikPortCount > 0 ? 'bg-danger' : 'bg-secondary'} rounded-pill">${missingTraefikPortCount}</span>
                                </li>
                            </ul>
                        </div>
                    </div>
                </div>
            `;

            const filterCards = modalBody.querySelectorAll('.stat-filter-card');
            const qualityCards = modalBody.querySelectorAll('.stat-quality-card');
            const drilldownSection = modalBody.querySelector('#stats-drilldown-section');
            const drilldownTitle = modalBody.querySelector('#drilldown-title');
            const drilldownList = modalBody.querySelector('#drilldown-list');
            const closeDrilldownBtn = modalBody.querySelector('#close-drilldown-btn');

            const renderDrilldown = (filterType) => {
                filterCards.forEach(card => {
                    if (card.dataset.filter === filterType) {
                        card.classList.add('border-primary', 'shadow');
                    } else {
                        card.classList.remove('border-primary', 'shadow');
                    }
                });

                qualityCards.forEach(card => {
                    if (card.dataset.filter === filterType) {
                        card.classList.add('bg-primary', 'bg-opacity-25', 'fw-bold');
                    } else {
                        card.classList.remove('bg-primary', 'bg-opacity-25', 'fw-bold');
                    }
                });

                let filtered = [];
                let titleText = '';

                if (filterType === 'tested') {
                    filtered = components.filter(c => (c.test_status || '').toLowerCase() === 'tested');
                    titleText = `<i class="bi bi-check-circle-fill me-1 text-success"></i> Tested &amp; Verified Components (${filtered.length})`;
                } else if (filterType === 'in_progress') {
                    filtered = components.filter(c => {
                        const st = (c.test_status || '').toLowerCase();
                        return st === 'in_progress' || st === 'beta' || st === 'testing';
                    });
                    titleText = `<i class="bi bi-hourglass-split me-1 text-warning"></i> In Testing / Progress Components (${filtered.length})`;
                } else if (filterType === 'untested') {
                    filtered = components.filter(c => {
                        const st = (c.test_status || '').toLowerCase();
                        return st === 'untested' || !st;
                    });
                    titleText = `<i class="bi bi-exclamation-circle-fill me-1 text-danger"></i> Untested / Pending Components (${filtered.length})`;
                } else if (filterType === 'missing_desc') {
                    filtered = components.filter(c => !c.description || !c.description.trim());
                    titleText = `<i class="bi bi-file-earmark-text-fill me-1 text-warning"></i> Components Missing Description (${filtered.length})`;
                } else if (filterType === 'missing_ui_port') {
                    filtered = components.filter(c => c.has_ui && !c.ui_port_variable);
                    titleText = `<i class="bi bi-exclamation-triangle-fill me-1 text-danger"></i> UI Enabled (Missing Port Var) (${filtered.length})`;
                } else if (filterType === 'missing_traefik_port') {
                    filtered = components.filter(c => c.has_traefik_support && !c.traefik_internal_port);
                    titleText = `<i class="bi bi-diagram-3-fill me-1 text-danger"></i> Traefik Enabled (Missing Internal Port) (${filtered.length})`;
                } else {
                    filtered = components;
                    titleText = `<i class="bi bi-collection-fill me-1 text-primary"></i> All Components (${filtered.length})`;
                }

                drilldownTitle.innerHTML = titleText;
                drilldownList.innerHTML = '';

                if (filtered.length === 0) {
                    drilldownList.innerHTML = `
                        <div class="p-3 text-center text-muted small"><i class="bi bi-check-all me-1 text-success"></i> Great job! No components match this filter.</div>
                    `;
                } else {
                    filtered.forEach(comp => {
                        const item = document.createElement('div');
                        item.className = 'list-group-item d-flex justify-content-between align-items-center py-2';
                        const st = (comp.test_status || 'untested').toLowerCase();
                        const statusClass = st === 'tested' ? 'bg-success' : (st === 'beta' || st === 'in_progress' ? 'bg-warning text-dark' : 'bg-danger');
                        const testedDate = comp.last_tested ? new Date(comp.last_tested).toLocaleDateString('nl-NL') : 'Nog niet getest';

                        item.innerHTML = `
                            <div>
                                <span class="fw-bold text-light">${comp.name || comp.id}</span>
                                <small class="text-muted ms-2">(${comp.group || 'general'})</small>
                                <span class="badge ${statusClass} ms-2" style="font-size: 0.75rem;">${comp.test_status || 'untested'}</span>
                                <small class="text-muted ms-2"><i class="bi bi-patch-check me-1"></i>Getest: ${testedDate}</small>
                            </div>
                            <button class="btn btn-sm btn-outline-primary navigate-comp-btn" data-comp-id="${comp.id}">
                                Open <i class="bi bi-arrow-right-short"></i>
                            </button>
                        `;
                        drilldownList.appendChild(item);
                    });

                    drilldownList.querySelectorAll('.navigate-comp-btn').forEach(btn => {
                        btn.addEventListener('click', async (e) => {
                            const compId = e.currentTarget.dataset.compId;
                            if (compId) {
                                const modalEl = document.getElementById('statsModal');
                                if (modalEl) {
                                    const modalInstance = bootstrap.Modal.getInstance(modalEl);
                                    if (modalInstance) modalInstance.hide();
                                }
                                await loadComponentDetails(compId, false);
                            }
                        });
                    });
                }

                drilldownSection.classList.remove('d-none');
            };

            filterCards.forEach(card => {
                card.addEventListener('click', () => {
                    renderDrilldown(card.dataset.filter);
                });
            });

            qualityCards.forEach(card => {
                card.addEventListener('click', () => {
                    renderDrilldown(card.dataset.filter);
                });
            });

            if (closeDrilldownBtn) {
                closeDrilldownBtn.addEventListener('click', () => {
                    drilldownSection.classList.add('d-none');
                    filterCards.forEach(card => card.classList.remove('border-primary', 'shadow'));
                    qualityCards.forEach(card => card.classList.remove('bg-primary', 'bg-opacity-25', 'fw-bold'));
                });
            }
        } catch (err) {
            modalBody.innerHTML = `
                <div class="alert alert-danger mb-0">
                    Failed to load statistics: ${err.message || err}
                </div>
            `;
        }
    };

    const setupStatsModal = () => {
        const statsModalEl = document.getElementById('statsModal');
        if (statsModalEl) {
            statsModalEl.addEventListener('show.bs.modal', async () => {
                await renderEcosystemStats();
            });
        }
        const statsBtn = document.getElementById('stats-btn');
        if (statsBtn) {
            statsBtn.addEventListener('click', async () => {
                await renderEcosystemStats();
            });
        }
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
        setupStatsModal();
        await setupGitSyncFeatures();
        document.addEventListener('click', (e) => {
            const target = /** @type {HTMLElement} */ (e.target);
            const btn = target.closest('.toggle-password-btn');
            if (!btn) return;
            e.preventDefault();
            const group = btn.closest('.input-group');
            if (!group) return;
            const input = /** @type {HTMLInputElement | null} */ (group.querySelector('input'));
            if (!input) return;

            const isPassword = input.type === 'password';
            input.type = isPassword ? 'text' : 'password';
            const icon = btn.querySelector('i');
            if (icon) {
                icon.className = isPassword ? 'fa-solid fa-eye-slash' : 'fa-solid fa-eye';
            }
        });
        updateUiForDirtyState();
        await refreshSyncStatusBadge();
    })();
});
