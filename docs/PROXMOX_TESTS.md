# Proxmox Automated Component Testing Report

**Run Timestamp:** 2026-07-16 09:56:01
**Total Tested:** 1 | **Passed:** 0 | **Failed:** 1

## Results Table

| Component ID | VM ID | IP Address | Deployment | Containers | HTTP | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `notify-push` | 104 | 192.168.178.154 | failed | Stopped | N/A | **❌ FAIL** |

## Details & Failures

### Component: `notify-push`
- **VMID:** 104
- **IP:** 192.168.178.154
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Deployment failed: non-zero return code | stderr:  Network nextcloud-internal Creating
 Network nextcloud-internal Created
 Container nextcloud-redis Creating
 Container nextcloud-db Creating
 Container nextcloud-db Created
 Container nextcloud-redis Created
 Container nextcloud-app Creating
 Container nextcloud-app Created
 Container notify-push Creating
 Container notify-push Created
 Container nextcloud-redis Starting
 Container nextcloud-db Starting
 Container nextcloud-db Started
 Container nextcloud-redis Started
 Container nextcloud-app Starting
 Container nextcloud-app Started
 Container notify-push Starting
Error response from daemon: failed to create task for container: failed to create shim task: OCI runtime create failed: runc create failed: unable to start container process: error during container init: exec: "/var/www/html/custom_apps/notify_push/bin/aarch64/notify_push": stat /var/www/html/custom_apps/notify_push/bin/aarch64/notify_push: no such file or directory
```
