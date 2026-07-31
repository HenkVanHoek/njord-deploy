# NjordDeploy: Data Contracts

**Version:** 1.9
**Status:** Active

This document is the Single Source of Truth (SST) for the schema of all
core data files used within the NjordDeploy project. It serves as a
formal specification to ensure that the **configurator_app**, the
**editor_app**, and all manager classes operate on a consistent and
well-defined data structure.

All data files must adhere to the schemas defined herein.

---

## `template-config/variables.json`

This file defines the user-configurable variables for a component. It is a JSON object with a single top-level key `"variables"`, which contains an array of variable objects:

```json
{
  "variables": [
    {
      "id": "VARIABLE_ID",
      ...
    }
  ]
}
```

Each variable object in the array has the following properties:

| Property      | Type     | Required                                    | Description                                                                                                                                                                                                                                                                                                                                              |
|---------------|----------|---------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `id`          | `string` | Yes                                         | The unique identifier for the variable. This is used as the key in the `.env` file and for template substitution (e.g., `{{ MY_VARIABLE_ID }}`). By convention, this should be uppercase.                                                                                                                                                                |
| `label`       | `string` | No                                          | A short, human-readable name for the UI. If not provided, the UI will derive a title from the `id`.                                                                                                                                                                                                                                                      |
| `description` | `string` | Yes                                         | A detailed, user-facing explanation of what the variable is for, including any security implications, required formats, or default behaviors. This is a critical field for ensuring correct configuration.                                                                                                                                               |
| `type`        | `string` | Yes                                         | The data type of the input, which controls the UI rendering. Valid options are: `text`, `password`, `select`, `choice`, `port`, `string`. Note: Any type other than `password` and `select` is rendered as a standard `text` input in the configurator UI.                                                                                             |
| `default`     | `string` | No                                          | The default value to pre-populate in the UI input field.                                                                                                                                                                                                                                                                                                 |
| `options`     | `array`  | **Yes** (if `type` is `choice` or `select`) | An array of strings used to populate a `<select>` dropdown.                                                                                                                                                                                                                                                                                              |
| `required`    | `string` | No                                          | Determines when the field is mandatory. Valid options are `always` or `clean-install`.                                                                                                                                                                                                                                                                   |
| `source`      | `string` | No                                          | **(New)** Specifies the source of the variable's value. If omitted, the value is expected from user input. The only valid option is: <ul><li>`dotenv`: Instructs the UI to render a disabled field, indicating the value is managed securely on the backend via the project's `.env` file. This prevents secrets from being entered in the UI.</li></ul> |
| `depends_on`  | `object` | No                                          | **(New)** An object that defines a conditional dependency for displaying this variable in the UI. The object must contain: `variable` (the `id` of the controlling variable) and `value` (the value the controlling variable must have for this field to be visible).                                                                                    |


---

## Component Manager Contracts

### Component Metadata Structure (`config/components_metadata.json` element)

This contract defines the structure for a single component element within the
`"components"` dictionary of `config/components_metadata.json`.

| Property                      | Type                     | Required | Description                                                                                                                              |
|-------------------------------|--------------------------|----------|------------------------------------------------------------------------------------------------------------------------------------------|
| `name`                        | `string`                 | Yes      | A human-readable name for the component.                                                                                                 |
| `group`                       | `string`                 | Yes      | The category ID this component belongs to (e.g., `network_management`, `media_servers`).                                                 |
| `description`                 | `string`                 | Yes      | A detailed description of the component's function for the UI.                                                                           |
| `ports`                       | `array<string>`          | No       | A list of port mappings used for live conflict checking (e.g., `80:80/tcp`, `8080`).                                                     |
| `has_ui`                      | `boolean`                | No       | If true, the component has a web interface and the backend should attempt to generate a service link.                                    |
| `ui_port_variable`            | `string`                 | No       | The ID of the variable containing the component's external UI host port. Preferred over `ui_port`.                                       |
| `ui_port`                     | `integer`                | No       | The default or fixed external UI host port, used if `ui_port_variable` is absent.                                                        |
| `protocol`                    | `string`                 | No       | The protocol for the UI link (`http` or `https`). Defaults to `http`.                                                                    |
| `has_configuration`           | `boolean`                | Yes      | If true, a `template-config/variables.json` file is expected.                                                                            |
| `docker_service_name`         | `string`                 | No       | The primary service name in the docker-compose file. Used to distinguish main containers from init containers. Defaults to component ID. |
| `depends_on`                  | `array<string>`          | No       | A list of component IDs this component depends on for ordering.                                                                          |
| `conflicts_with`              | `array<string>`          | No       | **(New)** A list of component IDs that this component conflicts with.                                                                    |
| `has_traefik_support`         | `boolean`                | No       | If true, the component requires Traefik setup and has a unique `traefik_internal_port`.                                                  |
| `traefik_internal_port`       | `integer`                | No       | The internal port used for Traefik routing (e.g., `80`). Required if `has_traefik_support` is true.                                      |
| `other_files`                 | `array<OtherFileConfig>` | No       | A list of configuration files to be generated, other than the main Docker Compose file. (`OtherFileConfig` schema defined below).        |
| `config_templates`            | `object`                 | No       | A dictionary mapping a template filename (string) to a destination path (string). Used for rendering additional configuration files from `template-config/` into the deployment package. |
| `package_id`                  | `string`                 | No       | The ID of the Package this component belongs to. Defaults to `"general-stack"` when not set.                                             |
| `component_version`           | `string`                 | No       | **(New)** The specific version of the component (e.g., `"latest"` or a specific release tag).                                            |
| `project_url`                 | `string`                 | No       | **(New)** The URL of the official homepage or codebase repository for the service.                                                       |
| `resource_profile`            | `object`                 | No       | **(New)** Resource requirements profile, specifying keys like `cpu`, `ram`, `storage_type`, `recommended_cores`, `recommended_ram_mb`, `recommended_storage_gb`. |
| `tags`                        | `array<string>`          | No       | **(New)** A list of searchable/filterable keyword tags associated with the component.                                                    |
| `traefik_host_variable`       | `string`                 | No       | **(New)** Specifies a custom variable ID that holds the hostname routing for Traefik.                                                    |
| `post_install_restart_option` | `string`                 | No       | **(New)** Custom configuration instruction specifying container restart options post-deployment.                                         |

### Component Details Output Contract (`get_all_components` / `get_component_details` return)

This contract defines the enriched structure returned by `ComponentManager.get_all_components` and `ComponentManager.get_component_details`. This is the final data model consumed by the frontend to render the component selection and configuration UI.

| Property                            | Type            | Required | Description                                                                                                                        |
|-------------------------------------|-----------------|----------|------------------------------------------------------------------------------------------------------------------------------------|
| `id`                                | `string`        | Yes      | The unique, machine-readable ID of the component (the dictionary key from `components_metadata.json`).                             |
| `required_variables`                | `array<object>` | Yes      | **(Merged)** The content of the component's `template-config/variables.json` file, detailing all user-facing configuration fields. |
| `name`                              | `string`        | Yes      | The human-readable name of the component (inherited from metadata).                                                                |
| `package_id`                        | `string`        | Yes      | The Package ID this component belongs to. Defaults to `"general-stack"` if absent in metadata.                                    |
| `tags`                              | `array<string>` | Yes      | A list of searchable tags. Defaults to `[]` if absent in metadata.                                                                |
| `resource_profile`                  | `object`        | Yes      | AI-generated resource estimate. Shape: `{"cpu": string, "ram": string, "storage_type": string}`. Defaults to `{"cpu": "medium", "ram": "medium", "storage_type": "persistent"}`. |
| **(All other metadata properties)** | *Varies*        | *Varies* | All other properties from the Component Metadata Structure are included.                                                           |

---

## Setup Manager Contracts

### Deployment Package Preparation Return Contract

This defines the return signature of `SetupManager.prepare_deployment_package`.

| Property | Type                                             | Required | Description                                                                                                                                                                                                    |
|----------|--------------------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| *Return* | `Tuple[bool, Optional[List[SetupManagerError]]]` | Yes      | A tuple where the first element is `True` on success and `False` on failure. On success, the second element is `None`. On failure, it is a list containing a single `SetupManagerError` object (schema below). |

### Setup Manager Error Sub-Contract (`SetupManagerError`)

This is the structured error returned by `prepare_deployment_package` on failure.

| Property  | Type     | Required | Description                                                                                                                                                                                      |
|-----------|----------|----------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `type`    | `string` | Yes      | A fixed string, always `"GenerationError"`.                                                                                                                                                      |
| `summary` | `string` | Yes      | A short, user-facing summary, always `"File generation failed."`.                                                                                                                                |
| `details` | `string` | Yes      | A detailed, multi-line error message, often including the name of the failing component and the raw, rendered content that caused the failure. This is the primary content for UI error reports. |

### Other File Generation Sub-Contract (`OtherFileConfig`)

This contract defines the structure of an element within the `other_files` list of a component's metadata, used to generate auxiliary configuration files.

| Property      | Type     | Required | Description                                                                                                  |
|---------------|----------|----------|--------------------------------------------------------------------------------------------------------------|
| `template`    | `string` | Yes      | The name of the Jinja2 template file, relative to the component's template directory.                        |
| `destination` | `string` | Yes      | The relative path and file name for the rendered output within the main deployment package output directory. |

---

## `components_metadata.json` — Top-Level Structure

The file `config/components_metadata.json` is the Single Source of Truth for
all component definitions. It contains four top-level keys:

| Top-Level Key   | Type     | Description                                                                                     |
|-----------------|----------|-------------------------------------------------------------------------------------------------|
| `components`    | `object` | Dictionary mapping a **Component ID** (`string`) to a Component Metadata object (schema above). |
| `packages`      | `object` | Dictionary mapping a **Package ID** (`string`) to a Package object (schema below).             |
| `_njorddeploy`  | `object` | Internal application metadata used by the Editor App (schema below).                           |
| `groups`        | `object` | *(Legacy/optional)* Dictionary mapping a **Group ID** to group display metadata.               |

### Package Object Schema (`packages` dictionary value)

A Package is a curated bundle of related components displayed together in the
Editor App. Managed via `ComponentManager.create_package` /
`update_package_metadata` / `delete_package`.

| Property       | Type     | Required | Description                                                                                  |
|----------------|----------|----------|----------------------------------------------------------------------------------------------|
| `name`         | `string` | Yes      | The human-readable display name for the package (e.g., `"Home Automation Stack"`).          |
| `description`  | `string` | No       | An optional description of the package's purpose.                                           |
| `network_type` | `string` | No       | The Docker network mode for the stack. Defaults to `"bridge"`.                              |

### `_njorddeploy` Internal Metadata Schema

This object stores application-level configuration that drives the Editor UI.
It is managed by `ComponentManager` methods and must not be edited manually.

| Property           | Type            | Required | Description                                                                                                                                              |
|--------------------|-----------------|----------|----------------------------------------------------------------------------------------------------------------------------------------------------------|
| `group_order`      | `array<string>` | No       | Ordered list of Group IDs controlling the display order of groups in the UI.                                                                             |
| `components_order` | `array<string>` | No       | Ordered list of Component IDs controlling the master sort order of the component list.                                                                   |
| `group_rules`      | `object`        | No       | Dictionary mapping a **Group ID** to a rule object. Currently supports `{"exclusive": true}` to enforce mutual exclusivity within the group.            |
| `default_group`    | `string`        | No       | The Group ID assigned to newly created components by default.                                                                                            |
| `global_variables` | `array<string>` | No       | **(New)** List of variable IDs that are loaded globally/system-wide rather than component-specific.                                                      |

---

## Deployment Manager Contracts

### Deployment Task Dictionary Structure

The main task dictionary is returned by `/task-status/<task_id>` and contains all state, log, and result data.

| Property        | Type                 | Required | Description                                                                                                                                    |
|-----------------|----------------------|----------|------------------------------------------------------------------------------------------------------------------------------------------------|
| `status`        | `string`             | Yes      | The current state of the task. Valid values include: `running`, `failed`, `completed`.                                                         |
| `logs`          | `array<string>`      | Yes      | A chronologically ordered list of raw log messages from the deployment process (for real-time console display).                                |
| `errors`        | `array<ReportError>` | Yes      | A list of structured error objects (`ReportError` schema defined below) generated during pre-flight or runtime. This list is empty on success. |
| `service_links` | `array<ServiceLink>` | No       | A list of web UI links (`ServiceLink` schema defined below) for successfully deployed services. Only present on a `completed` status.          |

### Structured Error Contract (`ReportError`)

This is the canonical structure for all validation and runtime errors reported
by the `DeploymentManager`.

| Property       | Type     | Required | Description                                                                                                                                                                                                                         |
|----------------|----------|----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `type`         | `string` | Yes      | A standardized, machine-readable category for the error. Format is `Category:Subtype` (e.g., `Validation:DuplicatePort`, `SSH:Connect`, `Deployment:Runtime`). This allows the front end to apply specific UI styling or help text. |
| `summary`      | `string` | Yes      | A short, user-facing description of the problem (e.g., "Host port conflict detected.").                                                                                                                                             |
| `details`      | `string` | Yes      | A detailed, technical explanation of the issue, including command output or conflicting values (e.g., "Ports 80 are already in use by other running Docker containers..."). This is for developer-level inspection.                 |
| `component_id` | `string` | Yes      | The unique ID of the component that triggered the error (e.g., `pi-hole`). Defaults to `N/A` for global or device-level errors (e.g., SSH connection failure).                                                                      |
| `timestamp`    | `string` | Yes      | The exact time the error was recorded, in `YYYY-MM-DD HH:MM:SS` format.                                                                                                                                                             |

### Target Device Contract (`managed_devices` list element)

This structure defines a single device object expected in the `managed_devices`
list passed to `start_deployment` (and used in various request bodies).

| Property   | Type     | Required | Description                                                                                 |
|------------|----------|----------|---------------------------------------------------------------------------------------------|
| `ip`       | `string` | Yes      | The IP address or hostname of the target device.                                            |
| `username` | `string` | Yes      | The SSH username to connect with (e.g., `pi`).                                              |
| `password` | `string` | Yes      | The SSH password for the connection.                                                        |

### Service Link Contract (`ServiceLink`)

This structure defines the objects within the `service_links` array.

| Property | Type     | Required | Description                                                                          |
|----------|----------|----------|--------------------------------------------------------------------------------------|
| `name`   | `string` | Yes      | The human-readable name of the service (e.g., "Traefik Proxy").                      |
| `url`    | `string` | Yes      | The full, constructed URL to access the service (e.g., `http://192.168.1.100:8080`). |

### SSH Manager I/O Contracts

The return signatures for the SSH utility methods:

#### `connect()` Return

| Type                  | Description                                                                               |
|-----------------------|-------------------------------------------------------------------------------------------|
| `Tuple<bool, string>` | `(success_status, message)` where `message` is a connection error description on failure. |

#### `execute_command()` Return

| Type                 | Description                                                                                                                                      |
|----------------------|--------------------------------------------------------------------------------------------------------------------------------------------------|
| `Tuple<int, string>` | `(exit_code, full_stdout_content)` where `exit_code` is the remote command exit status and `full_stdout_content` is the command standard output. |

#### `upload_content()` Return

| Type                  | Description                                                                     |
|-----------------------|---------------------------------------------------------------------------------|
| `Tuple<bool, string>` | `(success_status, message)` where `message` is an error description on failure. |

---

## Configurator Application Contracts (API Payloads)

### System Details Contract (Response from `/get-device-details`)

This is the simplified device resource summary retrieved for the UI.

| Property | Type            | Required | Description                                            |
|----------|-----------------|----------|--------------------------------------------------------|
| `model`  | `string`        | No       | The device model (e.g., "Raspberry Pi 4 Model B").     |
| `serial` | `string`        | No       | The device serial number.                              |
| `ram`    | `string`        | Yes      | The total RAM, formatted with units (e.g., "4096 MB"). |
| `disks`  | `array<object>` | Yes      | A list of disk information objects.                    |

**Disk Object Sub-Contract**

| Property     | Type     | Required | Description                                  |
|--------------|----------|----------|----------------------------------------------|
| `mounted_on` | `string` | Yes      | The mount point (e.g., `/`).                 |
| `size`       | `string` | No       | Total disk size, formatted with units.       |
| `pcent`      | `string` | No       | Disk utilization percentage (e.g., `45.2%`). |

### Software Groups Contract (Response from `/get-software-groups`)

This defines the structure used to categorize and display selectable components.

| Property | Type     | Required | Description                                                                                       |
|----------|----------|----------|---------------------------------------------------------------------------------------------------|
| `groups` | `object` | Yes      | A dictionary mapping a **Group Display Name** (string) to an array of **Component IDs** (string). |

### Required Variables Contract (Response from `/get-required-variables`)

This is the component-level view of variables for the configuration step.

| Property     | Type     | Required | Description                                                           |
|--------------|----------|----------|-----------------------------------------------------------------------|
| `components` | `object` | Yes      | A dictionary mapping a **Component ID** (string) to a details object. |

**Component Details Sub-Contract**

| Property    | Type            | Required | Description                                                      |
|-------------|-----------------|----------|------------------------------------------------------------------|
| `name`      | `string`        | Yes      | The component's human-readable name.                             |
| `variables` | `array<object>` | Yes      | The `template-config/variables.json` contract (already defined). |

### System Analyze Conflict Contract (Element of `external_conflicts.ports` from `/api/v1/system/analyze`)

This structure describes a conflict on a host port.

| Property              | Type      | Required | Description                                                                                  |
|-----------------------|-----------|----------|----------------------------------------------------------------------------------------------|
| `port`                | `integer` | Yes      | The host port in conflict.                                                                   |
| `conflict_type`       | `string`  | Yes      | Category of conflict (e.g., `DANGEROUS_NATIVE_PROCESS_CONFLICT`, `EXPECTED_REINSTALLATION`). |
| `conflicting_service` | `string`  | Yes      | Name of the service currently using the port.                                                |
| `proposed_service`    | `string`  | Yes      | Name of the service that wants to use the port.                                              |

### System Analyze Conflict Contract (Element of `external_conflicts.volumes` from `/api/v1/system/analyze`)

This structure describes a conflict on a host volume/path.

| Property           | Type     | Required | Description                                        |
|--------------------|----------|----------|----------------------------------------------------|
| `volume_path`      | `string` | Yes      | The host path in conflict (e.g., `/mnt/data`).     |
| `conflict_type`    | `string` | Yes      | Category of conflict (`EXISTING_VOLUME_CONFLICT`). |
| `proposed_service` | `string` | Yes      | Name of the service that wants to use the volume.  |

### System Analyze Warning Contract (Element of `resource_warnings` from `/api/v1/system/analyze`)

This structure describes a general resource warning.

| Property   | Type     | Required | Description                                                                                 |
|------------|----------|----------|---------------------------------------------------------------------------------------------|
| `type`     | `string` | Yes      | The resource type (e.g., `RAM`).                                                            |
| `message`  | `string` | Yes      | The human-readable warning message.                                                         |

### Deployment Request Contract (Request to `/deploy-configuration`)

This is the final payload sent to initiate the deployment.

| Property                | Type                            | Required | Description                                                                          |
|-------------------------|---------------------------------|----------|--------------------------------------------------------------------------------------|
| `output_path`           | `string`                        | Yes      | The local file system path where configuration artifacts were generated.             |
| `devices`               | `array<Target Device Contract>` | Yes      | The list of target devices.                                                          |
| `components_to_clean`   | `array<string>`                 | No       | List of component IDs whose containers should be stopped and removed pre-deployment. |
| `components_to_restart` | `array<string>`                 | No       | List of component IDs whose containers should be gracefully restarted (TBD).         |

---

## `docker-compose.template.yml` — Required Header Contract

Every `docker-compose.template.yml` file in `component_templates/` must begin
with the following four comment lines before any YAML content. This header is
validated by `SyncManager.validate_metadata_header` as a **gating condition**
before a component can be uploaded to the remote repository.

```yaml
# status: <untested|tested|stable|deprecated>
# last_tested_version: <version string or "none">
# platform_notes: <free text or "none">
# breaking_changes: <free text or "none">
```

| Header Field           | Required | Description                                                                                          |
|------------------------|----------|------------------------------------------------------------------------------------------------------|
| `status`               | Yes      | The test status of the component. Recommended values: `untested`, `tested`, `stable`, `deprecated`. |
| `last_tested_version`  | Yes      | The Docker image version last successfully tested (e.g., `"2.3.1"` or `"none"`).                    |
| `platform_notes`       | Yes      | Notes on platform compatibility (e.g., `"ARM64 only"` or `"none"`).                                 |
| `breaking_changes`     | Yes      | Description of any breaking changes relative to the previous version, or `"none"`.                  |
