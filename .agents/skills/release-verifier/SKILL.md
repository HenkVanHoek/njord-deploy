---
name: release-verifier
description: Workflows, scripts, and self-healing procedures for verifying GitHub Release builds, diagnosing build or test failures, repairing issues, and re-triggering releases in NjordDeploy.
---

# GitHub Release Verification and Self-Healing Workflow

Use this skill whenever a release has been tagged and pushed to GitHub to verify that the automated build pipeline (`release.yml`) completed successfully, confirm that release binaries/assets are published, and automatically diagnose, repair, and re-trigger the release if any build or test failure occurs.

---

## 1. Quick Verification Command

Run the automated status checking script to inspect the latest GitHub Actions workflow run and GitHub Release status:

```bash
python scripts/check_release_status.py
```

### Exit Codes:
* `0`: **SUCCESS** — Workflow completed with `conclusion: success` and release assets are published.
* `1`: **FAILURE** — The release pipeline failed (`conclusion: failure`).
* `2`: **IN PROGRESS** — The release pipeline is currently building (`status: in_progress`).

---

## 2. Full Workflow Steps

### Step 1: Monitor / Poll Release Build
Execute `python scripts/check_release_status.py`.
* If status is `in_progress`, wait 30–60 seconds and run the script again.
* If status is `success`, verify that all 3 platform assets (`NjordDeploy-Linux.zip`, `NjordDeploy-macOS.zip`, `NjordDeploy-Windows.zip`) are attached to the release.

---

### Step 2: Diagnose Failures (If Exit Code is 1)
If the build pipeline failed:

1. **Fetch Detailed Error Logs:**
   Open the workflow run URL displayed by `check_release_status.py` or fetch the workflow jobs via GitHub API:
   ```bash
   python3 -c "
   import requests
   res = requests.get('https://api.github.com/repos/HenkVanHoek/njord-deploy/actions/runs/<RUN_ID>/jobs')
   for job in res.json().get('jobs', []):
       print(job['name'], '->', job['conclusion'])
   "
   ```

2. **Categorize the Failure:**
   * **A. Pytest / Unit Test Failure:**
     * Run `pytest` locally to reproduce the exact test breakage.
     * Fix the underlying code or contract violation.
     * Re-verify locally: `pytest` and `pre-commit run --all-files`.

   * **B. PyInstaller Compilation / Spec Error:**
     * Run PyInstaller locally:
       ```bash
       pyinstaller NjordDeployInstaller.spec
       ```
     * Inspect `dist/` and `build/` logs to fix missing imports or spec file configurations.

   * **C. Missing Asset or File Name Mismatch:**
     * Check [.github/workflows/release.yml](file:///.github/workflows/release.yml) step `Package the executable`.
     * Ensure the path mapping matches the generated binary name in `dist/`.

   * **D. Pre-Commit / Linter / End-of-File Error:**
     * Run `pre-commit run --all-files` locally to fix trailing newlines, imports, or formatting.

---

### Step 3: Repair Code and Update Documentation
Once the issue is fixed locally:

1. **Update Documentation & Context:**
   ```bash
   python scripts/update_docs.py
   ```
2. **Verify Local Quality:**
   ```bash
   pre-commit run --all-files
   pytest
   ```

---

### Step 4: Re-Trigger the Release
To trigger a clean re-build of the release:

1. **Option A: Bump to a New Release Patch Version (Recommended):**
   ```bash
   bump-my-version bump patch
   python scripts/update_docs.py
   git add .
   git commit -m "fix(release): resolve build failure and re-trigger release"
   git push origin main --tags
   ```

2. **Option B: Re-tag Existing Tag (If required):**
   ```bash
   git tag -d <TAG_NAME>
   git push origin :refs/tags/<TAG_NAME>
   git tag <TAG_NAME>
   git push origin <TAG_NAME>
   ```

---

### Step 5: Final Verification
Re-run the status check script to ensure the new release pipeline finishes with clean success:

```bash
python scripts/check_release_status.py
```
