/**
 * scripts/static/js/proxmox_gui.js
 * Interactive frontend logic for NjordDeploy Proxmox Component Test GUI.
 */

(() => {
  "use strict";

  // Application State
  const state = {
    targetType: "components", // 'components' | 'packages'
    components: [],
    selectedIds: new Set(),
    activeFilter: "all", // 'all' | 'testable' | 'untested' | 'tested' | 'ui' | 'untestable'
    searchQuery: "",
    packages: [],
    selectedPackageIds: new Set(),
    activePackageFilter: "all", // 'all' | 'msp' | 'media-ai' | 'security' | 'productivity'
    packageSearchQuery: "",
    mode: "lxc", // 'lxc' | 'vm' | 'both'
    engine: "docker", // 'docker' | 'podman' | 'both'
    isRunning: false,
    eventSource: null,
    results: [],
    sortColumn: "timestamp",
    sortDirection: "desc",
    activeAiProvider: "",
    activeAiName: "",
    activeAiModel: "",
    currentReportFile: "",
    currentCompId: "",
  };

  // DOM Elements
  const elements = {
    // Header AI Provider Selector
    aiProviderSelect: document.getElementById("ai-provider-select"),

    // Target Switcher Tabs & Views
    tabServicesBtn: document.getElementById("tab-services-btn"),
    tabPackagesBtn: document.getElementById("tab-packages-btn"),
    servicesView: document.getElementById("services-view"),
    packagesView: document.getElementById("packages-view"),
    servicesCountBadge: document.getElementById("services-count-badge"),
    packagesCountBadge: document.getElementById("packages-count-badge"),

    // Config elements
    modeLxcBtn: document.getElementById("mode-lxc-btn"),
    modeVmBtn: document.getElementById("mode-vm-btn"),
    modeBothBtn: document.getElementById("mode-both-btn"),
    engineDockerBtn: document.getElementById("engine-docker-btn"),
    enginePodmanBtn: document.getElementById("engine-podman-btn"),
    engineBothBtn: document.getElementById("engine-both-btn"),
    nodeInput: document.getElementById("node-input"),
    templateIdInput: document.getElementById("template-id-input"),
    templateIdWrapper: document.getElementById("template-id-wrapper"),
    templatesDisplay: document.getElementById("templates-display"),
    toggleNetworkBtn: document.getElementById("toggle-network-btn"),
    configBridgeLabel: document.getElementById("config-bridge-label"),
    configGwLabel: document.getElementById("config-gw-label"),
    configIpLabel: document.getElementById("config-ip-label"),
    configNetStatus: document.getElementById("config-net-status"),

    // Filter & Search elements (Services)
    searchInput: document.getElementById("search-input"),
    searchClearBtn: document.getElementById("search-clear-btn"),
    filterPills: document.querySelectorAll("#services-view .filter-pill"),
    componentsGrid: document.getElementById("components-grid"),

    // Selection toolbar (Services)
    selectionCountBadge: document.getElementById("selection-count-badge"),
    selectAllFilteredBtn: document.getElementById("select-all-filtered-btn"),
    selectAllTestableBtn: document.getElementById("select-all-testable-btn"),
    deselectUntestableBtn: document.getElementById("deselect-untestable-btn"),
    deselectAllFilteredBtn: document.getElementById("deselect-all-filtered-btn"),
    clearSelectionBtn: document.getElementById("clear-selection-btn"),

    // Package search & filters
    packageSearchInput: document.getElementById("package-search-input"),
    packageSearchClearBtn: document.getElementById("package-search-clear-btn"),
    packageFilterPills: document.querySelectorAll("#package-filter-pills .filter-pill"),
    packagesGrid: document.getElementById("packages-grid"),
    packageSelectionCountBadge: document.getElementById("package-selection-count-badge"),
    selectAllPackagesBtn: document.getElementById("select-all-packages-btn"),
    clearPackagesSelectionBtn: document.getElementById("clear-packages-selection-btn"),

    // Runner controls
    startRunBtn: document.getElementById("start-run-btn"),
    stopRunBtn: document.getElementById("stop-run-btn"),
    maintainTemplatesBtn: document.getElementById("maintain-templates-btn"),
    startRunText: document.getElementById("start-run-text"),
    appStatusBadge: document.getElementById("app-status-badge"),

    // Terminal elements
    terminalBody: document.getElementById("terminal-body"),
    clearTerminalBtn: document.getElementById("clear-terminal-btn"),
    copyTerminalBtn: document.getElementById("copy-terminal-btn"),
    viewReportBtn: document.getElementById("view-report-btn"),
    exportLatestPdfBtn: document.getElementById("export-latest-pdf-btn"),

    // Results & History table
    resultsTableBody: document.getElementById("results-table-body"),
    clearHistoryBtn: document.getElementById("clear-history-btn"),
    aiBatchBtn: document.getElementById("ai-batch-btn"),
    aiFailuresBadge: document.getElementById("ai-failures-badge"),

    // Clear History Modal
    clearConfirmModal: document.getElementById("clear-confirm-modal"),
    closeClearModalBtn: document.getElementById("close-clear-modal-btn"),
    cancelClearBtn: document.getElementById("cancel-clear-btn"),
    confirmClearBtn: document.getElementById("confirm-clear-btn"),

    // AI Diagnostics Modal
    aiModal: document.getElementById("ai-modal"),
    aiModalTitle: document.getElementById("ai-modal-title"),
    aiModalBody: document.getElementById("ai-modal-body"),
    closeAiModalBtn: document.getElementById("close-ai-modal-btn"),
    aiModalCloseBtn: document.getElementById("ai-modal-close-btn"),
    aiModalApplyBtn: document.getElementById("ai-modal-apply-btn"),

    // Report modal
    reportModal: document.getElementById("report-modal"),
    closeModalBtn: document.getElementById("close-modal-btn"),
    reportModalCloseBtn: document.getElementById("report-modal-close-btn"),
    reportContent: document.getElementById("report-content"),
    reportRawContent: document.getElementById("report-raw-content"),
    btnReportViewFormatted: document.getElementById("btn-report-view-formatted"),
    btnReportViewRaw: document.getElementById("btn-report-view-raw"),
    btnReportExportPdf: document.getElementById("btn-report-export-pdf"),
    reportModalExportPdfBtn: document.getElementById("report-modal-export-pdf-btn"),
    reportModalMeta: document.getElementById("report-modal-meta"),
  };

  /**
   * Generates a formatted timestamp string (YYYY-MM-DD HH:MM:SS)
   */
  function getTimestamp() {
    const now = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    const yyyy = now.getFullYear();
    const mm = pad(now.getMonth() + 1);
    const dd = pad(now.getDate());
    const hh = pad(now.getHours());
    const min = pad(now.getMinutes());
    const ss = pad(now.getSeconds());
    return `${yyyy}-${mm}-${dd} ${hh}:${min}:${ss}`;
  }

  /**
   * Escape special regex characters in search query except '*' and '?'
   */
  function wildcardToRegex(pattern) {
    if (!pattern) return null;
    const escaped = pattern
      .replace(/[-[\]{}()+.,\\^$|#\s]/g, "\\$&")
      .replace(/\*/g, ".*")
      .replace(/\?/g, ".");
    return new RegExp(escaped, "i");
  }

  /**
   * Evaluates whether a component matches the wildcard pattern and active filter
   */
  function matchesFilter(comp) {
    // 1. Check active category/status filter
    if (state.activeFilter === "testable" && comp.is_untestable) {
      return false;
    }
    if (state.activeFilter === "untestable" && !comp.is_untestable) {
      return false;
    }
    if (state.activeFilter === "untested" && comp.status === "tested") {
      return false;
    }
    if (state.activeFilter === "tested" && comp.status !== "tested") {
      return false;
    }
    if (state.activeFilter === "ui" && !comp.has_ui) {
      return false;
    }

    // 2. Check search query (wildcard / substring)
    const q = state.searchQuery.trim();
    if (!q) return true;

    const regex = wildcardToRegex(q);
    if (!regex) return true;

    const targetFields = [
      comp.id || "",
      comp.name || "",
      comp.category || "",
      comp.description || "",
    ];

    return targetFields.some((field) => regex.test(field));
  }

  /**
   * Get list of currently visible components based on filter & search
   */
  function getFilteredComponents() {
    return state.components.filter(matchesFilter);
  }

  /**
   * Evaluates whether a package matches the wildcard pattern and active filter
   */
  function matchesPackageFilter(pkg) {
    const isMsp = (pkg.badge && pkg.badge.toLowerCase().includes("msp")) ||
      pkg.id.includes("workplace") || pkg.id.includes("archive") ||
      pkg.id.includes("agile") || pkg.id.includes("observability");
    const isMediaAi = pkg.id.includes("media") || pkg.id.includes("ollama") ||
      (pkg.badge && (pkg.badge.toLowerCase().includes("media") || pkg.badge.toLowerCase().includes("ai")));
    const isSecurity = pkg.id.includes("dns") || pkg.id.includes("shield") ||
      (pkg.badge && pkg.badge.toLowerCase().includes("security"));
    const isProductivity = pkg.id.includes("agile") || pkg.id.includes("caddy") ||
      pkg.id.includes("monitoring") || pkg.id.includes("smarthome");

    if (state.activePackageFilter === "msp" && !isMsp) return false;
    if (state.activePackageFilter === "media-ai" && !isMediaAi) return false;
    if (state.activePackageFilter === "security" && !isSecurity) return false;
    if (state.activePackageFilter === "productivity" && !isProductivity) return false;

    const q = state.packageSearchQuery.trim();
    if (!q) return true;

    const regex = wildcardToRegex(q);
    if (!regex) return true;

    const compNames = (pkg.components_detail || []).map((c) => c.name || c.id).join(" ");
    const targetFields = [
      pkg.id || "",
      pkg.name || "",
      pkg.badge || "",
      pkg.description || "",
      compNames,
    ];

    return targetFields.some((field) => regex.test(field));
  }

  /**
   * Get list of currently visible packages based on filter & search
   */
  function getFilteredPackages() {
    return state.packages.filter(matchesPackageFilter);
  }

  /**
   * Updates test network indicators and text values in the UI
   */
  function updateNetworkUI(networkConfig) {
    if (!networkConfig) return;
    if (elements.configBridgeLabel && networkConfig.bridge) {
      elements.configBridgeLabel.textContent = networkConfig.bridge;
    }
    if (elements.configGwLabel && networkConfig.gateway) {
      elements.configGwLabel.textContent = networkConfig.gateway;
    }
    if (elements.configIpLabel && networkConfig.test_ip) {
      const cidr = networkConfig.test_ip.includes("/")
        ? networkConfig.test_ip
        : `${networkConfig.test_ip}/24`;
      elements.configIpLabel.textContent = cidr;
    }
    if (elements.configNetStatus) {
      if (
        networkConfig.bridge === "vmbr1" ||
        (networkConfig.test_ip && networkConfig.test_ip.startsWith("10.99."))
      ) {
        elements.configNetStatus.textContent = "Geïsoleerd Test-Subnet";
        elements.configNetStatus.style.color = "var(--accent-green)";
      } else {
        elements.configNetStatus.textContent = "LAN Bridge (vmbr0)";
        elements.configNetStatus.style.color = "var(--accent-amber)";
      }
    }
  }

  /**
   * Updates the active Proxmox Golden Template badges (911-914)
   * dynamically based on Target Mode and Container Engine selections.
   */
  function updateTemplatesUI() {
    if (!elements.templatesDisplay) return;

    const mode = state.mode; // 'lxc' | 'vm' | 'both'
    const engine = state.engine; // 'docker' | 'podman' | 'both'

    const activeTemplates = [];

    const isLxc = mode === "lxc" || mode === "both";
    const isVm = mode === "vm" || mode === "both";
    const isDocker = engine === "docker" || engine === "both";
    const isPodman = engine === "podman" || engine === "both";

    if (isLxc && isDocker) {
      activeTemplates.push({
        id: 912,
        mode: "LXC",
        engine: "Docker",
        cls: "tpl-lxc-docker",
      });
    }
    if (isLxc && isPodman) {
      activeTemplates.push({
        id: 914,
        mode: "LXC",
        engine: "Podman",
        cls: "tpl-lxc-podman",
      });
    }
    if (isVm && isDocker) {
      activeTemplates.push({
        id: 911,
        mode: "VM",
        engine: "Docker",
        cls: "tpl-vm-docker",
      });
    }
    if (isVm && isPodman) {
      activeTemplates.push({
        id: 913,
        mode: "VM",
        engine: "Podman",
        cls: "tpl-vm-podman",
      });
    }

    elements.templatesDisplay.innerHTML = "";
    activeTemplates.forEach((t) => {
      const badge = document.createElement("span");
      badge.className = `template-badge ${t.cls}`;
      badge.title = `Template ID ${t.id}: ${t.engine} op ${t.mode}`;
      badge.innerHTML = `<strong>${t.id}</strong> <small>(${t.mode} ${t.engine})</small>`;
      elements.templatesDisplay.appendChild(badge);
    });

    if (elements.templateIdInput) {
      const firstTpl = activeTemplates[0];
      elements.templateIdInput.value = firstTpl ? String(firstTpl.id) : "902";
    }
  }

  /**
   * Updates selection badges and start button state
   */
  function updateSelectionUI() {
    const compCount = state.selectedIds.size;
    const totalComps = state.components.length;
    if (elements.selectionCountBadge) {
      elements.selectionCountBadge.textContent = `${compCount} of ${totalComps} selected`;
    }
    if (elements.servicesCountBadge) {
      elements.servicesCountBadge.textContent = String(totalComps);
    }

    const pkgCount = state.selectedPackageIds.size;
    const totalPkgs = state.packages.length;
    if (elements.packageSelectionCountBadge) {
      elements.packageSelectionCountBadge.textContent = `${pkgCount} of ${totalPkgs} stacks selected`;
    }
    if (elements.packagesCountBadge) {
      elements.packagesCountBadge.textContent = String(totalPkgs);
    }

    if (state.targetType === "packages") {
      if (pkgCount > 0) {
        elements.startRunText.textContent = `Start Stack Test Run (${pkgCount} ${
          pkgCount === 1 ? "stack" : "stacks"
        })`;
        elements.startRunBtn.disabled = state.isRunning;
      } else {
        elements.startRunText.textContent = "Start Stack Test Run (Select stacks)";
        elements.startRunBtn.disabled = true;
      }
    } else {
      if (compCount > 0) {
        elements.startRunText.textContent = `Start Test Run (${compCount} ${
          compCount === 1 ? "service" : "services"
        })`;
        elements.startRunBtn.disabled = state.isRunning;
      } else {
        elements.startRunText.textContent = "Start Test Run (Select services)";
        elements.startRunBtn.disabled = true;
      }
    }
  }

  /**
   * Renders component cards into the grid
   */
  function renderComponents() {
    const filtered = getFilteredComponents();

    if (filtered.length === 0) {
      elements.componentsGrid.innerHTML = `
        <div style="grid-column: 1 / -1; padding: 2rem; text-align: center; color: var(--text-muted);">
          No components match your search or filter criteria.
        </div>
      `;
      return;
    }

    const cardsHtml = filtered
      .map((comp) => {
        const isSelected = state.selectedIds.has(comp.id);
        const isUntestable = Boolean(comp.is_untestable);
        const isTested = comp.status === "tested";
        const statusClass = isTested ? "tag-tested" : "tag-untested";
        const statusText = isTested ? "Tested" : "Untested";

        let tagsHtml = `<span class="tag ${statusClass}">${statusText}</span>`;

        if (isUntestable) {
          const reasonAttr = escapeHtml(
            comp.untestable_reason || "Untestable / Skipped component"
          );
          tagsHtml += `<span class="tag tag-untestable" title="${reasonAttr}">⚠️ Untestable</span>`;
        }

        if (comp.has_ui) {
          tagsHtml += '<span class="tag tag-ui">🌐 UI</span>';
        }

        if (comp.category) {
          tagsHtml += `<span class="tag tag-category">${escapeHtml(comp.category)}</span>`;
        }

        const compName = escapeHtml(comp.name || comp.id);
        const compId = escapeHtml(comp.id);

        return `
          <div class="component-card ${isSelected ? "selected" : ""} ${
          isUntestable ? "untestable" : ""
        }" data-id="${compId}" data-component-id="${compId}">
            <input type="checkbox" class="component-checkbox" ${
              isSelected ? "checked" : ""
            } />
            <div class="component-info">
              <div class="component-name">${compName}</div>
              <div class="component-id">${compId}</div>
              <div class="component-tags">${tagsHtml}</div>
            </div>
          </div>
        `;
      })
      .join("");

    elements.componentsGrid.innerHTML = cardsHtml;
  }

  /**
   * Renders package cards into the packages grid
   */
  function renderPackages() {
    if (!elements.packagesGrid) return;
    const filtered = getFilteredPackages();

    if (filtered.length === 0) {
      elements.packagesGrid.innerHTML = `
        <div style="grid-column: 1 / -1; padding: 2rem; text-align: center; color: var(--text-muted);">
          No 1-click stacks match your search or filter criteria.
        </div>
      `;
      return;
    }

    const cardsHtml = filtered
      .map((pkg) => {
        const isSelected = state.selectedPackageIds.has(pkg.id);
        const isTested = pkg.status === "success" || pkg.status === "tested";
        const statusClass = isTested ? "tag-tested" : "tag-untested";
        const statusText = isTested ? "Tested ✅" : "Untested ⚪";

        let badgeClass = "package-badge-curated";
        const lowerBadge = (pkg.badge || "").toLowerCase();
        if (lowerBadge.includes("msp")) badgeClass = "package-badge-msp";
        else if (lowerBadge.includes("media")) badgeClass = "package-badge-media";
        else if (lowerBadge.includes("security")) badgeClass = "package-badge-security";
        else if (lowerBadge.includes("ai")) badgeClass = "package-badge-ai";

        const appsHtml = (pkg.components_detail || [])
          .map(
            (c) => `
            <span class="package-app-tag" title="${escapeHtml(c.id)}">
              <span>📦</span> ${escapeHtml(c.name || c.id)}
            </span>
          `
          )
          .join("");

        const pkgId = escapeHtml(pkg.id);
        const pkgName = escapeHtml(pkg.name || pkg.id);
        const pkgBadge = escapeHtml(pkg.badge || "Stack");
        const appCount = pkg.app_count || (pkg.components || []).length;
        const pkgDesc = escapeHtml(
          pkg.description || "A pre-configured turnkey stack of services."
        );

        return `
          <div class="package-card ${isSelected ? "selected" : ""}" data-package-id="${pkgId}">
            <div class="package-card-header">
              <span class="package-badge ${badgeClass}">${pkgBadge}</span>
              <div style="display: flex; align-items: center; gap: 0.5rem;">
                <span class="tag tag-category">${appCount} Apps</span>
                <input type="checkbox" class="package-checkbox" ${
                  isSelected ? "checked" : ""
                } />
              </div>
            </div>
            <div class="package-card-title">
              <span class="package-card-title-icon">📚</span>
              <span>${pkgName}</span>
            </div>
            <div class="package-card-desc">${pkgDesc}</div>
            <div class="package-apps-container">
              ${appsHtml}
            </div>
            <div class="package-card-footer">
              <span style="font-family: var(--font-mono); color: var(--text-muted);">${pkgId}</span>
              <span class="tag ${statusClass}">${statusText}</span>
            </div>
          </div>
        `;
      })
      .join("");

    elements.packagesGrid.innerHTML = cardsHtml;
  }

  /**
   * Switches active target selection view (Services vs Packages)
   */
  function switchTargetType(type) {
    state.targetType = type;
    if (type === "packages") {
      if (elements.tabPackagesBtn) elements.tabPackagesBtn.classList.add("active");
      if (elements.tabServicesBtn) elements.tabServicesBtn.classList.remove("active");
      if (elements.packagesView) elements.packagesView.style.display = "block";
      if (elements.servicesView) elements.servicesView.style.display = "none";
    } else {
      if (elements.tabServicesBtn) elements.tabServicesBtn.classList.add("active");
      if (elements.tabPackagesBtn) elements.tabPackagesBtn.classList.remove("active");
      if (elements.servicesView) elements.servicesView.style.display = "block";
      if (elements.packagesView) elements.packagesView.style.display = "none";
    }
    updateSelectionUI();
  }

  /**
   * Set execution status in header
   */
  function setStatus(status, text) {
    elements.appStatusBadge.className = `status-badge status-${status}`;
    elements.appStatusBadge.textContent = text || status.toUpperCase();
  }

  /**
   * Safely escapes HTML special characters
   */
  function escapeHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  /**
   * Converts ANSI color escape codes to styled HTML spans
   */
  function ansiToHtml(str) {
    const colorMap = {
      "0;31": "var(--accent-red)",
      "1;31": "var(--accent-red)",
      "31": "var(--accent-red)",
      "0;32": "var(--accent-green)",
      "1;32": "var(--accent-green)",
      "32": "var(--accent-green)",
      "0;33": "var(--accent-amber)",
      "1;33": "var(--accent-amber)",
      "33": "var(--accent-amber)",
      "0;34": "var(--accent-blue)",
      "1;34": "var(--accent-blue)",
      "34": "var(--accent-blue)",
      "0;35": "var(--accent-purple)",
      "1;35": "var(--accent-purple)",
      "35": "var(--accent-purple)",
      "0;36": "var(--accent-cyan)",
      "1;36": "var(--accent-cyan)",
      "36": "var(--accent-cyan)",
      "0;37": "var(--text-secondary)",
      "1;37": "#ffffff",
      "37": "var(--text-secondary)",
    };

    const escaped = escapeHtml(str);
    let result = escaped.replace(/\x1b\[([0-9;]+)m/g, (match, code) => {
      if (code === "0" || code === "") {
        return "</span>";
      }
      const color = colorMap[code];
      if (color) {
        return `<span style="color: ${color};">`;
      }
      return "";
    });

    // Strip any other unhandled ANSI escape sequences
    result = result.replace(/\x1b\[[0-9;]*[a-zA-Z]/g, "");
    return result;
  }

  /**
   * Append a log line to the live terminal with high-throughput RAF batching
   */
  const terminalBuffer = [];
  let terminalFlushPending = false;

  function appendLog(line) {
    terminalBuffer.push(line);
    if (!terminalFlushPending) {
      terminalFlushPending = true;
      requestAnimationFrame(() => {
        terminalFlushPending = false;
        if (!elements.terminalBody || terminalBuffer.length === 0) return;

        const fragment = document.createDocumentFragment();
        while (terminalBuffer.length > 0) {
          const l = terminalBuffer.shift();
          const lineDiv = document.createElement("div");
          lineDiv.className = "terminal-line";
          lineDiv.innerHTML = ansiToHtml(l);
          fragment.appendChild(lineDiv);
        }
        elements.terminalBody.appendChild(fragment);

        const excess = elements.terminalBody.childElementCount - 400;
        if (excess > 0) {
          for (let i = 0; i < excess; i++) {
            if (elements.terminalBody.firstChild) {
              elements.terminalBody.removeChild(elements.terminalBody.firstChild);
            }
          }
        }

        elements.terminalBody.scrollTop = elements.terminalBody.scrollHeight;
      });
    }
  }

  /**
   * Sorts results records array based on active column and direction
   */
  function sortResults(records, column, direction) {
    const mult = direction === "asc" ? 1 : -1;
    return [...records].sort((a, b) => {
      let valA = a[column];
      let valB = b[column];

      if (column === "timestamp") {
        return mult * String(valA || "").localeCompare(String(valB || ""));
      }

      if (column === "vmid") {
        const numA = parseInt(valA, 10);
        const numB = parseInt(valB, 10);
        const hasA = !isNaN(numA);
        const hasB = !isNaN(numB);
        if (hasA && hasB) {
          if (numA !== numB) return mult * (numA - numB);
        } else if (hasA) {
          return mult * -1;
        } else if (hasB) {
          return mult * 1;
        }
        return mult * String(valA || "").localeCompare(String(valB || ""));
      }

      if (column === "ip") {
        const parseIp = (ip) => {
          if (!ip || typeof ip !== "string") return null;
          const parts = ip.split(".").map((p) => parseInt(p, 10));
          if (parts.length === 4 && parts.every((p) => !isNaN(p))) {
            return parts[0] * 16777216 + parts[1] * 65536 + parts[2] * 256 + parts[3];
          }
          return null;
        };
        const numA = parseIp(valA);
        const numB = parseIp(valB);
        if (numA !== null && numB !== null) {
          if (numA !== numB) return mult * (numA - numB);
        } else if (numA !== null) {
          return mult * -1;
        } else if (numB !== null) {
          return mult * 1;
        }
        return mult * String(valA || "").localeCompare(String(valB || ""));
      }

      if (column === "running") {
        const numA = a.running ? 1 : 0;
        const numB = b.running ? 1 : 0;
        return mult * (numA - numB);
      }

      if (column === "http_ok") {
        const score = (v) => (v === true ? 2 : v === false ? 1 : 0);
        return mult * (score(a.http_ok) - score(b.http_ok));
      }

      if (column === "status") {
        const priority = { success: 4, running: 3, pending: 2, failed: 1 };
        const scoreA = priority[a.status] || 0;
        const scoreB = priority[b.status] || 0;
        if (scoreA !== scoreB) return mult * (scoreA - scoreB);
        return mult * String(a.status || "").localeCompare(String(b.status || ""));
      }

      valA = String(valA || "").toLowerCase();
      valB = String(valB || "").toLowerCase();
      return mult * valA.localeCompare(valB);
    });
  }

  /**
   * Updates sort indicators on the table header cells
   */
  function updateTableHeaderSortUI() {
    const headers = document.querySelectorAll(".results-table th[data-sort]");
    headers.forEach((th) => {
      const col = th.dataset.sort;
      th.classList.remove("sort-asc", "sort-desc");
      const iconSpan = th.querySelector(".sort-icon");
      if (col === state.sortColumn) {
        th.classList.add(state.sortDirection === "asc" ? "sort-asc" : "sort-desc");
        if (iconSpan) {
          iconSpan.textContent = state.sortDirection === "asc" ? "▲" : "▼";
        }
      } else {
        if (iconSpan) {
          iconSpan.textContent = "⇅";
        }
      }
    });
  }

  let activePatchData = null;

  /**
   * Renders code diff with colored additions and deletions
   */
  function renderDiffHtml(diffText) {
    if (!diffText) return "";
    const lines = diffText.split("\n");
    const htmlLines = lines.map((line) => {
      const escaped = escapeHtml(line);
      if (line.startsWith("+") && !line.startsWith("+++")) {
        return `<div class="ai-diff-add">${escaped}</div>`;
      } else if (line.startsWith("-") && !line.startsWith("---")) {
        return `<div class="ai-diff-del">${escaped}</div>`;
      }
      return `<div>${escaped}</div>`;
    });
    return `<div class="ai-diff-view">${htmlLines.join("")}</div>`;
  }

  /**
   * Opens AI single failure diagnosis modal with selected provider
   */
  async function openAiSingleDiagnosis(record) {
    if (!record) return;
    activePatchData = null;
    elements.aiModalApplyBtn.style.display = "none";
    const aiLabel = state.activeAiName || "AI";
    elements.aiModalTitle.textContent = `✨ ${aiLabel} Diagnosis: ${record.component_id} (${record.mode || ""}/${record.engine || ""})`;
    elements.aiModalBody.innerHTML = `
      <div style="text-align: center; padding: 2rem;">
        <div style="font-size: 2rem; margin-bottom: 0.75rem;">⏳</div>
        <div><strong>Analyzing failure with ${escapeHtml(aiLabel)}...</strong></div>
        <div style="color: var(--text-muted); font-size: 0.85rem; margin-top: 0.25rem;">
          Inspecting error logs, container status, and docker-compose template...
        </div>
      </div>
    `;
    elements.aiModal.classList.add("open");

    try {
      const res = await fetch("/api/ai/diagnose", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          component_id: record.component_id,
          record: record,
          provider: state.activeAiProvider || undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        elements.aiModalBody.innerHTML = `
          <div class="ai-card" style="border-color: var(--accent-red);">
            <div class="ai-card-title" style="color: var(--accent-red);">❌ Diagnosis Failed</div>
            <p>${escapeHtml(data.error || "Unknown AI diagnosis error")}</p>
          </div>
        `;
        return;
      }

      const diag = data.diagnosis;
      const targetType = diag.target_type || "TEMPLATE_CONFIG";

      let badgeHtml = "";
      if (targetType === "CORE_PLATFORM_CODE") {
        badgeHtml = `<span class="ai-badge-type ai-badge-core">🛠️ Core Platform Code Bug</span>`;
      } else if (targetType === "ENVIRONMENT_INFRA") {
        badgeHtml = `<span class="ai-badge-type ai-badge-infra">🌐 Host Environment Issue</span>`;
      } else if (targetType === "MATRIX_CONSTRAINT") {
        badgeHtml = `<span class="ai-badge-type ai-badge-matrix">⚠️ Matrix Constraint</span>`;
      } else {
        badgeHtml = `<span class="ai-badge-type ai-badge-template">📝 Template Configuration</span>`;
      }

      let bodyHtml = `
        <div class="ai-card">
          <div class="ai-card-title">
            <span>🔍 Root Cause Summary</span>
            <div style="display: flex; gap: 0.4rem; align-items: center;">
              ${badgeHtml}
              ${diag.category ? `<span class="ai-cluster-tag">${escapeHtml(diag.category)}</span>` : ""}
            </div>
          </div>
          ${diag.target_file ? `<div style="font-size: 0.8rem; font-family: var(--font-mono); color: var(--text-secondary); margin-bottom: 0.5rem;">📁 Target: <code>${escapeHtml(diag.target_file)}</code></div>` : ""}
          <p><strong>${escapeHtml(diag.summary || "")}</strong></p>
          <p style="color: var(--text-secondary); margin-top: 0.5rem; font-size: 0.88rem;">
            ${escapeHtml(diag.root_cause_analysis || "")}
          </p>
        </div>

        <div class="ai-card">
          <div class="ai-card-title">💡 Recommended Fix</div>
          <p style="font-size: 0.88rem;">${escapeHtml(diag.fix_description || "")}</p>
          ${diag.patch_notes ? `<p style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.4rem;"><em>Note: ${escapeHtml(diag.patch_notes)}</em></p>` : ""}
        </div>
      `;

      if (diag.suggested_root_mode) {
        const rootMode = diag.suggested_root_mode;
        bodyHtml += `
          <div class="ai-card" style="border-left: 3px solid #eab308;">
            <div class="ai-card-title" style="color: #fde047;">🛡️ Recommended Root Privilege Mode</div>
            <div style="font-size: 0.88rem; margin-bottom: 0.5rem;">
              <div><strong>Podman Mode:</strong> <code>${escapeHtml(rootMode.podman_mode || "rootful")}</code></div>
              <div style="margin-top: 0.25rem;"><strong>Requires Root:</strong> <code>true</code></div>
              ${rootMode.reason ? `<div style="margin-top: 0.4rem; color: var(--text-secondary);"><em>${escapeHtml(rootMode.reason)}</em></div>` : ""}
            </div>
            <button type="button" class="btn btn-warning btn-sm" id="applyRootModeBtn" style="margin-top: 0.5rem;">
              Apply Root Mode to Metadata
            </button>
          </div>
        `;
      }

      if (targetType === "MATRIX_CONSTRAINT" && diag.suggested_matrix) {
        const smModes = (diag.suggested_matrix.modes || []).map(m => `<span class="tag tag-category">${escapeHtml(m.toUpperCase())}</span>`).join(" ");
        const smEngines = (diag.suggested_matrix.engines || []).map(e => `<span class="tag tag-category">${escapeHtml(e.toUpperCase())}</span>`).join(" ");
        bodyHtml += `
          <div class="ai-card" style="border-left: 3px solid #a855f7;">
            <div class="ai-card-title" style="color: #c084fc;">📐 Recommended Metadata Matrix Constraint</div>
            <div style="font-size: 0.88rem; margin-bottom: 0.5rem;">
              <div><strong>Supported Modes:</strong> ${smModes || "All"}</div>
              <div style="margin-top: 0.25rem;"><strong>Supported Engines:</strong> ${smEngines || "All"}</div>
              ${diag.matrix_notes ? `<div style="margin-top: 0.4rem; color: var(--text-secondary);"><em>${escapeHtml(diag.matrix_notes)}</em></div>` : ""}
            </div>
            <button type="button" class="btn btn-warning btn-sm" id="applyMatrixConstraintBtn" style="margin-top: 0.5rem;">
              Apply Matrix Constraint to Metadata
            </button>
          </div>
        `;
      }

      if (diag.cross_matrix_notes) {
        bodyHtml += `
          <div class="ai-card" style="border-left: 3px solid var(--accent-cyan);">
            <div class="ai-card-title" style="color: #67e8f9;">⚖️ Cross-Matrix Impact (Docker/Podman & LXC/VM)</div>
            <p style="font-size: 0.88rem; color: var(--text-secondary);">${escapeHtml(diag.cross_matrix_notes)}</p>
          </div>
        `;
      }

      if (diag.action_plan) {
        bodyHtml += `
          <div class="ai-card" style="border-left: 3px solid var(--accent-blue);">
            <div class="ai-card-title" style="color: #93c5fd;">🎯 Developer Action Plan (IDE / PyCharm)</div>
            <p style="font-size: 0.88rem; white-space: pre-wrap;">${escapeHtml(diag.action_plan)}</p>
          </div>
        `;
      }

      if (diag.suggested_code_patch) {
        bodyHtml += `
          <div class="ai-card">
            <div class="ai-card-title">🛠️ Proposed Backend / Ansible Code Patch</div>
            <div class="ai-code-wrapper">
              <div class="ai-code-header">
                <span>${escapeHtml(diag.target_file || "Code Patch")}</span>
                <button type="button" class="btn-ai-copy" id="copyCodePatchBtn">Copy Patch</button>
              </div>
              <pre><code>${escapeHtml(diag.suggested_code_patch)}</code></pre>
            </div>
          </div>
        `;
      }

      if (diag.diff && targetType === "TEMPLATE_CONFIG") {
        bodyHtml += `
          <div class="ai-card">
            <div class="ai-card-title">📝 Proposed Template Diff</div>
            ${renderDiffHtml(diag.diff)}
          </div>
        `;
      }

      elements.aiModalBody.innerHTML = bodyHtml;

      const copyBtn = document.getElementById("copyCodePatchBtn");
      if (copyBtn && diag.suggested_code_patch) {
        copyBtn.addEventListener("click", () => {
          navigator.clipboard.writeText(diag.suggested_code_patch);
          copyBtn.textContent = "Copied!";
          setTimeout(() => {
            copyBtn.textContent = "Copy Patch";
          }, 1500);
        });
      }

      const applyRootModeBtn = document.getElementById("applyRootModeBtn");
      if (applyRootModeBtn && diag.suggested_root_mode) {
        applyRootModeBtn.addEventListener("click", async () => {
          applyRootModeBtn.disabled = true;
          applyRootModeBtn.textContent = "Applying...";
          try {
            const res = await fetch("/api/ai/apply-root-mode", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                component_id: record.component_id,
                requires_root: diag.suggested_root_mode.requires_root !== false,
                podman_mode: diag.suggested_root_mode.podman_mode || "rootful",
              }),
            });
            const resData = await res.json();
            if (res.ok && resData.success) {
              applyRootModeBtn.textContent = "✅ Applied to Metadata!";
              applyRootModeBtn.classList.remove("btn-warning");
              applyRootModeBtn.classList.add("btn-success");
            } else {
              applyRootModeBtn.textContent = `❌ Error: ${resData.error || "Failed"}`;
              applyRootModeBtn.disabled = false;
            }
          } catch (err) {
            applyRootModeBtn.textContent = `❌ Error: ${err.message}`;
            applyRootModeBtn.disabled = false;
          }
        });
      }

      const applyConstraintBtn = document.getElementById("applyMatrixConstraintBtn");
      if (applyConstraintBtn && diag.suggested_matrix) {
        applyConstraintBtn.addEventListener("click", async () => {
          applyConstraintBtn.disabled = true;
          applyConstraintBtn.textContent = "Applying...";
          try {
            const cRes = await fetch("/api/ai/apply-matrix-constraint", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                component_id: record.component_id,
                modes: diag.suggested_matrix.modes,
                engines: diag.suggested_matrix.engines,
                notes: diag.matrix_notes || "",
              }),
            });
            const cData = await cRes.json();
            if (cRes.ok && cData.success) {
              applyConstraintBtn.textContent = "✅ Constraint Applied to Metadata!";
              applyConstraintBtn.classList.remove("btn-warning");
              applyConstraintBtn.classList.add("btn-success");
            } else {
              applyConstraintBtn.textContent = `❌ Error: ${cData.error || "Failed"}`;
              applyConstraintBtn.disabled = false;
            }
          } catch (e) {
            applyConstraintBtn.textContent = `❌ Error: ${e.message}`;
            applyConstraintBtn.disabled = false;
          }
        });
      }

      if (diag.suggested_template && targetType === "TEMPLATE_CONFIG") {
        activePatchData = {
          component_id: record.component_id,
          template_content: diag.suggested_template,
        };
        elements.aiModalApplyBtn.style.display = "inline-flex";
        elements.aiModalApplyBtn.textContent = `Apply Patch to ${record.component_id}`;
      } else {
        elements.aiModalApplyBtn.style.display = "none";
      }
    } catch (err) {
      elements.aiModalBody.innerHTML = `
        <div class="ai-card" style="border-color: var(--accent-red);">
          <div class="ai-card-title" style="color: var(--accent-red);">❌ Network Error</div>
          <p>${escapeHtml(err.message)}</p>
        </div>
      `;
    }
  }

  /**
   * Opens AI batch systemic failure analysis modal with selected provider
   */
  async function openAiBatchDiagnosis() {
    activePatchData = null;
    elements.aiModalApplyBtn.style.display = "none";
    const aiLabel = state.activeAiName || "AI";
    elements.aiModalTitle.textContent = `✨ ${aiLabel} Systemic Batch Analysis`;
    elements.aiModalBody.innerHTML = `
      <div style="text-align: center; padding: 2rem;">
        <div style="font-size: 2rem; margin-bottom: 0.75rem;">⏳</div>
        <div><strong>Analyzing all test failures for systemic patterns with ${escapeHtml(aiLabel)}...</strong></div>
        <div style="color: var(--text-muted); font-size: 0.85rem; margin-top: 0.25rem;">
          Clustering errors by root causes, environment dependencies, and compose behaviors...
        </div>
      </div>
    `;
    elements.aiModal.classList.add("open");

    try {
      const failedRecords = state.results.filter((r) => r.status === "failed");
      const res = await fetch("/api/ai/diagnose", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          batch: true,
          records: failedRecords,
          provider: state.activeAiProvider || undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        elements.aiModalBody.innerHTML = `
          <div class="ai-card" style="border-color: var(--accent-red);">
            <div class="ai-card-title" style="color: var(--accent-red);">❌ Batch Analysis Failed</div>
            <p>${escapeHtml(data.error || "Unknown AI diagnosis error")}</p>
          </div>
        `;
        return;
      }

      const diag = data.diagnosis;
      let bodyHtml = `
        <div class="ai-card" style="background: linear-gradient(135deg, rgba(79, 70, 229, 0.1), rgba(124, 58, 237, 0.1)); border-color: #6366f1;">
          <div class="ai-card-title" style="color: #a5b4fc;">
            <span>🌐 Systemic Overview (${diag.total_analyzed || failedRecords.length} Failures Analyzed)</span>
          </div>
          <p style="font-size: 0.95rem; line-height: 1.5;">${escapeHtml(diag.systemic_summary || "")}</p>
        </div>
      `;

      if (Array.isArray(diag.clusters) && diag.clusters.length > 0) {
        bodyHtml += `<h4 style="margin: 1rem 0 0.5rem 0; color: var(--text-secondary);">Failure Clusters & Systemic Root Causes:</h4>`;
        diag.clusters.forEach((cluster) => {
          const affectedList = Array.isArray(cluster.affected_tests)
            ? cluster.affected_tests
                .map(
                  (t) =>
                    `<span class="tag tag-category" style="margin-right: 0.25rem; margin-bottom: 0.25rem; display: inline-block;">${escapeHtml(t)}</span>`
                )
                .join("")
            : "";

          let clusterBadge = "";
          if (cluster.target_type === "CORE_PLATFORM_CODE") {
            clusterBadge = `<span class="ai-badge-type ai-badge-core">🛠️ Core Code</span>`;
          } else if (cluster.target_type === "ENVIRONMENT_INFRA") {
            clusterBadge = `<span class="ai-badge-type ai-badge-infra">🌐 Infra</span>`;
          } else if (cluster.target_type === "TEMPLATE_CONFIG") {
            clusterBadge = `<span class="ai-badge-type ai-badge-template">📝 Template</span>`;
          }

          bodyHtml += `
            <div class="ai-card">
              <div class="ai-card-title">
                <span>📁 ${escapeHtml(cluster.cluster_name || "Pattern")}</span>
                <div style="display: flex; gap: 0.35rem; align-items: center;">
                  ${clusterBadge}
                  ${cluster.category ? `<span class="ai-cluster-tag">${escapeHtml(cluster.category)}</span>` : ""}
                </div>
              </div>
              <div style="margin-bottom: 0.5rem;">${affectedList}</div>
              <p style="color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 0.5rem;">
                <strong>Analysis:</strong> ${escapeHtml(cluster.root_cause_explanation || "")}
              </p>
              <div style="background: var(--bg-secondary); padding: 0.6rem 0.8rem; border-radius: var(--radius-sm); font-size: 0.85rem; border-left: 3px solid var(--accent-green);">
                <strong>Action:</strong> ${escapeHtml(cluster.recommended_action || "")}
              </div>
              ${cluster.cross_matrix_impact ? `<div style="margin-top: 0.4rem; font-size: 0.8rem; color: var(--text-muted);"><em>⚖️ Cross-Matrix Impact: ${escapeHtml(cluster.cross_matrix_impact)}</em></div>` : ""}
            </div>
          `;
        });
      }

      if (
        Array.isArray(diag.overall_recommendations) &&
        diag.overall_recommendations.length > 0
      ) {
        bodyHtml += `
          <div class="ai-card">
            <div class="ai-card-title">📋 Strategic Recommendations</div>
            <ul style="margin: 0; padding-left: 1.25rem; font-size: 0.88rem;">
              ${diag.overall_recommendations
                .map(
                  (r) => `<li style="margin-bottom: 0.25rem;">${escapeHtml(r)}</li>`
                )
                .join("")}
            </ul>
          </div>
        `;
      }

      elements.aiModalBody.innerHTML = bodyHtml;
    } catch (err) {
      elements.aiModalBody.innerHTML = `
        <div class="ai-card" style="border-color: var(--accent-red);">
          <div class="ai-card-title" style="color: var(--accent-red);">❌ Network Error</div>
          <p>${escapeHtml(err.message)}</p>
        </div>
      `;
    }
  }

  /**
   * Applies the AI suggested template patch to the active component
   */
  async function applyAiPatch() {
    if (!activePatchData) return;
    try {
      elements.aiModalApplyBtn.disabled = true;
      elements.aiModalApplyBtn.textContent = "Applying Patch...";
      const res = await fetch("/api/ai/apply-patch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(activePatchData),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        elements.aiModalApplyBtn.textContent = "✅ Patch Applied Successfully!";
        appendLog(
          `[${getTimestamp()}] [AI] Applied suggested template patch to component '${activePatchData.component_id}'.`
        );
        setTimeout(() => {
          elements.aiModal.classList.remove("open");
        }, 1200);
      } else {
        alert(`Failed to apply patch: ${data.error || "Unknown error"}`);
        elements.aiModalApplyBtn.disabled = false;
        elements.aiModalApplyBtn.textContent = `Apply Patch to ${activePatchData.component_id}`;
      }
    } catch (err) {
      alert(`Error applying patch: ${err.message}`);
      elements.aiModalApplyBtn.disabled = false;
    }
  }

  /**
   * Renders the complete results and history table with RAF batching
   */
  let renderTablePending = false;
  function renderResultsTable() {
    if (renderTablePending) return;
    renderTablePending = true;
    requestAnimationFrame(() => {
      renderTablePending = false;
      _doRenderResultsTable();
    });
  }

  function _doRenderResultsTable() {
    updateTableHeaderSortUI();

    const failedRecords = (state.results || []).filter(
      (r) => r.status === "failed"
    );
    if (elements.aiFailuresBadge) {
      elements.aiFailuresBadge.textContent = failedRecords.length;
      elements.aiFailuresBadge.style.display =
        failedRecords.length > 0 ? "inline-block" : "none";
    }
    if (elements.aiBatchBtn) {
      elements.aiBatchBtn.disabled = failedRecords.length === 0;
      elements.aiBatchBtn.style.opacity =
        failedRecords.length > 0 ? "1" : "0.5";
    }

    if (!state.results || state.results.length === 0) {
      elements.resultsTableBody.innerHTML = `
        <tr>
          <td colspan="11" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">
            No test history recorded yet.
          </td>
        </tr>
      `;
      return;
    }

    const sorted = sortResults(state.results, state.sortColumn, state.sortDirection);
    const maxRender = 50;
    const toRender = sorted.slice(0, maxRender);

    let rowsHtml = "";
    toRender.forEach((record) => {
      const recTime = record.timestamp || getTimestamp();
      const recMode = (
        record.mode || (state.mode === "both" ? "LXC" : state.mode)
      ).toUpperCase();
      const recEngine = (
        record.engine || (state.engine === "both" ? "DOCKER" : state.engine)
      ).toUpperCase();

      const isSuccess = record.status === "success";
      const isFail = record.status === "failed";
      const isSkipped = record.status === "skipped";
      const statusBadge = isSuccess
        ? '<span class="tag tag-tested">✅ PASS</span>'
        : isSkipped
        ? '<span class="tag tag-skipped">⏭️ SKIPPED</span>'
        : record.status === "running"
        ? '<span class="tag tag-ui">⏳ RUNNING</span>'
        : record.status === "pending"
        ? '<span class="tag tag-category">⚪ PENDING</span>'
        : '<span class="tag tag-untested">❌ FAIL</span>';

      let portLabel = "";
      if (record.port) {
        portLabel = `:${record.port} `;
      } else if (record.http_url) {
        try {
          const parsedUrl = new URL(record.http_url);
          portLabel = parsedUrl.port ? `:${parsedUrl.port} ` : "";
        } catch (e) {
          // Ignore URL parse error
        }
      }

      let httpBadge = '<span style="color: var(--text-muted);">—</span>';
      if (record.http_ok === true) {
        httpBadge = `<span class="tag tag-tested" style="font-size: 0.75rem; font-weight: 600;" title="HTTP probe successful">🌐 ${escapeHtml(portLabel)}[OK]</span>`;
      } else if (record.http_ok === false) {
        httpBadge = `<span class="tag tag-untested" style="font-size: 0.75rem; font-weight: 600;" title="HTTP probe failed">🌐 ${escapeHtml(portLabel)}[FAIL]</span>`;
      }

      let compLabel = `<strong>${escapeHtml(record.component_id || "—")}</strong>`;
      if (record.is_package) {
        const pkgName = record.package_name || record.component_id;
        compLabel = `<span class="tag tag-package" style="margin-right: 0.35rem;">📚 STACK</span><strong>${escapeHtml(pkgName)}</strong> <small style="color: var(--text-muted); font-family: var(--font-mono);">(${escapeHtml(record.component_id)})</small>`;
      }

      const containersVal = record.running_details
        ? escapeHtml(record.running_details)
        : (record.running ? "Running" : "Stopped");

      const reportFile = record.report_file || "";
      const compId = record.component_id || "";

      rowsHtml += `
        <tr>
          <td><small style="color: var(--text-muted); font-family: var(--font-mono);">${escapeHtml(recTime)}</small></td>
          <td>${compLabel}</td>
          <td><span class="tag ${recMode === "LXC" ? "tag-category" : "tag-ui"}">${escapeHtml(recMode)}</span></td>
          <td><code>${escapeHtml(recEngine)}</code></td>
          <td>${escapeHtml(String(record.vmid || "—"))}</td>
          <td><code>${escapeHtml(record.ip || "—")}</code></td>
          <td>${escapeHtml(record.deployment || "—")}</td>
          <td>${containersVal}</td>
          <td>${httpBadge}</td>
          <td>${statusBadge}</td>
          <td>
            <div style="display: inline-flex; gap: 0.35rem; align-items: center; justify-content: flex-start; flex-wrap: wrap;">
              <button type="button" class="btn-report-doc" data-file="${escapeHtml(reportFile)}" data-comp="${escapeHtml(compId)}" title="Open test report document"><span>📄</span> Report</button>
              <button type="button" class="btn-report-pdf" data-file="${escapeHtml(reportFile)}" data-comp="${escapeHtml(compId)}" title="Download test report as PDF"><span>📥</span> PDF</button>
              ${
                isFail && !record.is_package
                  ? `<button type="button" class="btn-ai-fix" data-comp="${escapeHtml(compId)}" data-mode="${escapeHtml(recMode)}" data-engine="${escapeHtml(recEngine)}" title="AI Diagnosis & Auto-Fix"><span>✨</span> AI Fix</button>`
                  : ""
              }
            </div>
          </td>
        </tr>
      `;
    });

    elements.resultsTableBody.innerHTML = rowsHtml;
  }

  /**
   * Loads cumulative test history from API
   */
  async function loadTestHistory() {
    try {
      const res = await fetch("/api/results");
      if (res.ok) {
        const historyData = await res.json();
        if (Array.isArray(historyData)) {
          const histRecords = historyData.map((rec, idx) => ({
            ...rec,
            is_history: true,
            _id: `hist-${idx}-${rec.component_id}-${(rec.mode || "").toUpperCase()}-${(rec.engine || "").toUpperCase()}-${rec.timestamp}`,
          }));

          // Preserve live records and merge with history safely
          const currentLive = state.results.filter((r) => !r.is_history);
          const historyKeySet = new Set(
            histRecords.map(
              (r) =>
                `${r.component_id}_${r.timestamp}_${(
                  r.mode || ""
                ).toUpperCase()}_${(r.engine || "").toUpperCase()}`
            )
          );

          const pendingLive = currentLive.filter(
            (r) =>
              !historyKeySet.has(
                `${r.component_id}_${r.timestamp}_${(
                  r.mode || ""
                ).toUpperCase()}_${(r.engine || "").toUpperCase()}`
              )
          );

          state.results = [...pendingLive, ...histRecords];
          renderResultsTable();
        }
      }
    } catch (err) {
      console.error("Failed to load test history:", err);
    }
  }

  /**
   * Clears all test results history
   */
  async function clearTestHistory() {
    try {
      const res = await fetch("/api/results/clear", { method: "POST" });
      const data = await res.json();
      if (res.ok && data.success) {
        state.results = [];
        renderResultsTable();
        appendLog(`[${getTimestamp()}] [GUI] Test history cleared successfully.`);
      }
    } catch (err) {
      console.error("Failed to clear test history:", err);
    } finally {
      elements.clearConfirmModal.classList.remove("open");
    }
  }

  /**
   * Parse log messages to update live test table
   */
  function handleStreamMessage(msgData) {
    if (!msgData) return;

    if (msgData.type === "log" && msgData.content) {
      appendLog(msgData.content);
    } else if (msgData.type === "record" && msgData.record) {
      const rec = msgData.record;
      const recMode = (rec.mode || "").toUpperCase();
      const recEngine = (rec.engine || "").toUpperCase();

      // Find matching live record matching component_id, mode, and engine
      const match =
        state.results.find(
          (r) =>
            !r.is_history &&
            r.component_id === rec.component_id &&
            (r.mode || "").toUpperCase() === recMode &&
            (r.engine || "").toUpperCase() === recEngine &&
            (r.status === "pending" || r.status === "running")
        ) ||
        state.results.find(
          (r) =>
            !r.is_history &&
            r.component_id === rec.component_id &&
            (r.mode || "").toUpperCase() === recMode &&
            (r.engine || "").toUpperCase() === recEngine
        );

      if (match) {
        const origTs = match.timestamp;
        Object.assign(match, rec);
        if (origTs) match.timestamp = origTs;
      } else {
        state.results.unshift({
          ...rec,
          timestamp: rec.timestamp || getTimestamp(),
          is_history: false,
          _id: `live-${rec.component_id}-${recMode}-${recEngine}-${Date.now()}`,
        });
      }
      renderResultsTable();
    } else if (msgData.type === "status") {
      if (msgData.status === "completed") {
        state.isRunning = false;
        elements.startRunBtn.disabled = false;
        elements.stopRunBtn.style.display = "none";
        const failCount = msgData.failed_count || 0;
        const passCount = msgData.passed_count || 0;
        if (failCount === 0) {
          setStatus("completed", `Run Finished: All Passed ✅ (${passCount} OK)`);
        } else {
          setStatus("failed", `Run Finished: ${failCount} Failed ❌ (${passCount} OK)`);
        }
        if (state.eventSource) {
          state.eventSource.close();
          state.eventSource = null;
        }
        // Refresh component cards and package cards to show updated tested status tags
        fetchComponents();
        fetchPackages();
        // Reload complete persisted history from server
        loadTestHistory();
      }
    }
  }

  /**
   * Connects to the Server-Sent Events (SSE) log stream
   */
  function connectStream() {
    if (state.eventSource) {
      state.eventSource.close();
    }

    state.eventSource = new EventSource("/api/stream");

    state.eventSource.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        handleStreamMessage(msg);
      } catch (err) {
        console.error("Error parsing stream event data:", err);
      }
    };

    state.eventSource.onerror = () => {
      // Reconnect automatically unless execution has finished
      if (!state.isRunning && state.eventSource) {
        state.eventSource.close();
        state.eventSource = null;
      }
    };
  }

  /**
   * Starts tests for selected components or packages
   */
  async function startTests() {
    if (state.targetType === "packages") {
      if (state.selectedPackageIds.size === 0) return;

      state.isRunning = true;
      elements.startRunBtn.disabled = true;
      elements.stopRunBtn.style.display = "inline-flex";
      setStatus("running", "Executing 1-Click Stack Test Run(s)...");

      const ts = getTimestamp();
      const numModes =
        state.mode === "both" || state.mode === "all" ? 2 : 1;
      const numEngines =
        state.engine === "both" || state.engine === "all" ? 2 : 1;
      const totalRuns = state.selectedPackageIds.size * numModes * numEngines;
      const modeLabel =
        state.mode === "both" || state.mode === "all"
          ? "LXC + VM (Matrix)"
          : state.mode.toUpperCase();
      const engineLabel =
        state.engine === "both" || state.engine === "all"
          ? "DOCKER + PODMAN (Matrix)"
          : state.engine.toUpperCase();

      appendLog(
        `\n======================================================================`
      );
      appendLog(
        `[${ts}] [GUI] EXECUTING 1-CLICK STACK TEST RUN(S): ${state.selectedPackageIds.size} STACKS (${totalRuns} TOTAL EXECUTIONS)`
      );
      appendLog(`[${ts}] [GUI] Target: ${modeLabel} | Engine: ${engineLabel}`);
      appendLog(
        `======================================================================\n`
      );

      const activeModes =
        state.mode === "both" || state.mode === "all"
          ? ["LXC", "VM"]
          : [state.mode.toUpperCase()];
      const activeEngines =
        state.engine === "both" || state.engine === "all"
          ? ["DOCKER", "PODMAN"]
          : [state.engine.toUpperCase()];

      // Pre-populate results table with pending rows for every matrix combination
      const newPendingRows = [];
      activeModes.forEach((m) => {
        activeEngines.forEach((e) => {
          state.selectedPackageIds.forEach((pkgId) => {
            const pkgObj = state.packages.find((p) => p.id === pkgId);
            newPendingRows.push({
              timestamp: ts,
              component_id: pkgId,
              package_name: pkgObj ? pkgObj.name : pkgId,
              mode: m,
              engine: e,
              status: "pending",
              deployment: "Pending",
              running: false,
              running_details: "Pending",
              vmid: "—",
              ip: "—",
              http_ok: null,
              is_package: true,
              is_history: false,
              _id: `live-pkg-${pkgId}-${m}-${e}-${Date.now()}-${Math.random()}`,
            });
          });
        });
      });
      state.results = [...newPendingRows, ...state.results];
      renderResultsTable();

      try {
        const payload = {
          target_type: "packages",
          packages: Array.from(state.selectedPackageIds),
          engine: state.engine,
          mode: state.mode,
          node: elements.nodeInput.value.trim() || "pve",
          template_id: elements.templateIdInput.value.trim() || "902",
        };

        const response = await fetch("/api/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        const result = await response.json();
        if (!response.ok || !result.success) {
          appendLog(
            `[ERROR] Failed to start package test run: ${result.error || "Unknown error"}`
          );
          setStatus("failed", "Failed to Start");
          state.isRunning = false;
          elements.startRunBtn.disabled = false;
          elements.stopRunBtn.style.display = "none";
          return;
        }

        connectStream();
      } catch (err) {
        appendLog(`[ERROR] Network error starting package tests: ${err.message}`);
        setStatus("failed", "Error");
        state.isRunning = false;
        elements.startRunBtn.disabled = false;
        elements.stopRunBtn.style.display = "none";
      }
    } else {
      if (state.selectedIds.size === 0) return;

      state.isRunning = true;
      elements.startRunBtn.disabled = true;
      elements.stopRunBtn.style.display = "inline-flex";
      setStatus("running", "Executing Test Run(s)...");

      const ts = getTimestamp();
      const numModes =
        state.mode === "both" || state.mode === "all" ? 2 : 1;
      const numEngines =
        state.engine === "both" || state.engine === "all" ? 2 : 1;
      const totalRuns = state.selectedIds.size * numModes * numEngines;
      const modeLabel =
        state.mode === "both" || state.mode === "all"
          ? "LXC + VM (Matrix)"
          : state.mode.toUpperCase();
      const engineLabel =
        state.engine === "both" || state.engine === "all"
          ? "DOCKER + PODMAN (Matrix)"
          : state.engine.toUpperCase();

      appendLog(
        `\n======================================================================`
      );
      appendLog(
        `[${ts}] [GUI] EXECUTING TEST RUN(S): ${state.selectedIds.size} SERVICES (${totalRuns} TOTAL EXECUTIONS)`
      );
      appendLog(`[${ts}] [GUI] Target: ${modeLabel} | Engine: ${engineLabel}`);
      appendLog(
        `======================================================================\n`
      );

      const activeModes =
        state.mode === "both" || state.mode === "all"
          ? ["LXC", "VM"]
          : [state.mode.toUpperCase()];
      const activeEngines =
        state.engine === "both" || state.engine === "all"
          ? ["DOCKER", "PODMAN"]
          : [state.engine.toUpperCase()];

      // Pre-populate results table with pending rows for every matrix combination
      const newPendingRows = [];
      activeModes.forEach((m) => {
        activeEngines.forEach((e) => {
          state.selectedIds.forEach((cid) => {
            newPendingRows.push({
              timestamp: ts,
              component_id: cid,
              mode: m,
              engine: e,
              status: "pending",
              deployment: "Pending",
              running: false,
              vmid: "—",
              ip: "—",
              http_ok: null,
              is_package: false,
              is_history: false,
              _id: `live-${cid}-${m}-${e}-${Date.now()}-${Math.random()}`,
            });
          });
        });
      });
      state.results = [...newPendingRows, ...state.results];
      renderResultsTable();

      try {
        const payload = {
          target_type: "components",
          components: Array.from(state.selectedIds),
          engine: state.engine,
          mode: state.mode,
          node: elements.nodeInput.value.trim() || "pve",
          template_id: elements.templateIdInput.value.trim() || "902",
        };

        const response = await fetch("/api/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        const result = await response.json();
        if (!response.ok || !result.success) {
          appendLog(
            `[ERROR] Failed to start test run: ${result.error || "Unknown error"}`
          );
          setStatus("failed", "Failed to Start");
          state.isRunning = false;
          elements.startRunBtn.disabled = false;
          elements.stopRunBtn.style.display = "none";
          return;
        }

        connectStream();
      } catch (err) {
        appendLog(`[ERROR] Network error starting tests: ${err.message}`);
        setStatus("failed", "Error");
        state.isRunning = false;
        elements.startRunBtn.disabled = false;
        elements.stopRunBtn.style.display = "none";
      }
    }
  }

  /**
   * Stops running tests and aborts the entire session
   */
  async function stopTests() {
    if (!state.isRunning) return;
    try {
      appendLog(`[${getTimestamp()}] [GUI] Aborting entire test session...`);
      elements.stopRunBtn.disabled = true;
      elements.stopRunBtn.innerHTML = "<span>⏹️</span> Aborting Session...";
      await fetch("/api/stop", { method: "POST" });
      state.isRunning = false;
      elements.startRunBtn.disabled = false;
      elements.stopRunBtn.style.display = "none";
      setStatus("failed", "Test session aborted by user ⏹️");
      state.results.forEach((r) => {
        if (r.status === "running" || r.status === "pending") {
          r.status = "failed";
          r.deployment = "Aborted";
          r.running = false;
          if (!r.error_message) {
            r.error_message = "Test session was manually aborted by user.";
          }
        }
      });
      renderResultsTable();
    } catch (err) {
      console.error("Failed to stop tests:", err);
    }
  }

  /**
   * Builds and maintains dedicated Proxmox test templates (911-914)
   */
  async function maintainTemplates() {
    if (state.isRunning) return;
    const confirmMaintenance = confirm(
      "🛠️ Build / Refresh dedicated Proxmox templates (911-914)?\n\n" +
      "This will build/update Docker & Podman templates on VM and LXC and pre-cache common container base images."
    );
    if (!confirmMaintenance) return;

    state.isRunning = true;
    elements.startRunBtn.disabled = true;
    if (elements.maintainTemplatesBtn) elements.maintainTemplatesBtn.disabled = true;
    elements.stopRunBtn.style.display = "inline-flex";
    setStatus("running", "Maintaining Proxmox Test Templates...");

    const ts = getTimestamp();
    appendLog(`\n======================================================================`);
    appendLog(`[${ts}] [GUI] BUILDING / REFRESHING DEDICATED PROXMOX TEST TEMPLATES (911-914)`);
    appendLog(`======================================================================\n`);

    try {
      const payload = {
        target_type: "templates",
        components: ["all"],
        node: elements.nodeInput.value.trim() || "pve",
      };

      const response = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      if (!data.success) {
        throw new Error(data.error || "Failed to start template maintenance");
      }

      connectStream();
    } catch (err) {
      appendLog(`[ERROR] Failed to start template maintenance: ${err.message}`);
      setStatus("error", "Failed to start template maintenance");
      state.isRunning = false;
      elements.startRunBtn.disabled = false;
      if (elements.maintainTemplatesBtn) elements.maintainTemplatesBtn.disabled = false;
      elements.stopRunBtn.style.display = "none";
    }
  }

  /**
   * Fallback Markdown renderer if marked.js is unavailable
   */
  function renderMarkdownFallback(md) {
    if (!md) return "";
    let html = escapeHtml(md);
    // Images: ![alt](url)
    html = html.replace(
      /!\[(.*?)\]\((.*?)\)/g,
      '<img src="$2" alt="$1" title="$1">'
    );
    // Links: [text](url)
    html = html.replace(
      /\[(.*?)\]\((.*?)\)/g,
      '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
    );
    // Headers: ###, ##, #
    html = html.replace(/^### (.*$)/gim, "<h3>$1</h3>");
    html = html.replace(/^## (.*$)/gim, "<h2>$1</h2>");
    html = html.replace(/^# (.*$)/gim, "<h1>$1</h1>");
    // Bold: **text**
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    // Inline code: `code`
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    // Line breaks
    html = html.replace(/\n/g, "<br>");
    return html;
  }

  /**
   * Fetches specific or latest markdown test report and renders Markdown & screenshots
   */
  async function loadReport(targetFile = null, compId = null) {
    try {
      if (elements.reportContent) {
        elements.reportContent.innerHTML = "<p><em>Loading report...</em></p>";
        elements.reportContent.style.display = "block";
      }
      if (elements.reportRawContent) {
        elements.reportRawContent.textContent = "Loading report...";
        elements.reportRawContent.style.display = "none";
      }
      if (elements.btnReportViewFormatted) {
        elements.btnReportViewFormatted.classList.add("active");
      }
      if (elements.btnReportViewRaw) {
        elements.btnReportViewRaw.classList.remove("active");
      }
      elements.reportModal.classList.add("open");

      let query = "";
      if (targetFile) {
        query = `file=${encodeURIComponent(targetFile)}`;
      } else if (compId) {
        query = `component=${encodeURIComponent(compId)}`;
      } else {
        const reportType = state.targetType === "packages" ? "package" : "latest";
        query = `type=${reportType}`;
      }

      const res = await fetch(`/api/report?${query}`);
      const data = await res.json();
      const modalTitle = document.getElementById("report-modal-title");
      if (modalTitle) {
        modalTitle.textContent = data.filename
          ? `Test Report (${data.filename})`
          : "Test Report";
      }
      if (elements.reportModalMeta) {
        elements.reportModalMeta.textContent = data.filename || "";
      }
      state.currentReportFile = data.filename || targetFile || "";
      state.currentCompId = compId || "";

      const rawText = data.report || "";
      if (elements.reportRawContent) {
        elements.reportRawContent.textContent = rawText || "No report generated yet.";
      }

      if (elements.reportContent) {
        if (!rawText) {
          elements.reportContent.innerHTML =
            "<p><em>No report generated yet.</em></p>";
        } else if (
          typeof window.marked !== "undefined" &&
          typeof window.marked.parse === "function"
        ) {
          elements.reportContent.innerHTML = window.marked.parse(rawText);
        } else {
          elements.reportContent.innerHTML = renderMarkdownFallback(rawText);
        }

        // Add interactive zoom behavior to embedded screenshot images
        elements.reportContent.querySelectorAll("img").forEach((img) => {
          img.addEventListener("click", () => {
            img.classList.toggle("zoomed");
          });
        });
      }
    } catch (err) {
      if (elements.reportContent) {
        elements.reportContent.innerHTML = `<p style="color: var(--status-error);">Error loading report: ${escapeHtml(err.message)}</p>`;
      }
      if (elements.reportRawContent) {
        elements.reportRawContent.textContent = `Error loading report: ${err.message}`;
      }
    }
  }

  /**
   * Generates and downloads an A4 PDF for a given report file or component
   */
  async function exportReportToPdf(targetFile, compId, triggerBtn) {
    const origText = triggerBtn ? triggerBtn.innerHTML : "";
    if (triggerBtn) {
      triggerBtn.disabled = true;
      triggerBtn.innerHTML = `<span>⏳</span> Exporteren...`;
    }

    try {
      let query = "";
      if (targetFile) {
        query = `file=${encodeURIComponent(targetFile)}`;
      } else if (compId) {
        query = `component=${encodeURIComponent(compId)}`;
      } else {
        const reportType = state.targetType === "packages" ? "package" : "latest";
        query = `type=${reportType}`;
      }

      const res = await fetch(`/api/report/pdf?${query}`);
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || `HTTP ${res.status}`);
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.style.display = "none";
      a.href = url;

      let downloadName = "test_report.pdf";
      const disposition = res.headers.get("Content-Disposition");
      if (disposition && disposition.includes("filename=")) {
        const match = disposition.match(/filename="?([^";]+)"?/);
        if (match && match[1]) {
          downloadName = match[1];
        }
      } else if (targetFile) {
        downloadName = targetFile.replace(/\.md$/, ".pdf");
      }

      a.download = downloadName;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error("PDF Export error:", err);
      alert(`Kon PDF rapport niet exporteren: ${err.message}`);
    } finally {
      if (triggerBtn) {
        triggerBtn.disabled = false;
        triggerBtn.innerHTML = origText;
      }
    }
  }

  /**
   * Initializes click handlers on sortable table headers
   */
  function initTableSorting() {
    const tableThead = document.querySelector(".results-table thead");
    if (!tableThead) return;

    tableThead.innerHTML = `
      <tr>
        <th data-sort="timestamp" class="sortable">Date / Time <span class="sort-icon"></span></th>
        <th data-sort="component_id" class="sortable">Target / Component <span class="sort-icon"></span></th>
        <th data-sort="mode" class="sortable">Target <span class="sort-icon"></span></th>
        <th data-sort="engine" class="sortable">Engine <span class="sort-icon"></span></th>
        <th data-sort="vmid" class="sortable">VM ID <span class="sort-icon"></span></th>
        <th data-sort="ip" class="sortable">IP Address <span class="sort-icon"></span></th>
        <th data-sort="deployment" class="sortable">Deployment <span class="sort-icon"></span></th>
        <th data-sort="running" class="sortable">Containers <span class="sort-icon"></span></th>
        <th data-sort="http_ok" class="sortable">HTTP UI <span class="sort-icon"></span></th>
        <th data-sort="status" class="sortable">Status <span class="sort-icon"></span></th>
        <th>Actions</th>
      </tr>
    `;

    tableThead.querySelectorAll("th[data-sort]").forEach((th) => {
      th.addEventListener("click", () => {
        const col = th.dataset.sort;
        if (state.sortColumn === col) {
          state.sortDirection = state.sortDirection === "asc" ? "desc" : "asc";
        } else {
          state.sortColumn = col;
          state.sortDirection = col === "timestamp" ? "desc" : "asc";
        }
        renderResultsTable();
      });
    });

    updateTableHeaderSortUI();
  }

  async function fetchComponents() {
    try {
      const compRes = await fetch("/api/components");
      if (compRes.ok) {
        state.components = await compRes.json();
        renderComponents();
        updateSelectionUI();
      }
    } catch (err) {
      console.error("Failed to fetch components:", err);
    }
  }

  async function fetchPackages() {
    try {
      const pkgRes = await fetch("/api/packages");
      if (pkgRes.ok) {
        state.packages = await pkgRes.json();
        renderPackages();
        updateSelectionUI();
      }
    } catch (err) {
      console.error("Failed to fetch packages:", err);
    }
  }

  /**
   * Initializes AI provider selector dropdown from API
   */
  async function initAiProviderSelector() {
    if (!elements.aiProviderSelect) return;

    try {
      const res = await fetch("/api/ai/providers");
      if (!res.ok) return;
      const data = await res.json();
      if (!data.success || !Array.isArray(data.providers)) return;

      const providers = data.providers;
      let activeProvider = data.active_provider || "gemini";

      // Check localStorage override
      const savedProvider = localStorage.getItem("njorddeploy_proxmox_ai_provider");
      if (savedProvider && providers.some((p) => p.id === savedProvider)) {
        activeProvider = savedProvider;
      }

      elements.aiProviderSelect.innerHTML = "";
      providers.forEach((p) => {
        const option = document.createElement("option");
        option.value = p.id;
        const icon = p.configured ? "🟢" : "⚪";
        const modelStr = p.model ? ` (${p.model})` : "";
        option.textContent = `${icon} ${p.name}${modelStr}`;
        if (p.id === activeProvider) {
          option.selected = true;
          state.activeAiProvider = p.id;
          state.activeAiName = p.name;
          state.activeAiModel = p.model;
        }
        elements.aiProviderSelect.appendChild(option);
      });

      // Update dropdown title/tooltip
      const activeObj = providers.find((p) => p.id === state.activeAiProvider);
      if (activeObj) {
        elements.aiProviderSelect.title = `Active AI: ${activeObj.name} (${activeObj.model || "default"})`;
      }

      elements.aiProviderSelect.addEventListener("change", async (e) => {
        const chosenId = e.target.value;
        const chosenObj = providers.find((p) => p.id === chosenId);
        state.activeAiProvider = chosenId;
        if (chosenObj) {
          state.activeAiName = chosenObj.name;
          state.activeAiModel = chosenObj.model;
          elements.aiProviderSelect.title = `Active AI: ${chosenObj.name} (${chosenObj.model || "default"})`;
        }
        localStorage.setItem("njorddeploy_proxmox_ai_provider", chosenId);

        try {
          await fetch("/api/ai/select-provider", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ provider: chosenId }),
          });
        } catch (err) {
          console.warn("Failed to persist AI provider selection to backend:", err);
        }
      });
    } catch (err) {
      console.error("Failed to load AI providers:", err);
    }
  }

  /**
   * Initializes application data from API
   */
  async function init() {
    initTableSorting();
    setupEventListeners();

    try {
      // 1. Fetch initial configuration & AI providers in parallel
      await Promise.all([
        (async () => {
          const configRes = await fetch("/api/config");
          if (configRes.ok) {
            const config = await configRes.json();
            if (config.node) elements.nodeInput.value = config.node;
            if (config.template_id) elements.templateIdInput.value = config.template_id;
            if (config.engine) {
              state.engine = config.engine.toLowerCase();
              if (state.engine === "podman") {
                elements.enginePodmanBtn.classList.add("active", "engine-podman");
                elements.engineDockerBtn.classList.remove("active");
              }
            }
            if (config.mode) {
              state.mode = config.mode.toLowerCase();
              if (state.mode === "vm") {
                elements.modeVmBtn.classList.add("active");
                elements.modeLxcBtn.classList.remove("active");
              } else if (state.mode === "both") {
                if (elements.modeBothBtn) {
                  elements.modeBothBtn.classList.add("active", "mode-both");
                }
                elements.modeLxcBtn.classList.remove("active");
              }
            }
            updateNetworkUI(config);
            updateTemplatesUI();
          }
        })(),
        initAiProviderSelector(),
      ]);

      // 2. Fetch components and packages in parallel
      await Promise.all([fetchComponents(), fetchPackages()]);

      // 3. Fetch cumulative test history in requestAnimationFrame to preserve smooth UI
      requestAnimationFrame(() => {
        loadTestHistory();
      });

      // 4. Check if a test run is actively in progress and attach live stream
      try {
        const statusRes = await fetch("/api/status");
        if (statusRes.ok) {
          const statusData = await statusRes.json();
          if (statusData.is_running) {
            state.isRunning = true;
            elements.startRunBtn.disabled = true;
            elements.stopRunBtn.style.display = "inline-flex";
            const comp = statusData.current_component || "Active Service";
            setStatus("running", `Active Run in Progress: ${comp} ⏳`);
            connectStream();
          }
        }
      } catch (statusErr) {
        console.warn("Could not check initial status:", statusErr);
      }
    } catch (err) {
      console.error("Initialization error:", err);
    }
  }

  /**
   * Sets up all interactive DOM event listeners immediately upon DOM ready
   */
  function setupEventListeners() {
    // Centralized Event Delegation for Component Selection
    elements.componentsGrid.addEventListener("click", (e) => {
      const card = e.target.closest(".component-card");
      if (!card) return;
      const compId = card.dataset.componentId || card.dataset.id;
      if (!compId) return;
      const checkbox = card.querySelector(".component-checkbox");
      if (e.target !== checkbox && checkbox) {
        checkbox.checked = !checkbox.checked;
      }
      if (checkbox && checkbox.checked) {
        state.selectedIds.add(compId);
        card.classList.add("selected");
      } else {
        state.selectedIds.delete(compId);
        card.classList.remove("selected");
      }
      updateSelectionUI();
    });

    // Centralized Event Delegation for Package Selection
    if (elements.packagesGrid) {
      elements.packagesGrid.addEventListener("click", (e) => {
        const card = e.target.closest(".package-card");
        if (!card) return;
        const pkgId = card.dataset.packageId;
        if (!pkgId) return;
        const checkbox = card.querySelector(".package-checkbox");
        if (e.target !== checkbox && checkbox) {
          checkbox.checked = !checkbox.checked;
        }
        if (checkbox && checkbox.checked) {
          state.selectedPackageIds.add(pkgId);
          card.classList.add("selected");
        } else {
          state.selectedPackageIds.delete(pkgId);
          card.classList.remove("selected");
        }
        updateSelectionUI();
      });
    }

    // Target View switch buttons (Services vs Packages)
    if (elements.tabServicesBtn) {
      elements.tabServicesBtn.addEventListener("click", () => switchTargetType("components"));
    }
    if (elements.tabPackagesBtn) {
      elements.tabPackagesBtn.addEventListener("click", () => switchTargetType("packages"));
    }

    // Search bar with live wildcard matching (Services, debounced)
    let searchDebounceTimer = null;
    elements.searchInput.addEventListener("input", (e) => {
      state.searchQuery = e.target.value;
      elements.searchClearBtn.style.display = state.searchQuery ? "block" : "none";
      clearTimeout(searchDebounceTimer);
      searchDebounceTimer = setTimeout(() => {
        renderComponents();
      }, 120);
    });

    elements.searchClearBtn.addEventListener("click", () => {
      clearTimeout(searchDebounceTimer);
      elements.searchInput.value = "";
      state.searchQuery = "";
      elements.searchClearBtn.style.display = "none";
      renderComponents();
      elements.searchInput.focus();
    });

    // Package search bar with live wildcard matching (debounced)
    let pkgSearchDebounceTimer = null;
    if (elements.packageSearchInput) {
      elements.packageSearchInput.addEventListener("input", (e) => {
        state.packageSearchQuery = e.target.value;
        if (elements.packageSearchClearBtn) {
          elements.packageSearchClearBtn.style.display = state.packageSearchQuery ? "block" : "none";
        }
        clearTimeout(pkgSearchDebounceTimer);
        pkgSearchDebounceTimer = setTimeout(() => {
          renderPackages();
        }, 120);
      });
    }

    if (elements.packageSearchClearBtn) {
      elements.packageSearchClearBtn.addEventListener("click", () => {
        clearTimeout(pkgSearchDebounceTimer);
        elements.packageSearchInput.value = "";
        state.packageSearchQuery = "";
        elements.packageSearchClearBtn.style.display = "none";
        renderPackages();
        elements.packageSearchInput.focus();
      });
    }

    // Category / Status Filter pills (Services)
    elements.filterPills.forEach((pill) => {
      pill.addEventListener("click", () => {
        elements.filterPills.forEach((p) => p.classList.remove("active"));
        pill.classList.add("active");
        state.activeFilter = pill.dataset.filter;
        renderComponents();
      });
    });

    // Filter pills (Packages)
    elements.packageFilterPills.forEach((pill) => {
      pill.addEventListener("click", () => {
        elements.packageFilterPills.forEach((p) => p.classList.remove("active"));
        pill.classList.add("active");
        state.activePackageFilter = pill.dataset.pkgFilter || "all";
        renderPackages();
      });
    });

    // Mode toggles
    elements.modeLxcBtn.addEventListener("click", () => {
      state.mode = "lxc";
      elements.modeLxcBtn.classList.add("active");
      elements.modeVmBtn.classList.remove("active");
      if (elements.modeBothBtn) elements.modeBothBtn.classList.remove("active", "mode-both");
      updateTemplatesUI();
    });

    elements.modeVmBtn.addEventListener("click", () => {
      state.mode = "vm";
      elements.modeVmBtn.classList.add("active");
      elements.modeLxcBtn.classList.remove("active");
      if (elements.modeBothBtn) elements.modeBothBtn.classList.remove("active", "mode-both");
      updateTemplatesUI();
    });

    if (elements.modeBothBtn) {
      elements.modeBothBtn.addEventListener("click", () => {
        state.mode = "both";
        elements.modeBothBtn.classList.add("active", "mode-both");
        elements.modeLxcBtn.classList.remove("active");
        elements.modeVmBtn.classList.remove("active");
        updateTemplatesUI();
      });
    }

    // Engine toggles
    elements.engineDockerBtn.addEventListener("click", () => {
      state.engine = "docker";
      elements.engineDockerBtn.classList.add("active");
      elements.enginePodmanBtn.classList.remove("active", "engine-podman");
      if (elements.engineBothBtn) elements.engineBothBtn.classList.remove("active", "engine-both");
      updateTemplatesUI();
    });

    elements.enginePodmanBtn.addEventListener("click", () => {
      state.engine = "podman";
      elements.enginePodmanBtn.classList.add("active", "engine-podman");
      elements.engineDockerBtn.classList.remove("active");
      if (elements.engineBothBtn) elements.engineBothBtn.classList.remove("active", "engine-both");
      updateTemplatesUI();
    });

    if (elements.engineBothBtn) {
      elements.engineBothBtn.addEventListener("click", () => {
        state.engine = "both";
        elements.engineBothBtn.classList.add("active", "engine-both");
        elements.engineDockerBtn.classList.remove("active");
        elements.enginePodmanBtn.classList.remove("active", "engine-podman");
        updateTemplatesUI();
      });
    }

    // Network profile toggle (Isolated Subnet vs LAN Bridge)
    if (elements.toggleNetworkBtn) {
      elements.toggleNetworkBtn.addEventListener("click", async () => {
        if (state.isRunning) {
          alert("Cannot switch network configuration while a test run is in progress.");
          return;
        }
        const currentBridge = elements.configBridgeLabel
          ? elements.configBridgeLabel.textContent.trim()
          : "";
        const targetProfile = currentBridge === "vmbr1" ? "lan" : "isolated";
        try {
          elements.toggleNetworkBtn.disabled = true;
          elements.toggleNetworkBtn.textContent = "⏳ Bezig...";
          const res = await fetch("/api/config/network", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ profile: targetProfile }),
          });
          if (res.ok) {
            const data = await res.json();
            updateNetworkUI(data);
            const ts = getTimestamp();
            appendLog(
              `[${ts}] [GUI] Test netwerk gewisseld naar ${data.profile.toUpperCase()} ` +
              `profiel (${data.bridge} | Gateway ${data.gateway} | Doel ${data.test_ip})`
            );
          } else {
            console.error("Failed to switch network configuration");
          }
        } catch (err) {
          console.error("Error toggling network profile:", err);
        } finally {
          elements.toggleNetworkBtn.disabled = false;
          elements.toggleNetworkBtn.textContent = "Wissel Netwerk";
        }
      });
    }

    // Batch selection buttons (Services)
    elements.selectAllFilteredBtn.addEventListener("click", () => {
      const filtered = getFilteredComponents();
      filtered.forEach((c) => state.selectedIds.add(c.id));
      renderComponents();
      updateSelectionUI();
    });

    if (elements.selectAllTestableBtn) {
      elements.selectAllTestableBtn.addEventListener("click", () => {
        const filtered = getFilteredComponents();
        filtered.forEach((c) => {
          if (!c.is_untestable) {
            state.selectedIds.add(c.id);
          }
        });
        renderComponents();
        updateSelectionUI();
      });
    }

    if (elements.deselectUntestableBtn) {
      elements.deselectUntestableBtn.addEventListener("click", () => {
        state.components.forEach((c) => {
          if (c.is_untestable) {
            state.selectedIds.delete(c.id);
          }
        });
        renderComponents();
        updateSelectionUI();
      });
    }

    elements.deselectAllFilteredBtn.addEventListener("click", () => {
      const filtered = getFilteredComponents();
      filtered.forEach((c) => state.selectedIds.delete(c.id));
      renderComponents();
      updateSelectionUI();
    });

    elements.clearSelectionBtn.addEventListener("click", () => {
      state.selectedIds.clear();
      renderComponents();
      updateSelectionUI();
    });

    // Batch selection buttons (Packages)
    if (elements.selectAllPackagesBtn) {
      elements.selectAllPackagesBtn.addEventListener("click", () => {
        const filtered = getFilteredPackages();
        filtered.forEach((p) => state.selectedPackageIds.add(p.id));
        renderPackages();
        updateSelectionUI();
      });
    }

    if (elements.clearPackagesSelectionBtn) {
      elements.clearPackagesSelectionBtn.addEventListener("click", () => {
        state.selectedPackageIds.clear();
        renderPackages();
        updateSelectionUI();
      });
    }

    // Runner triggers
    elements.startRunBtn.addEventListener("click", startTests);
    elements.stopRunBtn.addEventListener("click", stopTests);
    if (elements.maintainTemplatesBtn) {
      elements.maintainTemplatesBtn.addEventListener("click", maintainTemplates);
    }

    // Terminal controls
    elements.clearTerminalBtn.addEventListener("click", () => {
      elements.terminalBody.textContent = "";
    });

    elements.copyTerminalBtn.addEventListener("click", () => {
      navigator.clipboard.writeText(elements.terminalBody.textContent);
      elements.copyTerminalBtn.textContent = "Copied!";
      setTimeout(() => {
        elements.copyTerminalBtn.textContent = "Copy Logs";
      }, 1500);
    });

    // Table Action Event Delegation (Report and AI Fix)
    if (elements.resultsTableBody) {
      elements.resultsTableBody.addEventListener("click", (e) => {
        const reportBtn = e.target.closest(".btn-report-doc");
        if (reportBtn) {
          const file = reportBtn.getAttribute("data-file") || "";
          const comp = reportBtn.getAttribute("data-comp") || "";
          loadReport(file, comp);
          return;
        }

        const pdfBtn = e.target.closest(".btn-report-pdf");
        if (pdfBtn) {
          const file = pdfBtn.getAttribute("data-file") || "";
          const comp = pdfBtn.getAttribute("data-comp") || "";
          exportReportToPdf(file, comp, pdfBtn);
          return;
        }

        const aiBtn = e.target.closest(".btn-ai-fix");
        if (aiBtn) {
          const compId = aiBtn.getAttribute("data-comp") || "";
          const mode = aiBtn.getAttribute("data-mode") || "";
          const engine = aiBtn.getAttribute("data-engine") || "";
          const record =
            state.results.find(
              (r) =>
                r.component_id === compId &&
                (r.mode || "").toUpperCase() === mode.toUpperCase() &&
                (r.engine || "").toUpperCase() === engine.toUpperCase()
            ) || state.results.find((r) => r.component_id === compId);
          if (record) {
            openAiSingleDiagnosis(record);
          }
        }
      });
    }

    // Clear History Modal controls
    elements.clearHistoryBtn.addEventListener("click", () => {
      elements.clearConfirmModal.classList.add("open");
    });

    elements.closeClearModalBtn.addEventListener("click", () => {
      elements.clearConfirmModal.classList.remove("open");
    });

    elements.cancelClearBtn.addEventListener("click", () => {
      elements.clearConfirmModal.classList.remove("open");
    });

    elements.confirmClearBtn.addEventListener("click", clearTestHistory);

    elements.clearConfirmModal.addEventListener("click", (e) => {
      if (e.target === elements.clearConfirmModal) {
        elements.clearConfirmModal.classList.remove("open");
      }
    });

    // Report modal & PDF Export
    elements.viewReportBtn.addEventListener("click", () => loadReport());
    if (elements.exportLatestPdfBtn) {
      elements.exportLatestPdfBtn.addEventListener("click", () => {
        exportReportToPdf(null, null, elements.exportLatestPdfBtn);
      });
    }
    if (elements.btnReportExportPdf) {
      elements.btnReportExportPdf.addEventListener("click", () => {
        exportReportToPdf(
          state.currentReportFile,
          state.currentCompId,
          elements.btnReportExportPdf
        );
      });
    }
    if (elements.reportModalExportPdfBtn) {
      elements.reportModalExportPdfBtn.addEventListener("click", () => {
        exportReportToPdf(
          state.currentReportFile,
          state.currentCompId,
          elements.reportModalExportPdfBtn
        );
      });
    }
    elements.closeModalBtn.addEventListener("click", () => {
      elements.reportModal.classList.remove("open");
    });
    if (elements.reportModalCloseBtn) {
      elements.reportModalCloseBtn.addEventListener("click", () => {
        elements.reportModal.classList.remove("open");
      });
    }

    elements.reportModal.addEventListener("click", (e) => {
      if (e.target === elements.reportModal) {
        elements.reportModal.classList.remove("open");
      }
    });

    if (elements.btnReportViewFormatted) {
      elements.btnReportViewFormatted.addEventListener("click", () => {
        if (elements.reportContent) elements.reportContent.style.display = "block";
        if (elements.reportRawContent) elements.reportRawContent.style.display = "none";
        elements.btnReportViewFormatted.classList.add("active");
        if (elements.btnReportViewRaw) elements.btnReportViewRaw.classList.remove("active");
      });
    }
    if (elements.btnReportViewRaw) {
      elements.btnReportViewRaw.addEventListener("click", () => {
        if (elements.reportContent) elements.reportContent.style.display = "none";
        if (elements.reportRawContent) elements.reportRawContent.style.display = "block";
        if (elements.btnReportViewFormatted) elements.btnReportViewFormatted.classList.remove("active");
        elements.btnReportViewRaw.classList.add("active");
      });
    }

    // AI Diagnostics Modal controls
    if (elements.aiBatchBtn) {
      elements.aiBatchBtn.addEventListener("click", openAiBatchDiagnosis);
    }
    if (elements.closeAiModalBtn) {
      elements.closeAiModalBtn.addEventListener("click", () => {
        elements.aiModal.classList.remove("open");
      });
    }
    if (elements.aiModalCloseBtn) {
      elements.aiModalCloseBtn.addEventListener("click", () => {
        elements.aiModal.classList.remove("open");
      });
    }
    if (elements.aiModalApplyBtn) {
      elements.aiModalApplyBtn.addEventListener("click", applyAiPatch);
    }
    if (elements.aiModal) {
      elements.aiModal.addEventListener("click", (e) => {
        if (e.target === elements.aiModal) {
          elements.aiModal.classList.remove("open");
        }
      });
    }
  }

  // Run on DOM ready
  document.addEventListener("DOMContentLoaded", init);
})();
