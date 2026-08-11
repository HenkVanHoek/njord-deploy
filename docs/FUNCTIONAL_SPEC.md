# NjordDeploy - Functional Specification

This is a living document that defines the functional requirements for the
NjordDeploy project. It is based on the principles of Behavior-Driven
Development (BDD), focusing on user-centric stories and testable
acceptance criteria.

## 1. Core Principles

-   **For End-Users:** The system must be simple, intuitive, and require
    zero command-line interaction for basic setup and configuration. It
    must provide clear feedback and guidance throughout the process.
-   **For Developers:** The system must be metadata-driven. Adding new
    self-hosted services must be achievable by adding data (metadata,
    variables, templates) and should not require changes to the core
    application code.

## 2. User Personas

-   **The End-User (Alex):** A non-technical but enthusiastic user who
    wants to run self-hosted services on a single-board computer or
    Debian-based server (e.g., Raspberry Pi, Orange Pi, ODROID, Radxa,
    Pine64). Alex interacts exclusively with the **Configurator App**.
-   **The Developer (Charlie):** A technical user who maintains and extends
    the NjordDeploy project. Charlie interacts with the **Editor App**
    and the underlying data files.

## 3. Epics & User Stories

### Epic 1: Developer - Component Management

As Charlie, I need a robust set of tools to add, manage, and define the
self-hosted services that are available to the end-user.

---

#### Story: Creating a New Component

> As a Developer (Charlie), I want to use a web-based editor to create
> the core metadata for a new self-hosted service, so that I can establish
> its identity and basic properties within the system.

**Acceptance Criteria:**

-   **Given** I am on the component editor page,
-   **When** I click the "Create New Component" button,
-   **And** I enter a valid Component ID (e.g., `new-service`) and Name
    (e.g., `New Service`),
-   **Then** a new component is created and appears in the component list.
-   **And** a corresponding folder structure is created on the filesystem,
    including a default Docker Compose template and `variables.json` file.
-   **And** the component's metadata (`name`, `description`, `group`,
    `has_ui`) can be updated and saved via the "Core Metadata" tab.

---

#### Story: Defining User-Configurable Variables

> As a Developer (Charlie), I want to define all user-configurable
> parameters for a service as a list of variables in the editor, so that
-   they are automatically and correctly rendered in the end-user's UI.

**Acceptance Criteria:**

-   **Given** I am editing a component,
-   **When** I navigate to the "User Variables" tab,
-   **And** I add a new variable with an `id`, `label`, `description`,
    `type`, and `default` value,
-   **And** I click "Save All Changes",
-   **Then** the new variable definition is saved into that component's
    `template-config/variables.json` file.
-   **And** the editor successfully reloads this data when the component is
    selected again.

---

#### Story: Providing a Service Template

> As a Developer (Charlie), I want to provide a Docker Compose template
> for a service within the editor, so that the system can generate a
-   valid, user-configured service definition.

**Acceptance Criteria:**

-   **Given** I am editing a component,
-   **When** I navigate to the "Docker Compose Template Editor" tab,
-   **And** I enter valid Docker Compose YAML content, using `{{ VARIABLE_ID }}`
    macros for user-configurable values,
-   **And** I click "Save All Changes",
-   **Then** the content is saved to that component's
    `docker-compose.template.yml` file.

---

#### Story: Managing Component Groups

> As a Developer (Charlie), I want to manage the component groups,
> including renaming and deleting them, so that I can keep the software
> selection list well-organized.

**Acceptance Criteria:**

-   **Given** I am in the editor and open the "Manage Groups" modal,
-   **When** I click on a group's name,
-   **Then** I should be able to edit the name and save the change.
-
-   **Given** a group "Old Group" contains at least one component,
-   **And** during my current editing session, I move all components out of
    "Old Group",
-   **When** I then open the "Manage Groups" modal,
-   **Then** the system must recognize that "Old Group" is now empty, and
    the "Delete" button for it **must be enabled**.

---

#### Story: Improving Editor Usability

> As a Developer (Charlie), I want the primary controls in the editor's
> sidebar to remain visible at all times, so that I can quickly create new
> components or search the list without having to scroll.

**Acceptance Criteria:**

-   **Given** the list of components in the sidebar is long enough to
    require scrolling,
-   **When** I scroll down the component list,
-   **Then** the "Create New Component" button and the "Search
    components..." input field **must remain fixed** at the top of the
    sidebar and always be visible.

---

#### Story: AI-Assisted Component Generation

> As a Developer (Charlie), I want to create a component by specifying a Git repository URL (from GitHub, GitLab, Gitea, Forgejo, Codeberg, Bitbucket, or self-hosted Git servers) and custom instructions, so that the metadata, compose templates, variables, and config templates are automatically generated using AI.

**Acceptance Criteria:**

- **Given** I am on the component editor page,
- **When** I click the "Create with AI" button,
- **And** I enter a valid Git repository URL and optional instructions,
- **And** I select an AI provider (Ollama, Gemini, OpenAI, HostYourAI) or provide the required API credentials,
- **And** I click "Generate Component",
- **Then** the system contacts the selected AI engine and generates the component structure.
- **And** the system automatically retrieves the public repository's `README.md` and compose configuration files across multiple standard naming variations and branches to enrich the prompt context before calling the AI engine.
- **And** the system automatically validates the generated image name on Docker Hub / OCI registries and displays any warnings or errors in the preview modal.
- **And** I can preview the generated metadata, variables, compose template, and configuration templates in a preview modal.
- **And** when I click "Accept and Create", the component is registered and saved to the filesystem.

### Epic 2: End-User - System Configuration

As Alex, I need a simple, guided web interface to select and configure the
services I want to run on my Raspberry Pi.

---

#### Story: Selecting Software

> As an End-User (Alex), I want to select which self-hosted services I
> want to install from a clear, categorized list, so that I can easily
> choose my desired software stack.

**Acceptance Criteria:**

-   **Given** I have started the configurator app,
-   **When** I am on the "Software Selection" page,
-   **Then** I can see a list of available components, grouped by category.
-   **And** I can select one or more components to install.

---

#### Story: Configuring Services

> As an End-User (Alex), I want to configure the necessary settings for my
> chosen services through a simple web form, so that I do not need to
-   edit any configuration files manually.

**Acceptance Criteria:**

-   **Given** I have selected at least one service,
-   **When** I proceed to the "Configure Services" page,
-   **Then** I see a form containing input fields for each required variable
    (e.g., `UPTIME_KUMA_PORT`).
-   **And** the descriptive text for each input field is clear and helpful.
-   **And** the input fields are pre-filled with sensible default values.

---

#### Story: Viewing the Final Summary

> As an End-User (Alex), I want to see a final summary of my configured
> services with direct links to their web interfaces, so that I can
-   easily access them after installation is complete.

**Acceptance Criteria:**

-   **Given** the installation process has completed successfully,
-   **When** I am on the "Summary" page,
-   **Then** I see a list under "Access Your Services".
-   **And** this list contains a correctly formatted URL for each service
    I selected that is known to have a web interface (e.g., Uptime Kuma).
-   **And** I can navigate back to the previous configuration step or cancel
    the overall process at any time, even after deployment has started.

---

#### Story: Receiving Actionable Feedback on System Errors

> As an End-User (Alex), if the file generation process fails due to a
> system or template error, I want to see a detailed, human-readable
> report directly in the UI, so that I can create a high-quality bug
> report without needing to search for log files.

**Acceptance Criteria:**

-   **Given** a component template has a syntax error (e.g., bad indentation).
-   **When** I click "Generate Configuration Files".
-   **Then** the process must fail, and the UI must display an error screen.
-   **And** the error screen must contain a detailed report that includes
    the name of the failing component and the raw, rendered content that
    caused the crash.

### Epic 3: Configurator - Advanced Selection Logic

As Alex, I expect the system to be smart and guide me through complex
choices, preventing me from making configuration errors like selecting
conflicting software or forgetting to install a required dependency.

---

#### Story: Automatic Dependency Resolution

> As an End-User (Alex), when I select a service, I want the system to
> automatically select any other services it depends on, so that my
> installation is guaranteed to have all its requirements met without
> me needing to be an expert.

**Acceptance Criteria:**

-   **Given** a service "Sonarr" has a defined dependency on "Prowlarr" in
    the component metadata.
-   **When** I am on the "Software Selection" page and I check the box for
    "Sonarr",
-   **Then** the checkbox for "Prowlarr" should also become checked and
    appear locked (disabled).
-   **And** a visual indicator or tooltip should inform me that Prowlarr was
    selected automatically because Sonarr requires it.
-
-   **Given** Sonarr and the auto-selected Prowlarr are both checked,
-   **When** I uncheck the box for "Sonarr",
-   **Then** the checkbox for "Prowlarr" should become unlocked (enabled)
    again, but remain checked, allowing me to decide if I still want it.

---

#### Story: Enforcing Mutually Exclusive Choices

> As an End-User (Alex), when I am presented with a choice between similar
> types of software (e.g., different dashboard applications), I want the
> system to ensure I can only select one, so that I don't install
> redundant or conflicting services.

**Acceptance Criteria:**

-   **Given** there is a component group called "Dashboards" which is
    configured to be mutually exclusive.
-   **And** this group contains two services: "Homer" and "Homarr".
-   **When** I am on the "Software Selection" page and I select "Homer",
-   **Then** "Homer" is marked as my chosen dashboard.
-
-   **Given** "Homer" is already selected,
-   **When** I then select "Homarr",
-   **Then** "Homarr" should become selected, and "Homer" should be
    automatically deselected.
-   **And** only one component from the "Dashboards" group can be selected
    at any given time.
-
-   **Given** an option from an exclusive group is currently selected
    (e.g., "Homer"),
-   **When** I click on that same option ("Homer") again,
-   **Then** it should become deselected.
-   **And** no other option in that exclusive group should be selected.
-   **And** a manually selected component must always be deselectable,
    regardless of whether its group is defined as mutually exclusive.

---

#### Story: Pre-Deployment Conflict Gatekeeper

> As an End-User (Alex), before the system attempts to install any services,
> I want it to check for configuration conflicts (ports, volumes, resources)
> on the target Pi and immediately stop the process if critical issues
> are found, so that I can resolve the problem before any changes are made
> to the remote system.

**Acceptance Criteria:**

-   **Given** I have completed service configuration and proceed to the
    deployment step.
-   **And** the client has successfully retrieved the pre-flight analysis
    from `/api/v1/system/analyze`.
-   **When** I initiate the deployment by calling `/deploy-configuration`,
-   **Then** the backend must use the provided analysis to determine if any
    of the following critical issues exist:
    *   **DANGEROUS_NATIVE_PROCESS_CONFLICT**
    *   **EXISTING_VOLUME_CONFLICT**
    *   **UNEXPECTED_DOCKER_CONFLICT**
-   **And** if any of the critical issues listed above exist, the deployment
    **must be gated and prevented from starting**.
-   **And** the backend must return a `400 Bad Request` with an array of
    `ReportError` objects (as defined in `Deployment Manager Contracts`)
    to the client.
-   **And** all other conflict types (specifically `EXPECTED_REINSTALLATION`)
    and `resource_warnings` are treated as non-blocking information or warnings,
    which do not stop the deployment.
-   **And** the client must display the details from the `ReportError`
    objects and provide an explicit path for the user to return to the
    configuration step to resolve the issue.

---

#### Story: Runtime Docker Management on Target

> As an End-User (Alex), before services are installed, I want the system to
> ensure that the target device has a modern Docker Engine and Docker Compose
> plugin, and when an older engine is detected, I want a clear error with the
> option to allow an automated upgrade.

**Acceptance Criteria:**

-   **Given** deployment is initiated to a clean Raspberry Pi OS or Debian host
    without Docker,
-   **When** the deployment starts,
-   **Then** the system installs the latest Docker Engine and Compose plugin
    and proceeds with deployment.

-   **Given** the target has an older Docker Engine than 20.10.0 and upgrade is
    not allowed,
-   **When** the deployment starts,
-   **Then** the system must stop before any compose operations and return an
    error report with type Docker:Outdated and explanatory guidance.

-   **Given** the target has an older Docker Engine and ALLOW_DOCKER_UPGRADE=true
    or GLOBAL_ALLOW_DOCKER_UPGRADE=true is provided,
-   **When** the deployment starts,
-   **Then** the system removes older Docker packages, installs the latest engine
    and Compose plugin, and proceeds to deploy.

-   **Given** the remote user is not in the docker group,
-   **When** the deployment runs,
-   **Then** the system adds the user to the docker group for future sessions and
    uses sudo for Docker commands during the current session.

-   **And** Compose Spec is used and compose files do not include a version key.

---

### Epic 4: Developer - Component Repository Synchronisation

As Charlie, I need to synchronise locally developed components with the
shared `njord-deploy-components` GitHub repository, so that tested
components are available to all users without requiring a new application
release.

---

#### Story: Fetching Remote Component Status

> As a Developer (Charlie), I want to fetch the latest component list from
> the remote repository and see the synchronisation status of each
> component, so that I know which components are up to date, modified, or
> only available in one location.

**Acceptance Criteria:**

-   **Given** I am in the Editor App and open the "Git Sync Manager" modal,
-   **When** I click "Fetch / Check Status",
-   **Then** the system downloads the latest ZIP from the remote repository
    (`njord-deploy-components`) and compares it against the local files.
-   **And** each component is labelled with one of: `Synced`, `Modified`,
    `New in Repo` (remote only), or `Local Only`.

---

#### Story: Pulling a Remote Component

> As a Developer (Charlie), I want to pull a component from the remote
> repository into my local project, so that I receive the latest
> community-maintained version.

**Acceptance Criteria:**

-   **Given** a component with status `New in Repo` or `Modified` is shown
    in the sync list,
-   **When** I click "Diff & Sync" and confirm the pull action,
-   **Then** the local `components_metadata.json` and the component's
    `component_templates/` directory are overwritten with the remote version.

---

#### Story: Uploading a Local Component to the Remote Repository

> As a Developer (Charlie), I want to push a locally tested and validated
> component to the remote repository, so that it becomes available to
> all end-users through the sync mechanism.

**Acceptance Criteria:**

-   **Given** I have write access to the remote repository (verified via a
    dry-run Git push),
-   **And** the component's `docker-compose.template.yml` contains the
    required header comments: `# status`, `# last_tested_version`,
    `# platform_notes`, `# breaking_changes`,
-   **When** I click "Upload All to Remote",
-   **Then** the system commits and pushes the local changes to the remote
    repository via SSH (with HTTPS as fallback).
-   **And** if write access is not available, the "Upload All to Remote"
    button must be disabled with an explanatory tooltip.

---

### Epic 5: Developer - Proxmox LXC Provisioning

As Charlie, I need to automatically provision a clean Debian LXC container
on a Proxmox VE host so that I can test component deployments in a
repeatable, isolated environment.

---

#### Story: Creating a Proxmox LXC Container

> As a Developer (Charlie), I want to trigger the creation of a new LXC
> container on Proxmox via the Configurator API, so that I have a
> fresh target environment for automated component testing.

**Acceptance Criteria:**

-   **Given** the Proxmox credentials (`PROXMOX_HOST`, `PROXMOX_USER`,
    `PROXMOX_TOKEN_ID`, `PROXMOX_TOKEN_SECRET`) are configured in the
    environment,
-   **When** a `POST` request is made to `/api/proxmox/create-lxc` with
    the desired container parameters,
-   **Then** the system creates a new LXC container on the specified
    Proxmox node using the Proxmox VE REST API.
-   **And** if the credentials are missing or invalid, the API must return
    a `400` or `500` error with a descriptive message.
-   **And** the created container is immediately usable as a deployment
    target by the test runner (`scripts/proxmox_test_runner.py`).

---

#### Story: Creating a Proxmox LXC Container with Custom Hostname

> As a user or developer, I want to specify a custom, descriptive hostname when creating a new LXC container, so that the target server does not just get a generic UUID.

**Acceptance Criteria:**

-   **Given** the "Create New Proxmox LXC Target" scan method is selected,
-   **When** the user fills in a custom hostname in the container configuration form and starts provisioning,
-   **Then** the backend validates/sanitizes the hostname to conform to RFC DNS standards (alphanumeric characters and hyphens only, up to 63 characters).
-   **And** the container is created on Proxmox using this custom name instead of the task ID UUID.

---

#### Story: Listing Proxmox VM Templates

> As a user or developer, I want to see a list of my existing VM templates on Proxmox, so that I can easily select one to clone and provision a new target.

**Acceptance Criteria:**

-   **Given** Proxmox credentials are configured,
-   **When** a `POST` request is made to `/api/proxmox/list-templates`,
-   **Then** the backend retrieves all QEMU VM objects from the node and filters them to return only those marked as templates.
-   **And** the templates are returned sorted by VMID and loaded into the VM template dropdown.

---

#### Story: Creating a Proxmox VM Target

> As a user or developer, I want to clone and provision a new VM from a Proxmox template with automatic SSH key injection via cloud-init, so that I can set up a new target machine easily.

**Acceptance Criteria:**

-   **Given** the "Create New Proxmox VM Target" scan method is selected,
-   **When** the user specifies a hostname, template VMID, cores, memory, storage pool, and VM username, and starts provisioning,
-   **Then** the backend queries Proxmox for the next unused VMID, clones the template (linked clone with full clone fallback), configures Cloud-Init (setting username, password, SSH public key, ip=dhcp, guest agent enabled, and cloudinit drive), and boots the VM.
-   **And** the backend polls the guest agent to retrieve the VM's dynamic IP address.
-   **And** the backend connects via SSH and automatically installs Docker and sets up the `njorddeploy_net` network.

---

#### Story: Deploying to an Existing Proxmox Target

> As a user or developer, I want to select an existing VM or LXC container from my Proxmox server, so that I can redeploy or configure services on a pre-existing machine.

**Acceptance Criteria:**

-   **Then** if the user selects a target that is currently stopped, the backend automatically starts it using `/api/proxmox/start-target` and waits until it retrieves a valid IP address.
-   **And** if the target is already running, the backend retrieves its IP address using `/api/proxmox/get-target-ip` and proceeds directly to the deployment step.

---

### Epic 3: Platform Flexibility - Container Engines & Dynamic Repositories

#### Story: Container Engine Selection (Docker vs Rootless Podman)

> As an end-user (Alex) or enterprise administrator, I want to choose whether services are deployed using standard Docker or rootless Podman, so that I can adhere to strict security policies and unprivileged container standards.

**Acceptance Criteria:**
- **Given** the Configurator app is open,
- **When** the user selects Docker or Podman from the topbar dropdown or onboarding wizard,
- **Then** the backend persists the setting (`CONTAINER_ENGINE="docker"` or `"podman"`) in `.env` and session memory.
- **And** all host provisioning commands dynamically adapt (for Podman: unprivileged port start=53, user session lingering, subuid/subgid mapping).
- **And** all Ansible deployment tasks dynamically execute using the selected engine (`docker compose` or `podman compose`).

---

#### Story: Dynamic Components Repository & Air-Gapped Mode

> As a developer or air-gapped environment administrator, I want to specify a custom components repository URL or run in offline mode, so that I can use proprietary component catalogs without network dependencies.

**Acceptance Criteria:**
- **Given** the user navigates to Settings or the Onboarding wizard,
- **When** the user inputs a custom repository URL (GitHub, GitLab, Forgejo) and branch/token,
- **Then** the user can click "Test Connection" (`/api/validate-repo`) to verify connectivity.
- **And** if set to `"none"` or `"local"`, remote synchronization is cleanly disabled, and local pre-packaged templates are used without network delays.
