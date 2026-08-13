/**
 * scripts/static/js/proxmox_gui.js
 * Interactive frontend logic for NjordDeploy Proxmox Component Test GUI.
 */

(() => {
  "use strict";

  // Application State
  const state = {
    components: [],
    selectedIds: new Set(),
    activeFilter: "all", // 'all' | 'untested' | 'tested' | 'ui'
    searchQuery: "",
    mode: "lxc", // 'lxc' | 'vm' | 'both'
    engine: "docker", // 'docker' | 'podman' | 'both'
    isRunning: false,
    eventSource: null,
    results: [],
  };

  // DOM Elements
  const elements = {
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

    // Filter & Search elements
    searchInput: document.getElementById("search-input"),
    searchClearBtn: document.getElementById("search-clear-btn"),
    filterPills: document.querySelectorAll(".filter-pill"),
    componentsGrid: document.getElementById("components-grid"),

    // Selection toolbar
    selectionCountBadge: document.getElementById("selection-count-badge"),
    selectAllFilteredBtn: document.getElementById("select-all-filtered-btn"),
    deselectAllFilteredBtn: document.getElementById("deselect-all-filtered-btn"),
    clearSelectionBtn: document.getElementById("clear-selection-btn"),

    // Runner controls
    startRunBtn: document.getElementById("start-run-btn"),
    stopRunBtn: document.getElementById("stop-run-btn"),
    startRunText: document.getElementById("start-run-text"),
    appStatusBadge: document.getElementById("app-status-badge"),

    // Terminal elements
    terminalBody: document.getElementById("terminal-body"),
    clearTerminalBtn: document.getElementById("clear-terminal-btn"),
    copyTerminalBtn: document.getElementById("copy-terminal-btn"),
    viewReportBtn: document.getElementById("view-report-btn"),

    // Results & History table
    resultsTableBody: document.getElementById("results-table-body"),
    clearHistoryBtn: document.getElementById("clear-history-btn"),

    // Clear History Modal
    clearConfirmModal: document.getElementById("clear-confirm-modal"),
    closeClearModalBtn: document.getElementById("close-clear-modal-btn"),
    cancelClearBtn: document.getElementById("cancel-clear-btn"),
    confirmClearBtn: document.getElementById("confirm-clear-btn"),

    // Report modal
    reportModal: document.getElementById("report-modal"),
    closeModalBtn: document.getElementById("close-modal-btn"),
    reportContent: document.getElementById("report-content"),
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
   * Updates selection badge and start button state
   */
  function updateSelectionUI() {
    const count = state.selectedIds.size;
    const total = state.components.length;
    elements.selectionCountBadge.textContent = `${count} of ${total} selected`;

    if (count > 0) {
      elements.startRunText.textContent = `Start Test Run (${count} ${
        count === 1 ? "service" : "services"
      })`;
      elements.startRunBtn.disabled = state.isRunning;
    } else {
      elements.startRunText.textContent = "Start Test Run (Select services)";
      elements.startRunBtn.disabled = true;
    }
  }

  /**
   * Renders component cards into the grid
   */
  function renderComponents() {
    elements.componentsGrid.innerHTML = "";
    const filtered = getFilteredComponents();

    if (filtered.length === 0) {
      const emptyMsg = document.createElement("div");
      emptyMsg.style.gridColumn = "1 / -1";
      emptyMsg.style.padding = "2rem";
      emptyMsg.style.textAlign = "center";
      emptyMsg.style.color = "var(--text-muted)";
      emptyMsg.textContent = "No components match your search or filter criteria.";
      elements.componentsGrid.appendChild(emptyMsg);
      return;
    }

    filtered.forEach((comp) => {
      const card = document.createElement("div");
      const isSelected = state.selectedIds.has(comp.id);

      card.className = `component-card ${isSelected ? "selected" : ""}`;
      card.dataset.id = comp.id;

      const isTested = comp.status === "tested";
      const statusClass = isTested ? "tag-tested" : "tag-untested";
      const statusText = isTested ? "Tested" : "Untested";

      let tagsHtml = `
        <span class="tag ${statusClass}">${statusText}</span>
      `;

      if (comp.has_ui) {
        tagsHtml += '<span class="tag tag-ui">🌐 UI</span>';
      }

      if (comp.category) {
        tagsHtml += `<span class="tag tag-category">${comp.category}</span>`;
      }

      card.innerHTML = `
        <input type="checkbox" class="component-checkbox" ${
          isSelected ? "checked" : ""
        } />
        <div class="component-info">
          <div class="component-name">${comp.name || comp.id}</div>
          <div class="component-id">${comp.id}</div>
          <div class="component-tags">${tagsHtml}</div>
        </div>
      `;

      // Event listener to toggle selection
      const checkbox = card.querySelector(".component-checkbox");
      card.addEventListener("click", (e) => {
        if (e.target !== checkbox) {
          checkbox.checked = !checkbox.checked;
        }
        if (checkbox.checked) {
          state.selectedIds.add(comp.id);
          card.classList.add("selected");
        } else {
          state.selectedIds.delete(comp.id);
          card.classList.remove("selected");
        }
        updateSelectionUI();
      });

      checkbox.addEventListener("change", () => {
        if (checkbox.checked) {
          state.selectedIds.add(comp.id);
          card.classList.add("selected");
        } else {
          state.selectedIds.delete(comp.id);
          card.classList.remove("selected");
        }
        updateSelectionUI();
      });

      elements.componentsGrid.appendChild(card);
    });
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
   * Append a log line to the live terminal
   */
  function appendLog(line) {
    const lineDiv = document.createElement("div");
    lineDiv.className = "terminal-line";
    lineDiv.innerHTML = ansiToHtml(line);
    elements.terminalBody.appendChild(lineDiv);
    elements.terminalBody.scrollTop = elements.terminalBody.scrollHeight;
  }

  /**
   * Updates or inserts a record in the results table
   */
  function updateResultRecord(record, prepend = false) {
    if (!record || !record.component_id) return;

    // Remove empty placeholder row if present
    const emptyRow = elements.resultsTableBody.querySelector("tr td[colspan]");
    if (emptyRow) {
      elements.resultsTableBody.innerHTML = "";
    }

    const recTime = record.timestamp || getTimestamp();
    const recMode = (
      record.mode || (state.mode === "both" ? "LXC" : state.mode)
    ).toUpperCase();
    const recEngine = (
      record.engine || (state.engine === "both" ? "DOCKER" : state.engine)
    ).toUpperCase();
    const rowId = `result-row-${record.component_id}-${recMode}-${recEngine}-${recTime.replace(/[^a-zA-Z0-9]/g, "-")}`;
    let row = document.getElementById(rowId);

    if (!row) {
      row = document.createElement("tr");
      row.id = rowId;
      if (prepend && elements.resultsTableBody.firstChild) {
        elements.resultsTableBody.insertBefore(row, elements.resultsTableBody.firstChild);
      } else {
        elements.resultsTableBody.appendChild(row);
      }
    }

    const isSuccess = record.status === "success";
    const statusBadge = isSuccess
      ? '<span class="tag tag-tested">✅ PASS</span>'
      : record.status === "running"
      ? '<span class="tag tag-ui">⏳ RUNNING</span>'
      : record.status === "pending"
      ? '<span class="tag tag-category">⚪ PENDING</span>'
      : '<span class="tag tag-untested">❌ FAIL</span>';

    const httpBadge =
      record.http_ok === null || record.http_ok === undefined
        ? "N/A"
        : record.http_ok
        ? '<span style="color: var(--accent-green); font-weight: 600;">OK</span>'
        : '<span style="color: var(--accent-red); font-weight: 600;">FAIL</span>';

    row.innerHTML = `
      <td><small style="color: var(--text-muted); font-family: var(--font-mono);">${recTime}</small></td>
      <td><strong>${record.component_id}</strong></td>
      <td><span class="tag ${recMode === "LXC" ? "tag-category" : "tag-ui"}">${recMode}</span></td>
      <td><code>${recEngine}</code></td>
      <td>${record.vmid || "—"}</td>
      <td><code>${record.ip || "—"}</code></td>
      <td>${record.deployment || "—"}</td>
      <td>${record.running ? "Running" : "Stopped"}</td>
      <td>${httpBadge}</td>
      <td>${statusBadge}</td>
    `;
  }

  /**
   * Loads cumulative test history from API
   */
  async function loadTestHistory() {
    try {
      const res = await fetch("/api/results");
      if (res.ok) {
        const historyData = await res.json();
        if (Array.isArray(historyData) && historyData.length > 0) {
          elements.resultsTableBody.innerHTML = "";
          // Display in reverse chronological order (newest first)
          const reversed = [...historyData].reverse();
          reversed.forEach((rec) => updateResultRecord(rec, false));
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
        elements.resultsTableBody.innerHTML = `
          <tr>
            <td colspan="10" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">
              No test history recorded yet.
            </td>
          </tr>
        `;
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
      updateResultRecord(msgData.record);
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
        // Refresh component cards to show updated tested status tags
        fetchComponents();
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
   * Starts tests for selected components
   */
  async function startTests() {
    if (state.selectedIds.size === 0) return;

    state.isRunning = true;
    elements.startRunBtn.disabled = true;
    elements.stopRunBtn.style.display = "inline-flex";
    setStatus("running", "Starting Test Run...");

    const ts = getTimestamp();
    const numModes = state.mode === "both" ? 2 : 1;
    const numEngines = state.engine === "both" ? 2 : 1;
    const totalRuns = state.selectedIds.size * numModes * numEngines;
    const modeLabel =
      state.mode === "both" ? "LXC + VM (Matrix)" : state.mode.toUpperCase();
    const engineLabel =
      state.engine === "both"
        ? "DOCKER + PODMAN (Matrix)"
        : state.engine.toUpperCase();

    appendLog(
      `\n======================================================================`
    );
    appendLog(
      `[${ts}] [GUI] STARTING TEST RUN: ${state.selectedIds.size} SERVICES (${totalRuns} TOTAL EXECUTIONS)`
    );
    appendLog(`[${ts}] [GUI] Target: ${modeLabel} | Engine: ${engineLabel}`);
    appendLog(
      `======================================================================\n`
    );

    // Pre-populate results table with pending rows at top of table
    state.selectedIds.forEach((cid) => {
      updateResultRecord(
        {
          timestamp: ts,
          component_id: cid,
          mode: state.mode === "both" ? "LXC" : state.mode.toUpperCase(),
          engine: state.engine === "both" ? "DOCKER" : state.engine.toUpperCase(),
          status: "pending",
          deployment: "Pending",
          running: false,
        },
        true
      );
    });

    try {
      const payload = {
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

      // Connect to SSE stream
      connectStream();
    } catch (err) {
      appendLog(`[ERROR] Network error starting tests: ${err.message}`);
      setStatus("failed", "Error");
      state.isRunning = false;
      elements.startRunBtn.disabled = false;
      elements.stopRunBtn.style.display = "none";
    }
  }

  /**
   * Stops running tests
   */
  async function stopTests() {
    if (!state.isRunning) return;
    try {
      appendLog(`[${getTimestamp()}] [GUI] Requesting test runner termination...`);
      await fetch("/api/stop", { method: "POST" });
    } catch (err) {
      console.error("Failed to stop tests:", err);
    }
  }

  /**
   * Fetches latest markdown test report
   */
  async function loadReport() {
    try {
      elements.reportContent.textContent = "Loading report...";
      elements.reportModal.classList.add("open");
      const res = await fetch("/api/report");
      const data = await res.json();
      if (data.report) {
        elements.reportContent.textContent = data.report;
      } else {
        elements.reportContent.textContent = "No report generated yet.";
      }
    } catch (err) {
      elements.reportContent.textContent = `Error loading report: ${err.message}`;
    }
  }

  /**
   * Enforces exact table header column names and order
   */
  function ensureTableHeaders() {
    const tableThead = document.querySelector(".results-table thead");
    if (tableThead) {
      tableThead.innerHTML = `
        <tr>
          <th>Date / Time</th>
          <th>Component</th>
          <th>Target</th>
          <th>Engine</th>
          <th>VM ID</th>
          <th>IP Address</th>
          <th>Deployment</th>
          <th>Containers</th>
          <th>HTTP UI</th>
          <th>Status</th>
        </tr>
      `;
    }
  }

  async function fetchComponents() {
    const compRes = await fetch("/api/components");
    if (compRes.ok) {
      state.components = await compRes.json();
      renderComponents();
      updateSelectionUI();
    }
  }

  /**
   * Initializes application data from API
   */
  async function init() {
    ensureTableHeaders();

    try {
      // 1. Fetch initial configuration
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
      }

      // 2. Fetch components
      await fetchComponents();

      // 3. Fetch cumulative test history
      await loadTestHistory();
    } catch (err) {
      console.error("Initialization error:", err);
    }

    // Attach Event Listeners

    // Search bar with live wildcard matching
    elements.searchInput.addEventListener("input", (e) => {
      state.searchQuery = e.target.value;
      elements.searchClearBtn.style.display = state.searchQuery ? "block" : "none";
      renderComponents();
    });

    elements.searchClearBtn.addEventListener("click", () => {
      elements.searchInput.value = "";
      state.searchQuery = "";
      elements.searchClearBtn.style.display = "none";
      renderComponents();
      elements.searchInput.focus();
    });

    // Category / Status Filter pills
    elements.filterPills.forEach((pill) => {
      pill.addEventListener("click", () => {
        elements.filterPills.forEach((p) => p.classList.remove("active"));
        pill.classList.add("active");
        state.activeFilter = pill.dataset.filter;
        renderComponents();
      });
    });

    // Mode toggles
    elements.modeLxcBtn.addEventListener("click", () => {
      state.mode = "lxc";
      elements.modeLxcBtn.classList.add("active");
      elements.modeVmBtn.classList.remove("active");
      if (elements.modeBothBtn) elements.modeBothBtn.classList.remove("active", "mode-both");
      elements.templateIdWrapper.style.opacity = "0.5";
      elements.templateIdInput.disabled = true;
    });

    elements.modeVmBtn.addEventListener("click", () => {
      state.mode = "vm";
      elements.modeVmBtn.classList.add("active");
      elements.modeLxcBtn.classList.remove("active");
      if (elements.modeBothBtn) elements.modeBothBtn.classList.remove("active", "mode-both");
      elements.templateIdWrapper.style.opacity = "1";
      elements.templateIdInput.disabled = false;
    });

    if (elements.modeBothBtn) {
      elements.modeBothBtn.addEventListener("click", () => {
        state.mode = "both";
        elements.modeBothBtn.classList.add("active", "mode-both");
        elements.modeLxcBtn.classList.remove("active");
        elements.modeVmBtn.classList.remove("active");
        elements.templateIdWrapper.style.opacity = "1";
        elements.templateIdInput.disabled = false;
      });
    }

    // Engine toggles
    elements.engineDockerBtn.addEventListener("click", () => {
      state.engine = "docker";
      elements.engineDockerBtn.classList.add("active");
      elements.enginePodmanBtn.classList.remove("active", "engine-podman");
      if (elements.engineBothBtn) elements.engineBothBtn.classList.remove("active", "engine-both");
    });

    elements.enginePodmanBtn.addEventListener("click", () => {
      state.engine = "podman";
      elements.enginePodmanBtn.classList.add("active", "engine-podman");
      elements.engineDockerBtn.classList.remove("active");
      if (elements.engineBothBtn) elements.engineBothBtn.classList.remove("active", "engine-both");
    });

    if (elements.engineBothBtn) {
      elements.engineBothBtn.addEventListener("click", () => {
        state.engine = "both";
        elements.engineBothBtn.classList.add("active", "engine-both");
        elements.engineDockerBtn.classList.remove("active");
        elements.enginePodmanBtn.classList.remove("active", "engine-podman");
      });
    }

    // Batch selection buttons
    elements.selectAllFilteredBtn.addEventListener("click", () => {
      const filtered = getFilteredComponents();
      filtered.forEach((c) => state.selectedIds.add(c.id));
      renderComponents();
      updateSelectionUI();
    });

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

    // Runner triggers
    elements.startRunBtn.addEventListener("click", startTests);
    elements.stopRunBtn.addEventListener("click", stopTests);

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

    // Report modal
    elements.viewReportBtn.addEventListener("click", loadReport);
    elements.closeModalBtn.addEventListener("click", () => {
      elements.reportModal.classList.remove("open");
    });

    elements.reportModal.addEventListener("click", (e) => {
      if (e.target === elements.reportModal) {
        elements.reportModal.classList.remove("open");
      }
    });
  }

  // Run on DOM ready
  document.addEventListener("DOMContentLoaded", init);
})();
