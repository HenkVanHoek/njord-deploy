// src/configurator_app/static/js/backup_manager_ui.js
/* global bootstrap */

(function () {
    "use strict";

    document.addEventListener("DOMContentLoaded", () => {
        const modalEl = document.getElementById("backupRestoreModal");
        if (!modalEl) return;

        const targetIpInput = document.getElementById("backup-target-ip");
        const targetUserInput = document.getElementById("backup-target-user");
        const targetPassInput = document.getElementById("backup-target-pass");
        const targetPathInput = document.getElementById("backup-target-path");
        const connectBtn = document.getElementById("backup-connect-btn");

        const refreshInspectBtn = document.getElementById("backup-refresh-inspect-btn");
        const createBackupBtn = document.getElementById("backup-create-btn");
        const listBackupsBtn = document.getElementById("backup-refresh-list-btn");
        const restoreBackupBtn = document.getElementById("backup-restore-btn");
        const componentListContainer = document.getElementById("backup-components-container");
        const backupListContainer = document.getElementById("backup-archives-table-body");
        const backupStatusAlert = document.getElementById("backup-status-alert");
        const restoreStatusAlert = document.getElementById("restore-status-alert");

        // Helper to retrieve target credentials and path from modal inputs or fallback to wizard/session
        function getTargetCredentials() {
            let ip = targetIpInput ? targetIpInput.value.trim() : "";
            let username = targetUserInput ? targetUserInput.value.trim() : "root";
            let password = targetPassInput ? targetPassInput.value : "";
            let project_config_dir = targetPathInput ? targetPathInput.value.trim() : "/opt/njorddeploy";

            // Fallback to wizard fields or stored session if empty
            if (!ip) {
                const wizardIp = document.getElementById("ip_address") || document.getElementById("device_ip");
                if (wizardIp && wizardIp.value.trim()) {
                    ip = wizardIp.value.trim();
                    if (targetIpInput) targetIpInput.value = ip;
                } else {
                    const savedIp = sessionStorage.getItem("njorddeploy_backup_ip");
                    if (savedIp) {
                        ip = savedIp;
                        if (targetIpInput) targetIpInput.value = ip;
                    }
                }
            }

            if (!username) {
                const wizardUser = document.getElementById("username") || document.getElementById("ssh_user");
                if (wizardUser && wizardUser.value.trim()) {
                    username = wizardUser.value.trim();
                    if (targetUserInput) targetUserInput.value = username;
                } else {
                    const savedUser = sessionStorage.getItem("njorddeploy_backup_user");
                    if (savedUser) {
                        username = savedUser;
                        if (targetUserInput) targetUserInput.value = username;
                    }
                }
            }

            if (!password) {
                const wizardPass = document.getElementById("password") || document.getElementById("ssh_password");
                if (wizardPass && wizardPass.value) {
                    password = wizardPass.value;
                    if (targetPassInput) targetPassInput.value = password;
                } else {
                    const savedPass = sessionStorage.getItem("njorddeploy_backup_pass");
                    if (savedPass) {
                        password = savedPass;
                        if (targetPassInput) targetPassInput.value = password;
                    }
                }
            }

            if (!project_config_dir) {
                const savedPath = sessionStorage.getItem("njorddeploy_backup_path");
                if (savedPath) {
                    project_config_dir = savedPath;
                    if (targetPathInput) targetPathInput.value = project_config_dir;
                } else {
                    project_config_dir = "/opt/njorddeploy";
                }
            }

            return { ip, username, password, project_config_dir };
        }

        function saveCredentials(creds) {
            if (creds.ip) sessionStorage.setItem("njorddeploy_backup_ip", creds.ip);
            if (creds.username) sessionStorage.setItem("njorddeploy_backup_user", creds.username);
            if (creds.password) sessionStorage.setItem("njorddeploy_backup_pass", creds.password);
            if (creds.project_config_dir) sessionStorage.setItem("njorddeploy_backup_path", creds.project_config_dir);
        }

        function renderInitialState() {
            if (componentListContainer) {
                componentListContainer.innerHTML = `
                    <div class="text-center py-4 text-muted bg-body-tertiary border rounded">
                        <i class="fa-solid fa-server fa-2x mb-2 text-primary opacity-50"></i>
                        <div class="fw-semibold">Enter Target Host Details Above</div>
                        <div class="small mt-1 text-secondary">
                            Provide the IP address, SSH credentials, and stack directory above and click <strong>Connect</strong> to inspect services.
                        </div>
                    </div>
                `;
            }
            if (backupListContainer) {
                backupListContainer.innerHTML = `
                    <tr><td colspan="4" class="text-center py-3 text-muted">Enter host credentials and connect to list available archives.</td></tr>
                `;
            }
            if (createBackupBtn) createBackupBtn.disabled = true;
            if (restoreBackupBtn) restoreBackupBtn.disabled = true;
        }

        // 1. Inspect Target Volumes
        async function loadTargetVolumes() {
            if (!componentListContainer) return;
            const creds = getTargetCredentials();

            if (!creds.ip) {
                renderInitialState();
                return;
            }

            saveCredentials(creds);
            componentListContainer.innerHTML = `
                <div class="text-center py-4 text-muted bg-body-tertiary border rounded">
                    <span class="spinner-border text-primary spinner-border-sm me-2"></span> Inspecting stack at <code>${creds.project_config_dir}</code> on <code>${creds.ip}</code>...
                </div>
            `;
            if (backupStatusAlert) backupStatusAlert.classList.add("d-none");

            try {
                const response = await fetch("/api/backup/inspect", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(creds),
                });
                const data = await response.json();

                if (!response.ok || data.status !== "success") {
                    const errMsg = data.message || data.error || "No compose stack detected at specified path.";
                    componentListContainer.innerHTML = `
                        <div class="alert alert-warning small mb-0">
                            <i class="fa-solid fa-triangle-exclamation me-1"></i> ${errMsg}
                        </div>
                    `;
                    if (createBackupBtn) createBackupBtn.disabled = true;
                    return;
                }

                if (createBackupBtn) createBackupBtn.disabled = false;

                // Sync resolved path back to UI input if auto-detected differently
                if (data.managed_scope && targetPathInput && data.managed_scope !== targetPathInput.value) {
                    targetPathInput.value = data.managed_scope;
                    sessionStorage.setItem("njorddeploy_backup_path", data.managed_scope);
                }

                const components = data.components || [];
                if (components.length === 0) {
                    componentListContainer.innerHTML = `
                        <div class="alert alert-info small mb-0">
                            <i class="fa-solid fa-circle-info me-1"></i> No managed services found under <code>${data.managed_scope || creds.project_config_dir}</code>.
                        </div>
                    `;
                    return;
                }

                let html = '<div class="list-group list-group-flush border rounded">';
                components.forEach(comp => {
                    const heavyBadge = comp.is_heavy ? '<span class="badge bg-warning text-dark ms-2"><i class="fa-solid fa-hard-drive me-1"></i>Large Data</span>' : '';
                    html += `
                        <label class="list-group-item d-flex justify-content-between align-items-center cursor-pointer">
                            <div class="form-check m-0">
                                <input class="form-check-input backup-comp-checkbox" type="checkbox" value="${comp.id}" checked id="bk-comp-${comp.id}">
                                <label class="form-check-label fw-semibold ms-1" for="bk-comp-${comp.id}">
                                    ${comp.name}
                                </label>
                                ${heavyBadge}
                            </div>
                            <span class="badge bg-secondary rounded-pill">${comp.total_size_human}</span>
                        </label>
                    `;
                });
                html += '</div>';
                html += `
                    <div class="d-flex justify-content-between align-items-center mt-2 text-muted small px-1">
                        <span>Total Managed Footprint: <strong>${data.total_managed_size_human}</strong> (Scope: <code>${data.managed_scope}</code>)</span>
                        <a href="#" id="backup-toggle-all" class="text-decoration-none">Toggle All</a>
                    </div>
                `;
                componentListContainer.innerHTML = html;

                const toggleAll = document.getElementById("backup-toggle-all");
                if (toggleAll) {
                    toggleAll.addEventListener("click", (e) => {
                        e.preventDefault();
                        const boxes = componentListContainer.querySelectorAll(".backup-comp-checkbox");
                        const anyUnchecked = Array.from(boxes).some(b => !b.checked);
                        boxes.forEach(b => { b.checked = anyUnchecked; });
                    });
                }
            } catch (err) {
                componentListContainer.innerHTML = `
                    <div class="alert alert-danger small mb-0">
                        <i class="fa-solid fa-circle-exclamation me-1"></i> Failed to communicate with backup API: ${err.message}
                    </div>
                `;
            }
        }

        // 2. Create Backup Action
        if (createBackupBtn) {
            createBackupBtn.addEventListener("click", async () => {
                const creds = getTargetCredentials();
                if (!creds.ip) {
                    alert("Please enter the Target Host IP address above.");
                    return;
                }

                const boxes = document.querySelectorAll(".backup-comp-checkbox:checked");
                const selected = Array.from(boxes).map(b => b.value);
                const pauseCheckbox = document.getElementById("backup-pause-containers");
                const pauseContainers = pauseCheckbox ? pauseCheckbox.checked : false;

                if (selected.length === 0) {
                    alert("Please select at least one component to include in the backup.");
                    return;
                }

                createBackupBtn.disabled = true;
                createBackupBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Archiving...';
                if (backupStatusAlert) {
                    backupStatusAlert.className = "alert alert-info small mt-3";
                    backupStatusAlert.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Generating compressed backup tarball on target host...';
                    backupStatusAlert.classList.remove("d-none");
                }

                const payload = {
                    ...creds,
                    selected_components: selected,
                    pause_containers: pauseContainers,
                };

                try {
                    const res = await fetch("/api/backup/create", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(payload),
                    });
                    const data = await res.json();

                    if (!res.ok || data.status !== "success") {
                        if (backupStatusAlert) {
                            backupStatusAlert.className = "alert alert-danger small mt-3";
                            backupStatusAlert.innerHTML = `<i class="fa-solid fa-circle-xmark me-1"></i> Backup failed: ${data.message || data.error || "Unknown error"}`;
                        }
                    } else {
                        if (backupStatusAlert) {
                            backupStatusAlert.className = "alert alert-success small mt-3";
                            backupStatusAlert.innerHTML = `
                                <div><i class="fa-solid fa-circle-check me-1"></i> <strong>Backup Created Successfully!</strong></div>
                                <div class="mt-1">Archive: <code>${data.filename}</code> (${data.size_human})</div>
                                <div class="mt-2">
                                    <a href="/api/backup/download/${encodeURIComponent(data.filename)}?ip=${encodeURIComponent(creds.ip)}&username=${encodeURIComponent(creds.username)}&project_config_dir=${encodeURIComponent(creds.project_config_dir)}" class="btn btn-sm btn-success text-white">
                                        <i class="fa-solid fa-download me-1"></i> Download to Local Machine
                                    </a>
                                </div>
                            `;
                        }
                        loadBackupList();
                    }
                } catch (err) {
                    if (backupStatusAlert) {
                        backupStatusAlert.className = "alert alert-danger small mt-3";
                        backupStatusAlert.innerHTML = `<i class="fa-solid fa-circle-xmark me-1"></i> Network error: ${err.message}`;
                    }
                } finally {
                    createBackupBtn.disabled = false;
                    createBackupBtn.innerHTML = '<i class="fa-solid fa-box-archive me-1"></i> Create Backup';
                }
            });
        }

        // 3. List Existing Backups
        async function loadBackupList() {
            if (!backupListContainer) return;
            const creds = getTargetCredentials();

            if (!creds.ip) {
                backupListContainer.innerHTML = `
                    <tr><td colspan="4" class="text-center py-3 text-muted">Enter host credentials and connect to list available archives.</td></tr>
                `;
                return;
            }

            backupListContainer.innerHTML = `
                <tr><td colspan="4" class="text-center py-3 text-muted"><span class="spinner-border spinner-border-sm me-2"></span> Loading archives from <code>${creds.project_config_dir}</code> on <code>${creds.ip}</code>...</td></tr>
            `;

            try {
                const res = await fetch("/api/backup/list", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(creds),
                });
                const data = await res.json();

                if (!res.ok || data.status !== "success") {
                    backupListContainer.innerHTML = `
                        <tr><td colspan="4" class="text-center text-muted py-3">Unable to list backups. Make sure device is connected and directory exists.</td></tr>
                    `;
                    if (restoreBackupBtn) restoreBackupBtn.disabled = true;
                    return;
                }

                const backups = data.backups || [];
                if (backups.length === 0) {
                    backupListContainer.innerHTML = `
                        <tr><td colspan="4" class="text-center text-muted py-3">No previous backups found in <code>${creds.project_config_dir}/backups</code>.</td></tr>
                    `;
                    if (restoreBackupBtn) restoreBackupBtn.disabled = true;
                    return;
                }

                let html = "";
                backups.forEach(bk => {
                    html += `
                        <tr>
                            <td><input type="radio" name="selected_backup_radio" value="${bk.filename}" class="form-check-input"></td>
                            <td><code>${bk.filename}</code></td>
                            <td>${bk.created_at}</td>
                            <td><span class="badge bg-secondary">${bk.size_human}</span></td>
                        </tr>
                    `;
                });
                backupListContainer.innerHTML = html;

                // Auto-select first radio
                const firstRadio = backupListContainer.querySelector("input[type=radio]");
                if (firstRadio) firstRadio.checked = true;
                if (restoreBackupBtn) restoreBackupBtn.disabled = false;
            } catch (err) {
                backupListContainer.innerHTML = `
                    <tr><td colspan="4" class="text-center text-danger py-3">Error: ${err.message}</td></tr>
                `;
                if (restoreBackupBtn) restoreBackupBtn.disabled = true;
            }
        }

        // 4. Restore Backup Action
        if (restoreBackupBtn) {
            restoreBackupBtn.addEventListener("click", async () => {
                const selectedRadio = document.querySelector("input[name=selected_backup_radio]:checked");
                if (!selectedRadio) {
                    alert("Please select a backup archive to restore.");
                    return;
                }

                const filename = selectedRadio.value;
                if (!confirm(`Are you sure you want to restore from ${filename}?\nThis will stop current services and restore configurations and volumes in the active stack directory.`)) {
                    return;
                }

                restoreBackupBtn.disabled = true;
                restoreBackupBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Restoring...';
                if (restoreStatusAlert) {
                    restoreStatusAlert.className = "alert alert-info small mt-3";
                    restoreStatusAlert.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Restoring files and restarting container stack...';
                    restoreStatusAlert.classList.remove("d-none");
                }

                const creds = getTargetCredentials();
                try {
                    const res = await fetch("/api/backup/restore", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            ...creds,
                            backup_filename: filename,
                            restart_after: true,
                        }),
                    });
                    const data = await res.json();

                    if (!res.ok || data.status !== "success") {
                        if (restoreStatusAlert) {
                            restoreStatusAlert.className = "alert alert-danger small mt-3";
                            restoreStatusAlert.innerHTML = `<i class="fa-solid fa-circle-xmark me-1"></i> Restore failed: ${data.message || data.error || "Unknown error"}`;
                        }
                    } else {
                        if (restoreStatusAlert) {
                            restoreStatusAlert.className = "alert alert-success small mt-3";
                            restoreStatusAlert.innerHTML = `
                                <div><i class="fa-solid fa-circle-check me-1"></i> <strong>Restore Completed Successfully!</strong></div>
                                <div class="mt-1">All managed services and volume data have been restored and restarted in <code>${data.managed_scope || creds.project_config_dir}</code>.</div>
                            `;
                        }
                    }
                } catch (err) {
                    if (restoreStatusAlert) {
                        restoreStatusAlert.className = "alert alert-danger small mt-3";
                        restoreStatusAlert.innerHTML = `<i class="fa-solid fa-circle-xmark me-1"></i> Network error: ${err.message}`;
                    }
                } finally {
                    restoreBackupBtn.disabled = false;
                    restoreBackupBtn.innerHTML = '<i class="fa-solid fa-rotate-left me-1"></i> Restore Selected Backup';
                }
            });
        }

        // Connect button handler
        if (connectBtn) {
            connectBtn.addEventListener("click", async () => {
                connectBtn.disabled = true;
                connectBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Connecting...';
                await loadTargetVolumes();
                await loadBackupList();
                connectBtn.disabled = false;
                connectBtn.innerHTML = '<i class="fa-solid fa-plug me-1"></i> Connect';
            });
        }

        // Allow pressing Enter in target inputs to trigger connect
        [targetIpInput, targetUserInput, targetPassInput, targetPathInput].forEach(inp => {
            if (inp) {
                inp.addEventListener("keydown", (e) => {
                    if (e.key === "Enter") {
                        e.preventDefault();
                        if (connectBtn) connectBtn.click();
                    }
                });
            }
        });

        const scanComposeBtn = document.getElementById("backup-scan-compose-btn");
        const scanFeedback = document.getElementById("backup-scan-feedback");

        // Scan Host for Compose Files button handler
        if (scanComposeBtn) {
            scanComposeBtn.addEventListener("click", async () => {
                const creds = getTargetCredentials();
                if (!creds.ip) {
                    alert("Please enter the Target Host IP address first.");
                    return;
                }

                scanComposeBtn.disabled = true;
                scanComposeBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Scanning...';
                if (scanFeedback) {
                    scanFeedback.innerHTML = '<span class="spinner-border spinner-border-sm me-1 text-primary"></span> Searching $HOME, /opt, /srv...';
                }

                try {
                    const res = await fetch("/api/backup/discover-compose", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(creds),
                    });
                    const data = await res.json();

                    if (!res.ok || data.status !== "success" || !data.discovered_paths || data.discovered_paths.length === 0) {
                        if (scanFeedback) {
                            scanFeedback.innerHTML = '<span class="text-warning"><i class="fa-solid fa-triangle-exclamation me-1"></i> No compose files found.</span>';
                        }
                    } else {
                        const firstMatch = data.discovered_paths[0];
                        if (targetPathInput) {
                            targetPathInput.value = firstMatch.directory;
                            sessionStorage.setItem("njorddeploy_backup_path", firstMatch.directory);
                        }
                        if (scanFeedback) {
                            scanFeedback.innerHTML = `<span class="text-success"><i class="fa-solid fa-check me-1"></i> Found: <code>${firstMatch.directory}</code></span>`;
                        }
                        await loadTargetVolumes();
                        await loadBackupList();
                    }
                } catch (err) {
                    if (scanFeedback) {
                        scanFeedback.innerHTML = `<span class="text-danger"><i class="fa-solid fa-circle-xmark me-1"></i> Scan error: ${err.message}</span>`;
                    }
                } finally {
                    scanComposeBtn.disabled = false;
                    scanComposeBtn.innerHTML = '<i class="fa-solid fa-magnifying-glass me-1"></i> Scan Host';
                }
            });
        }

        // Save credentials on input change
        [targetIpInput, targetUserInput, targetPassInput, targetPathInput].forEach(inp => {
            if (inp) {
                inp.addEventListener("input", () => {
                    saveCredentials(getTargetCredentials());
                });
            }
        });

        // Attach modal trigger listeners
        modalEl.addEventListener("show.bs.modal", () => {
            if (backupStatusAlert) backupStatusAlert.classList.add("d-none");
            if (restoreStatusAlert) restoreStatusAlert.classList.add("d-none");
            if (scanFeedback) {
                scanFeedback.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles text-primary me-1"></i> Auto-detects compose stacks.';
            }
            getTargetCredentials(); // Pre-fills inputs with saved credentials if available
            renderInitialState();   // Shows prompt until user explicitly clicks Connect
        });

        if (refreshInspectBtn) refreshInspectBtn.addEventListener("click", loadTargetVolumes);
        if (listBackupsBtn) listBackupsBtn.addEventListener("click", loadBackupList);
    });
})();
