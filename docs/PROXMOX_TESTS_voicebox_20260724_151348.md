# Proxmox Automated Component Testing Report - voicebox

**Run Timestamp:** 2026-07-24 15:13:48
**Total Tested:** 1 | **Passed:** 0 | **Failed:** 1

## Results Table

| Component ID | VM ID | IP Address | Deployment | Containers | HTTP | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `voicebox` | 110 | 192.168.178.85 | success | Running | FAIL | **❌ FAIL** |

## Details & Failures

### Component: `voicebox`
- **VMID:** 110
- **IP:** 192.168.178.85
- **Deployment Outcome:** success
- **Error / Logs:**
```
Running containers:
njorddeploy-voicebox (Up 1 second (health: starting))
HTTP Probe failed after 15 attempts: HTTPConnectionPool(host='192.168.178.85', port=17600): Max retries exceeded with url: / (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x760d1b5358e0>: Failed to establish a new connection: [Errno 111] Connection refused')) (http://192.168.178.85:17600)
```
