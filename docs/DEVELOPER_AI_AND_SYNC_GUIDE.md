# Developer Guide: AI Integrations and Component Repository Synchronization

This guide documents the setup, architecture, and usage of the separate component repository and AI-assisted tools in NjordDeploy.

## 1. Separate Component Repository Architecture

To decouple the release cycle of individual self-hosted services from the main application installer, components are stored and maintained in a separate repository.

- Remote Repository: "https://github.com/HenkVanHoek/njord-deploy-components"
- Custom Repository Variable: "PI_SELFHOSTING_COMPONENTS_REPO" (Defaults to "HenkVanHoek/njord-deploy-components")
- Branch Variable: "PI_SELFHOSTING_COMPONENTS_BRANCH" (Defaults to "main")

### How Synchronization Works

The sync manager, defined in [sync_manager.py](file:///home/hvhoek/PycharmProjects/njord-deploy/src/managers/sync_manager.py), handles the data flow:

1. Fetching Remote Data:
   The application downloads the latest ZIP archive of the remote repository and extracts it to a local cache directory. On Linux, this is located inside the user data directory:
   "~/.local/share/NjordDeploy/remote_components_cache"

2. Diff and Compare:
   The system compares local component templates and metadata against the cached remote version. It detects if components are synced, modified, only available locally, or only available remotely.

3. Synchronizing (Pull):
   The user can pull components individually or in bulk. Pulling overwrites the local templates and the local "components_metadata.json" with the remote version.

4. Publishing (Push):
   Developers with write access can push local components back to the remote repository. The sync manager verifies write permission by executing a dry-run push using SSH or HTTPS.
   To pass the validation gate during upload, the template file "docker-compose.template.yml" must start with the following header comments:
   - "# status: <status>"
   - "# last_tested_version: <version>"
   - "# platform_notes: <notes>"
   - "# breaking_changes: <changes>"

---

## 2. AI-Assisted Component Generator (Multi-Provider & Multi-Forge Git Support)

The component editor includes an AI assistant that automatically bootstraps new components from any Git repository URL across all major hosting platforms and self-hosted instances.

### Supported Git Hosting Platforms & Repositories

The generator supports direct URL ingestion from:
- **GitHub**: `https://github.com/owner/repository`
- **GitLab**: `https://gitlab.com/group/subgroup/project` (supports arbitrarily nested group hierarchies and namespaces)
- **Gitea / Forgejo / Codeberg**: `https://codeberg.org/owner/repository` or any community instance
- **Bitbucket**: `https://bitbucket.org/workspace/repository`
- **Self-Hosted Git Instances**: Any self-hosted Git server (e.g. `https://git.yourdomain.com/owner/project`)

### Supported AI Providers & Configuration

The AI generator supports multiple AI providers with per-provider API key storage in the local `.env` file:

- **Google Gemini**: Uses `GEMINI_API_KEY`. Endpoint is fixed to Google's official OpenAI-compatible API (`https://generativelanguage.googleapis.com/v1beta/openai/`). Recommended model: `gemini-2.5-flash`.
  * *Architecture Note:* Google officially maintains this OpenAI-compatible layer alongside their native SDK (`google-genai` / Interactions API) to enable cross-provider interoperability. NjordDeploy deliberately routes Gemini through this endpoint so that a single unified client ([AIGeneratorEngine](file:///home/hvhoek/PycharmProjects/njord-deploy/src/utils/ai_generator_engine.py)) services Ollama, HostYourAI, OpenAI, and Gemini without fragmented SDK dependencies or separate code paths.
- **HostYourAI / Loes (EU)**: Uses `HOSTYOURAI_API_KEY`. Default base URL is `https://api.hostyourai.eu/v1` (configurable via `HOSTYOURAI_BASE_URL` or UI). Default model: `mistral-7b-instruct`.
- **OpenAI**: Uses `OPENAI_API_KEY`. Endpoint is fixed to `https://api.openai.com/v1`. Recommended model: `gpt-4o-mini`.
- **Ollama (Local LLM)**: Uses local endpoint (default `http://localhost:11434/v1`, configurable via `OLLAMA_BASE_URL`). Recommended model: `qwen2.5-coder:14b-instruct-q4_K_M`.
- **Custom Endpoint**: Uses `CUSTOM_AI_API_KEY` and configurable base URL (`CUSTOM_AI_BASE_URL`) for self-hosted OpenAI-compatible APIs (LM Studio, vLLM, LocalAI).

### Key Management & Provider Switching

- **Per-Provider Keys:** API keys are stored separately per provider in `.env` (`GEMINI_API_KEY`, `HOSTYOURAI_API_KEY`, `OPENAI_API_KEY`, `CUSTOM_AI_API_KEY`). Switching providers in the Editor App preserves stored keys without overwriting other providers.
- **Global Default Provider:** The `AI_PROVIDER` environment variable sets the global fallback provider.
- **Just-in-Time UI Saving:** In the "Import via AI" modal in the Editor App, entering an API key with "Save API key to local .env file" checked will automatically validate and save the key to `.env` upon successful component generation.

### How to Use

1. Start the Editor App.
2. Click the "Create with AI" button in the sidebar.
3. Input any public Git repository URL (e.g. `https://github.com/caddyserver/caddy`, `https://gitlab.com/...`, or `https://codeberg.org/...`) and add optional custom instructions.
4. Click "Generate Component".
   * **Automatic Context Enrichment:** The backend automatically attempts to fetch public documentation and compose files across standard variations (`README.md`, `readme.md`, `README`, `docker-compose.yml`, `docker-compose.yaml`, `compose.yml`, `compose.yaml`) across `main` and `master` branches from the repository to supply rich context in the prompt.
   * **Docker Hub & Registry Verification:** The generator queries public OCI registries (Docker Hub, GHCR, Quay) to verify that the generated image name exists. If the image is hosted on GHCR or custom registries, it automatically verifies and corrects the image name in metadata and compose templates.
   * **Validation & Self-Correction:** The generator automatically performs structure, variable consistency, and syntax validation checks. If any validation warnings or YAML syntax parsing errors (such as mismatched quotes or bad indentation) are detected, the backend executes an automatic self-correction loop (up to 3 attempts), feeding the warnings and errors back to the AI model to refine the configuration.
   * **Timeout & Error Resilience:** If the AI API times out or returns an upstream error, the editor intercepts this and displays a detailed explanation inside the modal with "Retry" and "Cancel" buttons.
5. The API returns a structured JSON payload containing metadata, user variables, and a Docker Compose template.
6. Review the preview of the generated files. If there are validation or image name warnings, they are displayed in the warning alert banner.
7. Click "Accept and Create" to save the bootstrapped files directly to the local project filesystem.

### Prompt Engineering & Rules Management

The core architectural guidelines and constraints that govern how the AI generates component configurations are stored in a separate JSON file: [ai_generator_rules.json](file:///home/hvhoek/PycharmProjects/njord-deploy/config/ai_generator_rules.json).

* **Decoupled Architecture:** Separating these rules from the Python code allows developers to adjust the system prompts, quality standards, and syntax validation rules without touching the application code or restarting the Flask development server.
* **Dynamic Loading:** The [AIGenerator](file:///home/hvhoek/PycharmProjects/njord-deploy/src/utils/ai_generator.py) class reads this file at runtime on every invocation. Modifications to the ruleset take effect immediately upon the next generation request.
* **Auto-Numbering:** Rules in the `rules` array are numbered sequentially at runtime (e.g. `1.`, `2.`, `3.`), making it easy to insert, remove, or rearrange rules in the JSON file without having to manually update rule numbers.
* **Dynamic Placeholders:** Special rule blocks (like `group_rule`) support runtime templates (e.g., dynamically listing the project's existing component groups like `reverse_proxy` or `databases`) with a fallback definition if no groups exist.

---

## 3. Local LLM and Context Generation (Ollama)

For offline development and deep codebase reasoning, you can run a local Llama 3-based assistant.

### Setup and Configuration

1. Create a Model file:
   Create a file named "NjordDeploy.Modelfile" in the project root (already present in the repository).

2. Build the Model in Ollama:
   Run the following terminal command:
   ```bash
   ollama create njorddeploy-expert -f NjordDeploy.Modelfile
   ```

3. Generate Codebase Context:
   Run the context generator script:
   ```bash
   python context_generator.py
   ```
   This script gathers all project code, runs a token count check to ensure it stays within the VRAM limit of an RTX 3060 (12GB VRAM), and produces the unified context file "llm_context.txt".

4. Ingest Context:
   Start a session with the "njorddeploy-expert" model in Open WebUI, then drag and drop the "llm_context.txt" file into your chat.

---

## 4. Component Governance & Admission Policy

To prevent a proliferation of rarely or never used components ("wildgroei"), developers must strictly adhere to the project's governance guidelines:

- **Product Owner Authorization:** The Product Owner is the sole gatekeeper of the components' repository. No component will be merged or distributed without explicit Product Owner approval.
- **Admission Standards:** Components must be highly-requested, popular, and resource-friendly self-hosted services compatible with Debian and Docker on Single-Board Computers (SBCs).
- **Quality Assurance:** Any component proposed for inclusion must pass local validation gates and be successfully deployed and verified via the automated Proxmox test suite (raising its status to `tested`).
- **Release and Workflow:** Contributors must submit modifications and new components via Pull Requests on the remote repository rather than pushing directly to the `main` branch.
