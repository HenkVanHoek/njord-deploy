// noinspection DuplicatedCode
/* global bootstrap */
// Enclose in an IIFE to avoid global scope pollution and bypass DOMContentLoaded race conditions
(function() {
    /**
     * @typedef {object} PortConflict
     * @property {number} port
     * @property {'DANGEROUS_NATIVE_PROCESS_CONFLICT'|'UNEXPECTED_DOCKER_CONFLICT'|'EXPECTED_REINSTALLATION'} conflict_type
     * @property {string} conflicting_service
     * @property {string} proposed_service
     */

    /**
     * @typedef {object} VolumeConflict
     * @property {string} volume_path
     * @property {'EXISTING_VOLUME_CONFLICT'} conflict_type
     * @property {string} proposed_service
     */

    /**
     * @typedef {object} ResourceWarning
     * @property {'RAM'|'DISK'} type
     * @property {string} message
     */

    /**
     * @typedef {object} SystemAnalysisResponse
     * @property {'success'|'error'} status
     * @property {string[]} [internal_conflicts]
     * @property {{ports: PortConflict[], volumes: VolumeConflict[]}} external_conflicts
     * @property {ResourceWarning[]} resource_warnings
     */

    /**
     * @typedef {object} DeploymentResponse
     * @property {string} task_id
     */

    /**
     * @typedef {object} Host
     * @property {string} ip
     * @property {string} [mac]
     * @property {string|null} hostname
     */

    /**
     * @typedef {object} ScanData
     * @property {Host[]} hosts
     * @property {string[]} [messages]
     * @property {boolean} [permissions_error]
     */

    /**
     * @typedef {object} DiskInfo
     * @property {string} mounted_on
     * @property {string} size
     * @property {string} pcent
     */

    /**
     * @typedef {object} DeviceDetails
     * @property {string} ip
     * @property {string} username
     * @property {string} password
     * @property {string} [hostname]
     * @property {string} [model]
     * @property {string} [serial]
     * @property {string} [ram]
     * @property {DiskInfo[]} [disks]
     */

    /**
     * @typedef {object} ComponentVariable
     * @property {string} id
     * @property {string} [label]
     * @property {string} description
     * @property {string} type
     * @property {string} [default]
     * @property {string[]} [options]
     * @property {'always'|'clean-install'} [required]
     * @property {'dotenv'} [source]
     */

    /**
     * @typedef {object} Component
     * @property {string} id
     * @property {string} name
     * @property {string} description
     * @property {string} [package_id]
     * @property {boolean} [default]
     * @property {string[]} [depends_on]
     * @property {boolean} [post_install_restart_option]
     * @property {ComponentVariable[]} required_variables
     * @property {boolean} has_traefik_support
     * @property {string} [ui_port_variable]
     * @property {string} [protocol]
     */

    /**
     * @typedef {object} PackageData
     * @property {string} name
     * @property {string} description
     */

    /**
     * @typedef {object} SoftwareResponseData
     * @property {Component[]} available_software
     * @property {Object.<string, PackageData>} [available_packages]
     */

    /**
     * @typedef {object} GroupDetails
     * @property {boolean} is_exclusive
     * @property {string[]} components
     */

    /**
     * @typedef {object} GroupData
     * @property {Object.<string, GroupDetails|string[]>} groups
     */

    /**
     * @typedef {object} ServiceLink
     * @property {string} name
     * @property {string} url
     */

    /**
     * @typedef {object} ReportError
     * @property {string} type
     * @property {string} summary
     * @property {string} details
     * @property {string} component_id
     * @property {string} timestamp
     */

    /**
     * @typedef {object} TaskStatus
     * @property {string} status
     * @property {string[]} logs
     * @property {number} last_update
     * @property {ServiceLink[]} service_links
     * @property {ReportError[]} errors
     */

    /**
     * @typedef {object} ApiError
     * @property {string} message - The error message.
     */

    // Simple HTML escape helper to prevent DOM-XSS
    function escapeHTML(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#x27;');
    }

    async function fetchAPI(url, options = {}) {
        try {
            const response = await fetch(url, options);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                const message = errorData.details || errorData.error || `Request failed with status ${response.status}`;
                return Promise.reject({message, details: errorData.details});
            }
            return response.json();
        } catch (networkError) {
            const error = /** @type {Error} */ (networkError);
            return Promise.reject({message: error.message || 'Network error, please check the connection.'});
        }
    }

    function setButtonState(button, isLoading, {text = '', loadingText = 'Loading...'} = {}) {
        if (!button) return;
        if (!button.dataset.originalText) {
            button.dataset.originalText = button.innerHTML;
        }
        const originalText = text || button.dataset.originalText;

        button.disabled = isLoading;
        if (isLoading) {
            button.innerHTML = `<i class="fa-solid fa-spinner fa-spin me-2"></i>${loadingText}`;
        } else {
            button.innerHTML = originalText;
        }
    }

    // Mitigation for DOM-XSS: updateWizardFooter is now completely programmatical
    function updateWizardFooter(message, type = 'muted') {
        const wizardFooter = document.getElementById('wizard-footer');
        if (!wizardFooter) return;

        wizardFooter.textContent = '';
        const p = document.createElement('p');
        p.className = `text-${type} small mb-0`;

        if (message.includes('Warning:') && message.includes('troubleshooting guide')) {
            const strong = document.createElement('strong');
            strong.textContent = 'Warning:';
            p.appendChild(strong);
            p.appendChild(document.createTextNode(' The scanner may not have required permissions. Please check our '));
            const a = document.createElement('a');
            a.href = 'https://github.com/HenkVanHoek/njord-deploy/blob/main/docs/TROUBLESHOOTING.md#network-scan-issues';
            a.target = '_blank';
            a.className = 'alert-link';
            a.textContent = 'troubleshooting guide';
            p.appendChild(a);
            p.appendChild(document.createTextNode('.'));
        } else if (message.includes('An error occurred:')) {
            const icon = document.createElement('i');
            icon.className = 'fa-solid fa-xmark me-2';
            p.appendChild(icon);
            p.appendChild(document.createTextNode(message.replace('<i class="fa-solid fa-xmark me-2"></i>', '')));
        } else {
            p.textContent = message;
        }
        wizardFooter.appendChild(p);
    }

    const wizardHeader = document.getElementById('wizard-header');
    const wizardBody = document.getElementById('wizard-body');

    /** @type {Object.<string, DeviceDetails>} */
    let managedDeviceCache = {};
    /** @type {string[]} */
    let selectedComponentsCache = [];
    /** @type {Component[]} */
    let allSoftwareCache = [];
    /** @type {Object.<string, any>} */
    let finalVariablesCache = {};
    /** @type {string[]} */
    let componentsToCleanCache = [];
    /** @type {string[]} */
    let componentsToRestartCache = [];
    /** @type {SystemAnalysisResponse | {}} */
    let analysisResultsCache = {};

    // Caches to preserve step states for Back button transitions
    /** @type {ScanData | null} */
    let lastScanData = null;
    let lastSubnetInput = '';

    const clearAllWizardState = () => {
        managedDeviceCache = {};
        selectedComponentsCache = [];
        allSoftwareCache = [];
        finalVariablesCache = {};
        componentsToCleanCache = [];
        componentsToRestartCache = [];
        analysisResultsCache = {};
        lastScanData = null;
        lastSubnetInput = '';
    };

    const updateLogoVisibility = () => {
        const logoLight = document.querySelector('.logo-light');
        const logoDark = document.querySelector('.logo-dark');
        if (!logoLight || !logoDark) return;

        const savedTheme = localStorage.getItem("user-theme-preference");
        const isDarkTheme = ["dark", "futuristic-dark", "high-contrast-dark"].includes(savedTheme);

        if (isDarkTheme) {
            logoLight.style.setProperty('display', 'none', 'important');
            logoDark.style.setProperty('display', 'inline-block', 'important');
        } else {
            logoLight.style.setProperty('display', 'inline-block', 'important');
            logoDark.style.setProperty('display', 'none', 'important');
        }
    };

    // Bulletproof: Hide progress bar row and wizard-header directly via CSS selectors
    // const toggleProgressBarVisibility = (show, percentage = 0) => {
    //     // Toggle the slim 4px progress bar container in the card
    //     const progressBarContainer = document.querySelector('.card > .progress');
    //     if (progressBarContainer) {
    //         progressBarContainer.style.display = show ? '' : 'none';
    //     }
    //
    //     // Update the bar width dynamically
    //     const progressBar = document.getElementById('wizard-progress-bar');
    //     if (progressBar && show) {
    //         progressBar.style.width = `${percentage}%`;
    //     }
    //
    //     // Toggle the wizard header gray bar
    //     if (wizardHeader) {
    //         wizardHeader.style.display = show ? '' : 'none';
    //     }
    // };

    const renderStep1_Welcome = () => {
        clearAllWizardState();
        // Option B: Hide progress bar and gray header bar on the Welcome screen (Step 0)
        toggleProgressBarVisibility(false, 0);

        updateWizardFooter('Select a scanning method to find NjordDeploy devices on your network.');

        const savedSubnet = lastSubnetInput || '';

        wizardBody.innerHTML = `
            <div class="text-center">
                <div class="mb-4 logo-container">
                    <!-- Custom 300x300 high-res brand logo centered on Step 0 Onboarding -->
                    <img src="/static/images/njorddeploy-icon512x512.png"
                         alt="NjordDeploy Logo"
                         class="logo-light"
                         style="width: 300px; height: 300px;">
                    <img src="/static/images/njorddeploy-icon512x512-dark.png"
                         alt="NjordDeploy Logo"
                         class="logo-dark"
                         style="width: 300px; height: 300px;">
                </div>
                <h2 class="h4">Network Discovery</h2>
                <p class="text-muted small">We need to find supported single-board computers (Raspberry Pi, Orange Pi, ODROID, Radxa, or Pine64) on your network to begin.</p>

                <div class="card card-body bg-light text-start mx-auto mb-4" style="max-width: 500px;">
                    <div class="form-check mb-2">
                        <input class="form-check-input" type="radio" name="scanMethod" id="autoDetectRadio" checked>
                        <label class="form-check-label fw-bold" for="autoDetectRadio">
                            <strong>Auto-Detect (Recommended)</strong>
                            <span class="d-block small text-muted">Scans your current local subnet automatically.</span>
                        </label>
                    </div>
                    <div class="form-check mb-2">
                        <input class="form-check-input" type="radio" name="scanMethod" id="manualScanRadio">
                        <label class="form-check-label" for="manualScanRadio">
                            <strong>Manual Subnet Scan</strong>
                            <span class="d-block small text-muted">Use this if you are on a different VLAN or VPN.</span>
                        </label>
                    </div>
                    <div class="mt-2 mb-3">
                        <input type="text" id="manualSubnetInput" class="form-control" placeholder="e.g. 192.168.1.0/24" value="${escapeHTML(savedSubnet)}" disabled aria-label="Manual subnet input">
                    </div>
                    <div class="form-check mb-2">
                        <input class="form-check-input" type="radio" name="scanMethod" id="method_direct_ip" value="direct_ip">
                        <label class="form-check-label" for="method_direct_ip">
                            <strong>Direct IP / Hostname / MAC Deployment</strong>
                            <span class="d-block small text-muted">Target a specific host or local MAC address directly, bypassing standard discovery.</span>
                        </label>
                    </div>
                    <div class="mt-2 mb-3 d-none" id="direct_ip_input_container">
                        <input type="text" class="form-control" name="direct_target_ip" id="direct_target_ip" placeholder="e.g., 100.121.216.150 or b8:27:eb:01:02:03" aria-label="Direct Target IP">
                    </div>
                    <div class="form-check mb-2">
                        <input class="form-check-input" type="radio" name="scanMethod" id="method_tailscale" value="tailscale" disabled>
                        <label class="form-check-label" for="method_tailscale">
                            <strong><i class="fa-solid fa-network-wired me-1"></i> Tailscale / Headscale Mesh Discovery</strong>
                            <span class="badge bg-secondary ms-2" id="tailscale-status-badge"><i class="fa-solid fa-circle-notch fa-spin me-1"></i>Checking...</span>
                            <span class="d-block small text-muted">Automatically discover online nodes across your Tailscale / Headscale overlay network.</span>
                        </label>
                    </div>
                    <div class="form-check mb-2">
                        <input class="form-check-input" type="radio" name="scanMethod" id="method_proxmox_lxc" value="proxmox_lxc">
                        <label class="form-check-label fw-bold" for="method_proxmox_lxc">
                            <strong>Create New Proxmox LXC Target</strong>
                            <span class="d-block small text-muted">Provision a brand new LXC container on your Proxmox VE server automatically.</span>
                        </label>
                    </div>
                    <div class="mt-2 d-none" id="proxmox_lxc_input_container">
                        <div class="row g-2">
                            <div class="col-sm-12">
                                <label for="lxc_hostname" class="form-label small mb-1">Container Name (Hostname)</label>
                                <input type="text" class="form-control form-control-sm" id="lxc_hostname" placeholder="e.g. njord-server">
                            </div>
                            <div class="col-sm-6">
                                <label for="lxc_cores" class="form-label small mb-1">CPU Cores</label>
                                <input type="number" class="form-control form-control-sm" id="lxc_cores" value="2" min="1">
                            </div>
                            <div class="col-sm-6">
                                <label for="lxc_memory" class="form-label small mb-1">RAM (MB)</label>
                                <input type="number" class="form-control form-control-sm" id="lxc_memory" value="4096" min="512">
                            </div>
                            <div class="col-sm-6">
                                <label for="lxc_storage_size" class="form-label small mb-1">Storage (GB)</label>
                                <input type="number" class="form-control form-control-sm" id="lxc_storage_size" value="20" min="5">
                            </div>
                            <div class="col-sm-6">
                                <label for="lxc_storage_name" class="form-label small mb-1">Storage Pool</label>
                                <input type="text" class="form-control form-control-sm" id="lxc_storage_name" value="local-lvm">
                            </div>
                        </div>
                    </div>
                    <div class="form-check mb-2">
                        <input class="form-check-input" type="radio" name="scanMethod" id="method_proxmox_vm" value="proxmox_vm">
                        <label class="form-check-label fw-bold" for="method_proxmox_vm">
                            <strong>Create New Proxmox VM Target</strong>
                            <span class="d-block small text-muted">Clone and provision a brand new QEMU VM from a Proxmox template.</span>
                        </label>
                    </div>
                    <div class="mt-2 d-none" id="proxmox_vm_input_container">
                        <div class="row g-2">
                            <div class="col-sm-6">
                                <label for="vm_hostname" class="form-label small mb-1">VM Name (Hostname)</label>
                                <input type="text" class="form-control form-control-sm" id="vm_hostname" placeholder="e.g. njord-vm">
                            </div>
                            <div class="col-sm-6">
                                <label for="vm_template_select" class="form-label small mb-1">Source VM Template</label>
                                <div class="input-group input-group-sm">
                                    <select class="form-select form-select-sm" id="vm_template_select">
                                        <option value="">-- Load Templates --</option>
                                    </select>
                                    <input type="number" class="form-control form-control-sm" id="vm_template_manual" placeholder="VMID" style="max-width: 80px;">
                                </div>
                            </div>
                            <div class="col-sm-6">
                                <label for="vm_cores" class="form-label small mb-1">CPU Cores</label>
                                <input type="number" class="form-control form-control-sm" id="vm_cores" value="2" min="1">
                            </div>
                            <div class="col-sm-6">
                                <label for="vm_memory" class="form-label small mb-1">RAM (MB)</label>
                                <input type="number" class="form-control form-control-sm" id="vm_memory" value="4096" min="512">
                            </div>
                            <div class="col-sm-6">
                                <label for="vm_storage_name" class="form-label small mb-1">Storage Pool</label>
                                <input type="text" class="form-control form-control-sm" id="vm_storage_name" value="local-lvm">
                            </div>
                            <div class="col-sm-6">
                                <label for="vm_storage_size" class="form-label small mb-1">Storage Size (GB)</label>
                                <input type="number" class="form-control form-control-sm" id="vm_storage_size" value="32" min="10">
                            </div>
                            <div class="col-sm-6">
                                <label for="vm_username" class="form-label small mb-1">VM Username</label>
                                <input type="text" class="form-control form-control-sm" id="vm_username" value="debian">
                            </div>
                        </div>
                    </div>
                    <div class="form-check mb-2">
                        <input class="form-check-input" type="radio" name="scanMethod" id="method_proxmox_existing" value="proxmox_existing">
                        <label class="form-check-label fw-bold" for="method_proxmox_existing">
                            <strong>Select Existing Proxmox Target</strong>
                            <span class="d-block small text-muted">Deploy to an existing VM or LXC container on your Proxmox server.</span>
                        </label>
                    </div>
                    <div class="mt-2 d-none" id="proxmox_existing_container">
                        <div class="mb-2">
                            <button type="button" class="btn btn-sm btn-outline-secondary" id="refresh-proxmox-targets-btn">
                                <i class="fa-solid fa-sync me-1"></i> Load/Refresh Targets
                            </button>
                        </div>
                        <div class="form-text text-danger d-none mb-2" id="proxmox_targets_error"></div>
                        <select class="form-select form-select-sm" id="proxmox_target_select" aria-label="Select Target">
                            <option value="">-- Click refresh/load to fetch targets --</option>
                        </select>
                    </div>
                </div>

                <div class="d-grid gap-2 col-8 mx-auto my-4">
                    <button id="begin-scan-btn" class="btn btn-primary btn-lg">
                        <i class="fa-solid fa-search me-2"></i> Begin Scan
                    </button>
                </div>
            </div>
        `;
        setupStep1();
        updateLogoVisibility();
    };

    /** @param {ScanData} scanData */
    const renderStep2_ConfigureDevices = (scanData) => {
        // Option B: Visual progress bar and header bar start here at 25%!
        toggleProgressBarVisibility(true, 25);
        if (wizardHeader) {
            wizardHeader.innerHTML = '<strong>Step 1 of 4: Discovery &amp; SSH</strong>';
        }
        updateWizardFooter('Enter the SSH credentials for the devices you want to manage.');
        const popoverContent = `
            The scanner looks for two types of devices:
            1. Physical single-board computers by checking for a hardware model file.
            2. NjordDeploy Virtual Pis by checking for the
               '/etc/njorddeploy-virtual-pi-server' file inside the guest OS.
        `.trim();
// Changed grid columns to support up to 6 Pis on desktop, and set gap to g-3
            wizardBody.innerHTML = `
                <div class="text-start">
                    <h2 class="h4 text-center">
                        Device Configuration
                        <i class="fa-solid fa-circle-question text-muted ms-2" style="font-size: 0.8em; cursor: pointer;"
                           data-bs-toggle="popover" data-bs-trigger="hover focus"
                           data-bs-title="How Detection Works"
                           data-bs-content="${escapeHTML(popoverContent)}"></i>
                    </h2>
                    <p class="text-muted text-center small mb-4">
                        Found ${scanData.hosts.length} potential Pi network interfaces.
                        Provide credentials for each device to get more details.
                    </p>
                    <div class="card card-body bg-light mb-4">
                        <h3 class="h6">Common Actions</h3>
                        <p class="small text-muted">
                            Use these fields to apply credentials to all devices, or to clear all selections.
                        </p>
                        <div class="row g-2">
                            <div class="col-sm-4">
                                <input type="text" class="form-control form-control-sm" id="master-username" placeholder="Username">
                            </div>
                            <div class="col-sm-4">
                                <div class="input-group input-group-sm">
                                    <input type="password" class="form-control form-control-sm" id="master-password" placeholder="Password">
                                    <button class="btn btn-outline-secondary toggle-password-btn" type="button" tabindex="-1" title="Show/Hide Password">
                                        <i class="fa-solid fa-eye"></i>
                                    </button>
                                </div>
                            </div>
                            <div class="col-sm-2 d-grid">
                                <button class="btn btn-secondary btn-sm" id="apply-to-all-btn">Apply</button>
                            </div>
                            <div class="col-sm-2 d-grid">
                                <button class="btn btn-outline-secondary btn-sm" id="deselect-all-btn">Clear All</button>
                            </div>
                        </div>
                    </div>
                    <div id="device-cards-container" class="row row-cols-1 row-cols-md-2 row-cols-xl-3 g-3"></div>
                    <div class="d-grid gap-2 col-8 mx-auto my-4" id="step2-action-area"></div>
                </div>
            `;
            const container = document.getElementById('device-cards-container');
        scanData.hosts.forEach((host, index) => {
            const cachedDevice = managedDeviceCache[host.ip];
            const isManaged = !!cachedDevice;
            const savedUser = cachedDevice ? cachedDevice.username : '';
            const savedPass = cachedDevice ? cachedDevice.password : '';

            const cardWrapper = document.createElement('div');
            cardWrapper.className = 'col';

            const card = document.createElement('div');
            card.className = 'card h-100 device-card shadow-sm';
            card.dataset.ip = host.ip;
            card.dataset.hostname = host.hostname || 'Unknown Host';

            const header = document.createElement('div');
            header.className = 'card-header bg-light';

            const title = document.createElement('div');
            title.className = 'fw-bold text-truncate mb-2';
            title.title = host.hostname || 'Unknown Host';

            const serverIcon = document.createElement('i');
            serverIcon.className = 'fa-solid fa-server me-2';
            title.appendChild(serverIcon);
            title.appendChild(document.createTextNode(host.hostname || 'Unknown Host'));

            const formCheck = document.createElement('div');
            formCheck.className = 'form-check form-switch';

            const switchInput = document.createElement('input');
            switchInput.className = 'form-check-input';
            switchInput.type = 'checkbox';
            switchInput.role = 'switch';
            switchInput.id = `manageDeviceSwitch-${index}`;
            switchInput.checked = isManaged;

            const switchLabel = document.createElement('label');
            switchLabel.className = 'form-check-label';
            switchLabel.htmlFor = `manageDeviceSwitch-${index}`;
            switchLabel.textContent = 'Manage';

            formCheck.appendChild(switchInput);
            formCheck.appendChild(switchLabel);

            header.appendChild(title);
            header.appendChild(formCheck);

            const body = document.createElement('div');
            body.className = 'card-body d-flex flex-column';

            const ipMacDiv = document.createElement('div');
            ipMacDiv.className = 'mb-3';

            const ipDiv = document.createElement('div');
            ipDiv.className = 'fw-bold text-primary';
            ipDiv.style.fontSize = '1.1rem';
            ipDiv.textContent = `IP: ${host.ip}`;

            const macDiv = document.createElement('div');
            macDiv.className = 'text-muted small';
            macDiv.textContent = `MAC: ${host.mac}`;

            ipMacDiv.appendChild(ipDiv);
            ipMacDiv.appendChild(macDiv);

            const rowG2 = document.createElement('div');
            rowG2.className = 'row g-2';

            const colUsername = document.createElement('div');
            colUsername.className = 'col-sm-6';
            const usernameInput = document.createElement('input');
            usernameInput.type = 'text';
            usernameInput.className = 'form-control form-control-sm device-username';
            usernameInput.placeholder = 'Username';
            usernameInput.value = savedUser;
            usernameInput.disabled = !isManaged;
            colUsername.appendChild(usernameInput);

            const colPassword = document.createElement('div');
            colPassword.className = 'col-sm-6';
            const passGroup = document.createElement('div');
            passGroup.className = 'input-group input-group-sm';
            const passwordInput = document.createElement('input');
            passwordInput.type = 'password';
            passwordInput.className = 'form-control form-control-sm device-password';
            passwordInput.placeholder = 'Password';
            passwordInput.value = savedPass;
            passwordInput.disabled = !isManaged;
            const passToggleBtn = document.createElement('button');
            passToggleBtn.type = 'button';
            passToggleBtn.className = 'btn btn-outline-secondary btn-sm toggle-password-btn';
            passToggleBtn.tabIndex = -1;
            passToggleBtn.title = 'Show/Hide Password';
            passToggleBtn.innerHTML = '<i class="fa-solid fa-eye"></i>';
            passGroup.appendChild(passwordInput);
            passGroup.appendChild(passToggleBtn);
            colPassword.appendChild(passGroup);

            rowG2.appendChild(colUsername);
            rowG2.appendChild(colPassword);

            const hwDetails = document.createElement('div');
            hwDetails.className = 'hardware-details mt-auto pt-3';
            hwDetails.style.fontSize = '0.8rem';
            hwDetails.style.display = isManaged ? 'block' : 'none';

            if (isManaged && cachedDevice) {
                const hr = document.createElement('hr');
                hr.className = 'my-2';
                hwDetails.appendChild(hr);

                const serialSpan = document.createElement('span');
                const chipIcon = document.createElement('i');
                chipIcon.className = 'fa-solid fa-microchip me-1';
                serialSpan.appendChild(chipIcon);
                serialSpan.appendChild(document.createTextNode(` Serial: ${cachedDevice.serial || 'N/A'}`));
                hwDetails.appendChild(serialSpan);
                hwDetails.appendChild(document.createElement('br'));

                const ramSpan = document.createElement('span');
                const ramIcon = document.createElement('i');
                ramIcon.className = 'fa-solid fa-memory me-1';
                ramSpan.appendChild(ramIcon);
                ramSpan.appendChild(document.createTextNode(` RAM: ${cachedDevice.ram || 'N/A'}`));
                hwDetails.appendChild(ramSpan);
                hwDetails.appendChild(document.createElement('br'));

                const diskInfo = cachedDevice.disks && cachedDevice.disks.length > 0 ? cachedDevice.disks.find(d => d.mounted_on === '/') : null;
                const diskSpan = document.createElement('span');
                const diskIcon = document.createElement('i');
                diskIcon.className = 'fa-solid fa-hard-drive me-1';
                diskSpan.appendChild(diskIcon);
                const diskText = diskInfo ? ` Disk: ${diskInfo.size} (${diskInfo.pcent} used)` : ' Disk: N/A';
                diskSpan.appendChild(document.createTextNode(diskText));
                hwDetails.appendChild(diskSpan);
            }

            body.appendChild(ipMacDiv);
            body.appendChild(rowG2);
            body.appendChild(hwDetails);

            const footer = document.createElement('div');
            footer.className = 'card-footer text-body-secondary small';
            footer.appendChild(document.createTextNode('Status: '));
            const statusSpan = document.createElement('span');
            statusSpan.className = 'status-text';
            if (isManaged && cachedDevice) {
                statusSpan.className = 'status-text text-success fw-bold';
                statusSpan.textContent = `Success! (Model: ${cachedDevice.model || 'Unknown Model'})`;
            } else {
                statusSpan.textContent = 'Pending credentials...';
            }
            footer.appendChild(statusSpan);

            card.appendChild(header);
            card.appendChild(body);
            card.appendChild(footer);

            cardWrapper.appendChild(card);
            container.appendChild(cardWrapper);
        });

        document.querySelectorAll('.device-card').forEach(card => {
            const manageSwitch = /** @type {HTMLInputElement} */ (card.querySelector('[type="checkbox"]'));
            const usernameInput = /** @type {HTMLInputElement} */ (card.querySelector('.device-username'));
            const passwordInput = /** @type {HTMLInputElement} */ (card.querySelector('.device-password'));

            if (manageSwitch && usernameInput && passwordInput) {
                const handleSwitchChange = () => {
                    const isDisabled = !manageSwitch.checked;
                    usernameInput.disabled = isDisabled;
                    passwordInput.disabled = isDisabled;
                    if (manageSwitch.checked) {
                        usernameInput.focus();
                    }
                };
                manageSwitch.addEventListener('change', handleSwitchChange);

                [usernameInput, passwordInput].forEach(input => {
                    input.addEventListener('input', () => {
                        if (!manageSwitch.checked && input.value.length > 0) {
                            manageSwitch.checked = true;
                            handleSwitchChange();
                        }
                    });
                });
                handleSwitchChange();
            }
        });

        document.getElementById('apply-to-all-btn').addEventListener('click', () => {
            const masterUsername = (/** @type {HTMLInputElement} */ (document.getElementById('master-username'))).value;
            const masterPassword = (/** @type {HTMLInputElement} */ (document.getElementById('master-password'))).value;
            document.querySelectorAll('.device-username').forEach(input => (/** @type {HTMLInputElement} */ (input)).value = masterUsername);
            document.querySelectorAll('.device-password').forEach(input => (/** @type {HTMLInputElement} */ (input)).value = masterPassword);
        });
        document.getElementById('deselect-all-btn').addEventListener('click', () => {
            document.querySelectorAll('.device-card .form-check-input').forEach(s => (/** @type {HTMLInputElement} */ (s)).checked = false);
        });

        // Set up the Back/Proceed action buttons dynamically
        const actionWrapper = document.createElement('div');
        actionWrapper.className = 'sticky-action-bar';

        const backBtn = document.createElement('button');
        backBtn.id = 'back-to-step1-btn';
        backBtn.className = 'btn btn-outline-secondary btn-lg';
        backBtn.innerHTML = '<i class="fa-solid fa-arrow-left me-2"></i>Back';
        backBtn.addEventListener('click', renderStep1_Welcome);
        actionWrapper.appendChild(backBtn);

        const getDetailsBtn = document.createElement('button');
        getDetailsBtn.id = 'get-details-btn';
        getDetailsBtn.className = 'btn btn-primary btn-lg';
        getDetailsBtn.innerHTML = '<i class="fa-solid fa-plug-circle-check me-2"></i>Connect & Get Details';
        getDetailsBtn.addEventListener('click', handleGetDeviceDetails);
        actionWrapper.appendChild(getDetailsBtn);

        if (Object.keys(managedDeviceCache).length > 0) {
            const proceedBtn = document.createElement('button');
            proceedBtn.id = 'proceed-to-step3-btn';
            proceedBtn.className = 'btn btn-success btn-lg';
            proceedBtn.innerHTML = '<i class="fa-solid fa-arrow-right-to-bracket me-2"></i>Proceed';
            proceedBtn.addEventListener('click', renderStep3_SelectSoftware);
            actionWrapper.appendChild(proceedBtn);
        }

        const step2ActionArea = document.getElementById('step2-action-area');
        if (step2ActionArea) {
            step2ActionArea.textContent = '';
            step2ActionArea.appendChild(actionWrapper);
        }

        const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');
        Array.from(popoverTriggerList).forEach(el => new bootstrap.Popover(el, {}));
    };

    const handleGetDeviceDetails = async () => {
        managedDeviceCache = {};
        const step2ActionArea = document.getElementById('step2-action-area');
        const getDetailsBtn = document.getElementById('get-details-btn');
        setButtonState(getDetailsBtn, true, {loadingText: 'Connecting...'});

        const promises = [];
        document.querySelectorAll('.device-card').forEach(card => {
            if (!(/** @type {HTMLInputElement} */ (card.querySelector('[type="checkbox"]'))).checked) return;

            const ip = (/** @type {HTMLElement} */ (card)).dataset.ip;
            const hostname = (/** @type {HTMLElement} */ (card)).dataset.hostname;
            const username = (/** @type {HTMLInputElement} */ (card.querySelector('.device-username'))).value;
            const password = (/** @type {HTMLInputElement} */ (card.querySelector('.device-password'))).value;
            const statusEl = card.querySelector('.status-text');
            const detailsEl = (/** @type {HTMLElement} */ (card.querySelector('.hardware-details')));

            detailsEl.style.display = 'none';
            detailsEl.textContent = '';
            statusEl.className = 'status-text text-primary';
            statusEl.textContent = 'Connecting...';

            const promise = fetchAPI('/get-device-details', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ip, username, password})
            })
                .then(data => {
                    /** @type {DeviceDetails} */
                    const details = data.details || data;

                    statusEl.className = 'status-text text-success fw-bold';
                    statusEl.textContent = `Success! (Model: ${details.model || 'Unknown Model'})`;
                    managedDeviceCache[ip] = { ...details, ip, username, password, hostname };

                    const diskInfo = details.disks && details.disks.length > 0 ? details.disks.find(d => d.mounted_on === '/') : null;

                    const hr = document.createElement('hr');
                    hr.className = 'my-2';
                    detailsEl.appendChild(hr);

                    const serialSpan = document.createElement('span');
                    const chipIcon = document.createElement('i');
                    chipIcon.className = 'fa-solid fa-microchip me-1';
                    serialSpan.appendChild(chipIcon);
                    serialSpan.appendChild(document.createTextNode(` Serial: ${details.serial || 'N/A'}`));
                    detailsEl.appendChild(serialSpan);
                    detailsEl.appendChild(document.createElement('br'));

                    const ramSpan = document.createElement('span');
                    const ramIcon = document.createElement('i');
                    ramIcon.className = 'fa-solid fa-memory me-1';
                    ramSpan.appendChild(ramIcon);
                    ramSpan.appendChild(document.createTextNode(` RAM: ${details.ram || 'N/A'}`));
                    detailsEl.appendChild(ramSpan);
                    detailsEl.appendChild(document.createElement('br'));

                    const diskSpan = document.createElement('span');
                    const diskIcon = document.createElement('i');
                    diskIcon.className = 'fa-solid fa-hard-drive me-1';
                    diskSpan.appendChild(diskIcon);
                    const diskText = diskInfo ? ` Disk: ${diskInfo.size} (${diskInfo.pcent} used)` : ' Disk: N/A';
                    diskSpan.appendChild(document.createTextNode(diskText));
                    detailsEl.appendChild(diskSpan);

                    detailsEl.style.display = 'block';
                })
                .catch(error => {
                    console.error(`Error for IP ${ip}:`, error);
                    statusEl.className = 'status-text text-danger';
                    statusEl.textContent = `Failed: ${error.message || 'Unknown error'}`;
                    delete managedDeviceCache[ip];
                });
            promises.push(promise);
        });

        await Promise.allSettled(promises);

        const actionWrapper = document.createElement('div');
        actionWrapper.className = 'sticky-action-bar';

        const backBtn = document.createElement('button');
        backBtn.id = 'back-to-step1-btn';
        backBtn.className = 'btn btn-outline-secondary btn-lg';
        backBtn.innerHTML = '<i class="fa-solid fa-arrow-left me-2"></i>Back';
        backBtn.addEventListener('click', renderStep1_Welcome);
        actionWrapper.appendChild(backBtn);

        actionWrapper.appendChild(getDetailsBtn);

        if (Object.keys(managedDeviceCache).length > 0) {
            const proceedBtn = document.createElement('button');
            proceedBtn.id = 'proceed-to-step3-btn';
            proceedBtn.className = 'btn btn-success btn-lg';
            proceedBtn.innerHTML = '<i class="fa-solid fa-arrow-right-to-bracket me-2"></i>Proceed';
            proceedBtn.addEventListener('click', renderStep3_SelectSoftware);
            actionWrapper.appendChild(proceedBtn);

            updateWizardFooter(`Found ${Object.keys(managedDeviceCache).length} manageable device(s). Ready to proceed.`, 'success');
        } else {
            updateWizardFooter('No devices could be contacted. Check credentials and click "Try Again".', 'danger');
        }

        setButtonState(getDetailsBtn, false, {text: '<i class="fa-solid fa-plug-circle-check me-2"></i>Try Again'});
        if (step2ActionArea) {
            step2ActionArea.textContent = '';
            step2ActionArea.appendChild(actionWrapper);
        }
    };

    /** @param {Component} component
     * @param {string} groupName
     * @param {boolean} isExclusive
     */
    const createComponentCard = (component, groupName, isExclusive) => {
        const escapedId = escapeHTML(component.id);
        const escapedName = escapeHTML(component.name);
        const escapedDesc = escapeHTML(component.description);
        const isChecked = selectedComponentsCache.includes(component.id) || component.default;

        let iconClass = "fa-solid fa-cubes text-secondary";
        const lowerId = component.id.toLowerCase();
        if (lowerId.includes("nextcloud")) {
            iconClass = "fa-solid fa-cloud text-primary";
        } else if (lowerId.includes("vaultwarden") || lowerId.includes("bitwarden")) {
            iconClass = "fa-solid fa-key text-warning";
        } else if (lowerId.includes("caddy")) {
            iconClass = "fa-solid fa-network-wired text-info";
        } else if (lowerId.includes("nginx")) {
            iconClass = "fa-solid fa-server text-info";
        } else if (lowerId.includes("pi-hole") || lowerId.includes("adguard")) {
            iconClass = "fa-solid fa-shield-halved text-danger";
        } else if (lowerId.includes("gitea") || lowerId.includes("git")) {
            iconClass = "fa-brands fa-git-alt text-warning";
        } else if (lowerId.includes("home-assistant") || lowerId.includes("homeassistant")) {
            iconClass = "fa-solid fa-house-laptop text-success";
        } else if (lowerId.includes("portainer")) {
            iconClass = "fa-brands fa-docker text-primary";
        } else if (lowerId.includes("filebrowser")) {
            iconClass = "fa-solid fa-folder-open text-warning";
        } else if (lowerId.includes("homarr")) {
            iconClass = "fa-solid fa-table-columns text-info";
        } else if (lowerId.includes("redis")) {
            iconClass = "fa-solid fa-database text-danger";
        } else if (lowerId.includes("mariadb") || lowerId.includes("mysql") || lowerId.includes("postgres")) {
            iconClass = "fa-solid fa-database text-primary";
        } else if (lowerId.includes("litellm") || lowerId.includes("open-webui") || lowerId.includes("ollama") || lowerId.includes("qwen")) {
            iconClass = "fa-solid fa-robot text-primary";
        }

        let matrixBadgeHtml = "";
        const supMatrix = component.supported_matrix;
        if (supMatrix && typeof supMatrix === 'object') {
            const engines = Array.isArray(supMatrix.engines) ? supMatrix.engines : ['docker', 'podman'];
            const modes = Array.isArray(supMatrix.modes) ? supMatrix.modes : ['lxc', 'vm'];
            const isDockerOnly = engines.length === 1 && engines[0] === 'docker';
            const isPodmanOnly = engines.length === 1 && engines[0] === 'podman';
            const isVmOnly = modes.length === 1 && modes[0] === 'vm';
            const isLxcOnly = modes.length === 1 && modes[0] === 'lxc';

            if (isDockerOnly) {
                matrixBadgeHtml += `<span class="badge bg-primary-subtle text-primary border border-primary-subtle small me-1 mb-2"><i class="fa-brands fa-docker me-1"></i>Docker Only</span>`;
            } else if (isPodmanOnly) {
                matrixBadgeHtml += `<span class="badge bg-warning-subtle text-warning border border-warning-subtle small me-1 mb-2"><i class="fa-solid fa-feather-pointed me-1"></i>Podman Only</span>`;
            }
            if (isVmOnly) {
                matrixBadgeHtml += `<span class="badge bg-info-subtle text-info border border-info-subtle small mb-2"><i class="fa-solid fa-server me-1"></i>VM Only</span>`;
            } else if (isLxcOnly) {
                matrixBadgeHtml += `<span class="badge bg-secondary-subtle text-secondary border border-secondary-subtle small mb-2"><i class="fa-solid fa-box me-1"></i>LXC Only</span>`;
            }
        }

        const cardClass = isChecked ? "card h-100 component-card border-success" : "card h-100 component-card";
        const btnClass = isChecked ? "btn btn-success btn-select-software w-100" : "btn btn-outline-primary btn-select-software w-100";
        const btnText = isChecked ? '<i class="fa-solid fa-check me-2"></i>Selected' : 'Select';
        const checkedAttr = isChecked ? 'checked' : '';

        const searchKeywords = [
            component.name || '',
            component.id || '',
            component.description || '',
            groupName || '',
            ...(Array.isArray(component.tags) ? component.tags : [])
        ].join(' ').toLowerCase();

        return `
            <div class="col">
                <div class="${cardClass}" style="cursor: pointer; transition: all 0.2s;" data-component-id="${escapedId}" data-group-name="${escapeHTML(groupName)}" data-exclusive="${isExclusive}" data-search-text="${escapeHTML(searchKeywords)}">
                    <div class="card-body d-flex flex-column align-items-center text-center p-3">
                        <div class="mb-3 p-3 bg-light rounded-circle d-flex align-items-center justify-content-center" style="width: 70px; height: 70px; background-color: rgba(255,255,255,0.05) !important;">
                            <i class="${iconClass} fa-2x"></i>
                        </div>
                        ${matrixBadgeHtml ? `<div>${matrixBadgeHtml}</div>` : ''}
                        <h5 class="card-title fw-bold mb-2">${escapedName}</h5>
                        <p class="card-text small text-muted flex-grow-1">${escapedDesc}</p>
                        <input type="checkbox" class="form-check-input d-none" id="comp-${escapedId}" value="${escapedId}" ${checkedAttr}>
                        <button class="${btnClass} mt-3" type="button" style="pointer-events: none;">${btnText}</button>
                    </div>
                </div>
            </div>
        `;
    };

    const renderStep3_SelectSoftware = async () => {
        // Option B: Visual progress bar at 50%
        toggleProgressBarVisibility(true, 50);
        if (wizardHeader) {
            wizardHeader.innerHTML = '<strong>Step 2 of 4: Select Software</strong>';
        }
        updateWizardFooter('Choose software to install. Selections in a category are mutually exclusive.');

        try {
            /** @type {[SoftwareResponseData, GroupData]} */
            const [softwareData, groupsData] = await Promise.all([
                fetchAPI('/get-available-software', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({devices: Object.values(managedDeviceCache)})
                }),
                fetchAPI('/get-software-groups')
            ]);

            allSoftwareCache = softwareData.available_software;
            const packages = softwareData.available_packages || {};
            const groups = groupsData.groups;
            const allGroupedComponents = new Set(Object.values(groups).flatMap(g => Array.isArray(g) ? g : g.components));

            let tabNavHTML = '<div class="nav flex-column nav-pills" id="v-pills-tab" role="tablist" aria-orientation="vertical">';
            let tabContentHTML = '<div class="tab-content" id="v-pills-tabContent">';
            let active = 'active';

            // Add Packages section first if packages exist
            if (Object.keys(packages).length > 0) {
                const activeClass = active ? 'show active' : '';
                tabNavHTML += `
                    <button class="nav-link ${active}" id="v-pills-packages-tab" data-bs-toggle="pill" data-bs-target="#v-pills-packages" type="button" role="tab">
                        <i class="fa-solid fa-layer-group me-2 text-warning"></i>Turnkey Stacks & Bundles
                    </button>`;

                tabContentHTML += `
                    <div class="tab-pane fade ${activeClass}" id="v-pills-packages" role="tabpanel">
                        <div class="d-flex flex-wrap justify-content-between align-items-center border-bottom pb-2 mb-3">
                            <div>
                                <h3 class="h5 mb-1"><i class="fa-solid fa-layer-group me-2 text-primary"></i>1-Click Turnkey Bundles & Stacks</h3>
                                <p class="text-muted small mb-0">Select an integrated, production-tested bundle tailored for MSPs, enterprise workflows, or homelabs.</p>
                            </div>
                        </div>
                        <div class="row row-cols-1 row-cols-lg-2 row-cols-xl-3 g-3">`;

                Object.keys(packages).forEach(pkgId => {
                    const pkg = packages[pkgId];
                    const pkgComponents = (pkg.components && Array.isArray(pkg.components))
                        ? allSoftwareCache.filter(c => pkg.components.includes(c.id))
                        : allSoftwareCache.filter(c => c.package_id === pkgId);
                    const compNames = pkgComponents.map(c => c.name).join(', ');
                    const escapedPkgId = escapeHTML(pkgId);
                    const escapedPkgName = escapeHTML(pkg.name);
                    const escapedPkgDesc = escapeHTML(pkg.description || 'A pre-configured turnkey stack of services.');

                    const isMsp = (pkg.badge && pkg.badge.toLowerCase().includes('msp')) || pkgId.includes('workplace') || pkgId.includes('archive') || pkgId.includes('agile') || pkgId.includes('observability');
                    const badgeClass = isMsp ? 'bg-primary text-white' : 'bg-secondary text-white';
                    const badgeIcon = isMsp ? 'fa-solid fa-briefcase' : 'fa-solid fa-cubes';
                    const badgeText = pkg.badge || (isMsp ? 'MSP Turnkey Bundle' : 'Curated Stack');
                    const iconClass = pkg.icon || (isMsp ? 'fa-solid fa-briefcase' : 'fa-solid fa-layer-group');

                    const pkgSearchText = [
                        pkg.name || '',
                        pkgId || '',
                        pkg.description || '',
                        badgeText || '',
                        compNames || ''
                    ].join(' ').toLowerCase();

                    const pillsHtml = pkgComponents.map(c => `
                        <span class="badge bg-body-secondary text-body border small text-truncate" style="max-width: 140px;" title="${escapeHTML(c.name)}">
                            <i class="fa-solid fa-cube text-primary me-1"></i>${escapeHTML(c.name)}
                        </span>
                    `).join('');

                    tabContentHTML += `
                        <div class="col">
                            <div class="card h-100 package-card border-primary shadow-sm" style="cursor: pointer; transition: all 0.25s ease;" data-package-id="${escapedPkgId}" data-components="${escapeHTML(JSON.stringify(pkgComponents.map(c=>c.id)))}" data-search-text="${escapeHTML(pkgSearchText)}">
                                <div class="card-body d-flex flex-column align-items-center text-center p-3">
                                    <div class="d-flex justify-content-between align-items-center w-100 mb-2">
                                        <span class="badge ${badgeClass} shadow-sm"><i class="${badgeIcon} me-1"></i>${escapeHTML(badgeText)}</span>
                                        <span class="badge bg-dark-subtle text-body-secondary small">${pkgComponents.length} Apps</span>
                                    </div>
                                    <div class="mb-2 p-3 bg-light rounded-circle d-flex align-items-center justify-content-center shadow-sm" style="width: 60px; height: 60px; background-color: rgba(255,255,255,0.05) !important;">
                                        <i class="${escapeHTML(iconClass)} text-primary fa-xl"></i>
                                    </div>
                                    <h5 class="card-title fw-bold mb-1 fs-6">${escapedPkgName}</h5>
                                    <p class="card-text small text-muted flex-grow-1 mb-2">${escapedPkgDesc}</p>
                                    <div class="d-flex flex-wrap justify-content-center gap-1 my-2 w-100" style="max-height: 75px; overflow-y: auto;">
                                        ${pillsHtml}
                                    </div>
                                    <input type="checkbox" class="form-check-input package-checkbox d-none" id="pkg-${escapedPkgId}" value="${escapedPkgId}">
                                    <button class="btn btn-outline-primary btn-select-package mt-2 w-100" type="button" style="pointer-events: none;">
                                        <i class="fa-solid fa-wand-magic-sparkles me-1"></i>Select 1-Click Bundle
                                    </button>
                                </div>
                            </div>
                        </div>
                    `;
                });
                tabContentHTML += `</div></div>`;
                active = ''; // Clear active state
            }

            // Add Groups
            Object.keys(groups).forEach((groupName) => {
                const groupInfo = groups[groupName];
                const isExclusive = Array.isArray(groupInfo) ? false : groupInfo.is_exclusive;
                const compList = Array.isArray(groupInfo) ? groupInfo : groupInfo.components;
                const tabId = `v-pills-${groupName.replace(/\s+/g, '-')}`;
                const activeClass = active ? 'show active' : '';

                let iconClass = "fa-solid fa-shapes";
                const lowerGroup = groupName.toLowerCase();
                if (lowerGroup.includes("database")) {
                    iconClass = "fa-solid fa-database";
                } else if (lowerGroup.includes("productivity")) {
                    iconClass = "fa-solid fa-cubes";
                } else if (lowerGroup.includes("network") || lowerGroup.includes("dns")) {
                    iconClass = "fa-solid fa-circle-nodes";
                } else if (lowerGroup.includes("security")) {
                    iconClass = "fa-solid fa-shield-halved";
                } else if (lowerGroup.includes("ai") || lowerGroup.includes("llm")) {
                    iconClass = "fa-solid fa-robot";
                } else if (lowerGroup.includes("media")) {
                    iconClass = "fa-solid fa-photo-film";
                } else if (lowerGroup.includes("home") || lowerGroup.includes("iot") || lowerGroup.includes("automation")) {
                    iconClass = "fa-solid fa-house-signal";
                } else if (lowerGroup.includes("chat") || lowerGroup.includes("message") || lowerGroup.includes("communication")) {
                    iconClass = "fa-solid fa-comments";
                } else if (lowerGroup.includes("system") || lowerGroup.includes("tool") || lowerGroup.includes("utilities")) {
                    iconClass = "fa-solid fa-toolbox";
                } else if (lowerGroup.includes("dashboard")) {
                    iconClass = "fa-solid fa-gauge-high";
                }

                tabNavHTML += `
                    <button class="nav-link ${active}" id="${tabId}-tab" data-bs-toggle="pill" data-bs-target="#${tabId}" type="button" role="tab">
                        <i class="${iconClass} me-2"></i>${escapeHTML(groupName)}
                    </button>`;

                tabContentHTML += `
                    <div class="tab-pane fade ${activeClass}" id="${tabId}" role="tabpanel">
                        <h3 class="h5 border-bottom pb-2 mb-3"><i class="${iconClass} me-2 text-primary"></i>${escapeHTML(groupName)}</h3>
                        <div class="row row-cols-1 row-cols-lg-2 row-cols-xl-3 g-3">`;

                compList.forEach(compId => {
                    const targetId = typeof compId === 'object' && compId ? compId.id : compId;
                    const component = allSoftwareCache.find(c => c.id === targetId);
                    if (component) {
                        tabContentHTML += createComponentCard(component, groupName, isExclusive);
                    }
                });
                tabContentHTML += `</div></div>`;
                active = '';
            });

            // Standalone Section
            let standaloneCardsHTML = '';
            allSoftwareCache.forEach(component => {
                if (!allGroupedComponents.has(component.id)) {
                    standaloneCardsHTML += createComponentCard(component, 'standalone', false);
                }
            });

            if (standaloneCardsHTML) {
                const activeClass = active ? 'show active' : '';
                tabNavHTML += `
                    <button class="nav-link ${active}" id="v-pills-standalone-tab" data-bs-toggle="pill" data-bs-target="#v-pills-standalone" type="button" role="tab">
                        <i class="fa-solid fa-box-open me-2"></i>Standalone
                    </button>`;

                tabContentHTML += `
                    <div class="tab-pane fade ${activeClass}" id="v-pills-standalone" role="tabpanel">
                        <h3 class="h5 border-bottom pb-2 mb-3"><i class="fa-solid fa-box-open me-2 text-primary"></i>Standalone Applications</h3>
                        <div class="row row-cols-1 row-cols-lg-2 row-cols-xl-3 g-3">
                            ${standaloneCardsHTML}
                        </div>
                    </div>`;
            }

            tabNavHTML += '</div>';
            tabContentHTML += '</div>';

            wizardBody.innerHTML = `
                <div class="text-start">
                    <div class="d-flex flex-wrap justify-content-between align-items-center mb-4 gap-3">
                        <div>
                            <h2 class="h4 mb-1"><i class="fa-solid fa-store me-2 text-primary"></i>Applications Marketplace</h2>
                            <p class="text-muted small mb-0">Browse categories or search across all available services and stacks.</p>
                        </div>
                        <div class="input-group" style="max-width: 340px;">
                            <span class="input-group-text bg-white border-end-0 text-muted"><i class="fa-solid fa-magnifying-glass"></i></span>
                            <input type="text" class="form-control border-start-0 ps-0" id="component-search-input" placeholder="Search applications, tags..." autocomplete="off">
                            <button class="btn btn-outline-secondary d-none" type="button" id="clear-component-search-btn" title="Clear search"><i class="fa-solid fa-xmark"></i></button>
                        </div>
                    </div>
                    <div class="row">
                        <div class="col-md-3 mb-4">
                            <div class="card p-2 border-0 bg-transparent">
                                ${tabNavHTML}
                            </div>
                        </div>
                        <div class="col-md-9">
                            <div id="marketplace-container" class="mb-4">
                                ${tabContentHTML}
                            </div>
                        </div>
                    </div>
                    <div class="alert alert-info mt-4 p-3 text-start" role="alert">
                        <i class="fa-solid fa-circle-info me-2 text-primary"></i>
                        <strong>Recommended Utilities:</strong> For a complete management experience, we highly recommend selecting
                        <strong>Portainer</strong> (for easy container management),
                        <strong>FileBrowser</strong> (for visual file and configuration editing), and
                        <strong>Homarr</strong> (as a central dashboard for all your services).
                    </div>
                    <div id="step3-action-area"></div>
                </div>
            `;

            // Interactive Selection Logic for Cards
            document.querySelectorAll('.component-card').forEach(card => {
                card.addEventListener('click', () => {
                    const compId = card.dataset.componentId;
                    const checkbox = /** @type {HTMLInputElement} */ (document.getElementById(`comp-${compId}`));
                    const button = card.querySelector('.btn-select-software');
                    if (!checkbox) return;

                    const groupName = card.dataset.groupName;
                    const isExclusive = card.dataset.exclusive === 'true';

                    // Toggle logic
                    const nextState = !checkbox.checked;

                    if (isExclusive && nextState) {
                        // Deselect other cards in this group
                        document.querySelectorAll(`.component-card[data-group-name="${groupName}"]`).forEach(otherCard => {
                            if (otherCard !== card) {
                                const otherId = otherCard.dataset.componentId;
                                const otherCheckbox = /** @type {HTMLInputElement} */ (document.getElementById(`comp-${otherId}`));
                                const otherBtn = otherCard.querySelector('.btn-select-software');
                                if (otherCheckbox) {
                                    otherCheckbox.checked = false;
                                    otherCard.classList.remove('border-success');
                                    if (otherBtn) {
                                        otherBtn.className = 'btn btn-outline-primary btn-select-software mt-3 w-100';
                                        otherBtn.innerHTML = 'Select';
                                    }
                                }
                            }
                        });
                    }

                    checkbox.checked = nextState;

                    if (checkbox.checked) {
                        card.classList.add('border-success');
                        button.className = 'btn btn-success btn-select-software mt-3 w-100';
                        button.innerHTML = '<i class="fa-solid fa-check me-2"></i>Selected';
                    } else {
                        card.classList.remove('border-success');
                        button.className = 'btn btn-outline-primary btn-select-software mt-3 w-100';
                        button.innerHTML = 'Select';
                    }

                    updatePackageCheckboxes();
                });
            });

            // Package Card clicks
            document.querySelectorAll('.package-card').forEach(card => {
                card.addEventListener('click', () => {
                    const pkgId = card.dataset.packageId;
                    const checkbox = /** @type {HTMLInputElement} */ (document.getElementById(`pkg-${pkgId}`));
                    const button = card.querySelector('.btn-select-package');
                    if (!checkbox) return;

                    checkbox.checked = !checkbox.checked;
                    const compIds = JSON.parse(card.dataset.components || '[]');

                    // Update all associated component cards
                    compIds.forEach(id => {
                        const compCheckbox = /** @type {HTMLInputElement} */ (document.getElementById(`comp-${id}`));
                        const compCard = document.querySelector(`.component-card[data-component-id="${id}"]`);
                        if (compCheckbox) {
                            compCheckbox.checked = checkbox.checked;
                            if (compCard) {
                                const compBtn = compCard.querySelector('.btn-select-software');
                                if (checkbox.checked) {
                                    compCard.classList.add('border-success');
                                    if (compBtn) {
                                        compBtn.className = 'btn btn-success btn-select-software mt-3 w-100';
                                        compBtn.innerHTML = '<i class="fa-solid fa-check me-2"></i>Selected';
                                    }
                                } else {
                                    compCard.classList.remove('border-success');
                                    if (compBtn) {
                                        compBtn.className = 'btn btn-outline-primary btn-select-software mt-3 w-100';
                                        compBtn.innerHTML = 'Select';
                                    }
                                }
                            }
                        }
                    });

                    // Update package card visual state
                    if (checkbox.checked) {
                        card.classList.remove('border-primary', 'border-info');
                        card.classList.add('border-success');
                        if (button) {
                            button.className = 'btn btn-success btn-select-package mt-2 w-100';
                            button.innerHTML = `<i class="fa-solid fa-check me-2"></i>Bundle Selected (${compIds.length} Apps)`;
                        }
                    } else {
                        card.classList.remove('border-success', 'border-info');
                        card.classList.add('border-primary');
                        if (button) {
                            button.className = 'btn btn-outline-primary btn-select-package mt-2 w-100';
                            button.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles me-1"></i>Select 1-Click Bundle';
                        }
                    }
                });
            });

            // Package checkbox synchronization helper
            const updatePackageCheckboxes = () => {
                document.querySelectorAll('.package-card').forEach(card => {
                    const pkgId = card.dataset.packageId;
                    const checkbox = /** @type {HTMLInputElement} */ (document.getElementById(`pkg-${pkgId}`));
                    const button = card.querySelector('.btn-select-package');
                    const compIds = JSON.parse(card.dataset.components || '[]');
                    if (compIds.length === 0) return;

                    const checkedCount = compIds.filter(id => {
                        const compInput = /** @type {HTMLInputElement} */ (document.getElementById(`comp-${id}`));
                        return compInput && compInput.checked;
                    }).length;

                    const allChecked = (checkedCount === compIds.length && compIds.length > 0);
                    if (checkbox) {
                        checkbox.checked = allChecked;
                    }

                    if (allChecked) {
                        card.classList.remove('border-primary', 'border-info');
                        card.classList.add('border-success');
                        if (button) {
                            button.className = 'btn btn-success btn-select-package mt-2 w-100';
                            button.innerHTML = `<i class="fa-solid fa-check me-2"></i>Bundle Selected (${compIds.length} Apps)`;
                        }
                    } else if (checkedCount > 0) {
                        card.classList.remove('border-success', 'border-primary');
                        card.classList.add('border-info');
                        if (button) {
                            button.className = 'btn btn-outline-info btn-select-package mt-2 w-100';
                            button.innerHTML = `<i class="fa-solid fa-list-check me-2"></i>Partial (${checkedCount}/${compIds.length} Apps)`;
                        }
                    } else {
                        card.classList.remove('border-success', 'border-info');
                        card.classList.add('border-primary');
                        if (button) {
                            button.className = 'btn btn-outline-primary btn-select-package mt-2 w-100';
                            button.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles me-1"></i>Select 1-Click Bundle';
                        }
                    }
                });
            };

            updatePackageCheckboxes(); // Run once to set initial state

            // Real-time Marketplace Component Search Logic
            const searchInput = /** @type {HTMLInputElement} */ (document.getElementById('component-search-input'));
            const clearSearchBtn = document.getElementById('clear-component-search-btn');

            if (searchInput) {
                const handleSearch = () => {
                    const query = searchInput.value.trim().toLowerCase();
                    if (clearSearchBtn) {
                        if (query) {
                            clearSearchBtn.classList.remove('d-none');
                        } else {
                            clearSearchBtn.classList.add('d-none');
                        }
                    }

                    let firstTabWithMatches = null;

                    document.querySelectorAll('.tab-pane').forEach(tabPane => {
                        const cols = tabPane.querySelectorAll('.row > .col');
                        let visibleCount = 0;

                        cols.forEach(col => {
                            const card = col.querySelector('.component-card, .package-card');
                            if (!card) return;
                            const text = (card.getAttribute('data-search-text') || '').toLowerCase();
                            if (!query || text.includes(query)) {
                                col.classList.remove('d-none');
                                visibleCount++;
                            } else {
                                col.classList.add('d-none');
                            }
                        });

                        // Manage no results placeholder per tab
                        const existingNoResults = tabPane.querySelector('.no-search-results-msg');
                        if (query && visibleCount === 0) {
                            if (!existingNoResults) {
                                const row = tabPane.querySelector('.row');
                                if (row) {
                                    const msgDiv = document.createElement('div');
                                    msgDiv.className = 'col-12 text-center text-muted py-4 no-search-results-msg';
                                    msgDiv.innerHTML = `<i class="fa-solid fa-filter-circle-xmark me-2"></i>No applications matching "<strong>${escapeHTML(query)}</strong>" in this category.`;
                                    row.appendChild(msgDiv);
                                }
                            }
                        } else if (existingNoResults) {
                            existingNoResults.remove();
                        }

                        // Track count on tab button
                        const tabBtn = document.querySelector(`button[data-bs-target="#${tabPane.id}"]`);
                        if (tabBtn) {
                            const badge = tabBtn.querySelector('.search-match-badge');
                            if (query) {
                                if (!badge) {
                                    const span = document.createElement('span');
                                    span.className = 'badge rounded-pill bg-primary-subtle text-primary ms-auto search-match-badge';
                                    span.textContent = String(visibleCount);
                                    tabBtn.appendChild(span);
                                } else {
                                    badge.textContent = String(visibleCount);
                                }
                                if (visibleCount > 0 && !firstTabWithMatches) {
                                    firstTabWithMatches = tabBtn;
                                }
                            } else if (badge) {
                                badge.remove();
                            }
                        }
                    });

                    // If active tab has 0 results and another tab has matches, switch tab
                    const activeTabPane = document.querySelector('.tab-pane.active');
                    if (query && activeTabPane) {
                        const activeVisibleCols = activeTabPane.querySelectorAll('.row > .col:not(.d-none)');
                        if (activeVisibleCols.length === 0 && firstTabWithMatches) {
                            bootstrap.Tab.getOrCreateInstance(firstTabWithMatches).show();
                        }
                    }
                };

                searchInput.addEventListener('input', handleSearch);
                if (clearSearchBtn) {
                    clearSearchBtn.addEventListener('click', () => {
                        searchInput.value = '';
                        handleSearch();
                        searchInput.focus();
                    });
                }
            }

            // Set up action area buttons dynamically with Back navigation
            const actionWrapper = document.createElement('div');
            actionWrapper.className = 'sticky-action-bar';

            const backBtn = document.createElement('button');
            backBtn.id = 'back-to-step2-btn';
            backBtn.className = 'btn btn-outline-secondary btn-lg';
            backBtn.innerHTML = '<i class="fa-solid fa-arrow-left me-2"></i>Back';
            backBtn.addEventListener('click', () => {
                if (lastScanData) {
                    renderStep2_ConfigureDevices(lastScanData);
                }
            });
            actionWrapper.appendChild(backBtn);

            const proceedBtn = document.createElement('button');
            proceedBtn.id = 'proceed-to-step4-btn';
            proceedBtn.className = 'btn btn-primary btn-lg';
            proceedBtn.innerHTML = '<i class="fa-solid fa-sliders me-2"></i>Configure Services';
            proceedBtn.addEventListener('click', renderStep4_ConfigureServices);
            actionWrapper.appendChild(proceedBtn);

            const step3ActionArea = document.getElementById('step3-action-area');
            if (step3ActionArea) {
                step3ActionArea.appendChild(actionWrapper);
            }

        } catch (error) {
            console.error('Error fetching software list:', error);
            wizardBody.innerHTML = `<p class="text-center text-danger">An error occurred while loading the software list: ${escapeHTML(error.message)}</p>`;
        }
    };

    /** @param {ComponentVariable} variable */
    const createVariableInput = (variable) => {
        const inputId = `var-${escapeHTML(variable.id)}`;
        let inputHTML;

        const savedValue = finalVariablesCache[variable.id] !== undefined
            ? finalVariablesCache[variable.id]
            : (variable.default || '');

        if (variable.source === 'dotenv') {
            const placeholder = '******** (Managed in .env file)';
            inputHTML = `<input type="text" class="form-control form-control-sm" id="${inputId}" name="${escapeHTML(variable.id)}" value="" placeholder="${placeholder}" disabled>`;
        } else if (variable.type === 'select' && variable.options) {
            const optionsHTML = variable.options.map(opt => `<option value="${escapeHTML(opt)}" ${opt === savedValue ? 'selected' : ''}>${escapeHTML(opt)}</option>`).join('');
            inputHTML = `<select class="form-select form-select-sm" id="${inputId}" name="${escapeHTML(variable.id)}">${optionsHTML}</select>`;
        } else if (variable.type === 'password') {
            inputHTML = `
                <div class="input-group input-group-sm">
                    <input type="password" class="form-control form-control-sm" id="${inputId}" name="${escapeHTML(variable.id)}" value="${escapeHTML(savedValue)}">
                    <button class="btn btn-outline-secondary toggle-password-btn" type="button" tabindex="-1" title="Show/Hide Password">
                        <i class="fa-solid fa-eye"></i>
                    </button>
                </div>
            `;
        } else {
            inputHTML = `<input type="text" class="form-control form-control-sm" id="${inputId}" name="${escapeHTML(variable.id)}" value="${escapeHTML(savedValue)}">`;
        }

        return `
            <div class="mb-3">
                <label for="${inputId}" class="form-label"><strong>${escapeHTML(variable.label) || escapeHTML(variable.id)}</strong></label>
                ${inputHTML}
                <div class="form-text small">${escapeHTML(variable.description)}</div>
            </div>
        `;
    };

    const validateConfiguration = () => {
        let isValid = true;
        let errorMessage = '';
        document.querySelectorAll('#variables-container .tab-pane').forEach(tab => {
            const compId = tab.id.replace('v-pills-', '');
            const isCleanInstall = (/** @type {HTMLInputElement} */ (document.getElementById(`clean-install-checkbox-${compId}`)))?.checked;
            const componentData = allSoftwareCache.find(c => c.id === compId);

            componentData?.required_variables?.forEach(variable => {
                const input = /** @type {HTMLInputElement|HTMLSelectElement} */ (tab.querySelector(`[name="${variable.id}"]`));
                if (!input) return;

                const isRequired = variable.required === 'always' || (variable.required === 'clean-install' && isCleanInstall);
                if (isRequired && !input.value) {
                    if (isValid) {
                        isValid = false;
                        errorMessage = `The '${variable.label || variable.id}' field is required for ${componentData.name}.`;
                    }
                    input.classList.add('is-invalid');
                } else {
                    input.classList.remove('is-invalid');
                }
            });
        });

        const reviewBtn = /** @type {HTMLButtonElement} */ (document.getElementById('review-selection-btn'));
        if (reviewBtn) reviewBtn.disabled = !isValid;

        const errorDiv = document.getElementById('config-error-display');
        if (errorDiv) {
            errorDiv.textContent = isValid ? '' : errorMessage;
            errorDiv.style.display = isValid ? 'none' : 'block';
        }

        return isValid;
    };

    const addRealTimeValidation = () => {
        document.querySelectorAll('.clean-install-checkbox, #variables-container input, #variables-container select').forEach(el => {
            const eventListener = () => {
                validateConfiguration();
            };
            el.addEventListener('input', eventListener);
            el.addEventListener('change', eventListener);
        });
        validateConfiguration();
    };

    const renderStep4_ConfigureServices = async () => {
        selectedComponentsCache = Array.from(document.querySelectorAll('#v-pills-tabContent .form-check-input:not(.package-checkbox):checked')).map(input => (/** @type {HTMLInputElement} */ (input)).value);
        // Option B: Visual progress bar at 75%
        toggleProgressBarVisibility(true, 75);
        if (wizardHeader) {
            wizardHeader.innerHTML = '<strong>Step 3 of 4: Configure Services</strong>';
        }
        updateWizardFooter('Provide the required values for your selected software.');

        if (selectedComponentsCache.length === 0) {
            wizardBody.innerHTML = `<p class="text-center text-muted">No software was selected. Please go back and select at least one component.</p>`;
            return;
        }

        wizardBody.innerHTML = `<div class="text-center"><i class="fa-solid fa-spinner fa-spin fa-2x text-muted"></i><p class="mt-2">Loading configuration options...</p></div>`;

        try {
            const data = await fetchAPI('/get-required-variables', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({selected_components: selectedComponentsCache})
            });

            const components = data.components;
            const componentsRequiringUi = selectedComponentsCache.filter(compId => {
                const fullComp = allSoftwareCache.find(c => c.id === compId);
                return (Object.keys(components).includes(compId)) || (fullComp && fullComp.post_install_restart_option);
            });

            if (componentsRequiringUi.length === 0) {
                wizardBody.innerHTML = `
                    <div class="text-start">
                        <h2 class="h4 text-center">Configure Services</h2>
                        <p class="text-center text-muted">The selected software requires no additional configuration.</p>
                        <div id="step4-action-area"></div>
                    </div>
                `;

                const actionWrapper = document.createElement('div');
                actionWrapper.className = 'sticky-action-bar';

                const backBtn = document.createElement('button');
                backBtn.id = 'back-to-step3-btn';
                backBtn.className = 'btn btn-outline-secondary btn-lg';
                backBtn.innerHTML = '<i class="fa-solid fa-arrow-left me-2"></i>Back';
                backBtn.addEventListener('click', renderStep3_SelectSoftware);
                actionWrapper.appendChild(backBtn);

                const reviewBtn = document.createElement('button');
                reviewBtn.id = 'review-selection-btn';
                reviewBtn.className = 'btn btn-primary btn-lg';
                reviewBtn.innerHTML = '<i class="fa-solid fa-clipboard-check me-2"></i>Review and Confirm';
                reviewBtn.addEventListener('click', handleReviewSelection);
                actionWrapper.appendChild(reviewBtn);

                const step4ActionArea = document.getElementById('step4-action-area');
                if (step4ActionArea) {
                    step4ActionArea.appendChild(actionWrapper);
                }
                return;
            }

            let navPillsHTML = '<div class="nav flex-column nav-pills me-3" role="tablist" aria-orientation="vertical">';
            let tabContentHTML = '<div class="tab-content">';
            let isFirstItem = true;

            selectedComponentsCache.forEach(compId => {
                const componentWithVars = components[compId];
                const fullComponentData = allSoftwareCache.find(c => c.id === compId);
                if (!fullComponentData || (!componentWithVars && !fullComponentData.post_install_restart_option)) return;

                const escapedCompId = escapeHTML(compId);
                const tabId = `v-pills-${escapedCompId}`;
                const activeClass = isFirstItem ? 'active' : '';
                navPillsHTML += `<button class="nav-link text-start ${activeClass}" data-bs-toggle="pill" data-bs-target="#${tabId}" type="button">${escapeHTML(fullComponentData.name)}</button>`;
                tabContentHTML += `<div class="tab-pane fade show ${activeClass}" id="${tabId}" role="tabpanel">`;

                if (componentWithVars?.variables?.length > 0) {
                    componentWithVars.variables.forEach(v => {
                        tabContentHTML += createVariableInput(v);
                    });
                } else {
                    tabContentHTML += '<p class="text-center text-muted pt-4">This component requires no variable configuration.</p>';
                }

                // Restore previously checked checkboxes for clean install and restart options
                const savedCleanChecked = componentsToCleanCache.includes(compId) ? 'checked' : '';
                const savedRestartChecked = componentsToRestartCache.includes(compId) ? 'checked' : '';

                tabContentHTML += `
                    <hr>
                    <div class="form-check mt-3">
                        <input class="form-check-input clean-install-checkbox" type="checkbox" id="clean-install-checkbox-${escapedCompId}" data-comp-id="${escapedCompId}" ${savedCleanChecked}>
                        <label class="form-check-label" for="clean-install-checkbox-${escapedCompId}">
                            <strong>Perform a clean reinstallation</strong>
                        </label>
                        <div class="form-text small">
                            This will permanently delete all existing data and settings for this service before deploying.
                        </div>
                    </div>`;

                if (fullComponentData.post_install_restart_option) {
                    tabContentHTML += `
                        <div class="form-check mt-3">
                            <input class="form-check-input restart-checkbox" type="checkbox" id="restart-checkbox-${escapedCompId}" data-comp-id="${escapedCompId}" ${savedRestartChecked}>
                            <label class="form-check-label" for="restart-checkbox-${escapedCompId}">
                                <strong>Restart container after installation</strong>
                            </label>
                            <div class="form-text small">
                                Recommended for services that require a restart to initialize properly.
                            </div>
                        </div>`;
                }
                tabContentHTML += '</div>';
                isFirstItem = false;
            });

            navPillsHTML += '</div>';
            tabContentHTML += '</div>';

            wizardBody.innerHTML = `
                <div class="text-start">
                    <h2 class="h4 text-center">Configure Services</h2>
                    <p class="text-muted text-center small mb-4">
                        Provide the required settings for your selected software.
                    </p>
                    <div class="row">
                        <div class="col-md-3">${navPillsHTML}</div>
                        <div class="col-md-9"><div id="variables-container">${tabContentHTML}</div></div>
                    </div>
                    <div class="d-grid gap-2 col-8 mx-auto my-4" id="step4-action-area"></div>
                </div>
            `;

            // Set up action area buttons dynamically with Back navigation
            const actionWrapper = document.createElement('div');
            actionWrapper.className = 'sticky-action-bar';

            const backBtn = document.createElement('button');
            backBtn.id = 'back-to-step3-btn';
            backBtn.className = 'btn btn-outline-secondary btn-lg';
            backBtn.innerHTML = '<i class="fa-solid fa-arrow-left me-2"></i>Back';
            backBtn.addEventListener('click', renderStep3_SelectSoftware);
            actionWrapper.appendChild(backBtn);

            const reviewBtn = document.createElement('button');
            reviewBtn.id = 'review-selection-btn';
            reviewBtn.className = 'btn btn-primary btn-lg';
            reviewBtn.innerHTML = '<i class="fa-solid fa-clipboard-check me-2"></i>Review and Confirm';
            reviewBtn.addEventListener('click', handleReviewSelection);
            actionWrapper.appendChild(reviewBtn);

            const step4ActionArea = document.getElementById('step4-action-area');
            if (step4ActionArea) {
                const configErrorDisplay = document.createElement('div');
                configErrorDisplay.id = 'config-error-display';
                configErrorDisplay.className = 'alert alert-danger';
                configErrorDisplay.style.display = 'none';
                configErrorDisplay.setAttribute('role', 'alert');
                step4ActionArea.appendChild(configErrorDisplay);
                step4ActionArea.appendChild(actionWrapper);
            }

            addRealTimeValidation();
        } catch (error) {
            console.error('Error fetching variables:', error);
            wizardBody.innerHTML = `<p class="text-center text-danger">An error occurred while loading configuration options: ${escapeHTML(error.message)}</p>`;
        }
    };

    /** @param {SystemAnalysisResponse} analysisData */
    const displayAnalysisResults = (analysisData) => {
        let warningsHTML = '';
        let expectedChangesHTML = '';
        let blockingConflictsHTML = '';
        let isBlocked = false;

        analysisData.resource_warnings?.forEach(w => {
            warningsHTML += `
                <li class="list-group-item">
                    <i class="fa-solid fa-triangle-exclamation text-warning me-2"></i>
                    <strong>${escapeHTML(w.type)} Warning:</strong> ${escapeHTML(w.message)}
                </li>`;
        });

        analysisData.external_conflicts?.ports?.forEach(p => {
            if (p.conflict_type === 'EXPECTED_REINSTALLATION') {
                expectedChangesHTML += `
                    <li class="list-group-item">
                        <i class="fa-solid fa-arrows-rotate text-info me-2"></i>
                        <strong>Port ${p.port} Re-use:</strong>
                        The existing service <strong>${escapeHTML(p.conflicting_service)}</strong> will be stopped and replaced by
                        <strong>${escapeHTML(p.proposed_service)}</strong>.
                    </li>`;
            } else {
                isBlocked = true;
                const icon = p.conflict_type === 'DANGEROUS_NATIVE_PROCESS_CONFLICT' ? 'fa-shield-halved' : 'fa-network-wired';
                blockingConflictsHTML += `
                    <li class="list-group-item">
                        <i class="fa-solid ${icon} text-danger me-2"></i>
                        <strong>Port ${p.port} Conflict:</strong>
                        This port is already in use by a critical service: <strong>${escapeHTML(p.conflicting_service)}</strong>.
                        You must change the port for <strong>${escapeHTML(p.proposed_service)}</strong> to continue.
                    </li>`;
            }
        });

        analysisData.external_conflicts?.volumes?.forEach(v => {
            warningsHTML += `
                <li class="list-group-item">
                    <i class="fa-solid fa-folder-open text-warning me-2"></i>
                    <strong>Shared Volume:</strong> The path <strong>${escapeHTML(v.volume_path)}</strong> is already in use and
                    will be shared with <strong>${escapeHTML(v.proposed_service)}</strong>. This is usually safe but be aware.
                </li>`;
        });

        const modalBodyHTML = `
            ${isBlocked ? `
                <div class="alert alert-danger" role="alert">
                    <h4 class="alert-heading">Action Required</h4>
                    <p>One or more blocking conflicts were detected. Please review the items below and adjust your
                       configuration before proceeding.</p>
                </div>` : ''}
            ${blockingConflictsHTML ? `
                <h5><i class="fa-solid fa-ban me-2"></i>Blocking Conflicts</h5>
                <ul class="list-group mb-4">${blockingConflictsHTML}</ul>` : ''}
            ${expectedChangesHTML ? `
                <h5><i class="fa-solid fa-info-circle me-2"></i>Expected Changes</h5>
                <ul class="list-group mb-4">${expectedChangesHTML}</ul>` : ''}
            ${warningsHTML ? `
                <h5><i class="fa-solid fa-triangle-exclamation me-2"></i>Warnings</h5>
                <ul class="list-group mb-2">${warningsHTML}</ul>` : ''}
            ${!blockingConflictsHTML && !expectedChangesHTML && !warningsHTML ? `
                <p class="text-center text-success">
                    <i class="fa-solid fa-check-circle me-2"></i>
                    No conflicts or warnings found. Your configuration looks good to go!
                </p>` : ''}
        `;

        document.getElementById('analysis-modal')?.remove();
        const modalHTML = `
            <div class="modal fade" id="analysis-modal" tabindex="-1" aria-labelledby="analysisModalLabel" aria-hidden="true">
              <div class="modal-dialog modal-lg modal-dialog-centered">
                <div class="modal-content">
                  <div class="modal-header">
                    <h5 class="modal-title" id="analysisModalLabel">Pre-flight Check Summary</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                  </div>
                  <div class="modal-body">${modalBodyHTML}</div>
                  <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Go Back &amp; Edit</button>
                    <button type="button" class="btn btn-primary" id="modal-proceed-btn" ${isBlocked ? 'disabled' : ''}>
                        ${isBlocked ? 'Cannot Proceed' : 'Proceed to Confirmation'}
                    </button>
                  </div>
                </div>
              </div>
            </div>`;
        document.body.insertAdjacentHTML('beforeend', modalHTML);

        const modalEl = document.querySelector('#analysis-modal');
        const proceedBtn = document.querySelector('#modal-proceed-btn');

        if (!modalEl || !proceedBtn) return;
        // @ts-ignore
        const analysisModal = new bootstrap.Modal(modalEl);

        proceedBtn.addEventListener('click', () => {
           /** @type {any} */ (analysisModal).hide();
            renderStep5_Confirmation();
        });
        /** @type {any} */ (analysisModal)["show" ]();
    };

    const handleReviewSelection = async () => {
        if (!validateConfiguration()) return;

        const reviewBtn = document.getElementById('review-selection-btn');
        const errorDiv = document.getElementById('config-error-display');
        setButtonState(reviewBtn, true, {loadingText: 'Analyzing...'});

        finalVariablesCache = {};
        document.querySelectorAll('#variables-container [name]:not(:disabled)').forEach(input => {
            const el = /** @type {HTMLInputElement|HTMLSelectElement} */ (input);
            finalVariablesCache[el.name] = el.value;
        });

        componentsToCleanCache = Array.from(document.querySelectorAll('.clean-install-checkbox:checked')).map(cb => (/** @type {HTMLElement} */ (cb)).dataset.compId);
        componentsToRestartCache = Array.from(document.querySelectorAll('.restart-checkbox:checked')).map(cb => (/** @type {HTMLElement} */ (cb)).dataset.compId);

        const componentsPayload = selectedComponentsCache.map(compId => {
            const componentData = allSoftwareCache.find(c => c.id === compId);
            const component = {id: compId, name: componentData?.name || compId, ports: [], volumes: []};
            componentData?.required_variables?.forEach(variable => {
                const userValue = finalVariablesCache[variable.id];
                if (userValue) {
                    if (variable.id.toUpperCase().endsWith('_PORT')) {
                        component.ports.push(`${userValue}:${userValue}/tcp`);
                    } else if (variable.id.toUpperCase().endsWith('_VOLUME_PATH')) {
                        component.volumes.push(userValue);
                    }
                }
            });
            return component;
        });

        try {
            const analysisData = await fetchAPI('/api/v1/system/analyze', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    devices: Object.values(managedDeviceCache),
                    components: componentsPayload,
                    is_reinstallation: componentsToCleanCache.length > 0
                })
            });

            if (analysisData.status === 'error') {
                const message = analysisData.internal_conflicts?.join(', ') || 'An internal validation error occurred.';
                if (errorDiv) {
                    errorDiv.textContent = message;
                    errorDiv.style.display = 'block';
                }
            } else {
                analysisResultsCache = analysisData;
                displayAnalysisResults(analysisData);
            }
        } catch (error) {
            console.error('Analysis failed:', error);
            if (errorDiv) {
                errorDiv.textContent = error.message || 'An unknown server error occurred.';
                errorDiv.style.display = 'block';
            }
        } finally {
            setButtonState(reviewBtn, false);
        }
    };

    const renderStep5_Confirmation = () => {
        // Option B: Visual progress bar at 100%
        toggleProgressBarVisibility(true, 100);
        if (wizardHeader) {
            wizardHeader.innerHTML = '<strong>Step 4 of 4: Confirmation</strong>';
        }
        updateWizardFooter('Please review your selections before generating files and deploying.');

        // Mitigation: string-fallbacks ensure we always pass a pure string to escapeHTML
        const devicesHTML = Object.values(managedDeviceCache).map(device => {
            const safeHostname = escapeHTML(device.hostname || 'Unknown Host');
            const safeIp = escapeHTML(device.ip || '0.0.0.0');
            return `<li><strong>${safeHostname}</strong> (${safeIp})</li>`;
        }).join('');

        const softwareHTML = selectedComponentsCache.map(compId => {
            const component = allSoftwareCache.find(c => c.id === compId);
            const safeName = escapeHTML(component?.name || 'Unknown');
            const safeDesc = escapeHTML(component?.description || 'No description.');
            return `<li><strong>${safeName}</strong>: ${safeDesc}</li>`;
        }).join('');

        wizardBody.innerHTML = `
            <div class="text-start">
                <h2 class="h4 text-center">Confirmation Summary</h2>
                <div class="card my-4">
                    <div class="card-header">Target Devices</div>
                    <div class="card-body"><ul class="list-unstyled mb-0">${devicesHTML}</ul></div>
                </div>
                <div class="card mb-4">
                    <div class="card-header">Selected Software</div>
                    <div class="card-body"><ul class="mb-0">${softwareHTML}</ul></div>
                </div>
                <div class="d-grid gap-2 col-8 mx-auto my-4" id="step5-action-area"></div>
            </div>`;

        // Set up action area buttons dynamically with Back navigation
        const actionWrapper = document.createElement('div');
        actionWrapper.className = 'sticky-action-bar';

        const backBtn = document.createElement('button');
        backBtn.id = 'back-to-step4-btn';
        backBtn.className = 'btn btn-outline-secondary btn-lg';
        backBtn.innerHTML = '<i class="fa-solid fa-arrow-left me-2"></i>Back';
        backBtn.addEventListener('click', renderStep4_ConfigureServices);
        actionWrapper.appendChild(backBtn);

        const finalBtn = document.createElement('button');
        finalBtn.id = 'final-generate-btn';
        finalBtn.className = 'btn btn-success btn-lg';
        finalBtn.innerHTML = '<i class="fa-solid fa-file-invoice me-2"></i>Generate Configuration Files';
        finalBtn.addEventListener('click', handleInstallation);
        actionWrapper.appendChild(finalBtn);

        const step5ActionArea = document.getElementById('step5-action-area');
        if (step5ActionArea) {
            step5ActionArea.appendChild(actionWrapper);
        }
    };

    const handleInstallation = async () => {
        const installBtn = document.getElementById('final-generate-btn');
        setButtonState(installBtn, true, {loadingText: 'Generating files...'});

        try {
            const result = await fetchAPI('/start-installation', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    selected_components: selectedComponentsCache,
                    devices: Object.values(managedDeviceCache),
                    env_vars: finalVariablesCache,
                    components_to_clean: componentsToCleanCache,
                })
            });

            // Mitigation: Hide progress bar entirely on final completed success screen
            toggleProgressBarVisibility(false, 0);

            wizardHeader.innerHTML = '<strong>Setup Complete</strong>';
            updateWizardFooter('Ready for deployment.');
            wizardBody.innerHTML = `
                <div class="text-center">
                    <div id="deployment-status-icon">
                        <i class="fa-solid fa-circle-check fa-3x text-success mb-3"></i>
                    </div>
                    <h2 id="deployment-status-title" class="h4">Files Generated Successfully!</h2>
                    <div id="deployment-status-subtitle-container">
                        <p class="text-muted">Your configuration files are ready.</p>
                    </div>
                    <span id="output-path-display" class="d-none">${escapeHTML(result.output_path)}</span>
                    <div id="final-actions-container">
                         <div class="sticky-action-bar" id="deployment-actions">
                            <button id="deploy-button" class="btn btn-primary">
                                <i class="fa-solid fa-rocket me-2"></i>Deploy to Target(s)
                            </button>
                            <button id="start-over-btn" class="btn btn-secondary">Start Over</button>
                        </div>
                    </div>
                    <div id="log-viewer-container" class="mt-4 text-start" style="display: none;">
                        <h3 class="h5 text-center">Deployment Progress</h3>
                        <div class="card">
                            <div class="card-body bg-dark text-white rounded"
                                 style="font-family: monospace; font-size: 0.9em; max-height: 400px; overflow-y: auto;">
                                <pre id="log-output" class="mb-0" style="white-space: pre-wrap;"></pre>
                            </div>
                        </div>
                    </div>
                </div>`;
            document.getElementById('deploy-button').addEventListener('click', async () => {
                const outputPath = document.getElementById('output-path-display').textContent;
                await handleDeployment(outputPath);
            });
            document.getElementById('start-over-btn').addEventListener('click', renderStep1_Welcome);
        } catch (error) {
            console.error('Installation failed:', error);
            wizardHeader.innerHTML = '<strong>Generation Failed</strong>';
            updateWizardFooter('The process could not be completed.', 'danger');

            let reportText = 'An unknown error occurred.';
            if (error.details && Array.isArray(error.details) && error.details.length > 0) {
                reportText = error.details[0].details || error.details[0].summary || error.message;
            } else if (error.message) {
                reportText = error.message;
            }

            const GITHUB_REPO_URL = "https://github.com/HenkVanHoek/njord-deploy";
            const issueBody = encodeURIComponent(
                `**Error Details:**\n\n\`\`\`\n${reportText}\n\`\`\`\n\n` +
                `**Context:**\n- Selected Components: ${selectedComponentsCache.join(', ')}`
            );
            const githubIssueURL = `${GITHUB_REPO_URL}/issues/new?title=` +
                `${encodeURIComponent("Configurator UI Error Report")}&body=${issueBody}`;
            wizardBody.innerHTML = `
                <div class="text-center">
                    <i class="fa-solid fa-circle-xmark fa-3x text-danger mb-3"></i>
                    <h2 class="h4">File Generation Failed</h2>
                    <p class="text-muted">An error occurred during the file generation process.</p>
                    <div class="accordion my-3" id="errorAccordion">
                      <div class="accordion-item">
                        <h2 class="accordion-header">
                            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse"
                                    data-bs-target="#collapseOne">
                                <strong>Click to view detailed error report</strong>
                            </button>
                        </h2>
                        <div id="collapseOne" class="accordion-collapse collapse" data-bs-parent="#errorAccordion">
                            <div class="accordion-body text-start">
                                <p class="small text-muted">Please copy the full text below when reporting an issue.</p>
                                <textarea class="form-control" rows="8" readonly>` +
                `**Error Details:**\n\n${escapeHTML(reportText)}</textarea>
                            </div>
                        </div>
                      </div>
                    </div>
                    <p class="text-muted small mt-4">This may be a known issue. Please check the Q&A section.</p>
                    <div class="d-grid gap-2 col-8 mx-auto mt-2">
                        <a href="${GITHUB_REPO_URL}/discussions" target="_blank" class="btn btn-info">
                            <i class="fa-solid fa-comments me-2"></i>Check Q&A / Discussions
                        </a>
                        <a href="${githubIssueURL}" target="_blank" class="btn btn-outline-secondary">
                            <i class="fa-brands fa-github me-2"></i>Report Issue on GitHub
                        </a>
                        <button id="start-over-fail-btn" class="btn btn-primary mt-2">Start Over</button>
                    </div>
                </div>`;
            document.getElementById('start-over-fail-btn').addEventListener('click', renderStep1_Welcome);
        }
    };

    /** @param {string} outputPath */
    const handleDeployment = async (outputPath) => {
        const deployButton = document.getElementById('deploy-button');
        const logContainer = document.getElementById('log-viewer-container');
        const logOutput = document.getElementById('log-output');

        const setupLogsTabs = async () => {
            const logContainer = document.getElementById('log-viewer-container');
            if (!logContainer) return;

            const selectedComponents = selectedComponentsCache;
            if (!selectedComponents || selectedComponents.length === 0) return;

            const originalCard = logContainer.querySelector('.card');
            if (!originalCard) return;

            // Fetch generated files for the session
            let generatedFiles = {};
            try {
                const response = await fetch('/get-generated-files', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        output_path: outputPath,
                        selected_components: selectedComponents
                    })
                });
                if (response.ok) {
                    const resData = await response.json();
                    generatedFiles = resData.files || {};
                }
            } catch (err) {
                console.error('Failed to load generated files:', err);
            }

            // Create check box wrapper to show/hide generated files
            const controlPanel = document.createElement('div');
            controlPanel.className = 'd-flex align-items-center mb-3 text-start bg-light p-2 rounded border';
            controlPanel.innerHTML = `
                <div class="form-check form-switch mb-0">
                    <input class="form-check-input" type="checkbox" id="show-configs-checkbox" style="cursor: pointer;">
                    <label class="form-check-label fw-bold text-dark" for="show-configs-checkbox" style="cursor: pointer; user-select: none;">
                        <i class="fa-solid fa-file-signature text-primary me-1"></i>Show Generated Configuration Files (for debugging)
                    </label>
                </div>
            `;

            // Function to render the tabs dynamically based on checkbox state
            const renderTabs = (showConfigs) => {
                logContainer.innerHTML = '';
                logContainer.appendChild(controlPanel);

                const tabList = document.createElement('ul');
                tabList.className = 'nav nav-tabs mb-3';
                tabList.id = 'log-tabs';
                tabList.setAttribute('role', 'tablist');

                // 1. Add Deployment Progress Tab
                tabList.innerHTML = `
                    <li class="nav-item" role="presentation">
                        <button class="nav-link active" id="deploy-log-tab" data-bs-toggle="tab" data-bs-target="#deploy-log-pane" type="button" role="tab">
                            <i class="fa-solid fa-server me-1"></i>Deployment Progress
                        </button>
                    </li>
                `;

                const tabContent = document.createElement('div');
                tabContent.className = 'tab-content';
                tabContent.id = 'log-tabs-content';

                const deployPane = document.createElement('div');
                deployPane.className = 'tab-pane fade show active';
                deployPane.id = 'deploy-log-pane';
                deployPane.setAttribute('role', 'tabpanel');
                deployPane.appendChild(originalCard.cloneNode(true));
                tabContent.appendChild(deployPane);

                // 2. Add Generated Files Tabs if checked
                if (showConfigs) {
                    Object.entries(generatedFiles).forEach(([fileName, content]) => {
                        const safeId = 'cfg-' + fileName.replace(/[^a-zA-Z0-9]/g, '-');

                        const li = document.createElement('li');
                        li.className = 'nav-item';
                        li.setAttribute('role', 'presentation');
                        li.innerHTML = `
                            <button class="nav-link" id="tab-${safeId}" data-bs-toggle="tab" data-bs-target="#pane-${safeId}" type="button" role="tab">
                                <i class="fa-solid fa-file-code text-warning me-1"></i>${escapeHTML(fileName)}
                            </button>
                        `;
                        tabList.appendChild(li);

                        const pane = document.createElement('div');
                        pane.className = 'tab-pane fade';
                        pane.id = `pane-${safeId}`;
                        pane.setAttribute('role', 'tabpanel');
                        pane.innerHTML = `
                            <div class="card">
                                <div class="card-body bg-dark text-white rounded" style="font-family: monospace; font-size: 0.9em; max-height: 400px; overflow-y: auto;">
                                    <div class="d-flex justify-content-between align-items-center mb-2">
                                        <span class="text-muted small">File: ${escapeHTML(fileName)}</span>
                                        <button class="btn btn-sm btn-outline-light btn-copy-config" data-target-id="code-${safeId}">
                                            <i class="fa-solid fa-copy me-1"></i>Copy
                                        </button>
                                    </div>
                                    <pre id="code-${safeId}" class="mb-0 text-light" style="white-space: pre-wrap;">${escapeHTML(content)}</pre>
                                </div>
                            </div>
                        `;
                        tabContent.appendChild(pane);
                    });
                }

                // 3. Add Container Logs Tabs
                selectedComponents.forEach(compId => {
                    const compData = allSoftwareCache.find(c => c.id === compId);
                    const compName = compData ? compData.name : compId;
                    const containerName = `njorddeploy-${compId}`;
                    const paneId = `log-pane-${compId}`;
                    const escapedCompId = escapeHTML(compId);
                    const escapedPaneId = escapeHTML(paneId);

                    const li = document.createElement('li');
                    li.className = 'nav-item';
                    li.setAttribute('role', 'presentation');
                    li.innerHTML = `
                        <button class="nav-link" id="tab-${escapedCompId}" data-bs-toggle="tab" data-bs-target="#${escapedPaneId}" type="button" role="tab">
                            <i class="fa-solid fa-cubes text-info me-1"></i>${escapeHTML(compName)} Logs
                        </button>
                    `;
                    tabList.appendChild(li);

                    const pane = document.createElement('div');
                    pane.className = 'tab-pane fade';
                    pane.id = paneId;
                    pane.setAttribute('role', 'tabpanel');
                    pane.innerHTML = `
                        <div class="card">
                            <div class="card-body bg-dark text-white rounded" style="font-family: monospace; font-size: 0.9em; max-height: 400px; overflow-y: auto;">
                                <div class="d-flex justify-content-between align-items-center mb-2">
                                    <span class="text-muted small">Container: ${escapeHTML(containerName)}</span>
                                    <button class="btn btn-sm btn-outline-info btn-refresh-logs" data-comp-id="${escapedCompId}">
                                        <i class="fa-solid fa-arrows-rotate me-1"></i>Refresh
                                    </button>
                                </div>
                                <pre id="log-output-${escapedCompId}" class="mb-0 text-light" style="white-space: pre-wrap;">Loading logs...</pre>
                            </div>
                        </div>
                    `;
                    tabContent.appendChild(pane);
                });

                logContainer.appendChild(tabList);
                logContainer.appendChild(tabContent);

                // Re-bind click event listeners for copy buttons
                if (showConfigs) {
                    logContainer.querySelectorAll('.btn-copy-config').forEach(btn => {
                        btn.addEventListener('click', (e) => {
                            const targetId = e.currentTarget.getAttribute('data-target-id');
                            const pre = document.getElementById(targetId);
                            if (pre) {
                                navigator.clipboard.writeText(pre.textContent).then(() => {
                                    const originalText = e.currentTarget.innerHTML;
                                    e.currentTarget.innerHTML = '<i class="fa-solid fa-check me-1"></i>Copied!';
                                    setTimeout(() => {
                                        e.currentTarget.innerHTML = originalText;
                                    }, 2000);
                                }).catch(err => {
                                    console.error('Failed to copy text:', err);
                                });
                            }
                        });
                    });
                }

                // Re-bind container logs fetching logic
                const devices = Object.values(managedDeviceCache);
                const targetDevice = devices[0];

                if (targetDevice) {
                    const fetchLogs = async (compId) => {
                        const logPre = document.getElementById(`log-output-${compId}`);
                        if (!logPre) return;
                        logPre.textContent = 'Fetching logs from host...';

                        try {
                            const response = await fetch('/get-container-logs', {
                                method: 'POST',
                                headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({
                                    ip: targetDevice.ip,
                                    username: targetDevice.username,
                                    password: targetDevice.password,
                                    container_name: `njorddeploy-${compId}`
                                })
                            });
                            const resData = await response.json();
                            if (response.ok) {
                                logPre.textContent = resData.logs || 'No logs found in container.';
                            } else {
                                logPre.textContent = `Error: ${resData.error || 'Failed to fetch logs.'}`;
                            }
                        } catch (err) {
                            logPre.textContent = `Connection error: ${err.message}`;
                        }
                    };

                    selectedComponents.forEach(compId => {
                        const tabButton = document.getElementById(`tab-${compId}`);
                        if (tabButton) {
                            tabButton.addEventListener('shown.bs.tab', async () => {
                                await fetchLogs(compId);
                            });
                        }
                        const refreshBtn = tabContent.querySelector(`.btn-refresh-logs[data-comp-id="${compId}"]`);
                        if (refreshBtn) {
                            refreshBtn.addEventListener('click', async (e) => {
                                e.stopPropagation();
                                await fetchLogs(compId);
                            });
                        }
                    });
                }
            };

            // Initial render: showConfigs = false
            renderTabs(false);

            // Bind checkbox toggle event
            const checkbox = controlPanel.querySelector('#show-configs-checkbox');
            if (checkbox) {
                checkbox.addEventListener('change', (e) => {
                    renderTabs(e.target.checked);
                    const newCheckbox = logContainer.querySelector('#show-configs-checkbox');
                    if (newCheckbox) {
                        newCheckbox.checked = e.target.checked;
                    }
                });
            }
        };

        setButtonState(deployButton, true, {loadingText: 'Deploying...'});
        logContainer.style.display = 'block';
        logOutput.innerHTML = '';
        wizardHeader.innerHTML = '<strong>Deploying Services</strong>';
        updateWizardFooter('Deploying services...', 'primary');

        const statusIcon = document.getElementById('deployment-status-icon');
        const statusTitle = document.getElementById('deployment-status-title');
        const subtitleContainer = document.getElementById('deployment-status-subtitle-container');

        if (statusIcon) {
            statusIcon.innerHTML = '<i class="fa-solid fa-spinner fa-spin fa-3x text-primary mb-3"></i>';
        }
        if (statusTitle) {
            statusTitle.textContent = 'Deploying Services...';
        }
        if (subtitleContainer) {
            subtitleContainer.innerHTML = `
                <div class="mx-auto mb-3" style="max-width: 500px;">
                    <div class="progress" style="height: 20px;">
                        <div id="deployment-progress-bar" class="progress-bar progress-bar-striped progress-bar-animated bg-success" role="progressbar" style="width: 0;" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">0%</div>
                    </div>
                    <div id="deployment-playbook-step" class="text-muted small mt-2">Initializing deployment...</div>
                </div>
            `;
        }

        // Mitigation: Hide progress bar entirely during active deployment
        toggleProgressBarVisibility(false, 0);

        try {
            const selectedComponentsData = selectedComponentsCache
                .map(id => allSoftwareCache.find(c => c.id === id))
                .filter(Boolean);

            /** @type {DeploymentResponse} */
            const data = await fetchAPI('/deploy-configuration', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    output_path: outputPath,
                    devices: Object.values(managedDeviceCache),
                    components_to_clean: componentsToCleanCache,
                    components_to_restart: componentsToRestartCache,
                    analysis_results: analysisResultsCache,
                    selected_components_data: selectedComponentsData,
                    global_vars: finalVariablesCache
                }),
            });

            const taskId = data.task_id;
            const eventSource = new EventSource(`/stream-deployment/${taskId}`);
            let hasErrors = false;

            const watchdogTimer = setTimeout(() => {
                eventSource.close();
                logOutput.innerHTML += '\n<span class="text-danger fw-bold">[ERROR] Connection to server timed out.</span>\n';
                wizardHeader.innerHTML = '<strong>Deployment Failed</strong>';
                updateWizardFooter('Connection timed out. Please check the backend console.', 'danger');
                setButtonState(deployButton, false, {text: '<i class="fa-solid fa-triangle-exclamation me-2"></i>Deployment Failed - Retry?'});
                if (statusIcon) {
                    statusIcon.innerHTML = '<i class="fa-solid fa-circle-xmark fa-3x text-danger mb-3"></i>';
                }
                if (statusTitle) {
                    statusTitle.textContent = 'Deployment Failed';
                }
                const progressBar = document.getElementById('deployment-progress-bar');
                const playbookStep = document.getElementById('deployment-playbook-step');
                if (progressBar) {
                    progressBar.classList.remove('bg-success');
                    progressBar.classList.add('bg-danger');
                }
                if (playbookStep) {
                    playbookStep.className = 'text-danger fw-bold mt-2';
                    playbookStep.textContent = 'Connection timed out.';
                }
            }, 30000);

            eventSource.onmessage = event => {
                clearTimeout(watchdogTimer);
                const line = event.data;
                let className = 'text-light';
                if (line.includes('SUCCESS:')) className = 'text-success';
                if (line.includes('ERROR:') || line.includes('FATAL:')) {
                    className = 'text-danger';
                    hasErrors = true;
                }
                if (line.includes('WARN:')) className = 'text-warning';
                if (line.includes('---')) className = 'text-info fw-bold';
                const span = document.createElement('span');
                span.className = className;
                span.textContent = line + '\n';
                logOutput.appendChild(span);
                logOutput.parentElement.scrollTop = logOutput.parentElement.scrollHeight;

                // Dynamically update the progress bar and step status
                const progressBar = document.getElementById('deployment-progress-bar');
                const playbookStep = document.getElementById('deployment-playbook-step');

                let progress = 0;
                let stepText = '';

                if (line.includes('Pre flight check')) {
                    progress = 10;
                    stepText = 'Checking disk space...';
                } else if (line.includes('Ensure prerequisites for Docker')) {
                    progress = 20;
                    stepText = 'Installing system dependencies...';
                } else if (line.includes('keyring exists')) {
                    progress = 30;
                    stepText = 'Preparing Docker keyring...';
                } else if (line.includes('Download Docker official GPG')) {
                    progress = 40;
                    stepText = 'Fetching Docker security keys...';
                } else if (line.includes('Add Docker repository')) {
                    progress = 50;
                    stepText = 'Adding Docker package repositories...';
                } else if (line.includes('Docker CE and Compose plugin')) {
                    progress = 65;
                    stepText = 'Installing Docker Engine (this may take a minute)...';
                } else if (line.includes('project directory exists')) {
                    progress = 70;
                    stepText = 'Creating configuration directories...';
                } else if (line.includes('Copy all deployment files')) {
                    progress = 80;
                    stepText = 'Transferring configuration files to target...';
                } else if (line.includes('Perform Clean Install')) {
                    progress = 85;
                    stepText = 'Performing clean install of services...';
                } else if (line.includes('Docker network exists')) {
                    progress = 90;
                    stepText = 'Setting up container network...';
                } else if (line.includes('Pull latest service images')) {
                    progress = 93;
                    stepText = 'Downloading Docker images...';
                } else if (line.includes('Deploy services with Docker')) {
                    progress = 96;
                    stepText = 'Starting services...';
                } else if (line.includes('Restart specifically requested')) {
                    progress = 98;
                    stepText = 'Restarting services...';
                } else if (line.includes('SUCCESS:') || line.includes('finished successfully')) {
                    progress = 100;
                    stepText = 'Deployment completed successfully!';
                }

                if (progress > 0 && progressBar) {
                    progressBar.style.width = `${progress}%`;
                    progressBar.setAttribute('aria-valuenow', String(progress));
                    progressBar.textContent = `${progress}%`;
                }
                if (stepText && playbookStep) {
                    playbookStep.textContent = stepText;
                }

                if (line.includes('FAILED:') || line.includes('FATAL:')) {
                    if (progressBar) {
                        progressBar.classList.remove('bg-success');
                        progressBar.classList.add('bg-danger');
                    }
                    if (playbookStep) {
                        playbookStep.className = 'text-danger fw-bold mt-2';
                        playbookStep.textContent = 'Deployment failed. Check logs below.';
                    }
                    if (statusIcon) {
                        statusIcon.innerHTML = '<i class="fa-solid fa-circle-xmark fa-3x text-danger mb-3"></i>';
                    }
                    if (statusTitle) {
                        statusTitle.textContent = 'Deployment Failed';
                    }
                }

                if (line.includes('SUCCESS:')) {
                    if (statusIcon) {
                        statusIcon.innerHTML = '<i class="fa-solid fa-circle-check fa-3x text-success mb-3"></i>';
                    }
                    if (statusTitle) {
                        statusTitle.textContent = 'Deployment Successful';
                    }
                }
            };

            eventSource.onerror = async () => {
                clearTimeout(watchdogTimer);
                eventSource.close();

                const progressBar = document.getElementById('deployment-progress-bar');
                const playbookStep = document.getElementById('deployment-playbook-step');

                if (hasErrors) {
                    setButtonState(deployButton, false, {text: '<i class="fa-solid fa-triangle-exclamation me-2"></i>Show Error Report'});
                    wizardHeader.innerHTML = '<strong>Deployment Finished with Errors</strong>';
                    updateWizardFooter('Deployment completed, but some steps failed.', 'warning');
                    deployButton.onclick = async () => {
                        await showErrorSummary(taskId);
                    };

                    if (statusIcon) {
                        statusIcon.innerHTML = '<i class="fa-solid fa-circle-xmark fa-3x text-danger mb-3"></i>';
                    }
                    if (statusTitle) {
                        statusTitle.textContent = 'Deployment Failed';
                    }
                    if (progressBar) {
                        progressBar.classList.remove('bg-success');
                        progressBar.classList.add('bg-danger');
                    }
                    if (playbookStep) {
                        playbookStep.className = 'text-danger fw-bold mt-2';
                        playbookStep.textContent = 'Deployment failed with errors.';
                    }
                } else {
                    setButtonState(deployButton, false, {text: '<i class="fa-solid fa-circle-check me-2"></i>Deployment Finished'});
                    wizardHeader.innerHTML = '<strong>Deployment Finished</strong>';
                    updateWizardFooter('Deployment process completed successfully.', 'success');

                    const targetHosts = Object.values(managedDeviceCache)
                        .map(d => `${escapeHTML(d.hostname || 'Unknown Host')} (${escapeHTML(d.ip)})`)
                        .join(', ');

                    if (statusIcon) {
                        statusIcon.innerHTML = '<i class="fa-solid fa-circle-check fa-3x text-success mb-3"></i>';
                    }
                    if (statusTitle) {
                        statusTitle.textContent = `Deployment Successful on ${targetHosts}!`;
                    }
                    if (progressBar) {
                        progressBar.style.width = '100%';
                        progressBar.setAttribute('aria-valuenow', '100');
                        progressBar.textContent = '100%';
                    }
                    if (playbookStep) {
                        playbookStep.textContent = 'All services are up and running.';
                    }

                    await setupLogsTabs();

                    const finalActions = document.getElementById('final-actions-container');
                    if (finalActions) {
                        finalActions.innerHTML = `
                            <div class="sticky-action-bar d-flex gap-2 justify-content-center">
                                 <button id="show-summary-btn" class="btn btn-info btn-lg">
                                    <i class="fa-solid fa-list-check me-2"></i>Access Your Services
                                 </button>
                                 <button id="ai-eval-btn" class="btn btn-primary btn-lg">
                                    <i class="fa-solid fa-robot me-2"></i>AI Health Report
                                 </button>
                            </div>`;
                        document.getElementById('show-summary-btn').addEventListener('click', async () => {
                            await showServicesSummary(taskId);
                        });
                        document.getElementById('ai-eval-btn').addEventListener('click', async () => {
                            await triggerDeploymentEvaluation(taskId);
                        });
                    }

                    // Automatically trigger AI evaluation modal upon completion
                    setTimeout(() => {
                        triggerDeploymentEvaluation(taskId);
                    }, 800);
                }
            };
        } catch (error) {
            console.error('Failed to start deployment:', error);
            logOutput.innerHTML += `<span class="text-danger fw-bold">ERROR: Failed to initiate deployment. ${escapeHTML(error.message)}\n</span>`;
            wizardHeader.innerHTML = '<strong>Deployment Failed</strong>';
            setButtonState(deployButton, false, {text: '<i class="fa-solid fa-triangle-exclamation me-2"></i>Deployment Failed - Retry?'});
            updateWizardFooter('Could not start deployment process.', 'danger');
        }
    };

    /** @param {string} taskId */
    const showErrorSummary = async (taskId) => {
        const errorBtn = document.getElementById('deploy-button');
        setButtonState(errorBtn, true, {loadingText: 'Fetching Report...'});
        try {
            /** @type {TaskStatus} */
            const taskData = await fetchAPI(`/task-status/${taskId}`);

            let errorsHTML;
            if (taskData.errors && taskData.errors.length > 0) {
                errorsHTML = taskData.errors.map(err => `
                    <div class="list-group-item">
                        <div class="d-flex w-100 justify-content-between">
                            <h6 class="mb-1">${escapeHTML(err.summary || '')}</h6>
                            <small class="text-muted">${escapeHTML(err.timestamp || '')}</small>
                        </div>
                        <p class="mb-1 small"><strong>Type:</strong> ${escapeHTML(err.type || '')}</p>
                        <p class="mb-1 small"><strong>Details:</strong> ${escapeHTML(err.details || '')}</p>
                        <small class="text-muted">Component: ${escapeHTML(err.component_id || '')}</small>
                    </div>
                `).join('');
            } else {
                errorsHTML = '<p class="text-center">No detailed error information was found for this task.</p>';
            }

            document.getElementById('error-report-modal')?.remove();
            const modalHTML = `
                <div class="modal fade" id="error-report-modal" tabindex="-1" aria-labelledby="errorReportModalLabel" aria-hidden="true">
                  <div class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
                    <div class="modal-content">
                      <div class="modal-header">
                        <h5 class="modal-title" id="errorReportModalLabel">Deployment Error Report</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                      </div>
                      <div class="modal-body">
                        <p>The following errors occurred during the deployment process:</p>
                        <div class="list-group">${errorsHTML}</div>
                      </div>
                      <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                      </div>
                    </div>
                  </div>
                </div>`
            document.body.insertAdjacentHTML('beforeend', modalHTML);

            const errorModalEl = document.getElementById('error-report-modal');

            if (!errorModalEl) return;

            // Mitigation: JSDoc cast converts errorModalEl safely to HTMLElement to avoid parameter mismatch
            const errorModal = new bootstrap.Modal(/** @type {HTMLElement} */ (errorModalEl));
            errorModal["show"]();
        } catch (error) {
            console.error('Failed to fetch error summary:', error);
            updateWizardFooter('Could not retrieve the error report.', 'danger');
        } finally {
            setButtonState(errorBtn, false, {text: '<i class="fa-solid fa-triangle-exclamation me-2"></i>Show Error Report'});
        }
    };

    /** @param {string} taskId */
    const showServicesSummary = async (taskId) => {
        const summaryBtn = document.getElementById('show-summary-btn');
        if (!summaryBtn) return;

        setButtonState(summaryBtn, true, {loadingText: 'Loading...'});
        try {
            const finalData = await fetchAPI(`/task-status/${taskId}`);
            let allLinks = finalData.service_links || [];

            // --- DE BULLETPROOF FALLBACK ---
            if (allLinks.length === 0 && typeof selectedComponentsCache !== 'undefined') {

                const managedIps = Object.keys(managedDeviceCache);
                const piIp = (typeof finalVariablesCache !== 'undefined' && finalVariablesCache['PISelfhosting_HOST_IP'])
                    ? finalVariablesCache['PISelfhosting_HOST_IP']
                    : (managedIps.length > 0 ? managedIps[0] : window.location.hostname);

                selectedComponentsCache.forEach(compId => {
                    const comp = allSoftwareCache.find(c => c.id === compId);
                    if (comp && comp.ui_port_variable) {
                        let port = finalVariablesCache[comp.ui_port_variable];
                        if (!port && comp.required_variables) {
                            const varDef = comp.required_variables.find(v => v.id === comp.ui_port_variable);
                            if (varDef) port = varDef.default;
                        }
                        if (!port && /^\d+$/.test(String(comp.ui_port_variable).trim())) {
                            port = String(comp.ui_port_variable).trim();
                        }
                        const protocol = comp.protocol || 'http';
                        if (port) {
                            allLinks.push({
                                name: comp.name,
                                url: `${protocol}://${piIp}:${port}`
                            });
                        }
                    }
                });
            }

            if (allLinks.length > 0) {
                const uniqueLinks = Array.from(new Set(allLinks.map(a => a.url)))
                    .map(url => allLinks.find(a => a.url === url));

                const linksHTML = uniqueLinks
                    .map(link => `<li class="mb-2"><a href="${escapeHTML(link.url)}" target="_blank" class="fw-bold text-decoration-none">${escapeHTML(link.name)}</a><br><code class="text-muted">${escapeHTML(link.url)}</code></li>`)
                    .join('');

                const summaryBox = `
                <div id="service-links-summary" class="card mt-4 text-start shadow-sm border-success">
                    <div class="card-header bg-success text-white fw-bold">
                        <i class="fa-solid fa-rocket me-2"></i>Access Your Services
                    </div>
                    <div class="card-body">
                        <ul class="list-unstyled mb-0">${linksHTML}</ul>
                    </div>
                </div>`;

                document.getElementById('service-links-summary')?.remove();
                document.getElementById('log-viewer-container').insertAdjacentHTML('beforebegin', summaryBox);
                setButtonState(summaryBtn, false, {text: '<i class="fa-solid fa-check me-2"></i>Links Generated'});
            } else {
                setButtonState(summaryBtn, false, {text: 'No Web Interfaces Found'});
            }
        } catch (error) {
            console.error("Failed to show summary:", error);
            setButtonState(summaryBtn, false, {text: 'Error Loading Summary'});
        }
    };

    const setupStep1 = () => {
        const scanBtn = document.getElementById('begin-scan-btn');
        const manualInput = /** @type {HTMLInputElement} */ (document.getElementById('manualSubnetInput'));
        const directIpContainer = document.getElementById('direct_ip_input_container');
        const directIpInput = /** @type {HTMLInputElement} */ (document.getElementById('direct_target_ip'));

        const autoRadio = document.getElementById('autoDetectRadio');
        const manualRadio = document.getElementById('manualScanRadio');
        const directRadio = document.getElementById('method_direct_ip');
        const tsRadio = document.getElementById('method_tailscale');
        const lxcRadio = document.getElementById('method_proxmox_lxc');
        const lxcContainer = document.getElementById('proxmox_lxc_input_container');

        const vmRadio = document.getElementById('method_proxmox_vm');
        const vmContainer = document.getElementById('proxmox_vm_input_container');

        const existingRadio = document.getElementById('method_proxmox_existing');
        const existingContainer = document.getElementById('proxmox_existing_container');
        const refreshBtn = document.getElementById('refresh-proxmox-targets-btn');
        const targetSelect = /** @type {HTMLSelectElement} */ (document.getElementById('proxmox_target_select'));
        const targetsError = document.getElementById('proxmox_targets_error');

        // Check Tailscale status dynamically on Step 1 setup
        fetch('/tailscale-status')
            .then(res => res.json())
            .then(data => {
                const badge = document.getElementById('tailscale-status-badge');
                if (!tsRadio || !badge) return;
                if (data.active) {
                    (/** @type {HTMLInputElement} */ (tsRadio)).disabled = false;
                    badge.className = 'badge bg-success ms-2';
                    badge.innerHTML = `<i class="fa-solid fa-check me-1"></i> Active (${data.peers ? data.peers.length : 0} peers)`;
                } else if (data.timed_out) {
                    (/** @type {HTMLInputElement} */ (tsRadio)).disabled = false;
                    badge.className = 'badge bg-warning text-dark ms-2';
                    badge.innerHTML = '<i class="fa-solid fa-clock me-1"></i> Active (Busy / Click to Scan)';
                    badge.title = 'Tailscale CLI daemon timed out during background check, but radio option remains available.';
                } else {
                    (/** @type {HTMLInputElement} */ (tsRadio)).disabled = true;
                    badge.className = 'badge bg-secondary ms-2';
                    badge.textContent = 'Inactive / Not Found';
                    badge.title = data.reason || 'Tailscale is not active on this host';
                }
            })
            .catch(() => {
                const badge = document.getElementById('tailscale-status-badge');
                if (badge) {
                    badge.className = 'badge bg-secondary ms-2';
                    badge.textContent = 'Inactive';
                }
            });

        const loadVmTemplates = async () => {
            const templateSelect = document.getElementById('vm_template_select');
            if (!templateSelect) return;
            if (templateSelect.options.length > 1) return;
            templateSelect.innerHTML = '<option value="">-- Loading templates... --</option>';
            try {
                const res = await fetchAPI('/api/proxmox/list-templates', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'}
                });
                templateSelect.innerHTML = '<option value="">-- Select Template --</option>';
                if (res.templates && res.templates.length > 0) {
                    res.templates.forEach(t => {
                        const opt = document.createElement('option');
                        opt.value = t.vmid;
                        opt.textContent = `[${t.vmid}] ${t.name}`;
                        templateSelect.appendChild(opt);
                    });
                } else {
                    templateSelect.innerHTML = '<option value="">-- No templates found --</option>';
                }
            } catch (err) {
                console.error('Failed to load VM templates:', err);
                templateSelect.innerHTML = '<option value="">-- Error loading templates --</option>';
            }
        };

        const templateSelectEl = document.getElementById('vm_template_select');
        const templateManualEl = /** @type {HTMLInputElement} */ (document.getElementById('vm_template_manual'));
        if (templateSelectEl && templateManualEl) {
            templateSelectEl.addEventListener('change', () => {
                if (templateSelectEl.value) {
                    templateManualEl.value = templateSelectEl.value;
                }
            });
        }

        const methodHelpMap = {
            auto: {
                icon: 'fa-solid fa-wifi',
                title: 'Auto-Detect Local Subnet (L2 ARP Broadcast)',
                text: 'Scans your primary local subnet using L2 ARP broadcasts (nmap -sn -PR). Ideal for Raspberry Pi or SBCs connected directly to your local router.',
                snippet: 'ssh-copy-id pi@192.168.1.50'
            },
            manual: {
                icon: 'fa-solid fa-network-wired',
                title: 'Manual Subnet Scan (Custom CIDR)',
                text: 'Scans a custom IP range (e.g. 192.168.2.0/24 or 10.0.0.0/24). Use this if your target devices are on a separate VLAN, IoT network, or sub-router.',
                snippet: 'ssh-copy-id username@192.168.2.100'
            },
            direct: {
                icon: 'fa-solid fa-bullseye',
                title: 'Direct Target Deployment (IP / Hostname / MAC)',
                text: 'Directly connects to a specific IP (192.168.1.50 or Tailscale IP 100.x.y.z), local domain (my-server.local), or MAC address without scanning the network.',
                snippet: 'ssh-copy-id username@target-ip'
            },
            tailscale: {
                icon: 'fa-solid fa-diagram-project',
                title: 'Tailscale / Headscale Mesh Discovery',
                text: 'Automatically queries your local Tailscale daemon status to list all online nodes across your global overlay network. Bypasses L2 local subnet sweeps entirely.',
                snippet: 'ssh-copy-id username@100.x.y.z'
            },
            lxc: {
                icon: 'fa-solid fa-box',
                title: 'Automated Proxmox LXC Provisioning',
                text: 'Provisions a brand new Debian LXC container on your Proxmox VE server via API/SSH, automatically installs Docker Engine, and sets up root SSH access.',
                snippet: 'ssh-copy-id root@proxmox-host-ip'
            },
            vm: {
                icon: 'fa-solid fa-desktop',
                title: 'Automated Proxmox QEMU VM Cloning',
                text: 'Clones a clean Debian cloud-init master template on your Proxmox VE server, configures CPU/RAM/Disk, and boots up a brand-new QEMU Virtual Machine target.',
                snippet: 'ssh-copy-id debian@vm-ip'
            },
            existing: {
                icon: 'fa-solid fa-server',
                title: 'Existing Proxmox VE Target Selection',
                text: 'Fetches existing LXC containers and VMs from your Proxmox server, allowing you to select and auto-start an existing target for service deployment.',
                snippet: 'ssh-copy-id root@target-ip'
            }
        };

        const updateMethodHelpCard = (key) => {
            const data = methodHelpMap[key] || methodHelpMap.auto;
            const iconEl = document.getElementById('method-help-icon');
            const titleEl = document.getElementById('method-help-title');
            const textEl = document.getElementById('method-help-text');
            const snippetEl = document.getElementById('method-help-snippet');
            if (iconEl) iconEl.innerHTML = `<i class="${data.icon}"></i>`;
            if (titleEl) titleEl.textContent = data.title;
            if (textEl) textEl.textContent = data.text;
            if (snippetEl) snippetEl.textContent = data.snippet;
        };

        const copyBtn = document.getElementById('copy-snippet-btn');
        if (copyBtn) {
            copyBtn.addEventListener('click', () => {
                const snippetEl = document.getElementById('method-help-snippet');
                if (snippetEl && snippetEl.textContent) {
                    navigator.clipboard.writeText(snippetEl.textContent).then(() => {
                        copyBtn.innerHTML = '<i class="fa-solid fa-check me-1"></i> Copied!';
                        setTimeout(() => {
                            copyBtn.innerHTML = '<i class="fa-solid fa-copy me-1"></i> Copy';
                        }, 2000);
                    });
                }
            });
        }

        const updateInputs = async () => {
            if (autoRadio && (/** @type {HTMLInputElement} */ (autoRadio)).checked) {
                manualInput.disabled = true;
                if (directIpContainer) directIpContainer.classList.add('d-none');
                if (lxcContainer) lxcContainer.classList.add('d-none');
                if (vmContainer) vmContainer.classList.add('d-none');
                if (existingContainer) existingContainer.classList.add('d-none');
                if (scanBtn) scanBtn.innerHTML = '<i class="fa-solid fa-search me-2"></i> Begin Scan';
                updateMethodHelpCard('auto');
            }
            if (manualRadio && (/** @type {HTMLInputElement} */ (manualRadio)).checked) {
                manualInput.disabled = false;
                manualInput.focus();
                if (directIpContainer) directIpContainer.classList.add('d-none');
                if (lxcContainer) lxcContainer.classList.add('d-none');
                if (vmContainer) vmContainer.classList.add('d-none');
                if (existingContainer) existingContainer.classList.add('d-none');
                if (scanBtn) scanBtn.innerHTML = '<i class="fa-solid fa-search me-2"></i> Begin Scan';
                updateMethodHelpCard('manual');
            }
            if (directRadio && (/** @type {HTMLInputElement} */ (directRadio)).checked) {
                manualInput.disabled = true;
                if (lxcContainer) lxcContainer.classList.add('d-none');
                if (vmContainer) vmContainer.classList.add('d-none');
                if (existingContainer) existingContainer.classList.add('d-none');
                if (directIpContainer) {
                    directIpContainer.classList.remove('d-none');
                    if (directIpInput) directIpInput.focus();
                }
                if (scanBtn) scanBtn.innerHTML = '<i class="fa-solid fa-search me-2"></i> Begin Scan';
                updateMethodHelpCard('direct');
            }
            if (tsRadio && (/** @type {HTMLInputElement} */ (tsRadio)).checked) {
                manualInput.disabled = true;
                if (directIpContainer) directIpContainer.classList.add('d-none');
                if (lxcContainer) lxcContainer.classList.add('d-none');
                if (vmContainer) vmContainer.classList.add('d-none');
                if (existingContainer) existingContainer.classList.add('d-none');
                if (scanBtn) scanBtn.innerHTML = '<i class="fa-solid fa-network-wired me-2"></i> Discover Tailscale Mesh';
                updateMethodHelpCard('tailscale');
            }
            if (lxcRadio && (/** @type {HTMLInputElement} */ (lxcRadio)).checked) {
                manualInput.disabled = true;
                if (directIpContainer) directIpContainer.classList.add('d-none');
                if (vmContainer) vmContainer.classList.add('d-none');
                if (existingContainer) existingContainer.classList.add('d-none');
                if (lxcContainer) lxcContainer.classList.remove('d-none');
                if (scanBtn) scanBtn.innerHTML = '<i class="fa-solid fa-cloud-plus me-2"></i> Create & Provision LXC';
                updateMethodHelpCard('lxc');
            }
            if (vmRadio && (/** @type {HTMLInputElement} */ (vmRadio)).checked) {
                manualInput.disabled = true;
                if (directIpContainer) directIpContainer.classList.add('d-none');
                if (lxcContainer) lxcContainer.classList.add('d-none');
                if (existingContainer) existingContainer.classList.add('d-none');
                if (vmContainer) vmContainer.classList.remove('d-none');
                if (scanBtn) scanBtn.innerHTML = '<i class="fa-solid fa-cloud-plus me-2"></i> Create & Provision VM';
                updateMethodHelpCard('vm');
                await loadVmTemplates();
            }
            if (existingRadio && (/** @type {HTMLInputElement} */ (existingRadio)).checked) {
                manualInput.disabled = true;
                if (directIpContainer) directIpContainer.classList.add('d-none');
                if (lxcContainer) lxcContainer.classList.add('d-none');
                if (vmContainer) vmContainer.classList.add('d-none');
                if (existingContainer) existingContainer.classList.remove('d-none');
                if (scanBtn) scanBtn.innerHTML = '<i class="fa-solid fa-network-wired me-2"></i> Use Selected Target';
                updateMethodHelpCard('existing');
            }
        };

        if (autoRadio) autoRadio.addEventListener('change', updateInputs);
        if (manualRadio) manualRadio.addEventListener('change', updateInputs);
        if (directRadio) directRadio.addEventListener('change', updateInputs);
        if (tsRadio) tsRadio.addEventListener('change', updateInputs);
        if (lxcRadio) lxcRadio.addEventListener('change', updateInputs);
        if (vmRadio) vmRadio.addEventListener('change', updateInputs);
        if (existingRadio) existingRadio.addEventListener('change', updateInputs);

        if (refreshBtn) {
            refreshBtn.addEventListener('click', async () => {
                setButtonState(refreshBtn, true, {loadingText: 'Loading...'});
                if (targetsError) targetsError.classList.add('d-none');
                try {
                    const res = await fetchAPI('/api/proxmox/list-targets', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'}
                    });
                    if (targetSelect) {
                        targetSelect.innerHTML = '<option value="">-- Choose an existing VM or LXC container --</option>';
                        res.targets.forEach(t => {
                            const option = document.createElement('option');
                            option.value = JSON.stringify({
                                node: t.node,
                                vmid: t.vmid,
                                type: t.type,
                                status: t.status,
                                name: t.name
                            });
                            const statusEmoji = t.status === 'running' ? '🟢' : '🔴';
                            option.textContent = `[${t.type.toUpperCase()}] ${t.name} (VMID ${t.vmid}) - ${statusEmoji} ${t.status}`;
                            targetSelect.appendChild(option);
                        });
                    }
                } catch (err) {
                    console.error('Failed to load targets:', err);
                    if (targetsError) {
                        targetsError.textContent = `Failed to load targets: ${err.message}`;
                        targetsError.classList.remove('d-none');
                    }
                } finally {
                    setButtonState(refreshBtn, false, {text: 'Load/Refresh Targets'});
                }
            });
        }

        const performScan = async () => {
            const isLxc = lxcRadio && (/** @type {HTMLInputElement} */ (lxcRadio)).checked;
            const isVm = vmRadio && (/** @type {HTMLInputElement} */ (vmRadio)).checked;
            const isExisting = existingRadio && (/** @type {HTMLInputElement} */ (existingRadio)).checked;

            if (isExisting) {
                const selectedVal = targetSelect ? targetSelect.value : '';
                if (!selectedVal) {
                    updateWizardFooter('<i class="fa-solid fa-xmark me-2"></i>Please select a Proxmox target first.', 'danger');
                    return;
                }
                const target = JSON.parse(selectedVal);

                setButtonState(scanBtn, true, {loadingText: 'Connecting...'});
                updateWizardFooter(`Querying Proxmox target ${target.name} (VMID ${target.vmid})...`, 'primary');

                try {
                    let ipRes;
                    if (target.status === 'stopped') {
                        updateWizardFooter(`Starting ${target.type.toUpperCase()} target (VMID ${target.vmid}) and waiting for IP address...`, 'primary');
                        ipRes = await fetchAPI('/api/proxmox/start-target', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                node: target.node,
                                vmid: target.vmid,
                                type: target.type
                            })
                        });
                    } else {
                        ipRes = await fetchAPI('/api/proxmox/get-target-ip', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                node: target.node,
                                vmid: target.vmid,
                                type: target.type
                            })
                        });
                    }

                    if (!ipRes.ip) {
                        throw new Error('Failed to retrieve target IP address. Make sure the container/VM is running and guest agent/network interface is active.');
                    }

                    // Cache target credentials
                    managedDeviceCache[ipRes.ip] = {
                        ip: ipRes.ip,
                        hostname: target.name,
                        username: target.type === 'lxc' ? 'root' : '',
                        password: ''
                    };

                    const virtualScanData = {
                        hosts: [{
                            ip: ipRes.ip,
                            hostname: target.name
                        }],
                        messages: [],
                        permissions_error: false
                    };

                    lastScanData = virtualScanData;
                    renderStep2_ConfigureDevices(virtualScanData);
                } catch (error) {
                    console.error('An error occurred during Proxmox target configuration:', error);
                    updateWizardFooter(`<i class="fa-solid fa-xmark me-2"></i>An error occurred: ${escapeHTML(error.message)}`, 'danger');
                } finally {
                    setButtonState(scanBtn, false);
                    scanBtn.innerHTML = '<i class="fa-solid fa-network-wired me-2"></i> Use Selected Target';
                }
                return;
            }

            if (isLxc) {
                setButtonState(scanBtn, true, {loadingText: 'Provisioning LXC...'});
                updateWizardFooter('Creating Proxmox LXC container and installing Docker (this takes a few minutes)...', 'primary');

                const coresVal = parseInt(document.getElementById('lxc_cores').value) || 2;
                const memVal = parseInt(document.getElementById('lxc_memory').value) || 4096;
                const sizeVal = document.getElementById('lxc_storage_size').value || '20';
                const storageNameVal = document.getElementById('lxc_storage_name').value || 'local-lvm';
                const hostnameVal = document.getElementById('lxc_hostname').value.trim();

                try {
                    const lxcResult = await fetchAPI('/api/proxmox/create-lxc', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            cores: coresVal,
                            memory: memVal,
                            storage_size: sizeVal,
                            storage_name: storageNameVal,
                            hostname: hostnameVal
                        })
                    });

                    // Cache root user credentials so Step 2 automatically configures them
                    managedDeviceCache[lxcResult.ip] = {
                        ip: lxcResult.ip,
                        hostname: lxcResult.hostname || `LXC-${lxcResult.vmid}`,
                        username: 'root',
                        password: lxcResult.password
                    };

                    const virtualScanData = {
                        hosts: [{
                            ip: lxcResult.ip,
                            hostname: lxcResult.hostname || `LXC-${lxcResult.vmid}`
                        }],
                        messages: [],
                        permissions_error: false
                    };

                    lastScanData = virtualScanData;
                    renderStep2_ConfigureDevices(virtualScanData);
                } catch (error) {
                    console.error('An error occurred during Proxmox LXC creation:', error);
                    updateWizardFooter(`<i class="fa-solid fa-xmark me-2"></i>An error occurred: ${escapeHTML(error.message)}`, 'danger');
                } finally {
                    setButtonState(scanBtn, false);
                    scanBtn.innerHTML = '<i class="fa-solid fa-cloud-plus me-2"></i> Create & Provision LXC';
                }
                return;
            }

            if (isVm) {
                setButtonState(scanBtn, true, {loadingText: 'Provisioning VM...'});
                updateWizardFooter('Cloning Proxmox VM, configuring Cloud-Init, and installing Docker (this takes a few minutes)...', 'primary');

                const coresVal = parseInt(/** @type {HTMLInputElement} */ (document.getElementById('vm_cores')).value) || 2;
                const memVal = parseInt(/** @type {HTMLInputElement} */ (document.getElementById('vm_memory')).value) || 4096;
                const storageNameVal = (/** @type {HTMLInputElement} */ (document.getElementById('vm_storage_name'))).value || 'local-lvm';
                const storageSizeVal = parseInt(/** @type {HTMLInputElement} */ (document.getElementById('vm_storage_size')).value) || 32;
                const hostnameVal = (/** @type {HTMLInputElement} */ (document.getElementById('vm_hostname'))).value.trim();
                const templateManualVal = (/** @type {HTMLInputElement} */ (document.getElementById('vm_template_manual'))).value.trim();
                const usernameVal = (/** @type {HTMLInputElement} */ (document.getElementById('vm_username'))).value.trim() || 'debian';

                if (!templateManualVal) {
                    updateWizardFooter('<i class="fa-solid fa-xmark me-2"></i>Please select a template or enter a Template VMID.', 'danger');
                    setButtonState(scanBtn, false);
                    scanBtn.innerHTML = '<i class="fa-solid fa-cloud-plus me-2"></i> Create & Provision VM';
                    return;
                }

                try {
                    const vmResult = await fetchAPI('/api/proxmox/create-vm', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            cores: coresVal,
                            memory: memVal,
                            storage_name: storageNameVal,
                            storage_size: storageSizeVal,
                            hostname: hostnameVal,
                            template_vmid: templateManualVal,
                            username: usernameVal
                        })
                    });

                    // Cache credentials
                    managedDeviceCache[vmResult.ip] = {
                        ip: vmResult.ip,
                        hostname: vmResult.hostname || `VM-${vmResult.vmid}`,
                        username: vmResult.username || 'debian',
                        password: vmResult.password
                    };

                    const virtualScanData = {
                        hosts: [{
                            ip: vmResult.ip,
                            hostname: vmResult.hostname || `VM-${vmResult.vmid}`
                        }],
                        messages: [],
                        permissions_error: false
                    };

                    lastScanData = virtualScanData;
                    renderStep2_ConfigureDevices(virtualScanData);
                } catch (error) {
                    console.error('An error occurred during Proxmox VM creation:', error);
                    updateWizardFooter(`<i class="fa-solid fa-xmark me-2"></i>An error occurred: ${escapeHTML(error.message)}`, 'danger');
                } finally {
                    setButtonState(scanBtn, false);
                    scanBtn.innerHTML = '<i class="fa-solid fa-cloud-plus me-2"></i> Create & Provision VM';
                }
                return;
            }

            setButtonState(scanBtn, true, {loadingText: 'Scanning...'});
            updateWizardFooter('Scanning network for supported single-board computers...', 'primary');

            const isDirectIp = directRadio && (/** @type {HTMLInputElement} */ (directRadio)).checked;
            const isManual = manualRadio && (/** @type {HTMLInputElement} */ (manualRadio)).checked;
            const isTailscale = tsRadio && (/** @type {HTMLInputElement} */ (tsRadio)).checked;
            const subnetToScan = isManual ? manualInput.value : null;
            const directIpValue = isDirectIp ? (directIpInput ? directIpInput.value : "") : null;

            try {
                const discoveryMethod = isTailscale ? 'tailscale' : (isDirectIp ? 'direct_ip' : (isManual ? 'manual' : 'auto'));
                /** @type {ScanData} */
                const data = await fetchAPI('/scan-pis', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        subnet: subnetToScan,
                        discovery_method: discoveryMethod,
                        direct_target_ip: directIpValue
                    })
                });
                if (data.permissions_error) {
                    const troubleshootingUrl = 'https://github.com/HenkVanHoek/njord-deploy/blob/main/docs/TROUBLESHOOTING.md#network-scan-issues';
                    updateWizardFooter(`<strong>Warning:</strong> The scanner may not have required permissions. Please check our <a href='${troubleshootingUrl}' target='_blank'>troubleshooting guide</a>.`, 'warning');
                } else {
                    lastScanData = data; // Cache the scan data
                    if (subnetToScan) lastSubnetInput = subnetToScan; // Cache manual subnet
                    renderStep2_ConfigureDevices(data);
                }
            } catch (error) {
                console.error('An error occurred during the scan:', error);
                updateWizardFooter(`<i class="fa-solid fa-xmark me-2"></i>An error occurred: ${escapeHTML(error.message)}`, 'danger');
            } finally {
                setButtonState(scanBtn, false);
                scanBtn.innerHTML = '<i class="fa-solid fa-search me-2"></i> Begin Scan';
            }
        };

        if (scanBtn) scanBtn.addEventListener('click', performScan);
    };

    // Modern helper to toggle top horizontal progress bar and small logo visibility
    const toggleProgressBarVisibility = (show, percentage = 0) => {
        const stepsBar = document.querySelector('.row.text-center.mb-4, .d-flex.align-items-center.mb-4');
        if (stepsBar) {
            stepsBar.style.display = show ? '' : 'none';
        }
        if (wizardHeader) {
            wizardHeader.style.display = show ? '' : 'none';
        }

        // Mitigation: Safely update the new slim 4px horizontal progress line in the card
        const progressBarContainer = document.querySelector('.card > .progress');
        if (progressBarContainer) {
            progressBarContainer.style.display = show ? '' : 'none';
        }

        const progressBar = document.getElementById('wizard-progress-bar');
        if (progressBar && show) {
            progressBar.style.width = `${percentage}%`;
        }
    };

    // Listen for theme change events or dropdown button clicks
    document.querySelectorAll('[data-theme-value]').forEach(button => {
        button.addEventListener('click', () => {
            setTimeout(updateLogoVisibility, 50);
        });
    });

    // Delegated click event for password visibility toggle buttons
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

    /**
     * Triggers AI Deployment Health Evaluation and displays report modal.
     * @param {string} taskId
     * @param {string} [componentName='NjordDeploy Service Stack']
     */
    async function triggerDeploymentEvaluation(taskId, componentName = 'NjordDeploy Service Stack') {
        const modalEl = document.getElementById('deploymentEvalModal');
        if (!modalEl) return;

        // @ts-ignore
        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);

        const banner = document.getElementById('evalStatusBanner');
        const icon = document.getElementById('evalStatusIcon');
        const title = document.getElementById('evalStatusTitle');
        const summary = document.getElementById('evalSummaryText');
        const actionCard = document.getElementById('evalActionCard');
        const bugCard = document.getElementById('evalBugCard');

        if (banner) banner.className = 'alert alert-info d-flex align-items-center mb-3';
        if (icon) icon.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
        if (title) title.textContent = 'Analyzing Deployment Log & Health Status...';
        if (summary) summary.textContent = 'Evaluating log output with AI provider...';
        if (actionCard) actionCard.classList.add('d-none');
        if (bugCard) bugCard.classList.add('d-none');

        modal.show();

        try {
            const response = await fetch(`/api/deployment/${taskId}/evaluate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ component_name: componentName, use_ai: true })
            });
            const res = await response.json();

            if (summary) summary.textContent = res.summary || 'No summary provided.';

            if (res.status === 'GREEN') {
                if (banner) banner.className = 'alert alert-success d-flex align-items-center mb-3';
                if (icon) icon.innerHTML = '<i class="fa-solid fa-circle-check text-success"></i>';
                if (title) title.textContent = 'Deployment Healthy (Everything OK)';
            } else if (res.status === 'YELLOW') {
                if (banner) banner.className = 'alert alert-warning d-flex align-items-center mb-3';
                if (icon) icon.innerHTML = '<i class="fa-solid fa-triangle-exclamation text-warning"></i>';
                if (title) title.textContent = 'Configuration Tuning Recommended';

                if (actionCard) actionCard.classList.remove('d-none');
                const actionText = document.getElementById('evalActionText');
                if (actionText) actionText.textContent = res.user_action || 'Review configuration parameters.';

                if (res.doc_anchor) {
                    const docContainer = document.getElementById('evalDocLinkContainer');
                    const docLink = document.getElementById('evalDocLink');
                    if (docContainer) docContainer.classList.remove('d-none');
                    if (docLink) {
                        // @ts-ignore
                        docLink.href = `https://github.com/HenkVanHoek/njord-deploy/blob/main/docs/${res.doc_anchor}`;
                    }
                }
            } else {
                if (banner) banner.className = 'alert alert-danger d-flex align-items-center mb-3';
                if (icon) icon.innerHTML = '<i class="fa-solid fa-circle-xmark text-danger"></i>';
                if (title) title.textContent = 'Showstopper / Bug Identified';

                if (bugCard) bugCard.classList.remove('d-none');

                const keywords = res.github_keywords || componentName;
                const searchUrl = `https://github.com/HenkVanHoek/njord-deploy/issues?q=${encodeURIComponent(keywords)}`;
                const searchLink = document.getElementById('evalSearchGithubLink');
                if (searchLink) {
                    // @ts-ignore
                    searchLink.href = searchUrl;
                }

                const issueTitle = `[Bug] Deployment failure in ${componentName}`;
                const issueBody = `### Component\n${componentName}\n\n### Summary\n${res.summary}\n\n### Log Excerpt\n${res.user_action}`;
                const newIssueUrl = `https://github.com/HenkVanHoek/njord-deploy/issues/new?title=${encodeURIComponent(issueTitle)}&body=${encodeURIComponent(issueBody)}`;
                const reportLink = document.getElementById('evalReportGithubLink');
                if (reportLink) {
                    // @ts-ignore
                    reportLink.href = newIssueUrl;
                }
            }
        } catch (err) {
            if (banner) banner.className = 'alert alert-danger d-flex align-items-center mb-3';
            if (icon) icon.innerHTML = '<i class="fa-solid fa-exclamation-circle text-danger"></i>';
            if (title) title.textContent = 'Evaluation Failed';
            if (summary) summary.textContent = 'Failed to analyze deployment logs: ' + err.message;
        }
    }

    /**
     * Initializes the topbar Container Engine status badge, engine switcher dropdown,
     * and First-Run / Onboarding Setup Modal.
     */
    function initEngineAndRepoManagement() {
        const topbarBadge = document.getElementById('topbar-engine-badge');
        const topbarName = document.getElementById('topbar-engine-name');
        const topbarIcon = document.getElementById('topbar-engine-icon');
        const openOnboardBtn = document.getElementById('btn-open-onboarding-modal');
        const onboardModalEl = document.getElementById('onboardingModal');

        async function refreshEngineStatus() {
            try {
                const res = await fetch('/api/engine-status');
                if (!res.ok) return;
                const data = await res.json();
                const isPodman = data.engine === 'podman';

                if (topbarName) topbarName.textContent = isPodman ? 'Podman' : 'Docker';
                if (topbarIcon) {
                    topbarIcon.className = isPodman
                        ? 'fa-solid fa-feather-pointed me-1'
                        : 'fa-brands fa-docker me-1';
                }
                if (topbarBadge) {
                    topbarBadge.className = isPodman
                        ? 'badge bg-warning text-dark d-flex align-items-center me-1'
                        : 'badge bg-primary text-white d-flex align-items-center me-1';
                }
            } catch (e) {
                console.warn('Could not refresh engine status:', e);
            }
        }

        // Engine switcher buttons
        document.querySelectorAll('.btn-switch-engine').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const target = e.currentTarget;
                // @ts-ignore
                const engine = target.getAttribute('data-engine');
                if (!engine) return;
                try {
                    const res = await fetch('/api/engine-switch', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ engine })
                    });
                    const result = await res.json();
                    if (res.ok) {
                        await refreshEngineStatus();
                    } else {
                        alert(result.error || 'Failed to switch engine.');
                    }
                } catch (err) {
                    alert('Error switching container engine: ' + err.message);
                }
            });
        });

        // Setup / Onboarding Modal
        if (openOnboardBtn && onboardModalEl) {
            openOnboardBtn.addEventListener('click', () => {
                // @ts-ignore
                const modal = bootstrap.Modal.getOrCreateInstance(onboardModalEl);
                modal.show();
            });
        }

        // First-run automatic trigger
        async function checkFirstRun() {
            try {
                const res = await fetch('/api/first-run-status');
                if (!res.ok) return;
                const data = await res.json();
                if (data.first_run && onboardModalEl) {
                    // @ts-ignore
                    const modal = bootstrap.Modal.getOrCreateInstance(onboardModalEl);
                    modal.show();
                }
            } catch (e) {
                console.warn('First run check failed:', e);
            }
        }

        // Card choices styling
        const radioDocker = document.getElementById('engine-radio-docker');
        const radioPodman = document.getElementById('engine-radio-podman');
        const cardDocker = document.getElementById('card-choice-docker');
        const cardPodman = document.getElementById('card-choice-podman');

        function updateEngineCardSelection() {
            // @ts-ignore
            if (radioDocker && radioDocker.checked) {
                if (cardDocker) { cardDocker.classList.add('border-primary', 'bg-light'); }
                if (cardPodman) { cardPodman.classList.remove('border-primary', 'bg-light'); }
            } else if (radioPodman && radioPodman.checked) {
                if (cardPodman) { cardPodman.classList.add('border-primary', 'bg-light'); }
                if (cardDocker) { cardDocker.classList.remove('border-primary', 'bg-light'); }
            }
        }

        if (cardDocker && radioDocker) {
            cardDocker.addEventListener('click', () => {
                // @ts-ignore
                radioDocker.checked = true;
                updateEngineCardSelection();
            });
        }
        if (cardPodman && radioPodman) {
            cardPodman.addEventListener('click', () => {
                // @ts-ignore
                radioPodman.checked = true;
                updateEngineCardSelection();
            });
        }

        // Onboarding preset change
        const repoPreset = document.getElementById('onboard-repo-preset');
        const customRepoGroup = document.getElementById('onboard-custom-repo-group');
        if (repoPreset && customRepoGroup) {
            repoPreset.addEventListener('change', () => {
                // @ts-ignore
                if (repoPreset.value === 'custom') {
                    customRepoGroup.classList.remove('d-none');
                } else {
                    customRepoGroup.classList.add('d-none');
                }
            });
        }

        // Onboard Validate Repo button
        const validateBtn = document.getElementById('onboard-validate-btn');
        const feedbackEl = document.getElementById('onboard-validation-feedback');
        if (validateBtn && feedbackEl) {
            validateBtn.addEventListener('click', async () => {
                const urlEl = document.getElementById('onboard-custom-url');
                const branchEl = document.getElementById('onboard-custom-branch');
                const tokenEl = document.getElementById('onboard-custom-token');
                // @ts-ignore
                const url = urlEl ? urlEl.value.trim() : '';
                // @ts-ignore
                const branch = branchEl ? branchEl.value.trim() : 'main';
                // @ts-ignore
                const token = tokenEl ? tokenEl.value.trim() : '';

                if (!url) {
                    feedbackEl.className = 'small mt-2 text-warning';
                    feedbackEl.textContent = 'Please enter a repository URL.';
                    return;
                }

                validateBtn.disabled = true;
                feedbackEl.className = 'small mt-2 text-info';
                feedbackEl.textContent = 'Testing connection...';

                try {
                    const res = await fetch('/api/validate-repo', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ url, branch, token })
                    });
                    const data = await res.json();
                    if (res.ok && data.valid) {
                        feedbackEl.className = 'small mt-2 text-success';
                        feedbackEl.textContent = '✓ ' + data.message;
                    } else {
                        feedbackEl.className = 'small mt-2 text-danger';
                        feedbackEl.textContent = '✗ ' + (data.message || 'Validation failed.');
                    }
                } catch (err) {
                    feedbackEl.className = 'small mt-2 text-danger';
                    feedbackEl.textContent = 'Error: ' + err.message;
                } finally {
                    validateBtn.disabled = false;
                }
            });
        }

        // Onboard Save button
        const saveOnboardBtn = document.getElementById('onboard-save-btn');
        if (saveOnboardBtn) {
            saveOnboardBtn.addEventListener('click', async () => {
                // @ts-ignore
                const chosenEngine = (radioPodman && radioPodman.checked) ? 'podman' : 'docker';
                // @ts-ignore
                const preset = repoPreset ? repoPreset.value : 'default';
                let repoUrl = 'HenkVanHoek/njord-deploy-components';
                let repoBranch = 'main';
                let repoToken = '';

                if (preset === 'local') {
                    repoUrl = 'none';
                } else if (preset === 'custom') {
                    const urlEl = document.getElementById('onboard-custom-url');
                    const branchEl = document.getElementById('onboard-custom-branch');
                    const tokenEl = document.getElementById('onboard-custom-token');
                    // @ts-ignore
                    repoUrl = urlEl ? urlEl.value.trim() : '';
                    // @ts-ignore
                    repoBranch = branchEl ? branchEl.value.trim() : 'main';
                    // @ts-ignore
                    repoToken = tokenEl ? tokenEl.value.trim() : '';
                }

                saveOnboardBtn.disabled = true;
                const origHtml = saveOnboardBtn.innerHTML;
                saveOnboardBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-1"></i> Saving...';

                try {
                    await fetch('/api/settings', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            mode: 'form',
                            settings: {
                                CONTAINER_ENGINE: chosenEngine,
                                COMPONENTS_REPO_URL: repoUrl,
                                COMPONENTS_REPO_BRANCH: repoBranch,
                                COMPONENTS_REPO_TOKEN: repoToken,
                            }
                        })
                    });

                    await fetch('/api/engine-switch', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ engine: chosenEngine })
                    });

                    await refreshEngineStatus();

                    if (onboardModalEl) {
                        // @ts-ignore
                        const modal = bootstrap.Modal.getInstance(onboardModalEl);
                        if (modal) modal.hide();
                    }
                } catch (err) {
                    alert('Failed to save settings: ' + err.message);
                } finally {
                    saveOnboardBtn.disabled = false;
                    saveOnboardBtn.innerHTML = origHtml;
                }
            });
        }

        refreshEngineStatus();
        checkFirstRun();
    }

    /**
     * Initializes the Quick Start modal, Prerequisites Banner, and Intro.js Interactive Tour.
     */
    function initQuickStartAndTour() {
        const quickStartModalEl = document.getElementById('quickStartModal');
        const hideGuideCheckbox = document.getElementById('hide-quickstart-checkbox');
        const navQuickStartBtn = document.getElementById('nav-quick-start-btn');
        const navStartTourBtn = document.getElementById('nav-start-tour-btn');
        const quickstartTourBtn = document.getElementById('quickstart-tour-btn');
        const prereqCollapseEl = document.getElementById('prerequisitesCollapse');
        const prereqChevron = document.getElementById('prereq-chevron');

        // Manage collapsible prerequisites banner state and chevron
        if (prereqCollapseEl && prereqChevron) {
            prereqCollapseEl.addEventListener('show.bs.collapse', () => {
                prereqChevron.className = 'fa-solid fa-chevron-up text-primary transition-transform';
                localStorage.setItem('configurator_prerequisites_open', 'true');
            });
            prereqCollapseEl.addEventListener('hide.bs.collapse', () => {
                prereqChevron.className = 'fa-solid fa-chevron-down text-muted transition-transform';
                localStorage.setItem('configurator_prerequisites_open', 'false');
            });

            // Restore user preference if previously expanded
            if (localStorage.getItem('configurator_prerequisites_open') === 'true') {
                // @ts-ignore
                const collapseInstance = bootstrap.Collapse.getOrCreateInstance(prereqCollapseEl, { toggle: false });
                collapseInstance.show();
            }
        }

        function startInteractiveTour(e) {
            if (e) e.preventDefault();
            localStorage.setItem('configurator_tour_shown', 'true');

            // Hide quick start modal if currently open
            if (quickStartModalEl) {
                // @ts-ignore
                const modal = bootstrap.Modal.getInstance(quickStartModalEl);
                if (modal) modal.hide();
            }

            // @ts-ignore
            if (window.introJs) {
                // @ts-ignore
                window.introJs().setOptions({
                    steps: [
                        {
                            title: "Welcome to NjordDeploy",
                            intro: "Welcome to the <strong>NjordDeploy Deployment Wizard</strong>! This quick guided tour walks you through discovering devices, configuring stacks, and launching self-hosted services."
                        },
                        {
                            element: document.getElementById("prerequisites-banner-card"),
                            title: "Getting Started & Prerequisites",
                            intro: "Click this banner anytime to view target machine requirements, SSH setup hints, and direct links to get API keys for optional AI Failure Diagnosis & Generation.",
                            position: "bottom"
                        },
                        {
                            element: document.getElementById("topbar-engine-badge") || document.getElementById("engineDropdown"),
                            title: "Active Container Engine",
                            intro: "NjordDeploy supports standard <strong>Docker CE</strong> and rootless <strong>Podman</strong>. Switch engines or configure your component template repository anytime.",
                            position: "bottom"
                        },
                        {
                            element: document.getElementById("themeDropdown"),
                            title: "Themes & Accessibility",
                            intro: "Switch effortlessly between <strong>Futuristic Dark</strong>, <strong>Standard Light</strong>, and <strong>High-Contrast</strong> themes.",
                            position: "bottom"
                        },
                        {
                            element: document.getElementById("discovery-methods-card"),
                            title: "Target Discovery Methods",
                            intro: "Select how to find your target machine: <strong>Auto-Detect</strong> via L2 ARP sweep, <strong>Manual CIDR</strong> subnet scan, <strong>Direct IP / Hostname / MAC</strong>, <strong>Tailscale mesh</strong>, or <strong>Proxmox LXC/VM</strong> provisioning.",
                            position: "top"
                        },
                        {
                            element: document.getElementById("method-help-card"),
                            title: "Contextual Help & SSH Tip",
                            intro: "Get instant setup tips and 1-click <code>ssh-copy-id</code> snippets to authorize your SSH key on the target machine for secure, passwordless deployment.",
                            position: "top"
                        },
                        {
                            element: document.getElementById("begin-scan-btn"),
                            title: "Start Discovery",
                            intro: "Click <strong>Begin Scan</strong> to find devices on your network, select your target single-board computer, and proceed to service selection.",
                            position: "top"
                        },
                        {
                            element: document.getElementById("nav-backup-btn"),
                            title: "Backup & Disaster Recovery",
                            intro: "Create full archives of your stack configurations and volume data, or restore from previous backups directly from the navigation bar.",
                            position: "bottom"
                        },
                        {
                            title: "Ready to Deploy!",
                            intro: "You're all set! Choose a discovery option and click <strong>Begin Scan</strong> to start deploying your self-hosted services."
                        }
                    ],
                    showProgress: true,
                    showBullets: false,
                    disableInteraction: false,
                    nextLabel: 'Next &rarr;',
                    prevLabel: '&larr; Back',
                    doneLabel: 'Done'
                }).start();
            }
        }

        if (navQuickStartBtn && quickStartModalEl) {
            navQuickStartBtn.addEventListener('click', (e) => {
                e.preventDefault();
                // @ts-ignore
                const modal = bootstrap.Modal.getOrCreateInstance(quickStartModalEl);
                modal.show();
            });
        }

        if (navStartTourBtn) {
            navStartTourBtn.addEventListener('click', (e) => {
                startInteractiveTour(e);
            });
        }

        if (quickstartTourBtn) {
            quickstartTourBtn.addEventListener('click', (e) => {
                startInteractiveTour(e);
            });
        }

        if (hideGuideCheckbox) {
            const isHidden = localStorage.getItem('configurator_hide_quickstart_guide') === 'true';
            // @ts-ignore
            hideGuideCheckbox.checked = isHidden;

            hideGuideCheckbox.addEventListener('change', (e) => {
                // @ts-ignore
                if (e.target && e.target.checked) {
                    localStorage.setItem('configurator_hide_quickstart_guide', 'true');
                } else {
                    localStorage.removeItem('configurator_hide_quickstart_guide');
                }
            });
        }

        // Auto-show Quick Start on first visit if not explicitly hidden
        const guideHidden = localStorage.getItem('configurator_hide_quickstart_guide') === 'true';
        const guideShown = localStorage.getItem('configurator_quickstart_shown') === 'true';

        if (!guideHidden && !guideShown && quickStartModalEl) {
            localStorage.setItem('configurator_quickstart_shown', 'true');
            setTimeout(() => {
                // Check if onboarding modal (engine setup) isn't showing
                const onboardModalEl = document.getElementById('onboardingModal');
                const isEngineModalOpen = onboardModalEl && onboardModalEl.classList.contains('show');
                if (!isEngineModalOpen) {
                    // @ts-ignore
                    const modal = bootstrap.Modal.getOrCreateInstance(quickStartModalEl);
                    modal.show();
                }
            }, 600);
        }
    }

    // Initialize Onboarding/Welcome Step 0 on page load
    renderStep1_Welcome();
    initEngineAndRepoManagement();
    initQuickStartAndTour();
})();
