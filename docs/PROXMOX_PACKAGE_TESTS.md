# Proxmox Automated Package Testing Report

**Run Timestamp:** 2026-09-27 15:06:17
**Total Packages Tested:** 1 | **Passed:** 1 | **Failed:** 0

## Packages Summary Table

| Package ID     | Package Name               | Target | Engine | VM ID | IP Address  | Deployment | Status     |
|:---------------|:---------------------------|:-------|:-------|:------|:------------|:-----------|:-----------|
| `immich-stack` | Immich Photo & Kiosk Suite | VM     | DOCKER | 107   | 10.99.0.199 | success    | **✅ PASS** |

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
| `immich-kiosk` | `none`    | —                           | ℹ️ WIZARD |


---
