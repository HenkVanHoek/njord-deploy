---
name: operational-update
description: Workflows and automated procedures for synchronizing repositories, compiling universal Debian 12 standalone binaries on Proxmox VE, safely backing up, updating, and health-checking the live operational NjordDeploy installation (VM 140 / njorddeploy-vm).
---

# 🚀 Operational NjordDeploy Live Update & Deployment Workflow

Gebruik deze skill om de operationele installatie van **NjordDeploy** op de Proxmox server (**VM 140** `njorddeploy-vm` @ `192.168.178.40` of geconfigureerd via `.env`) veilig en geautomatiseerd bij te werken naar de allernieuwste softwarestand en componentencatalogus.

---

## 🎯 Wat doet deze skill?

1. **Pre-flight Verificatie & Repository Synchronisatie:**
   - Controleert of de lokale repositories (`njord-deploy`, `njord-deploy-components`, `njord-deploy-design-system`) up-to-date en schoon zijn.
   - Voert lokale tests en statische kwaliteitscontroles uit (`pytest`, `flake8`, `mypy`).

2. **Universele Debian 12 Compilatie (GLIBC 2.36 Baseline):**
   - Start via [`scripts/build_linux_binary_proxmox.py`](file:///home/hvhoek/PycharmProjects/njord-deploy/scripts/build_linux_binary_proxmox.py) een tijdelijke, schone Debian 12 container op Proxmox.
   - Bouwt de drie standalone binaries:
     - `NjordDeployConfigurator` (Configurator Web App - Poort 5001)
     - `NjordDeployEditor` (Component Editor Web App - Poort 5000)
     - `NjordDeployProxmoxTest` (Proxmox Test Suite Web App - Poort 5050)
   - Haalt de universele uitvoerbare bestanden terug naar `dist/`.

3. **Veilige Remote Deployment op VM 140:**
   - Verbindt via SSH met de doelhost (`192.168.178.40`).
   - Stopt netjes de actieve systemd-services.
   - Maakt een point-in-time snapshot backup van `/opt/njorddeploy/` naar `/opt/njorddeploy.bak_<timestamp>/`.
   - Plaatst de nieuwe binaries in `/opt/njorddeploy/` met permissies `0755` en eigenaar `hvhoek:hvhoek`.
   - Herlaadt systemd daemons en start alle services opnieuw.

4. **Health Check & Interface Verificatie:**
   - Verifieert actieve `HTTP 200 OK` status op alle 3 poorten:
     - Configurator: `http://192.168.178.40:5001/`
     - Component Editor: `http://192.168.178.40:5000/`
     - Proxmox GUI: `http://192.168.178.40:5050/`

5. **Logboek & Notificaties:**
   - Exporteert automatisch een gestructureerd Markdown-verslag naar **Henks Geheugen** (Obsidian).
   - Verstuurt optioneel een statusbericht via de **Signal REST API**.

---

## 🛠️ Gebruik van het Geautomatiseerde Update Script

Het script [`scripts/update_operational_vm.py`](file:///home/hvhoek/PycharmProjects/njord-deploy/scripts/update_operational_vm.py) voert de volledige cyclus uit:

### A. Snelle Update (met bestaande binaries in `dist/`)
```bash
python scripts/update_operational_vm.py
```

### B. Volledige Update inclusief Verse Debian 12 Rebuild & Signal Notificatie
```bash
python scripts/update_operational_vm.py --build --signal
```

### C. Aangepaste Doelhost of IP
```bash
python scripts/update_operational_vm.py --host 192.168.178.40 --user pivm --build
```

---

## ⚙️ Relevante Configuratie (.env)

```bash
# Operational Target VM
OPERATIONAL_VM_IP="192.168.178.40"
PROXMOX_VM_USER="pivm"
PROXMOX_VM_PASSWORD="your-secure-password"

# Proxmox VE Server API
PROXMOX_HOST="https://192.168.178.51:8006"
PROXMOX_USER="root@pam"
PROXMOX_TOKEN_ID="clone-token"
PROXMOX_TOKEN_SECRET="xxxx-xxxx-xxxx-xxxx"
PROXMOX_NODE="pve"

# Signal Messenger API (Optioneel)
SIGNAL_API_URL="http://192.168.178.118:8090"
SIGNAL_SENDER="+31600000000"
SIGNAL_RECIPIENT="+31600000000"
```

---

## 📋 Verificatie Checklist na Update

- [ ] `njorddeploy-configurator.service` is `active (running)`
- [ ] `njorddeploy-editor.service` is `active (running)`
- [ ] `njorddeploy-proxmox-test.service` is `active (running)`
- [ ] [http://192.168.178.40:5001/](http://192.168.178.40:5001/) toont de nieuwste Configurator UI
- [ ] [http://192.168.178.40:5000/](http://192.168.178.40:5000/) toont alle 100 componenten
- [ ] [http://192.168.178.40:5050/](http://192.168.178.40:5050/) toont de Proxmox Test Suite
- [ ] Update-notitie opgeslagen in Henks Geheugen (`Nextcloud/Henks Geheugen/Projecten/Njord-deploy/Logboek/`)
