---
name: code-security
description: Guidelines, security rules, SSRF prevention, input validation, and remediation workflows for GitHub CodeQL and Bandit security alerts in NjordDeploy.
---

# Code Security & Vulnerability Remediation (NjordDeploy)

Use this skill to identify, prevent, and remediate security vulnerabilities in NjordDeploy, specifically focusing on GitHub CodeQL alerts (such as SSRF `py/full-ssrf`), Bandit static analysis findings, and input validation across Flask routes and backend managers.

---

## 1. Core Security Principles (Air Traffic Control Grade)

1. **Never Trust User Input**: Any parameter from `request.get_json()`, `request.args`, `request.form`, or headers must be strictly validated and type-narrowed before use.
2. **Defend Against SSRF (Server-Side Request Forgery)**: Outgoing HTTP requests (`requests.get`, `requests.post`, etc.) must never consume unvalidated or raw user-supplied URLs.
3. **Mandatory Timeouts**: All HTTP requests must specify an explicit `timeout` parameter (Bandit `B113`).
4. **Safe File and Path Handling**: Prevent directory traversal by normalizing and validating paths with `pathlib.Path.resolve()` and containment checks.
5. **No Dangerous Deserialization / Execution**: Always use `yaml.safe_load()`, never execute raw shell strings with `shell=True`, and avoid `eval`/`exec`.

---

## 2. SSRF Prevention & Safe URL Handling (`py/full-ssrf`)

### The Hazard:
When an endpoint accepts a user-provided URL (e.g. `base_url` or `repo_url`) and performs a server-side request (via `requests.get()` or `requests.post()`), attackers could probe internal network services, access cloud metadata endpoints, or trigger arbitrary network protocols (`file://`, `gopher://`).

### Mandatory Safe URL Validation Pattern:
Whenever an outgoing request URL is derived from user input, validate and reconstruct it through a centralized validator:

```python
import urllib.parse
from typing import Optional, Tuple

ALLOWED_SCHEMES = {"http", "https"}


def validate_and_sanitize_url(
    raw_url: Optional[str],
    allowed_schemes: set[str] = ALLOWED_SCHEMES,
    default_url: Optional[str] = None,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validates and sanitizes a URL to prevent SSRF and injection.

    Returns:
        (is_valid, sanitized_url, error_message)
    """
    url_to_check = (raw_url or default_url or "").strip()
    if not url_to_check:
        return False, None, "URL cannot be empty."

    try:
        parsed = urllib.parse.urlsplit(url_to_check)
    except Exception as e:
        return False, None, f"Malformed URL: {e}"

    # 1. Validate Scheme
    if not parsed.scheme or parsed.scheme.lower() not in allowed_schemes:
        return (
            False,
            None,
            f"Invalid URL scheme '{parsed.scheme}'. Only {allowed_schemes} are allowed.",
        )

    # 2. Validate Hostname / Netloc
    if not parsed.netloc or not parsed.hostname:
        return False, None, "URL must contain a valid hostname."

    # 3. Clean and reconstruct normalized URL
    # Rebuilding from parsed parts removes CRLF injection and scheme bypasses
    clean_url = urllib.parse.urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc,
            parsed.path,
            parsed.query,
            "",  # Strip fragment
        )
    )
    return True, clean_url, None
```

### Safe Target URL Construction (e.g. Ollama API / Service Endpoints):
Never perform naive string replacements like `url.replace("/v1", "/api/tags")` on unvalidated strings. Instead:
1. Validate the base URL first using `validate_and_sanitize_url`.
2. Construct the target path cleanly:
```python
is_valid, clean_base, err = validate_and_sanitize_url(
    base_url, default_url="http://localhost:11434/v1"
)
if not is_valid or not clean_base:
    return jsonify({"error": f"Invalid URL: {err}"}), 400

# Strip trailing /v1 or / and build target path
parsed = urllib.parse.urlsplit(clean_base)
base_path = parsed.path.rstrip("/")
if base_path.endswith("/v1"):
    base_path = base_path[:-3]

target_path = f"{base_path}/api/tags"
target_url = urllib.parse.urlunsplit(
    (parsed.scheme, parsed.netloc, target_path, "", "")
)

resp = requests.get(target_url, timeout=3)
```

---

## 3. CodeQL Alert Remediation Reference

| Alert Rule ID | Description | Remediation Strategy |
| :--- | :--- | :--- |
| `py/full-ssrf` | Full server-side request forgery | Validate scheme (`http`/`https`), validate `netloc`/`hostname`, and reconstruct URL via `urllib.parse.urlsplit` / `urlunsplit`. |
| `py/path-injection` | Relative path traversal | Resolve path with `Path(p).resolve()`, verify `resolved_path.is_relative_to(base_dir)` or `os.path.commonpath`. |
| `py/command-injection` | Command injection | Use `subprocess.Popen(cmd_list, shell=False)` with argument lists, never interpolate strings into shell commands. |
| `py/unsafe-deserialization` | Unsafe YAML/pickle loading | Always use `yaml.safe_load(content)` and avoid `pickle.loads()`. |
| `B113` (Bandit) | Requests call without timeout | Always supply `timeout=3` (or appropriate seconds) in all `requests.*` calls. |
| `PII / IP Leak` (Check Secrets) | Leaked private IPs or personal emails | Anonymize with placeholders (`<server-ip>`, `192.168.1.100`, `testuser@example.com`). |

---

## 4. Secret Leaks, PII & Infrastructure IP Sanitization Guard

All documentation, sample configs, comments, and public files must be strictly sanitized before committing or pushing to GitHub:

1. **Private Infrastructure & Production IPs**:
   - Never commit operational/production IPs (e.g. `192.168.178.x`, production VPS IPs) into public documentation (`docs/`, `README.md`).
   - Use standard RFC-safe placeholders: `<server-ip>`, `192.168.1.100`, `10.0.0.1`, or `127.0.0.1`.
2. **Personal Identifiable Information (PII) & Emails**:
   - Never hardcode personal corporate domains or personal emails (e.g. `@almereautomatisering.nl`).
   - Always use standard RFC 2606 test domains: `admin@example.com`, `testuser@example.com`, or `<email>`.
3. **Automated Enforcement**:
   - Handled automatically via `python3 scripts/check_secrets.py` within `pre-commit run --all-files`.

---

## 5. Verification Workflow

When addressing security alerts, creating new endpoints, or updating documentation:

### Step 1: Run Pre-Commit Security & PII Checks
```bash
pre-commit run --all-files
```

### Step 2: Run Static Security Analysis (Bandit)
```bash
pre-commit run bandit --all-files
```

### Step 3: Run Security & Unit Tests
```bash
pytest tests/test_security_utils.py tests/editor_app/test_editor_app_api.py
```

### Step 4: Verify with PyCharm Diagnostics
Use `ide_get_diagnostics` to confirm 0 type errors and inspections on the modified files.
