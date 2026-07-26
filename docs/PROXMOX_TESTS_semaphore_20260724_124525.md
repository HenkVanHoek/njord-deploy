# Proxmox Automated Component Testing Report - semaphore

**Run Timestamp:** 2026-07-24 12:45:25
**Total Tested:** 1 | **Passed:** 0 | **Failed:** 1

## Results Table

| Component ID | VM ID | IP Address | Deployment | Containers | HTTP | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `semaphore` | 110 | N/A | failed | Stopped | N/A | **❌ FAIL** |

## Details & Failures

### Component: `semaphore`
- **VMID:** 110
- **IP:** N/A
- **Deployment Outcome:** failed
- **Error / Logs:**
```
500 Server Error: unable to find configuration file for VM 900 on node 'pve' for url: https://192.168.178.51:8006/api2/json/nodes/pve/qemu/900/clone (Response: {"data":null,"message":"unable to find configuration file for VM 900 on node 'pve'\n"})
```
