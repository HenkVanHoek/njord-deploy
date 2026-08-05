# Proxmox Automated Component Testing Report - mariadb,adminer,phpmyadmin

**Run Timestamp:** 2026-08-04 20:35:03
**Total Tested:** 2 | **Passed:** 1 | **Failed:** 1

## Results Table

| Component ID | VM ID | IP Address | Deployment | Containers | HTTP | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `adminer` | 103 | 192.168.178.26 | success | Running | OK | **✅ PASS** |
| `phpmyadmin` | 103 | 192.168.178.30 | failed | Stopped | N/A | **❌ FAIL** |

## Details & Failures

### Component: `phpmyadmin`
- **VMID:** 103
- **IP:** 192.168.178.30
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Deployment failed: non-zero return code | stderr: time="2026-08-04T18:35:02Z" level=warning msg="The \"DB_PASS\" variable is not set. Defaulting to a blank string."
service "phpmyadmin" depends on undefined service "mariadb": invalid compose project
```
