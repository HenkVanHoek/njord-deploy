// src/editor_app/static/ui_render_utils.js

/**
 * @fileoverview Utility functions for rendering the NjordDeploy Editor UI.
 * This file contains DOM creation and manipulation logic, separated from core
 * application state and API interaction logic.
 */

// Define the mandatory and supported variable types and sources for the UI
// NEW FEATURE: Added 'choice' to support dropdown selections for variables.
const VARIABLE_TYPES = ['string', 'port', 'path', 'password', 'port_exclude_traefik', 'choice'];
const VARIABLE_SOURCES = [
    { value: '', label: 'User Input' },
    { value: 'dotenv', label: 'DotEnv' }
];
const VARIABLE_REQUIRED_OPTIONS = [
    { value: '', label: 'Not Required' },
    { value: 'always', label: 'Required Always' },
    { value: 'clean-install', label: 'Required on Clean Install' }
];

/**
 * Creates a standard HTML option element.
 * @param {string} value - The option value.
 * @param {string} text - The option display text.
 * @param {boolean} isSelected - Whether the option should be pre-selected.
 * @returns {HTMLOptionElement}
 */
const createOption = (value, text, isSelected) => {
    const option = document.createElement('option');
    option.value = value;
    // FIX: Use the provided text, but fall back to the value if text is missing.
    // This makes the function more robust.
    option.textContent = text || value;
    if (isSelected) {
        option.selected = true;
    }
    return option;
};

/**
 * Creates an input, select, or textarea element for a variable field.
 * @param {string} tag - The HTML tag name ('input', 'select', or 'textarea').
 * @param {number} index - The index of the variable in the list.
 * @param {string} field - The variable field name ('id', 'type', 'default', etc.).
 * @param {string} value - The initial value.
 * @param {string} [type='text'] - The input type.
 * @returns {HTMLElement}
 */
const createVariableField = (tag, index, field, value, type = 'text') => {
    const element = document.createElement(tag);
    element.className = tag === 'textarea' ? 'form-control form-control-sm' : 'form-control form-control-sm';
    element.dataset.index = index.toString();
    element.dataset.field = field;

    if (tag === 'input') {
        element.type = type;
        element.value = value || '';
    } else if (tag === 'textarea') {
        element.rows = 2;
        element.textContent = value || '';
    } else if (tag === 'select') {
        element.className = 'form-select form-select-sm';
        // Options populated externally in renderVariableRow
    }

    return element;
};

/**
 * Renders a single row for a component variable using robust DOM manipulation.
 * @param {object} variable - The variable object.
 * @param {number} index - The index of the variable in the list.
 * @returns {HTMLDivElement}
 */
const renderVariableRow = (variable, index) => {
    const rowCard = document.createElement('div');
    rowCard.className = 'card mb-3';
    // NEW FEATURE: Add attributes to support the depends_on feature.
    // A unique identifier for the variable's container card.
    rowCard.dataset.variableId = variable.id;
    // If depends_on exists, add its properties as data attributes for easy lookup.
    if (variable.depends_on) {
        rowCard.dataset.dependsOnId = variable.depends_on.id;
        rowCard.dataset.dependsOnValue = variable.depends_on.value;
    }


    const cardBody = document.createElement('div');
    cardBody.className = 'card-body';

    // Top row with 6 columns for Variable ID, Label, Type, Source, Default, Required
    const topRow = document.createElement('div');
    topRow.className = 'row g-2 align-items-center mb-3';

    const fields = [
        { label: 'Variable ID', field: 'id', tag: 'input', width: 'col-md-2' },
        { label: 'Label (Optional)', field: 'label', tag: 'input', width: 'col-md-2' },
        { label: 'Type', field: 'type', tag: 'select', width: 'col-md-2', options: VARIABLE_TYPES },
        { label: 'Source', field: 'source', tag: 'select', width: 'col-md-2', options: VARIABLE_SOURCES },
        { label: 'Default Value', field: 'default', tag: 'input', width: 'col-md-2' },
        { label: 'Required', field: 'required', tag: 'select', width: 'col-md-2', options: VARIABLE_REQUIRED_OPTIONS }
    ];

    fields.forEach(f => {
        const col = document.createElement('div');
        col.className = f.width;

        const label = document.createElement('label');
        label.className = 'form-label small';
        label.textContent = f.label;
        col.appendChild(label);

        let element;
        let optionsToRender = [];

        // Determine element type and options source
        if (f.field === 'default' && variable.type === 'choice') {
            element = createVariableField('select', index, f.field, variable.default);
            // ROBUSTNESS FIX: Handle if variable.options is an array of strings OR objects.
            if (variable.options && Array.isArray(variable.options)) {
                optionsToRender = variable.options.map(opt => {
                    if (typeof opt === 'string') {
                        return { value: opt, label: opt };
                    }
                    return opt; // Assumes { value, label } structure
                });
            }
        } else {
            element = createVariableField(f.tag, index, f.field, variable[f.field]);
            if (f.tag === 'select') {
                const rawOptions = f.options || [];
                if (f.field === 'type') {
                    // Type options are strings, convert them to objects with labels
                    optionsToRender = rawOptions.map(v => ({
                        value: v,
                        label: v.replace(/_/g, ' ').replace('port', 'Port').replace('exclude traefik', '(Exclude Traefik)')
                    }));
                } else {
                    // Source/Required options are already objects
                    optionsToRender = rawOptions;
                }
            }
        }

        // Populate the select element if it has options
        if (element.tagName === 'SELECT' && optionsToRender.length > 0) {
            optionsToRender.forEach(opt => {
                element.appendChild(createOption(opt.value, opt.label, opt.value === variable[f.field]));
            });
        }


        col.appendChild(element);
        topRow.appendChild(col);
    });

    // Description row (full width)
    const descRow = document.createElement('div');
    descRow.className = 'row';
    const descCol = document.createElement('div');
    descCol.className = 'col-12';

    const descLabel = document.createElement('label');
    descLabel.className = 'form-label small';
    descLabel.textContent = 'Description';
    descCol.appendChild(descLabel);

    const descTextarea = createVariableField('textarea', index, 'description', variable.description);
    descCol.appendChild(descTextarea);
    descRow.appendChild(descCol);

    if (variable.id === 'TRAEFIK_DASHBOARD_USERS') {
        const hashHint = document.createElement('div');
        hashHint.className = 'alert alert-sm alert-warning mt-2 mb-0 small';
        // Corrected line length for PEP 8 compliance in spirit
        const hintText = `
            <i class="bi bi-shield-lock-fill"></i>
            **Security Critical:** Use the **Generate Hash** button at the top right to create a secure
            password hash. Copy the result into your global \`.env\` file, and then reference it
            here using the macro <code>{{ DOTENV.YOUR_KEY }}</code>.
        `;
        hashHint.innerHTML = hintText.trim();
        descCol.appendChild(hashHint);
    }

    // Remove button
    const removeButton = document.createElement('button');
    removeButton.className = 'btn btn-sm btn-outline-danger mt-3';
    removeButton.dataset.index = index.toString();
    removeButton.innerHTML = '<i class="bi bi-trash"></i> Remove';

    cardBody.appendChild(topRow);
    cardBody.appendChild(descRow);
    cardBody.appendChild(removeButton);
    rowCard.appendChild(cardBody);

    return rowCard;
};


/**
 * Renders the complete Variables tab pane with all variable rows.
 * It is responsible for *rendering* the initial state and setting up the
 * necessary event listeners for state mutation/dirty tracking.
 *
 * @param {object} params - Parameters for rendering.
 * @param {object[]} params.variables - Array of ComponentVariable objects.
 * @param {function} params.renderAllRowsCallback - A function to re-render all rows (e.g., after adding/deleting).
 * @param {function} params.markTabDirtyCallback - A function to mark the 'variables-pane' as dirty.
 * @param {function} params.onAddVariable - A function to call when the 'Add New Variable' button is clicked.
 */
export function renderVariablesPane({ variables, renderAllRowsCallback, markTabDirtyCallback, onAddVariable }) {
    const container = document.getElementById('variables-pane');
    if (!container) return;
    container.innerHTML = ''; // Clear container

    // 1. Render Hint Alert
    const alertHtml = `
        <div class="alert alert-info small">
            <i class="bi bi-info-circle-fill"></i>
            <strong>Hint:</strong> The <strong>Default Value</strong> field supports special macros.
            Use <code>{{ CONFIG_BASE_PATH }}/your-path</code> for portable data paths, and
            <code>{{ DOTENV.YOUR_GLOBAL_VAR }}</code> to bind the value to the user <strong>.env</strong> file.
            <a href="https://github.com/HenkVanHoek/njord-deploy/blob/main/docs/ARCHITECTURE.md#25-the-variable-and-macro-system" target="_blank" class="alert-link">Learn More</a>.
        </div>`;
    container.insertAdjacentHTML('beforeend', alertHtml);

    // 2. Render List Container
    const listContainer = document.createElement('div');
    listContainer.id = 'variables-list';
    listContainer.className = 'mt-3';
    container.appendChild(listContainer);

    // 3. Render Add Button
    const addButton = document.createElement('button');
    addButton.id = 'add-variable-btn';
    addButton.className = 'btn btn-secondary mt-3';
    addButton.innerHTML = '<i class="bi bi-plus-circle"></i> Add New Variable';
    addButton.addEventListener('click', onAddVariable);
    container.appendChild(addButton);

    // NEW FEATURE: Function to update visibility of dependent variables.
    const updateDependentVisibility = () => {
        const dependentCards = document.querySelectorAll('#variables-list .card[data-depends-on-id]');
        dependentCards.forEach(dependentCard => {
            const controllerId = dependentCard.dataset.dependsOnId;
            const requiredValue = dependentCard.dataset.dependsOnValue;

            const controllerInput = document.querySelector(`.card[data-variable-id="${controllerId}"] [data-field="default"]`);

            if (controllerInput) {
                const isVisible = controllerInput.value === requiredValue;
                dependentCard.style.display = isVisible ? '' : 'none';
            }
        });
    };

    // Function to render all rows in the list container
    const renderRows = () => {
        listContainer.innerHTML = '';
        if (variables.length === 0) {
            listContainer.innerHTML = '<p class="text-muted">No user variables defined.</p>';
        }
        variables.forEach((variable, index) => {
            listContainer.appendChild(renderVariableRow(variable, index));
        });
        // NEW FEATURE: Set the initial visibility state after rendering.
        updateDependentVisibility();
    };

    // Set up delegated event listener for changes
    listContainer.addEventListener('input', e => {
        if (e.target.matches('input') || e.target.matches('select') || e.target.matches('textarea')) {
            markTabDirtyCallback();
        }
    });

    // NEW FEATURE: Add a 'change' listener to handle visibility updates from dropdowns.
    listContainer.addEventListener('change', e => {
        const select = e.target;
        if (select.matches('select[data-field="default"]')) {
            updateDependentVisibility();
        }
    });


    // Set up delegated event listener for remove buttons
    listContainer.addEventListener('click', e => {
        const removeButton = e.target.closest('button');
        if (removeButton && removeButton.dataset.index) {
            // Re-render handled by the main app via the callback after state mutation
            renderAllRowsCallback(parseInt(removeButton.dataset.index, 10));
            markTabDirtyCallback();
        }
    });

    // Initial render of rows
    renderRows();
    return renderRows; // Return the inner render function for easy re-render from editor.v2.js
}

/**
 * Renders the main editor pane with component metadata and sets up event handlers.
 * @param {object} details - Component metadata details.
 * @param {object} componentData - Global component data (for groups datalist).
 * @param {function} markTabDirtyCallback - Function to mark the 'metadata-pane' as dirty.
 * @param {function} handleSaveChanges - Function to call when the save button is clicked.
 * @param {function} handleDeleteComponent - Function to call when the delete button is clicked.
 * @returns {void}
 */
export function renderEditor(details, componentData, markTabDirtyCallback, handleSaveChanges, handleDeleteComponent) {
    const componentId = details.id;
    let dependsOn = Array.isArray(details.depends_on) ? details.depends_on : (details.depends_on ? [details.depends_on] : []);
    const dependsOnStr = dependsOn.join(', ');

    let conflictsWith = Array.isArray(details.conflicts_with) ? details.conflicts_with : (details.conflicts_with ? [details.conflicts_with] : []);
    const conflictsWithStr = conflictsWith.join(', ');

    // 1. Update Title
    document.getElementById('editor-title').textContent = details.name || componentId;

    // 2. Render Metadata Pane
    const metadataPane = document.getElementById('metadata-pane');
    if (!metadataPane) return;
    metadataPane.innerHTML = ''; // Clear existing content

    const renderMetadataField = (type, id, label, value, readOnly = false, isCheckbox = false, rows = 1, listId = null, selectOptions = null) => {
        const div = document.createElement('div');
        div.className = 'mb-3';

        const labelEl = document.createElement('label');
        labelEl.htmlFor = id;
        labelEl.className = 'form-label';
        labelEl.textContent = label;

        let input;
        if (isCheckbox) {
            div.className = 'form-check form-switch mb-2';
            input = document.createElement('input');
            input.className = 'form-check-input';
            input.type = 'checkbox';
            input.role = 'switch';
            input.id = id;
            input.checked = value;
            labelEl.className = 'form-check-label';
            div.appendChild(input);
            div.appendChild(labelEl);
            return div;
        } else if (type === 'select') {
            input = document.createElement('select');
            input.className = 'form-select';
            if (Array.isArray(selectOptions)) {
                selectOptions.forEach(opt => {
                    const optEl = document.createElement('option');
                    optEl.value = opt.value;
                    optEl.textContent = opt.label;
                    if (opt.value === value) optEl.selected = true;
                    input.appendChild(optEl);
                });
            }
        } else if (type === 'textarea') {
            input = document.createElement('textarea');
            input.rows = rows;
            input.textContent = value || '';
        } else {
            input = document.createElement('input');
            input.type = type;
            input.value = value || '';
            if (readOnly) input.readOnly = true;
            if (listId) input.setAttribute('list', listId);
        }

        if (type !== 'select') {
            input.className = 'form-control';
        }
        input.id = id;

        div.appendChild(labelEl);
        div.appendChild(input);
        return div;
    };

    // --- Component ID and Name ---
    metadataPane.appendChild(renderMetadataField('text', 'comp-id', 'Component ID', componentId, true));
    metadataPane.appendChild(renderMetadataField('text', 'comp-name', 'Name', details.name));

    // --- Description ---
    metadataPane.appendChild(renderMetadataField('textarea', 'comp-desc', 'Description', details.description, false, false, 3));

    // --- Group and Depends On (Row layout) ---
    const rowGroupDeps = document.createElement('div');
    rowGroupDeps.className = 'row';

    // Group Field (with Datalist)
    const colGroup = document.createElement('div');
    colGroup.className = 'col-md-6 mb-3';
    const groupField = renderMetadataField('text', 'comp-group', 'Group', details.group, false, false, 1, 'group-datalist');
    colGroup.appendChild(groupField.firstChild);
    colGroup.appendChild(groupField.lastChild);

    // Depends On Field
    const colDeps = document.createElement('div');
    colDeps.className = 'col-md-6 mb-3';
    const depsField = renderMetadataField('text', 'comp-deps', 'Depends On (comma-separated IDs)', dependsOnStr, false, false, 1, 'component-id-datalist');
    colDeps.appendChild(depsField.firstChild);
    colDeps.appendChild(depsField.lastChild);

    rowGroupDeps.appendChild(colGroup);
    rowGroupDeps.appendChild(colDeps);
    metadataPane.appendChild(rowGroupDeps);

    // --- Conflicts With (Row layout) ---
    const rowConflicts = document.createElement('div');
    rowConflicts.className = 'row';

    // Conflicts With Field
    const colConflicts = document.createElement('div');
    colConflicts.className = 'col-md-6 mb-3';
    const conflictsField = renderMetadataField('text', 'comp-conflicts', 'Conflicts With (comma-separated IDs)', conflictsWithStr, false, false, 1, 'component-id-datalist');
    colConflicts.appendChild(conflictsField.firstChild);
    colConflicts.appendChild(conflictsField.lastChild);

    rowConflicts.appendChild(colConflicts);
    metadataPane.appendChild(rowConflicts);


    // --- Datalist for Groups ---
    const datalistGroups = document.createElement('datalist');
    datalistGroups.id = 'group-datalist';

    if (componentData && componentData.groups) {
        // Use a Set to ensure unique values and clean up the list
        const seenGroups = new Set();
        componentData.groups.forEach(group => {
            if (!seenGroups.has(group.id)) {
                const option = document.createElement('option');
                option.value = group.id; // Value submitted to backend
                option.textContent = group.name || group.id; // Friendly name for user
                datalistGroups.appendChild(option);
                seenGroups.add(group.id);
            }
        });
    }

    // --- Datalist for Packages ---
    const datalistPackages = document.createElement('datalist');
    datalistPackages.id = 'package-datalist';
    if (componentData && componentData.packages) {
        Object.keys(componentData.packages).forEach(pkgId => {
            const option = document.createElement('option');
            option.value = pkgId;
            option.textContent = componentData.packages[pkgId].name;
            datalistPackages.appendChild(option);
        });
    }
    metadataPane.appendChild(datalistPackages);
    if (componentData && componentData.groups) {
        componentData.groups.forEach(group => {
            const option = document.createElement('option');
            option.value = group.id;
            option.textContent = group.name;
            datalistGroups.appendChild(option);
        });
    }
    // Datalist for ALL Component IDs (for Conflicts With / Depends On)
    const datalistComponents = document.createElement('datalist');
    datalistComponents.id = 'component-id-datalist';
    if (componentData && componentData.groups) {
        componentData.groups.forEach(group => {
            group.components.forEach(comp => {
                const option = document.createElement('option');
                option.value = comp.id;
                option.textContent = comp.name;
                datalistComponents.appendChild(option);
            });
        });
    }

    metadataPane.appendChild(datalistGroups);
    metadataPane.appendChild(datalistComponents);


    // --- Checkboxes & Status ---
    metadataPane.appendChild(renderMetadataField('checkbox', 'comp-has-ui', 'Has Web UI', details.has_ui, false, true));
    metadataPane.appendChild(renderMetadataField('checkbox', 'comp-has-config', 'Has User Configuration', details.has_configuration, false, true));

    // --- Test Status ---
    const testStatusOptions = [
        { value: 'untested', label: 'Untested / Pending QA' },
        { value: 'tested', label: 'Tested & Verified' },
        { value: 'in_progress', label: 'In Progress / Testing' },
        { value: 'beta', label: 'Beta' }
    ];
    metadataPane.appendChild(renderMetadataField(
        'select',
        'comp-test-status',
        'Test Status',
        details.test_status || 'untested',
        false,
        false,
        1,
        null,
        testStatusOptions
    ));

    // --- UI Port Variable ---
    metadataPane.appendChild(renderMetadataField(
        'text',
        'comp-ui-port-variable',
        'UI Port Variable (for Configurator Access Links)',
        details.ui_port_variable || ''
    ));

    // --- Traefik Support Checkbox ---
    const hasTraefikSupportField = renderMetadataField(
        'checkbox',
        'comp-has-traefik',
        'Has Traefik Support',
        details.has_traefik_support || false,
        false,
        true
    );
    metadataPane.appendChild(hasTraefikSupportField);

    // --- Traefik Internal Port (Number Input) ---
    const traefikInternalPortField = renderMetadataField(
        'number',
        'comp-traefik-port',
        'Traefik Internal Port',
        details.traefik_internal_port || '',
        false,
        false,
        1,
        null
    );
    traefikInternalPortField.id = 'traefik-port-wrapper';
    const portInput = traefikInternalPortField.querySelector('#comp-traefik-port');
    metadataPane.appendChild(traefikInternalPortField);

    const hasTraefikInput = hasTraefikSupportField.querySelector('#comp-has-traefik');

    // Conditional visibility logic
    if (hasTraefikInput && traefikInternalPortField && portInput) {
        const traefikPortWrapper = document.getElementById('traefik-port-wrapper');
        const updatePortVisibility = () => {
            if (hasTraefikInput.checked) {
                traefikPortWrapper.style.display = '';
                portInput.disabled = false;
                if (!portInput.value) {
                    portInput.value = 80;
                }
            } else {
                traefikPortWrapper.style.display = 'none';
                portInput.disabled = true;
            }
        };
        updatePortVisibility();
        hasTraefikInput.addEventListener('change', () => {
            updatePortVisibility();
            markTabDirtyCallback('metadata-pane');
        });
    }

    // --- AI Orchestration Section (New) ---
    const aiSectionHeader = document.createElement('h5');
    aiSectionHeader.className = 'mt-4 mb-3 text-info';
    aiSectionHeader.innerHTML = '<i class="bi bi-robot"></i> AI & Package Orchestration';
    metadataPane.appendChild(aiSectionHeader);

    const rowAi = document.createElement('div');
    rowAi.className = 'row';

    // Package ID Dropdown (Converted to select dropdown for validated choices)
    const colPkg = document.createElement('div');
    colPkg.className = 'col-md-6 mb-3';

    const pkgLabel = document.createElement('label');
    pkgLabel.htmlFor = 'comp-package-id';
    pkgLabel.className = 'form-label';
    pkgLabel.textContent = 'Package ID';
    colPkg.appendChild(pkgLabel);

    const pkgSelect = document.createElement('select');
    pkgSelect.className = 'form-select';
    pkgSelect.id = 'comp-package-id';

    // Add a default unassigned Standalone option at the top of select dropdown
    const noneOption = document.createElement('option');
    noneOption.value = '';
    noneOption.textContent = 'None / Standalone (Unassigned)';
    if (!details.package_id) {
        noneOption.selected = true;
    }
    pkgSelect.appendChild(noneOption);

    if (componentData && componentData.packages) {
        Object.keys(componentData.packages).forEach(pkgId => {
            const pkg = componentData.packages[pkgId];
            const option = document.createElement('option');
            option.value = pkgId;
            option.textContent = pkg.name || pkgId;
            if (pkgId === details.package_id) {
                option.selected = true;
            }
            pkgSelect.appendChild(option);
        });
    }
    colPkg.appendChild(pkgSelect);

    // AI Tags (Comma-separated)
    const colTags = document.createElement('div');
    colTags.className = 'col-md-6 mb-3';
    const tagsStr = Array.isArray(details.tags) ? details.tags.join(', ') : '';
    const tagsField = renderMetadataField('text', 'comp-tags', 'AI Search Tags (comma-separated)', tagsStr);
    colTags.appendChild(tagsField.firstChild);
    colTags.appendChild(tagsField.lastChild);

    rowAi.appendChild(colPkg);
    rowAi.appendChild(colTags);
    metadataPane.appendChild(rowAi);

    // Resource Profile Row
    const rowResources = document.createElement('div');
    rowResources.className = 'row bg-light p-3 rounded mb-3 mx-0';

    const profile = details.resource_profile || { cpu: 'medium', ram: 'medium' };

    const renderProfileSelect = (id, label, value, options) => {
        const col = document.createElement('div');
        col.className = 'col-md-4';
        const lbl = document.createElement('label');
        lbl.className = 'form-label small';
        lbl.textContent = label;
        const sel = document.createElement('select');
        sel.className = 'form-select form-select-sm';
        sel.id = id;
        options.forEach(opt => {
            const o = document.createElement('option');
            o.value = opt;
            o.textContent = opt.charAt(0).toUpperCase() + opt.slice(1);
            if (opt === value) o.selected = true;
            sel.appendChild(o);
        });
        col.appendChild(lbl);
        col.appendChild(sel);
        return col;
    };

    rowResources.appendChild(renderProfileSelect('comp-cpu', 'CPU Load', profile.cpu, ['low', 'medium', 'high']));
    rowResources.appendChild(renderProfileSelect('comp-ram', 'RAM Usage', profile.ram, ['low', 'medium', 'high']));
    rowResources.appendChild(renderProfileSelect('comp-storage', 'Storage Type', profile.storage_type || 'persistent', ['persistent', 'temporary']));

    metadataPane.appendChild(rowResources);

    // Recommended LXC Resources Row
    const rowLxcResources = document.createElement('div');
    rowLxcResources.className = 'row bg-light p-3 rounded mb-3 mx-0 border-top';

    const renderLxcInput = (id, label, value, placeholder) => {
        const col = document.createElement('div');
        col.className = 'col-md-4';
        const lbl = document.createElement('label');
        lbl.className = 'form-label small';
        lbl.textContent = label;
        const input = document.createElement('input');
        input.type = 'number';
        input.className = 'form-control form-control-sm';
        input.id = id;
        input.min = '0';
        input.placeholder = placeholder;
        input.value = value !== undefined && value !== null ? value : '';
        col.appendChild(lbl);
        col.appendChild(input);
        return col;
    };

    rowLxcResources.appendChild(renderLxcInput('comp-lxc-cores', 'Recommended Cores', profile.recommended_cores, 'e.g. 2'));
    rowLxcResources.appendChild(renderLxcInput('comp-lxc-ram', 'Recommended RAM (MB)', profile.recommended_ram_mb, 'e.g. 4096'));
    rowLxcResources.appendChild(renderLxcInput('comp-lxc-storage', 'Recommended Storage (GB)', profile.recommended_storage_gb, 'e.g. 20'));

    metadataPane.appendChild(rowLxcResources);
    // 3. Setup Metadata Event Listener
    metadataPane.addEventListener('input', () => markTabDirtyCallback('metadata-pane'));
    metadataPane.addEventListener('change', () => markTabDirtyCallback('metadata-pane'));

    // 4. Setup Control Buttons
    const saveButton = document.getElementById('save-changes-btn');
    if (saveButton) saveButton.onclick = () => handleSaveChanges(componentId);
    const deleteButton = document.getElementById('delete-component-btn');
    if (deleteButton) deleteButton.onclick = () => handleDeleteComponent(componentId);
}
