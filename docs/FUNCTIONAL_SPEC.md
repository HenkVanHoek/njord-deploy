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
    wants to run self-hosted services on a Raspberry Pi. Alex interacts
    exclusively with the **Configurator App**.
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

> As a Developer (Charlie), I want to create a component by specifying a GitHub repository URL and custom instructions, so that the metadata, compose templates, variables, and config templates are automatically generated using AI.

**Acceptance Criteria:**

- **Given** I am on the component editor page,
- **When** I click the "Create with AI" button,
- **And** I enter a valid GitHub repository URL and optional instructions,
- **And** I provide a Gemini API Key (or rely on the GEMINI_API_KEY environment variable),
- **And** I click "Generate Component",
- **Then** the system contacts the Gemini API and generates the component structure.
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
