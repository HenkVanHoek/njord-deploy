---
name: github-release
description: Workflows for publishing releases, bumping versions, and tagging code in NjordDeploy
---

# GitHub Release and Version Bumping Workflow

This skill guides the agent in bumping the version of NjordDeploy, tagging the code, and triggering the GitHub Release Pipeline.

## Tools & Commands

We use `bump-my-version` to manage versions and tags.

### 1. Check current version
```bash
bump-my-version show current_version
```

### 2. Bump version and tag code
Choose the appropriate bump type depending on the release changes:
* **Patch release** (bug fixes, small additions):
  ```bash
  bump-my-version bump patch
  ```
* **Minor release** (new features, major changes):
  ```bash
  bump-my-version bump minor
  ```
* **Major release** (breaking changes, redesign):
  ```bash
  bump-my-version bump major
  ```

*Note: Running `bump-my-version` will automatically modify version strings in `pyproject.toml` and `README.md`, perform a Git commit with a standardized release message, and create a local Git tag starting with `v` (e.g. `v0.4.47-Alpha`).*

### 3. Push release to GitHub
To trigger the automated build pipeline (`release.yml`), push the commit and the tags to the remote repository:
```bash
git push origin main --tags
```

## GitHub Action Pipeline
Once pushed, the GitHub Actions runner will trigger `release.yml` and:
1. Run tests across Linux, macOS, and Windows.
2. Package the app using PyInstaller.
3. Automatically publish a new release under GitHub Releases.
