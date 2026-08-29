# 🚀 NjordDeploy Multi-OS Release Installer Test Report

**Datum & Tijd:** 2026-08-29 08:49:03
**Versie / Tag:** `Local Build`
**Totale Tests:** 3 | **Geslaagd:** 0 | **Mislukt:** 3

---

| Omgeving / Besturingssysteem | Status | Details |
| :--- | :---: | :--- |
| **Debian 12 (VM)** | ❌ FAIL | HTTP interface verification failed on port 5001. |
| **Debian 12 (LXC)** | ❌ FAIL | HTTP interface verification failed on port 5001. |
| **Ubuntu 24.04 (LXC)** | ❌ FAIL | HTTP interface verification failed on port 5001. |

---

## 🔍 Verificatiecriteria
- **Installatie:** Binary en shortcuts correct geplaatst (`install.sh` / `.exe` / `start.bat`).
- **Service Executie:** NjordDeploy Configurator gestart in achtergrond (systemd / nohup / PowerShell).
- **Health Check:** HTTP status `200 OK` geverifieerd op poort `5001` (of fallback `5000`).
- **Opruiming:** Tijdelijke Proxmox VM's en LXC containers automatisch verwijderd.
