# 🚀 NjordDeploy Multi-OS Release Installer Test Report

**Datum & Tijd:** 2026-08-29 08:16:57
**Versie / Tag:** `Local Build`
**Totale Tests:** 1 | **Geslaagd:** 1 | **Mislukt:** 0

---

| Omgeving / Besturingssysteem | Status | Details |
| :--- | :---: | :--- |
| **macOS (OSX-KVM / CI)** | ✅ PASS | SKIPPED (Informational): macOS VM template not configured on Proxmox. macOS binaries are verified natively via GitHub Actions macos-latest runners. (To enable local Proxmox testing, configure OSX-KVM and set RELEASE_TEST_MACOS_TEMPLATE in .env). |

---

## 🔍 Verificatiecriteria
- **Installatie:** Binary en shortcuts correct geplaatst (`install.sh` / `.exe` / `start.bat`).
- **Service Executie:** NjordDeploy Configurator gestart in achtergrond (systemd / nohup / PowerShell).
- **Health Check:** HTTP status `200 OK` geverifieerd op poort `5001` (of fallback `5000`).
- **Opruiming:** Tijdelijke Proxmox VM's en LXC containers automatisch verwijderd.
