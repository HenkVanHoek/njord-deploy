---
name: design-system-sync
description: Operations for modifying UI styles in njorddeploy-design-system and synchronizing them to the NjordDeploy app.
---

# UI Styles & Design System Synchronization

Use this skill when the user asks to modify UI styles, CSS, or make design system changes.

## Important Guidelines:
1. **NEVER modify** `njorddeploy-style.css` directly in the configurator or editor app of `NjordDeploy`.
2. All style modifications must be made in the `njorddeploy-design-system` repository.
3. After modifying styles in `njorddeploy-design-system`, you must run the synchronization script to sync the changes.

## Synchronization Workflow:
1. Navigate to the `NjordDeploy` project.
2. Run the script using the following command:
   ```bash
   python scripts/fetch_assets.py
   ```
3. Verify that the files in `NjordDeploy/src/configurator_app/static/css/` are updated correctly.
4. Commit the changes in both repositories if needed.
