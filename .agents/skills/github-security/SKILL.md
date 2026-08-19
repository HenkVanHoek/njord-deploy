---
name: github-security
description: Query GitHub Security Alerts (CodeQL code scanning, Dependabot vulnerable dependencies, and Secret Scanning) via GitHub API or CLI, inspect findings, and propose/apply Air-Traffic-Control grade code remediations.
---

# GitHub Security Alerts & Remediation Workflow (NjordDeploy)

Use this skill to query, inspect, and automatically remediate security vulnerabilities flagged on GitHub for the **NjordDeploy** repository. This covers **GitHub Code Scanning (CodeQL)**, **Dependabot Vulnerability Alerts**, and **Secret Scanning Alerts**.

---

## 1. Quick Fetch Command

Use the built-in retrieval tool to fetch and display open security alerts from GitHub:

```bash
# Fetch all open security alerts (Code Scanning, Dependabot, Secret Scanning)
python scripts/fetch_github_security_alerts.py

# Filter specifically for CodeQL Code Scanning alerts
python scripts/fetch_github_security_alerts.py --type code-scanning

# Filter specifically for Dependabot dependency alerts
python scripts/fetch_github_security_alerts.py --type dependabot

# Output as raw JSON for structured agent processing
python scripts/fetch_github_security_alerts.py --json
```

### Authentication & Token Requirements:
GitHub Security endpoints require an authenticated token with security permissions:
* **Environment Variable:** `export GITHUB_TOKEN="ghp_..."` or `export GH_TOKEN="ghp_..."`
* **CLI Parameter:** `python scripts/fetch_github_security_alerts.py --token <TOKEN>`
* **Required Token Permissions:**
  * Classic PAT: `security_events`, `repo`
  * Fine-grained PAT: Read permissions for *Code scanning alerts*, *Dependabot alerts*, and *Secret scanning alerts*.

---

## 2. End-to-End Security Remediation Workflow

```
 ┌─────────────────────────────────────────────────────────────┐
 │ 1. Query GitHub Security Alerts via fetch_github_security_alerts.py │
 └──────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ 2. Inspect File Location, CWE/CVE Rule, and Code Context    │
 └──────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ 3. Apply ATC-Grade Remediation Pattern (SSRF, Path, Deps)   │
 └──────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ 4. Verify Fix Locally (Bandit, Flake8, Mypy, Pytest)        │
 └──────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ 5. Commit & Push Fix to Trigger CodeQL / CI Verification    │
 └─────────────────────────────────────────────────────────────┘
```

---

## 3. Remediation Patterns Catalog

### A. CodeQL Code Scanning Alerts (`code-scanning`)

#### 1. Server-Side Request Forgery (`py/full-ssrf` / `py/partial-ssrf`)
* **Hazard:** User-supplied URLs passed directly to `requests.get()` / `requests.post()` allowing internal network scanning or metadata probing.
* **Remediation:**
  Validate and sanitize the scheme, host, and path using `validate_and_sanitize_url` and reconstruct via `urllib.parse`:
  ```python
  import urllib.parse
  from utils.security_utils import validate_and_sanitize_url

  # Validate base URL
  is_valid, clean_url, error = validate_and_sanitize_url(
      user_input_url,
      default_url="http://localhost:11434/v1"
  )
  if not is_valid or not clean_url:
      return jsonify({"error": f"Invalid URL: {error}"}), 400

  # Safely reconstruct endpoint
  parsed = urllib.parse.urlsplit(clean_url)
  target_url = urllib.parse.urlunsplit(
      (parsed.scheme, parsed.netloc, f"{parsed.path.rstrip('/')}/api/tags", "", "")
  )
  response = requests.get(target_url, timeout=5)
  ```

#### 2. Path Traversal / Injection (`py/path-injection`)
* **Hazard:** Unsanitized file paths allowing access outside intended directories (`../../etc/passwd`).
* **Remediation:**
  Resolve paths to canonical absolute form and verify directory containment:
  ```python
  from pathlib import Path

  base_dir = Path("/safe/base/directory").resolve()
  target_file = (base_dir / user_supplied_filename).resolve()

  # Ensure target is strictly inside base directory
  if not target_file.is_relative_to(base_dir):
      raise ValueError("Access outside permitted directory is forbidden.")
  ```

#### 3. Command Injection (`py/command-injection`)
* **Hazard:** Interpolating unescaped user strings into shell commands (`shell=True`).
* **Remediation:**
  Use structured argument lists with `subprocess.run(..., shell=False)`:
  ```python
  import subprocess  # nosec B404

  # Safe: structured argument list without shell execution
  cmd = ["docker", "compose", "-f", compose_file, "up", "-d"]
  result = subprocess.run(  # nosec B603
      cmd,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      text=True,
      check=True,
  )
  ```

#### 4. Missing Request Timeout (Bandit `B113` / `py/requests-missing-timeout`)
* **Hazard:** Requests without timeouts can hang indefinitely, causing resource exhaustion.
* **Remediation:**
  Always specify explicit `timeout` in seconds on all `requests.*` calls:
  ```python
  resp = requests.get("https://api.github.com", timeout=10)
  ```

#### 5. Unsafe YAML Deserialization (`py/unsafe-deserialization`)
* **Hazard:** `yaml.load()` can instantiate arbitrary Python objects leading to remote code execution.
* **Remediation:**
  Always use `yaml.safe_load()`:
  ```python
  import yaml

  data = yaml.safe_load(yaml_content)
  ```

---

### B. Dependabot Dependency Alerts (`dependabot`)

1. **Locate Advisory:**
   Inspect the vulnerable package name, current version range, and minimum patched version reported by Dependabot.
2. **Update Dependency Definition:**
   In [pyproject.toml](file:///home/hvhoek/PycharmProjects/njord-deploy/pyproject.toml):
   ```toml
   dependencies = [
       "flask>=3.0.0",
       "requests>=2.32.0",
       "jinja2>=3.1.4",
       ...
   ]
   ```
3. **Verify Compatibility:**
   Run full test suite:
   ```bash
   .venv/bin/pytest
   ```

---

### C. Secret Scanning Alerts (`secret-scanning`)

1. **Locate Secret:**
   Identify the file and line number containing hardcoded credentials or API keys.
2. **Remove & Externalize:**
   Replace the hardcoded secret with environment variable lookup (`os.environ.get(...)`) or secure runtime configuration.
3. **Verify Locally with Secret Guard:**
   ```bash
   python scripts/check_secrets.py <modified_files>
   ```
4. **Revoke Compromised Credentials:**
   Notify user to immediately revoke/rotate the exposed token in GitHub or provider dashboard.

---

## 4. Local Verification & Quality Gate

Before proposing or committing any security fix, execute all verification checks:

```bash
# 1. Run Bandit Security Static Analyzer
.venv/bin/pre-commit run bandit --all-files

# 2. Run Pre-Commit Checks (Flake8, Black, Mypy, Secret Guard)
.venv/bin/pre-commit run --all-files

# 3. Run Full All-in-One Quality Check
./scripts/check_code_quality.sh

# 4. Run Pytest Suite
.venv/bin/pytest
```
