# Proxmox Automated Component Testing Report - adminer

**Run Timestamp:** 2026-09-05 14:53:57
**Execution Profile:** `MATRIX (4 envs)` | **Total Tested:** 4 | **Passed:** 4 | **Skipped:** 0 | **Failed:** 0

## Results Table

| Date / Time | Component ID | Target | Engine | VM ID | IP Address | Deployment | Containers | HTTP | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 2026-09-05 14:50:33 | `adminer` | `LXC` | `DOCKER` | 104 | 10.99.0.199 | success | Running | OK | **✅ PASS** |
| 2026-09-05 14:51:14 | `adminer` | `LXC` | `PODMAN` | 104 | 10.99.0.199 | success | Running | OK | **✅ PASS** |
| 2026-09-05 14:52:19 | `adminer` | `VM` | `DOCKER` | 104 | 10.99.0.199 | success | Running | OK | **✅ PASS** |
| 2026-09-05 14:53:21 | `adminer` | `VM` | `PODMAN` | 104 | 10.99.0.199 | success | Running | OK | **✅ PASS** |

## Visual Verification & Web UI Screenshots

### Component: `adminer` (LXC + DOCKER)
- **Web UI Endpoint:** [http://10.99.0.199:8084](http://10.99.0.199:8084)
- **Target Mode:** `LXC` | **Engine:** `DOCKER`
- **VM ID:** 104 | **IP:** `10.99.0.199`

![adminer Web UI](images/test_screenshots/adminer_lxc_docker_20260905_145049.png)

### Component: `adminer` (LXC + PODMAN)
- **Web UI Endpoint:** [http://10.99.0.199:8084](http://10.99.0.199:8084)
- **Target Mode:** `LXC` | **Engine:** `PODMAN`
- **VM ID:** 104 | **IP:** `10.99.0.199`

![adminer Web UI](images/test_screenshots/adminer_lxc_podman_20260905_145135.png)

### Component: `adminer` (VM + DOCKER)
- **Web UI Endpoint:** [http://10.99.0.199:8084](http://10.99.0.199:8084)
- **Target Mode:** `VM` | **Engine:** `DOCKER`
- **VM ID:** 104 | **IP:** `10.99.0.199`

![adminer Web UI](images/test_screenshots/adminer_vm_docker_20260905_145239.png)

### Component: `adminer` (VM + PODMAN)
- **Web UI Endpoint:** [http://10.99.0.199:8084](http://10.99.0.199:8084)
- **Target Mode:** `VM` | **Engine:** `PODMAN`
- **VM ID:** 104 | **IP:** `10.99.0.199`

![adminer Web UI](images/test_screenshots/adminer_vm_podman_20260905_145349.png)


## Details & Failures

All components completed execution and verification successfully!
