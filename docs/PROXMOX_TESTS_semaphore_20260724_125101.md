# Proxmox Automated Component Testing Report - semaphore

**Run Timestamp:** 2026-07-24 12:51:01
**Total Tested:** 1 | **Passed:** 0 | **Failed:** 1

## Results Table

| Component ID | VM ID | IP Address | Deployment | Containers | HTTP | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `semaphore` | 110 | 192.168.178.60 | success | Stopped | FAIL | **❌ FAIL** |

## Details & Failures

### Component: `semaphore`
- **VMID:** 110
- **IP:** 192.168.178.60
- **Deployment Outcome:** success
- **Error / Logs:**
```
No running containers found (exit code: 0).
HTTP Probe failed after 15 attempts: HTTPConnectionPool(host='192.168.178.60', port=3000): Max retries exceeded with url: / (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x775939713ef0>: Failed to establish a new connection: [Errno 111] Connection refused')) (http://192.168.178.60:3000)
```
