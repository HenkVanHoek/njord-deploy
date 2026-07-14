---
name: proxmox-test
description: Workflows voor het automatisch testen van NjordDeploy componenten in een gekloonde Proxmox VM.
---

# Proxmox Component Integration Testing Workflow

Gebruik deze skill om NjordDeploy componenten te valideren door ze automatisch te deployen en testen op een tijdelijk gekloonde VM binnen een Proxmox VE server.

## 1. Vereiste Omgevingsvariabelen

Configureer de volgende keys in de `.env` file van het project:

```bash
# Proxmox VE Cluster credentials
PROXMOX_HOST="https://<your-proxmox-ip>:8006"
PROXMOX_USER="root@pam"
PROXMOX_TOKEN_ID="clone-token"
PROXMOX_TOKEN_SECRET="xxxx-xxxx-xxxx-xxxx"
PROXMOX_NODE="pve"
PROXMOX_TEMPLATE_ID="900"

# Target VM credentials
PROXMOX_VM_USER="<your-vm-user>"
PROXMOX_VM_PASSWORD="your-ssh-and-sudo-password"

# Optional resources
PROXMOX_VM_RAM="2048"
PROXMOX_VM_CORES="2"
```

## 2. Testen Uitvoeren

### A. Test alle componenten (volledige integratietest run):
```bash
python scripts/proxmox_test_runner.py
```

### B. Test specifieke componenten:
```bash
python scripts/proxmox_test_runner.py --components adguard-home,pi-hole
```

### C. Excludeer bepaalde componenten:
```bash
python scripts/proxmox_test_runner.py --exclude homeassistant,frigate
```

### D. Specificeer een andere template of Proxmox node via CLI:
```bash
python scripts/proxmox_test_runner.py --template-id 901 --node pve-node2
```

## 3. Rapportage & Resultaten

* **JSON Rapport**: De ruwe testresultaten worden opgeslagen in `tests/proxmox_results.json`.
* **Markdown Rapport**: Een leesbaar overzicht van de testrun met foutdetails wordt opgeslagen in `docs/PROXMOX_TESTS.md`.

## 4. Problemen Oplossen (Troubleshooting)

### A. QEMU Guest Agent is niet actief
Als de test-runner time-out bij het ophalen van het IP-adres van de VM:
* Zorg ervoor dat de `qemu-guest-agent` daemon is geïnstalleerd en ingeschakeld in het besturingssysteem van je master template VM:
  ```bash
  sudo apt-get update && sudo apt-get install -y qemu-guest-agent
  sudo systemctl enable --now qemu-guest-agent
  ```
* De test-runner configureert de gekloonde VM automatisch met `agent: enabled=1` en koppelt een netwerkkaart (`net0`) en Cloud-Init drive (`ide2`), maar de daemon in de VM moet wel actief zijn om te reageren op API queries.

### B. Geen ondersteuning voor Linked Clones
Als je opslagpool (bijv. `local-lvm`) geen snapshots/linked clones ondersteunt, gooit Proxmox een API fout. De test-runner heeft een automatische fallback ingebouwd en zal in dat geval automatisch overschakelen naar een **Full Clone**. Dit duurt iets langer maar voorkomt dat de test faalt.

### C. Master Template VMID
Op de node `pve` is de master template VMID standaard ingesteld op `105` (`pi-master-template`). Als je een andere template wilt gebruiken, geef dit dan mee via de CLI optie `--template-id <id>`.
