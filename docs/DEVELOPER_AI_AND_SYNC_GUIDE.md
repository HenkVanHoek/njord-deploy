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

## 2. AI-Assisted Component Generator (Google Gemini)

The component editor includes an AI assistant that automatically bootstraps new components using a GitHub repository URL.

### Setup and Configuration

The generator communicates with the Gemini REST API using the model "gemini-2.5-flash".

To use this feature, you must provide a Gemini API Key:
- Option A: Define the key in the ".env" file using the variable "GEMINI_API_KEY".
- Option B: Enter the key in the Create with AI dialog in the web interface. The key is saved locally in browser storage.

### How to Use

1. Start the Editor App.
2. Click the "Create with AI" button in the sidebar.
3. Input the GitHub repository URL (such as "https://github.com/caddyserver/caddy") and add optional custom instructions.
4. Click "Generate Component". The backend sends a request to the Gemini API with structural instructions and validation rules.
5. The API returns a structured JSON payload containing metadata, user variables, and a Docker Compose template.
6. Review the preview of the generated files.
7. Click "Accept and Create" to save the bootstrapped files directly to the local project filesystem.

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
