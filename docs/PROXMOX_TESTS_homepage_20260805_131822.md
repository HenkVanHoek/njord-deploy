# Proxmox Automated Component Testing Report - homepage

**Run Timestamp:** 2026-08-05 13:18:22
**Total Tested:** 1 | **Passed:** 0 | **Failed:** 1

## Results Table

| Component ID | VM ID | IP Address | Deployment | Containers | HTTP | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `homepage` | 104 | 192.168.178.37 | failed | Stopped | N/A | **❌ FAIL** |

## Details & Failures

### Component: `homepage`
- **VMID:** 104
- **IP:** 192.168.178.37
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Deployment failed: '/usr/bin/apt-get -y -o "Dpkg::Options::=--force-confdef" -o "Dpkg::Options::=--force-confold"       install 'docker-ce=5:29.7.1-1~debian.12~bookworm' 'docker-ce-cli=5:29.7.1-1~debian.12~bookworm' 'containerd.io=2.2.6-1~debian.12~bookworm' 'docker-compose-plugin=5.4.0-1~debian.12~bookworm'' failed: E: Could not get lock /var/lib/dpkg/lock-frontend. It is held by process 613 (apt-get)
E: Unable to acquire the dpkg frontend lock (/var/lib/dpkg/lock-frontend), is another process using it?
 | stderr: E: Could not get lock /var/lib/dpkg/lock-frontend. It is held by process 613 (apt-get)
E: Unable to acquire the dpkg frontend lock (/var/lib/dpkg/lock-frontend), is another process using it?

```
