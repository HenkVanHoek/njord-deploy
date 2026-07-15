# Proxmox Automated Component Testing Report

**Run Timestamp:** 2026-07-15 23:17:58
**Total Tested:** 1 | **Passed:** 0 | **Failed:** 1

## Results Table

| Component ID | VM ID | IP Address | Deployment | Containers | HTTP | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `web-notepad` | 104 | 192.168.178.141 | failed | Stopped | N/A | **❌ FAIL** |

## Details & Failures

### Component: `web-notepad`
- **VMID:** 104
- **IP:** 192.168.178.141
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Deployment failed: non-zero return code | stderr:  Image pajikos/minimalist-web-notepad:latest Pulling
 Image pajikos/minimalist-web-notepad:latest Error pull access denied for pajikos/minimalist-web-notepad, repository does not exist or may require 'docker login'
Error response from daemon: pull access denied for pajikos/minimalist-web-notepad, repository does not exist or may require 'docker login'
```
