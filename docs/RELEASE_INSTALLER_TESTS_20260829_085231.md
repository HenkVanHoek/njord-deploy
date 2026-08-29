# 🚀 NjordDeploy Multi-OS Release Installer Test Report

**Datum & Tijd:** 2026-08-29 08:52:31
**Versie / Tag:** `Local Build`
**Totale Tests:** 3 | **Geslaagd:** 3 | **Mislukt:** 0

---

| Omgeving / Besturingssysteem | Status | Details |
| :--- | :---: | :--- |
| **Debian 12 (VM)** | ✅ PASS | Debian VM Test Passed successfully. |
| **Debian 12 (LXC)** | ✅ PASS | Debian LXC Test Passed successfully. |
| **Ubuntu 24.04 (LXC)** | ✅ PASS | Ubuntu LXC Test Passed successfully. |

---

## 🔍 Verificatiecriteria
- **Installatie:** Binary en shortcuts correct geplaatst (`install.sh` / `.exe` / `start.bat`).
- **Service Executie:** NjordDeploy Configurator gestart in achtergrond (systemd / nohup / PowerShell).
- **Health Check:** HTTP status `200 OK` geverifieerd op poort `5001` (of fallback `5000`).
- **Opruiming:** Tijdelijke Proxmox VM's en LXC containers automatisch verwijderd.
