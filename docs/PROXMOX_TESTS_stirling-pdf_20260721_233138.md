# Proxmox Automated Component Testing Report - stirling-pdf

**Run Timestamp:** 2026-07-21 23:31:38
**Total Tested:** 1 | **Passed:** 0 | **Failed:** 1

## Results Table

| Component ID | VM ID | IP Address | Deployment | Containers | HTTP | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `stirling-pdf` | 110 | 192.168.178.61 | failed | Stopped | N/A | **❌ FAIL** |

## Details & Failures

### Component: `stirling-pdf`
- **VMID:** 110
- **IP:** 192.168.178.61
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Deployment failed: non-zero return code | stderr:  Image stirlingpdf/stirling-pdf:latest Pulling
 Image stirlingpdf/stirling-pdf:latest Error pull access denied for stirlingpdf/stirling-pdf, repository does not exist or may require 'docker login'
Error response from daemon: pull access denied for stirlingpdf/stirling-pdf, repository does not exist or may require 'docker login'
```
