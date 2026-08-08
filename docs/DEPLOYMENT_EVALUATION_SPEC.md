# Specification: Post-Deployment AI Log Evaluation & Health Reporting

## 1. Overview & Purpose

NjordDeploy's `configurator_app` is designed for end-users provisioning self-hosted services on single-board computers (SBCs) or Proxmox LXC containers. End-users are not software developers; when a deployment encounters issues or behaves unexpectedly, dumping raw stack traces or Jinja template errors is unhelpful.

The **Post-Deployment AI Log Evaluation System** automatically inspects deployment logs, container execution statuses, and service endpoints upon session completion. Using the integrated `ai_provider_manager`, it generates a human-readable **Health & Action Report** categorized into three distinct scenarios, offering direct resolution paths, documentation links, or pre-filled GitHub issue reporting.

---

## 2. Core Scenarios & Decision Flow

Upon completion (or premature termination) of a deployment session, the system evaluates the deployment artifacts and renders one of three report states:

```
                      +-----------------------------+
                      | Deployment Session Complete |
                      +--------------+--------------+
                                     |
                                     v
                   +-----------------------------------+
                   | Log Sanitization & AI Evaluator   |
                   | (via src/utils/ai_provider_manager)|
                   +-----------------+-----------------+
                                     |
           +-------------------------+-------------------------+
           |                         |                         |
           v                         v                         v
  +------------------+      +------------------+      +------------------+
  |    Scenario 1    |      |    Scenario 2    |      |    Scenario 3    |
  | Status: GREEN    |      | Status: YELLOW   |      | Status: RED      |
  | (All Systems OK) |      | (Config Tuning)  |      | (Software Bug)   |
  +--------+---------+      +--------+---------+      +--------+---------+
           |                         |                         |
  +--------v---------+      +--------v---------+      +--------v---------+
  | - Service Links  |      | - Parameter Fix  |      | - Search Existing|
  | - Confirm [ OK ] |      | - Doc Link       |      |   GitHub Issues  |
  +------------------+      | - Reconfigure UI |      | - Draft New      |
                            +------------------+      |   GitHub Issue   |
                                                      +------------------+
```

### 2.1 Scenario 1: Clean Deployment (`GREEN`)
* **Condition:** Containers are running, HTTP health checks succeed (200/302 OK), and no panic/fatal log entries are detected.
* **UI Presentation:**
  * Success indicator with clickable service URLs (e.g., `http://192.168.1.150:8080`).
  * Simple confirmation button: `[ OK / Dashboard ]`.

### 2.2 Scenario 2: Parameter & Configuration Tuning Required (`YELLOW`)
* **Condition:** Deployment finished or partially failed due to user-configurable parameters (e.g., port already bound by `systemd-resolved`, invalid timezone, DB password too short, invalid volume path).
* **UI Presentation:**
  * Plain-language explanation of the issue (e.g., *"Port 53 is already in use on the target node"*).
  * **Direct UI Action:** `[ ⚙️ Adjust Parameters ]` button that redirects back to the configuration form with recommended fixes pre-selected.
  * **Documentation Reference:** `[ 📖 View User Guide: Resolving Port Conflicts ]` linking directly to relevant section in `docs/` or online manual.

### 2.3 Scenario 3: Fatal Error / Package Bug Identified (`RED`)
* **Condition:** Fatal exception, broken Docker compose syntax, Jinja rendering failure, architecture incompatibility (e.g. x86 image on ARM64), or NjordDeploy system error.
* **UI Presentation:**
  * Explanation that a software/template issue occurred.
  * **Deduplication Check:** Automated lookup against open/closed GitHub issues using error signatures.
    * If a match is found: *"This issue is already tracked in Issue #42: [Title]. Follow or comment here."*
  * **Draft GitHub Issue:** `[ 🐛 Report Problem on GitHub ]` button.
    * Pre-fills GitHub issue title, environment context (SBC model, OS, Docker version), and sanitized log excerpt via URL parameters or standard template.
    * Requires 1-click user confirmation before opening GitHub issue in browser.

---

## 3. System Architecture & Components

### 3.1 `src/managers/deployment_evaluator.py`
The core evaluation engine responsible for:
1. **Data Collection:**
   * Fetching container statuses via SSH / Docker API.
   * Gathering last 100 lines of `docker compose logs`.
   * Probing service ports / HTTP health endpoints.
2. **Log Sanitization (Privacy & Security):**
   * Regex filtering to scrub passwords, API tokens, secret keys, private SSH keys, and internal credentials (`***MASKED***`).
3. **AI Evaluation Request:**
   * Sending structured context to `ai_provider_manager` (Ollama, Gemini, HostYourAI, OpenAI).
   * System Prompt instructing LLM to output structured JSON:
     ```json
     {
       "status": "GREEN | YELLOW | RED",
       "summary": "Human readable 1-2 sentence description",
       "user_action": "Description of recommended parameter fix or next step",
       "doc_anchor": "USER_GUIDE.md#port-conflicts",
       "github_keywords": "jinja2 UndefinedError volume_path"
     }
     ```
4. **Fallback Engine (Deterministic Rules):**
   * If AI provider is disabled, offline, or unconfigured, evaluate status using deterministic rule-based log patterns (e.g., matching `bind: address already in use` -> YELLOW).
5. **GitHub Deduplication Check:**
   * Optional query to `https://api.github.com/repos/HenkVanHoek/njord-deploy/issues` using `github_keywords`.

### 3.2 Backend API Endpoint (`src/configurator_app/app.py`)
* `POST /api/deployment/<session_id>/evaluate`
* Invokes `DeploymentEvaluator.evaluate(session_id)`.
* Returns structured JSON payload to the frontend.

### 3.3 Frontend UI Integration (`src/configurator_app/templates/` & `static/js/`)
* Interactive evaluation modal rendered upon deployment completion.
* Dynamic rendering based on `GREEN`, `YELLOW`, or `RED` status payload.

---

## 4. Privacy, Security & Data Protection

* **Strict Sanitization:** Logs MUST be sanitized before transmission to external AI providers (Gemini, OpenAI, HostYourAI) or GitHub issue drafts.
* **No Auto-Submit:** GitHub issues are NEVER automatically submitted without explicit user confirmation in the UI.

---

## 5. Implementation Roadmap

1. **Phase 1: Backend Engine & Sanitizer** (`src/managers/deployment_evaluator.py` & unit tests).
2. **Phase 2: Fallback Rules & AI Integration** (Connecting `ai_provider_manager`).
3. **Phase 3: GitHub Issue Search & Pre-fill Generator**.
4. **Phase 4: Configurator UI Evaluation Modal** (HTML/JS integration in `configurator_app`).
