# Proxmox Automated Component Testing Report - prometheus,grafana

**Run Timestamp:** 2026-08-03 20:32:57
**Total Tested:** 2 | **Passed:** 1 | **Failed:** 1

## Results Table

| Component ID | VM ID | IP Address | Deployment | Containers | HTTP | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `grafana` | 111 | 192.168.178.133 | success | Running | FAIL | **❌ FAIL** |
| `prometheus` | 111 | 192.168.178.134 | success | Running | OK | **✅ PASS** |

## Details & Failures

### Component: `grafana`
- **VMID:** 111
- **IP:** 192.168.178.133
- **Deployment Outcome:** success
- **Error / Logs:**
```
Running containers:
njorddeploy-prometheus (Up 2 seconds)
njorddeploy-grafana (Restarting (1) Less than a second ago)
njorddeploy-node-exporter (Up 2 seconds)
njorddeploy-cadvisor (Up 2 seconds (health: starting))
HTTP Probe failed after 15 attempts: HTTPConnectionPool(host='192.168.178.133', port=3000): Max retries exceeded with url: / (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x79161afee870>: Failed to establish a new connection: [Errno 111] Connection refused')) (http://192.168.178.133:3000)
```
