# Proxmox Automated Package Testing Report

**Run Timestamp:** 2026-07-20 08:51:25
**Total Packages Tested:** 3 | **Passed:** 2 | **Failed:** 1

## Packages Summary Table

| Package ID | Package Name | VM ID | IP Address | Deployment | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `caddy-filebrowser-stack` | Caddy & Filebrowser Stack | 110 | 192.168.178.57 | success | **✅ PASS** |
| `media-stack` | Media Stack | 110 | 192.168.178.57 | success | **✅ PASS** |
| `nextcloud-stack` | Nextcloud Stack | 110 | 192.168.178.57 | failed | **❌ FAIL** |

## Detailed Components Verification Status

### Package: `caddy-filebrowser-stack` (Caddy & Filebrowser Stack)
- **VMID:** 110
- **IP:** 192.168.178.57
- **Deployment:** success
- **Overall Status:** ✅ PASS

#### Component Health Status:

| Component ID | Container Running | HTTP UI Port | Log Error (Traceback/Fatal) | Version | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `caddy` | Running | N/A | None | unknown | ✅ OK |
| `filebrowser` | Running | OK | None | unknown | ✅ OK |

---

### Package: `media-stack` (Media Stack)
- **VMID:** 110
- **IP:** 192.168.178.57
- **Deployment:** success
- **Overall Status:** ✅ PASS

#### Component Health Status:

| Component ID | Container Running | HTTP UI Port | Log Error (Traceback/Fatal) | Version | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `jellyfin` | Running | OK | None | unknown | ✅ OK |
| `qbittorrent` | Running | OK | None | unknown | ✅ OK |
| `radarr` | Running | OK | None | unknown | ✅ OK |
| `sabnzbd` | Running | OK | None | unknown | ✅ OK |
| `sonarr` | Running | OK | None | unknown | ✅ OK |

---

### Package: `nextcloud-stack` (Nextcloud Stack)
- **VMID:** 110
- **IP:** 192.168.178.57
- **Deployment:** failed
- **Overall Status:** ❌ FAIL

**Error / Failures Message:**
```
Deployment failed: non-zero return code | stderr:  Network nextcloud-internal Creating
 Network nextcloud-internal Created
 Container nextcloud-redis Creating
 Container nextcloud-db Creating
 Container nextcloud-redis Created
 Container nextcloud-db Created
 Container nextcloud-db-dumper Creating
 Container nextcloud-app Creating
 Container nextcloud-db-dumper Created
 Container nextcloud-app Created
 Container notify-push Creating
 Container notify-push Created
 Container nextcloud-redis Starting
 Container nextcloud-db Starting
 Container nextcloud-redis Started
 Container nextcloud-db Started
 Container nextcloud-db-dumper Starting
 Container nextcloud-app Starting
 Container nextcloud-db-dumper Started
 Container nextcloud-app Started
 Container notify-push Starting
Error response from daemon: failed to create task for container: failed to create shim task: OCI runtime create failed: runc create failed: unable to start container process: error during container init: exec: "/var/www/html/custom_apps/notify_push/bin/aarch64/notify_push": stat /var/www/html/custom_apps/notify_push/bin/aarch64/notify_push: no such file or directory
```

---
