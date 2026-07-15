# Proxmox Automated Component Testing Report

**Run Timestamp:** 2026-07-15 23:23:09
**Total Tested:** 1 | **Passed:** 0 | **Failed:** 1

## Results Table

| Component ID | VM ID | IP Address | Deployment | Containers | HTTP | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `zigbee2mqtt` | 104 | 192.168.178.126 | failed | Stopped | N/A | **❌ FAIL** |

## Details & Failures

### Component: `zigbee2mqtt`
- **VMID:** 104
- **IP:** 192.168.178.126
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Deployment failed: non-zero return code | stderr:  Container njorddeploy-zigbee2mqtt Creating
 Container njorddeploy-zigbee2mqtt Created
 Container njorddeploy-zigbee2mqtt Starting
Error response from daemon: error gathering device information while adding custom device "/dev/ttyUSB0": no such file or directory
```
