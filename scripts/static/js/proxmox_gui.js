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
    sortColumn: "timestamp",
    sortDirection: "desc",
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
    selectAllTestableBtn: document.getElementById("select-all-testable-btn"),
    deselectUntestableBtn: document.getElementById("deselect-untestable-btn"),
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
      const isUntestable = Boolean(comp.is_untestable);

      card.className = `component-card ${isSelected ? "selected" : ""} ${
        isUntestable ? "untestable" : ""
      }`;
      card.dataset.id = comp.id;

      const isTested = comp.status === "tested";
      const statusClass = isTested ? "tag-tested" : "tag-untested";
      const statusText = isTested ? "Tested" : "Untested";

      let tagsHtml = `
        <span class="tag ${statusClass}">${statusText}</span>
      `;

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
   * Opens Gemini AI single failure diagnosis modal
   */
  async function openAiSingleDiagnosis(record) {
    if (!record) return;
    activePatchData = null;
    elements.aiModalApplyBtn.style.display = "none";
    elements.aiModalTitle.textContent = `✨ Gemini AI Diagnosis: ${record.component_id} (${record.mode || ""}/${record.engine || ""})`;
    elements.aiModalBody.innerHTML = `
      <div style="text-align: center; padding: 2rem;">
        <div style="font-size: 2rem; margin-bottom: 0.75rem;">⏳</div>
        <div><strong>Analyzing failure with Gemini AI...</strong></div>
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
   * Opens Gemini AI batch systemic failure analysis modal
   */
  async function openAiBatchDiagnosis() {
    activePatchData = null;
    elements.aiModalApplyBtn.style.display = "none";
    elements.aiModalTitle.textContent = "✨ Gemini AI Systemic Batch Analysis";
    elements.aiModalBody.innerHTML = `
      <div style="text-align: center; padding: 2rem;">
        <div style="font-size: 2rem; margin-bottom: 0.75rem;">⏳</div>
        <div><strong>Analyzing all test failures for systemic patterns with Gemini AI...</strong></div>
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
   * Renders the complete results and history table
   */
  function renderResultsTable() {
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
    elements.resultsTableBody.innerHTML = "";

    sorted.forEach((record) => {
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

      const httpBadge =
        record.http_ok === null || record.http_ok === undefined
          ? "N/A"
          : record.http_ok
          ? '<span style="color: var(--accent-green); font-weight: 600;">OK</span>'
          : '<span style="color: var(--accent-red); font-weight: 600;">FAIL</span>';

      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><small style="color: var(--text-muted); font-family: var(--font-mono);">${escapeHtml(recTime)}</small></td>
        <td><strong>${escapeHtml(record.component_id || "—")}</strong></td>
        <td><span class="tag ${recMode === "LXC" ? "tag-category" : "tag-ui"}">${escapeHtml(recMode)}</span></td>
        <td><code>${escapeHtml(recEngine)}</code></td>
        <td>${escapeHtml(String(record.vmid || "—"))}</td>
        <td><code>${escapeHtml(record.ip || "—")}</code></td>
        <td>${escapeHtml(record.deployment || "—")}</td>
        <td>${record.running ? "Running" : "Stopped"}</td>
        <td>${httpBadge}</td>
        <td>${statusBadge}</td>
        <td>
          ${
            isFail
              ? `<button type="button" class="btn-ai-fix" data-comp="${escapeHtml(record.component_id || "")}"><span>✨</span> AI Fix</button>`
              : '<span style="color: var(--text-muted);">—</span>'
          }
        </td>
      `;

      const aiBtn = tr.querySelector(".btn-ai-fix");
      if (aiBtn) {
        aiBtn.addEventListener("click", () => openAiSingleDiagnosis(record));
      }

      elements.resultsTableBody.appendChild(tr);
    });
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
            _id: `hist-${idx}-${rec.component_id}-${rec.timestamp}`,
          }));

          // Preserve live records and merge with history safely
          const currentLive = state.results.filter((r) => !r.is_history);
          const historyKeySet = new Set(
            histRecords.map(
              (r) =>
                `${r.component_id}_${r.timestamp}_${r.mode || ""}_${
                  r.engine || ""
                }`
            )
          );

          const pendingLive = currentLive.filter(
            (r) =>
              !historyKeySet.has(
                `${r.component_id}_${r.timestamp}_${r.mode || ""}_${
                  r.engine || ""
                }`
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
      // Find matching live record
      const match =
        state.results.find(
          (r) =>
            !r.is_history &&
            r.component_id === rec.component_id &&
            (r.status === "pending" || r.status === "running")
        ) ||
        state.results.find(
          (r) => !r.is_history && r.component_id === rec.component_id
        );

      if (match) {
        Object.assign(match, rec);
        if (rec.timestamp) match.timestamp = rec.timestamp;
      } else {
        state.results.unshift({
          ...rec,
          timestamp: rec.timestamp || getTimestamp(),
          is_history: false,
          _id: `live-${rec.component_id}-${Date.now()}`,
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
        // Refresh component cards to show updated tested status tags
        fetchComponents();
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
   * Starts tests for selected components
   */
  async function startTests() {
    if (state.selectedIds.size === 0) return;

    state.isRunning = true;
    elements.startRunBtn.disabled = true;
    elements.stopRunBtn.style.display = "inline-flex";
    setStatus("running", "Executing Test Run(s)...");

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
      `[${ts}] [GUI] EXECUTING TEST RUN(S): ${state.selectedIds.size} SERVICES (${totalRuns} TOTAL EXECUTIONS)`
    );
    appendLog(`[${ts}] [GUI] Target: ${modeLabel} | Engine: ${engineLabel}`);
    appendLog(
      `======================================================================\n`
    );

    // Pre-populate results table with pending rows (newest timestamp)
    state.selectedIds.forEach((cid) => {
      state.results.unshift({
        timestamp: ts,
        component_id: cid,
        mode: state.mode === "both" ? "LXC" : state.mode.toUpperCase(),
        engine: state.engine === "both" ? "DOCKER" : state.engine.toUpperCase(),
        status: "pending",
        deployment: "Pending",
        running: false,
        vmid: "—",
        ip: "—",
        http_ok: null,
        is_history: false,
        _id: `live-${cid}-${Date.now()}-${Math.random()}`,
      });
    });
    renderResultsTable();

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
   * Initializes click handlers on sortable table headers
   */
  function initTableSorting() {
    const tableThead = document.querySelector(".results-table thead");
    if (!tableThead) return;

    tableThead.innerHTML = `
      <tr>
        <th data-sort="timestamp" class="sortable">Date / Time <span class="sort-icon"></span></th>
        <th data-sort="component_id" class="sortable">Component <span class="sort-icon"></span></th>
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
    initTableSorting();

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
