# NjordDeploy Component Editor - Visual Feature & Menu Guide

Welcome to the comprehensive feature guide and visual tour for the **NjordDeploy Component Editor** (`http://localhost:5000`).

The Component Editor is a developer and maintainer workspace for creating, inspecting, customizing, and synchronizing modular self-hosted service definitions within the NjordDeploy ecosystem.

---

## 🎬 Animated Feature Tour

![NjordDeploy Component Editor Feature Tour](images/editor_tour/njorddeploy-editor-features.gif)

---

## 🧭 Menu Options & Workspace Breakdown

### 1. Main Workspace & Sidebar Navigation
![Workspace](images/editor_tour/editor_slide_1_workspace.png)
* **Groups vs Packages View:** Toggle between browsing individual service categories (DNS, AI, Media, Smart Home) or bundled all-in-one software stacks.
* **Instant Filtering & Search:** Rapid real-time search across 50+ modular components by name, description, tags, or ports.
* **Expand / Collapse All:** Quick controls to inspect deep category trees with 1 click.
* **Theme Switching:** Choose between *Futuristic Dark (Glassmorphic)*, *Standard Light*, and *High Contrast* accessibility modes.

---

### 2. User Variables & Dynamic Macro System
![User Variables](images/editor_tour/editor_slide_2_variables.png)
* **Variable Definition:** Configure environment variables, port bindings, and storage mounts exposed to end-users during deployment.
* **Dynamic Macro System:**
  * `{{ CONFIG_BASE_PATH }}/your-service`: Generates portable data paths across target hosts.
  * `{{ DOTENV.YOUR_VAR }}`: Binds component variables dynamically to the target server's global `.env` file.
* **Field Validation:** Built-in schema validation for port ranges (1–65535), boolean flags, and directory paths.

---

### 3. Jinja2 Docker Compose Template Editor & Validator
![Compose Editor](images/editor_tour/editor_slide_3_compose.png)
* **Syntax Highlighting & Formatting:** Jinja2 + YAML template editor tailored for modern Docker Compose definitions.
* **Jinja Context Badges:** Click to insert standard contextual variables:
  * `{{ CONTAINER_ENGINE }}`: Resolves to `docker` or `podman`.
  * `{{ TARGET_MODE }}`: Resolves to `lxc` or `vm`.
  * `{{ DATA_ROOT }}` & `{{ CONFIG_BASE_PATH }}`.
* **Conditionals Dropdown:** Quick insertion of engine-specific blocks (`{% if CONTAINER_ENGINE == 'podman' %}`).
* **Live Template Validation:** Evaluates Jinja syntax and Compose YAML structure before saving.

---

### 4. AI Component Generator (HostYourAI / Loes)
![AI Generator](images/editor_slide_4_ai_generator.png)
* **1-Click Git Ingestion:** Input any public repository URL (**GitHub, GitLab, Forgejo, Codeberg, Bitbucket, or self-hosted Git**).
* **Name Disambiguation:** Custom component ID field (e.g. `immich-custom`) prevents collisions with existing library components.
* **European Sovereign AI:** Powered by **HostYourAI / Loes (EU Sovereign Cloud)** for privacy-first, GDPR-compliant AI generation, as well as local Ollama, Google Gemini, and OpenAI.
* **Deep Context Stepper:** Automatically fetches `README.md` and Compose files, generates ports, and validates non-root volume permissions.

---

### 5. Remote Component Repository Sync & Diff
![Git Sync](images/editor_tour/editor_slide_5_git_sync.png)
* **Decoupled Architecture:** Components are maintained in a dedicated repository (`HenkVanHoek/njord-deploy-components`).
* **Bi-Directional Diffing:** Inspect local vs remote modifications before pulling or pushing.
* **Write Permission Verification:** Automated SSH / token verification ensures authorized uploads.
* **Required Template Headers:** Enforces governance standards (`# status:`, `# last_tested_version:`, `# platform_notes:`).

---

### 6. Ecosystem Analytics & Component Statistics
![Stats Modal](images/editor_tour/editor_slide_6_stats.png)
* **Live Library Metrics:** Total active services, groups, packages, and tested statuses.
* **Category Distribution:** Visual charts displaying service distribution across AI, DNS, Media, Smart Home, and Databases.
* **Compatibility Matrix:** Quick view of Docker vs Podman support across all components.

---

### 7. Security Hash Generator (Basic Auth)
![Hash Generator](images/editor_tour/editor_slide_7_hash.png)
* **Built-in Crypto Utility:** Generates secure password hashes for reverse proxies (Nginx Proxy Manager, Caddy, Traefik).
* **Supported Algorithms:** **Argon2id**, **bcrypt**, and **SHA-512**.
* **1-Click Copy:** Copies formatted auth strings directly into user variable configurations.

---

### 8. Curated Packages & Stack Management
![Package Management](images/editor_tour/editor_slide_8_packages.png)
* **All-in-One Stacks:** Combine complementary services (e.g. *AdGuard Home + Unbound*, *Nextcloud + Redis + MariaDB*, *Frigate + Coral TPU*) into 1-click installable bundles.
* **Dependency & Conflict Rules:** Define required companion services and mutual exclusivity rules.
