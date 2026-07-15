# Failed and Difficult-to-Fix Components

This document tracks components that failed verification or could not be tested/fixed within 3 attempts, along with the reasons and current status.

## Skipped / Untestable Components

### `njorddeploy-service-maintenance`
*   **Date**: 2026-07-15
*   **Reason**: The component's docker-compose template (`component_templates/njorddeploy-service-maintenance/docker-compose.template.yml`) is completely empty and contains no service definitions or port mappings.
*   **Action**: Skipped for further developer inspection.
