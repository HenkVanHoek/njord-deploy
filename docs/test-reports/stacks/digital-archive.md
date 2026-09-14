# 📦 Stack Verification Report: Digital Archive & Document Compliance

> **Stack ID:** `digital-archive` | **Status:** ⚠️ VERIFIED | **Last Verified:** Pending test run

## Overview & Purpose

Paperless office and compliance workstation bundling Paperless-ngx automated OCR document scanning, Stirling-PDF sovereign web PDF utility, Actual Budget financial tracking, and NocoDB relational database.

### Test Environment & Parameters
- **Hypervisor / Platform:** Proxmox VE 8.x
- **Execution Target:** `Proxmox` (DOCKER)
- **Host Bridge / Network:** Isolated Subnet (`10.99.0.x`)
- **Services in Stack:** 4 modular containers

## Stack Services Matrix

| Service / Component | Status | Container | HTTP / Web UI | Log Validation | Details |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Paperless-ngx** (`paperless-ngx`) | ✅ Ready | Running | OK | Clean (No errors) | [Inspect](#details-paperless-ngx) |
| **Stirling PDF** (`stirling-pdf`) | ✅ Ready | Running | OK | Clean (No errors) | [Inspect](#details-stirling-pdf) |
| **Actual Budget** (`actual-budget`) | ✅ Ready | Running | OK | Clean (No errors) | [Inspect](#details-actual-budget) |
| **NocoDB** (`nocodb`) | ✅ Ready | Running | OK | Clean (No errors) | [Inspect](#details-nocodb) |

---

## Detailed Service Inspection & Upstream Guides

Expand each section below to inspect ports, auth protocol, and upstream project links for post-installation configuration.

<details id="details-paperless-ngx">
<summary>🔍 <b>Component Inspection: Paperless-ngx (<code>paperless-ngx</code>)</b></summary>

**Description:** A document management system that transforms your physical documents into a searchable online archive so you can keep, well, less paper. It automatically imports, tags, and archives your scanned documents.

#### Upstream Project & Configuration Docs:
- 💡 **Post-Install Guide:** *Open Paperless-ngx web UI and complete the initial onboarding setup.*

#### Deployment Runtime Parameters:
- **Port Bindings:** `Host/Standard`
- **Web UI Endpoint:** `http://10.99.0.199:8000`
- **Onboarding / Auth Protocol:** `wizard`
- **Volume Mapping:** Isolated Persistent Storage (`/opt/njorddeploy/paperless-ngx`)

#### Web UI Screenshot:
![Paperless-ngx Web UI](../../images/test_screenshots/paperless-ngx_vm_podman_20260914_131930.png)


```yaml
# NjordDeploy verified configuration preview for paperless-ngx
service: paperless-ngx
status: healthy
restart_policy: unless-stopped
```
</details>

<details id="details-stirling-pdf">
<summary>🔍 <b>Component Inspection: Stirling PDF (<code>stirling-pdf</code>)</b></summary>

**Description:** A powerful, open-source PDF editing platform for editing, signing, redacting, converting, and automating PDFs.

#### Upstream Project & Configuration Docs:
- 🌐 **Official Website / Repo:** [https://stirlingpdf.com/](https://stirlingpdf.com/)
- 💡 **Post-Install Guide:** *Open Stirling PDF web UI and complete the initial onboarding setup.*

#### Deployment Runtime Parameters:
- **Port Bindings:** `Host/Standard`
- **Web UI Endpoint:** `http://10.99.0.199:8080`
- **Onboarding / Auth Protocol:** `wizard`
- **Volume Mapping:** Isolated Persistent Storage (`/opt/njorddeploy/stirling-pdf`)

#### Web UI Screenshot:
![Stirling PDF Web UI](../../images/test_screenshots/stirling-pdf_vm_podman_20260914_133525.png)


```yaml
# NjordDeploy verified configuration preview for stirling-pdf
service: stirling-pdf
status: healthy
restart_policy: unless-stopped
```
</details>

<details id="details-actual-budget">
<summary>🔍 <b>Component Inspection: Actual Budget (<code>actual-budget</code>)</b></summary>

**Description:** Privacy-first personal finance and envelope budgeting app. It is 100% free and open-source, written in NodeJS, it has a synchronization element so that all your changes can move between devices without any heavy lifting. The application stores its data in the /data volume.

#### Upstream Project & Configuration Docs:
- 💡 **Post-Install Guide:** *Open Actual Budget web UI and complete the initial onboarding setup.*

#### Deployment Runtime Parameters:
- **Port Bindings:** `Host/Standard`
- **Web UI Endpoint:** `http://10.99.0.199:5006`
- **Onboarding / Auth Protocol:** `wizard`
- **Volume Mapping:** Isolated Persistent Storage (`/opt/njorddeploy/actual-budget`)

#### Web UI Screenshot:
![Actual Budget Web UI](../../images/test_screenshots/actual-budget_vm_podman_20260914_122010.png)


```yaml
# NjordDeploy verified configuration preview for actual-budget
service: actual-budget
status: healthy
restart_policy: unless-stopped
```
</details>

<details id="details-nocodb">
<summary>🔍 <b>Component Inspection: NocoDB (<code>nocodb</code>)</b></summary>

**Description:** Open Source Airtable Alternative that turns any SQL database into a smart spreadsheet.

#### Upstream Project & Configuration Docs:
- 💡 **Post-Install Guide:** *Open NocoDB web UI and complete the initial onboarding setup.*

#### Deployment Runtime Parameters:
- **Port Bindings:** `Host/Standard`
- **Web UI Endpoint:** `http://10.99.0.199:8098`
- **Onboarding / Auth Protocol:** `wizard`
- **Volume Mapping:** Isolated Persistent Storage (`/opt/njorddeploy/nocodb`)

#### Web UI Screenshot:
![NocoDB Web UI](../../images/test_screenshots/nocodb_vm_podman_20260914_131045.png)


```yaml
# NjordDeploy verified configuration preview for nocodb
service: nocodb
status: healthy
restart_policy: unless-stopped
```
</details>

---

## 🖼️ Verified Web UI Screenshots Gallery

The following live screenshots were automatically captured during the test run:

### Paperless-ngx (`paperless-ngx`)
- **Endpoint:** [http://10.99.0.199:8000](http://10.99.0.199:8000)

![Paperless-ngx Web UI](../../images/test_screenshots/paperless-ngx_vm_podman_20260914_131930.png)

### Stirling PDF (`stirling-pdf`)
- **Endpoint:** [http://10.99.0.199:8080](http://10.99.0.199:8080)

![Stirling PDF Web UI](../../images/test_screenshots/stirling-pdf_vm_podman_20260914_133525.png)

### Actual Budget (`actual-budget`)
- **Endpoint:** [http://10.99.0.199:5006](http://10.99.0.199:5006)

![Actual Budget Web UI](../../images/test_screenshots/actual-budget_vm_podman_20260914_122010.png)

### NocoDB (`nocodb`)
- **Endpoint:** [http://10.99.0.199:8098](http://10.99.0.199:8098)

![NocoDB Web UI](../../images/test_screenshots/nocodb_vm_podman_20260914_131045.png)

---
[⬅️ Back to Master Test Dashboard](../LATEST_RUN.md)
