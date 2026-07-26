# Proxmox Automated Component Testing Report - voicebox

**Run Timestamp:** 2026-07-24 14:54:10
**Total Tested:** 1 | **Passed:** 0 | **Failed:** 1

## Results Table

| Component ID | VM ID | IP Address | Deployment | Containers | HTTP | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `voicebox` | 110 | 192.168.178.82 | failed | Stopped | N/A | **❌ FAIL** |

## Details & Failures

### Component: `voicebox`
- **VMID:** 110
- **IP:** 192.168.178.82
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Deployment failed: non-zero return code | stderr: validating /opt/njorddeploy/docker-compose.yml: services.voicebox.build additional properties 'pull_policy' not allowed
```
