# NjordDeploy Project Roadmap

This document outlines the development roadmap for NjordDeploy. It is a living document that details our current priorities, planned features for upcoming releases, and long-term goals. Our aim is to be transparent about our direction and to help contributors understand where they can best apply their efforts.

## Guiding Principles

Our development is guided by the following principles:
1.  **Stability First**: Core features must be robust, reliable, and well-tested before new, complex functionality is added.
2.  **User Experience**: The primary goal is to simplify the self-hosting journey for our users.
3.  **Maintainability**: The codebase and architecture should remain clean, modular, and easy for new contributors to understand.

---

## Phase 1: Foundation & Core Usability (Complete)

This phase focused on creating a rock-solid, feature-rich, and user-friendly installer with a single, well-supported database backend.

*   **[✅] Solidify Core Installer**: Refactored to a full Python application with a seamless web-based UI. The core generation engine has been hardened for stability and now provides robust, detailed error reporting.
*   **[✅] Robust Component System**: Implemented a metadata-driven system (`components_metadata.json`) to easily add and manage new services.
*   **[✅] Comprehensive Testing**: Expanded the `pytest` suite to ensure the reliability of the installer and utility functions. The entire test suite is now stable, passing, and provides a solid foundation for future development.
*   **[✅] Documentation**: Created clear documentation for both end-users and contributors. Core architectural documents (`ARCHITECTURE.md`, `DATA_CONTRACTS.md`, `FUNCTIONAL_SPEC.md`) are now up-to-date with the latest design patterns.
*   **MariaDB as the Primary Database**: Standardized on MariaDB as the sole database option to ensure stability and reduce testing complexity.

---

## Phase 2: Expansion & Flexibility (Current Focus)

With a stable foundation, this phase will focus on expanding the ecosystem, improving the developer experience, and providing more options for advanced users.

*   **[In Progress] Component Configuration Tools**: Develop modular, post-installation tools for key services. The core ONVIF camera discovery and configuration tool for Frigate (`frigate_camera_config_tool.py`) has been completed, with dashboard integration being the next step.
*   **[Planned] Integrated Backup & Restore**: Develop a user-friendly, Flask-based tool to back up and restore all persistent service data. This is a critical feature for data security and user peace of mind.
    *   **Implementation**: This will be a new, optional management tool built with Flask. It will provide a simple web UI to automatically detect and back up all persistent Docker volumes. The tool will feature **smart, configurable defaults**, allowing users to easily exclude large data volumes (like Frigate video recordings) to ensure fast and efficient backups of critical configuration data.
*   **[✅] AI-Assisted Component Generation**:
    *   **Why?**: To dramatically accelerate the process of adding new services and lower the barrier for new contributors. As a nod to the powerful AI assistance that has been instrumental in this project's development, this feature brings that same power directly to our developers.
    *   **Implementation**: This has been implemented as an intuitive UI in the Editor where a developer can describe a service or input any Git repository URL (supporting GitHub, GitLab, Gitea, Forgejo, Codeberg, Bitbucket, and self-hosted Git servers). The backend queries an LLM to generate draft versions of the component's metadata, variables, and `docker-compose.template.yml`.
        1.  **[✅] Multi-Provider AI Support**: Fully active support for local models (Ollama RTX 3060) and cloud APIs (Google Gemini, OpenAI, HostYourAI EU), featuring automatic repository analysis, image presence verification across Docker Hub & OCI registries, validation warning flags, and multi-turn self-correction loops.
        2.  **[✅] Multi-Forge Git Support**: Generalized repository parsing and raw content extraction across GitHub, GitLab (including nested namespaces), Codeberg, Gitea, Bitbucket, and self-hosted instances.
*   **[Planned] Advanced Installer Options**: Introduce an "Advanced Mode" in the installer for power users to tweak more specific Docker settings.

---

## Phase 3: Long-Term Vision (Future)

This is a collection of ideas that are being considered for the long-term future.

*   **Introduce PostgreSQL Support**:
    *   **Why?**: To support a new class of powerful applications that require or strongly prefer PostgreSQL (e.g., Mastodon).
    *   **Implementation**: This will be a significant architectural update reserved for a future major version.
*   **Provider-Agnostic Off-site Backups**: Enhance the Backup & Restore tool with an automated off-site capability using a generic tool like `rclone`. This will allow users to send encrypted backups to any of the 70+ cloud storage providers `rclone` supports.
*   **Plugin Marketplace**: An interface where the community can submit new component templates for easy inclusion.
*   **Multi-Node/Clustering Support**: The ability to deploy services across multiple Raspberry Pi devices.
*   **Enhanced Security Auditing**: Tools to scan configurations for common security misconfigurations.

We welcome discussion on this roadmap! Please open an issue to discuss any of the points above or to propose new features.
