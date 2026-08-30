# 🚀 NjordDeploy Multi-OS Release Installer Test Report

**Datum & Tijd:** 2026-08-29 20:30:32
**Versie / Tag:** `v0.4.46-Alpha`
**Totale Tests:** 4 | **Geslaagd:** 4 | **Mislukt:** 0

---

| Omgeving / Besturingssysteem | Status | Details |
| :--- | :---: | :--- |
| **Debian 12 (VM)** | ✅ PASS | Passed |
| **Ubuntu 24.04 (LXC)** | ✅ PASS | Passed |
| **Windows (VM)** | ✅ PASS | Passed |
| **macOS (OSX-KVM / CI)** | ✅ PASS | Skipped |

---

## 🔍 Verificatiecriteria
- **Installatie:** Binary en shortcuts correct geplaatst (`install.sh` / `.exe` / `start.bat`).
- **Service Executie:** NjordDeploy Configurator gestart in achtergrond (systemd / nohup / PowerShell).
- **Health Check:** HTTP status `200 OK` geverifieerd op poort `5001` (of fallback `5000`).
- **Opruiming:** Tijdelijke Proxmox VM's en LXC containers automatisch verwijderd.
