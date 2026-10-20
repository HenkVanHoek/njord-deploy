# Proxmox Automated Package Testing Report

**Run Timestamp:** 2026-10-20 15:13:32
**Total Packages Tested:** 5 | **Passed:** 5 | **Failed:** 0

## Packages Summary Table

| Package ID          | Package Name                  | Target | Engine | VM ID | IP Address      | Deployment | Status     |
|:--------------------|:------------------------------|:-------|:-------|:------|:----------------|:-----------|:-----------|
| `immich-stack`      | Immich Photo & Kiosk Suite    | VM     | DOCKER | 107   | 10.99.0.199     | success    | **✅ PASS** |
| `open-webui-ollama` | Open WebUI & Ollama AI Studio | LXC    | DOCKER | 107   | 192.168.178.199 | success    | **✅ PASS** |
| `open-webui-ollama` | Open WebUI & Ollama AI Studio | LXC    | PODMAN | 107   | 192.168.178.199 | success    | **✅ PASS** |
| `open-webui-ollama` | Open WebUI & Ollama AI Studio | VM     | DOCKER | 107   | 192.168.178.199 | success    | **✅ PASS** |
| `open-webui-ollama` | Open WebUI & Ollama AI Studio | VM     | PODMAN | 107   | 192.168.178.199 | success    | **✅ PASS** |

## Detailed Components Verification Status

### Package: `immich-stack` (Immich Photo & Kiosk Suite)
- **Target:** VM | **Engine:** DOCKER
- **VMID:** 107
- **IP:** 10.99.0.199
- **Deployment:** success
- **Overall Status:** ✅ PASS

#### Component Health Status:

| Component ID   | Container Running | HTTP UI Port | Log Error (Traceback/Fatal) | Version | Status |
|:---------------|:------------------|:-------------|:----------------------------|:--------|:-------|
| `immich`       | Running           | OK           | None                        | unknown | ✅ OK   |
| `immich-kiosk` | Running           | OK           | None                        | unknown | ✅ OK   |

#### Web UI Screenshots:

##### Component: `immich`
- **Endpoint:** [http://10.99.0.199:2283](http://10.99.0.199:2283)

![immich Web UI](images/test_screenshots/pkg_immich_vm_docker_20260927_150607.png)

##### Component: `immich-kiosk`
- **Endpoint:** [http://10.99.0.199:2284](http://10.99.0.199:2284)

![immich-kiosk Web UI](images/test_screenshots/pkg_immich-kiosk_vm_docker_20260927_150610.png)


#### 🔑 First-Run Credentials & Onboarding Verification:

| Component ID   | Auth Type | Extracted Setup Key / Token | Status    |
|:---------------|:----------|:----------------------------|:----------|
| `immich`       | `wizard`  | *Onboarding Wizard*         | ℹ️ WIZARD |
| `immich-kiosk` | `none`    | —                           | ℹ️ NONE   |


---

### Package: `open-webui-ollama` (Open WebUI & Ollama AI Studio)
- **Target:** LXC | **Engine:** DOCKER
- **VMID:** 107
- **IP:** 192.168.178.199
- **Deployment:** success
- **Overall Status:** ✅ PASS

#### Component Health Status:

| Component ID | Container Running | HTTP UI Port | Log Error (Traceback/Fatal) | Version | Status |
|:-------------|:------------------|:-------------|:----------------------------|:--------|:-------|
| `ollama`     | Running           | N/A          | None                        | unknown | ✅ OK   |
| `open-webui` | Running           | OK           | None                        | unknown | ✅ OK   |
| `litellm`    | Running           | OK           | None                        | unknown | ✅ OK   |
| `speaches`   | Running           | OK           | None                        | unknown | ✅ OK   |

#### 🔑 First-Run Credentials & Onboarding Verification:

| Component ID | Auth Type | Extracted Setup Key / Token | Status    |
|:-------------|:----------|:----------------------------|:----------|
| `ollama`     | `none`    | —                           | ℹ️ NONE   |
| `open-webui` | `wizard`  | *Onboarding Wizard*         | ℹ️ WIZARD |
| `litellm`    | `wizard`  | *Onboarding Wizard*         | ℹ️ WIZARD |
| `speaches`   | `none`    | —                           | ℹ️ NONE   |


---

### Package: `open-webui-ollama` (Open WebUI & Ollama AI Studio)
- **Target:** LXC | **Engine:** PODMAN
- **VMID:** 107
- **IP:** 192.168.178.199
- **Deployment:** success
- **Overall Status:** ✅ PASS

#### Component Health Status:

| Component ID | Container Running | HTTP UI Port | Log Error (Traceback/Fatal) | Version | Status |
|:-------------|:------------------|:-------------|:----------------------------|:--------|:-------|
| `ollama`     | Running           | N/A          | None                        | unknown | ✅ OK   |
| `open-webui` | Running           | OK           | None                        | unknown | ✅ OK   |
| `litellm`    | Running           | OK           | None                        | unknown | ✅ OK   |
| `speaches`   | Running           | OK           | None                        | unknown | ✅ OK   |

#### 🔑 First-Run Credentials & Onboarding Verification:

| Component ID | Auth Type | Extracted Setup Key / Token | Status    |
|:-------------|:----------|:----------------------------|:----------|
| `ollama`     | `none`    | —                           | ℹ️ NONE   |
| `open-webui` | `wizard`  | *Onboarding Wizard*         | ℹ️ WIZARD |
| `litellm`    | `wizard`  | *Onboarding Wizard*         | ℹ️ WIZARD |
| `speaches`   | `none`    | —                           | ℹ️ NONE   |


---

### Package: `open-webui-ollama` (Open WebUI & Ollama AI Studio)
- **Target:** VM | **Engine:** DOCKER
- **VMID:** 107
- **IP:** 192.168.178.199
- **Deployment:** success
- **Overall Status:** ✅ PASS

#### Component Health Status:

| Component ID | Container Running | HTTP UI Port | Log Error (Traceback/Fatal) | Version | Status |
|:-------------|:------------------|:-------------|:----------------------------|:--------|:-------|
| `ollama`     | Running           | N/A          | None                        | unknown | ✅ OK   |
| `open-webui` | Running           | OK           | None                        | unknown | ✅ OK   |
| `litellm`    | Running           | OK           | None                        | unknown | ✅ OK   |
| `speaches`   | Running           | OK           | None                        | unknown | ✅ OK   |

#### 🔑 First-Run Credentials & Onboarding Verification:

| Component ID | Auth Type | Extracted Setup Key / Token | Status    |
|:-------------|:----------|:----------------------------|:----------|
| `ollama`     | `none`    | —                           | ℹ️ NONE   |
| `open-webui` | `wizard`  | *Onboarding Wizard*         | ℹ️ WIZARD |
| `litellm`    | `wizard`  | *Onboarding Wizard*         | ℹ️ WIZARD |
| `speaches`   | `none`    | —                           | ℹ️ NONE   |


---

### Package: `open-webui-ollama` (Open WebUI & Ollama AI Studio)
- **Target:** VM | **Engine:** PODMAN
- **VMID:** 107
- **IP:** 192.168.178.199
- **Deployment:** success
- **Overall Status:** ✅ PASS

#### Component Health Status:

| Component ID | Container Running | HTTP UI Port | Log Error (Traceback/Fatal) | Version | Status |
|:-------------|:------------------|:-------------|:----------------------------|:--------|:-------|
| `ollama`     | Running           | N/A          | None                        | unknown | ✅ OK   |
| `open-webui` | Running           | OK           | None                        | unknown | ✅ OK   |
| `litellm`    | Running           | OK           | None                        | unknown | ✅ OK   |
| `speaches`   | Running           | OK           | None                        | unknown | ✅ OK   |

#### 🔑 First-Run Credentials & Onboarding Verification:

| Component ID | Auth Type | Extracted Setup Key / Token | Status    |
|:-------------|:----------|:----------------------------|:----------|
| `ollama`     | `none`    | —                           | ℹ️ NONE   |
| `open-webui` | `wizard`  | *Onboarding Wizard*         | ℹ️ WIZARD |
| `litellm`    | `wizard`  | *Onboarding Wizard*         | ℹ️ WIZARD |
| `speaches`   | `none`    | —                           | ℹ️ NONE   |


---
