---
name: proxmox-lxc
description: Workflows en scripts voor het automatisch aanmaken, inrichten (Docker) en beheren van LXC-containers in Proxmox VE.
---

# Proxmox LXC Container Provisioning Workflow

Gebruik deze skill om automatisch LXC-containers aan te maken op je Proxmox VE-server die specifiek zijn ingericht voor NjordDeploy (inclusief Docker en de benodigde netwerkverbindingen).

## 1. Vereiste Omgevingsvariabelen

Zorg ervoor dat de volgende keys correct zijn ingevuld in je `.env` bestand:

```bash
PROXMOX_HOST="https://<your-proxmox-ip>:8006"
PROXMOX_USER="root@pam"
PROXMOX_TOKEN_ID="clone-token"
PROXMOX_TOKEN_SECRET="xxxx-xxxx-xxxx-xxxx"
PROXMOX_NODE="pve"
```

## 2. Een LXC Container Aanmaken en Inrichten

Het script `scripts/create_proxmox_lxc.py` regelt de volledige installatie. Het voert de volgende stappen uit:
1. Vraagt het eerstvolgende beschikbare VMID op bij Proxmox.
2. Haalt de openbare SSH-sleutel van NjordDeploy op.
3. Zoekt op de opslag (`local`) naar een bruikbare Debian of Ubuntu LXC-template.
4. Maakt de container aan met Nesting en Keyctl ingeschakeld (nodig voor Docker in LXC).
5. Wacht tot de container online is en een IP-adres krijgt via DHCP.
6. Maakt verbinding via SSH en installeert automatisch Docker, en start het `njorddeploy_net` Docker-netwerk.

### Commando voor 15+ gebruikers (Aanbevolen specs):
```bash
python scripts/create_proxmox_lxc.py --cores 4 --memory 8192 --storage-size 40 --storage-name local-lvm
```

### Opties:
* `--cores <aantal>`: Aantal CPU cores (standaard: `4`).
* `--memory <MB>`: Werkgeheugen in MB (standaard: `8192` voor 8GB).
* `--storage-size <GB>`: Grootte van de SSD (standaard: `40`).
* `--storage-name <naam>`: Proxmox storage pool (standaard: `local-lvm`).
* `--node <naam>`: Proxmox node naam (standaard: `pve`).
* `--password <wachtwoord>`: Root-wachtwoord voor de container.

## 3. Beheer na installatie

Zodra het script klaar is, toont het de container-details (ID, IP-adres, root-wachtwoord).
Je kunt de container direct gebruiken als deployment-target in NjordDeploy door de host op te geven in de configurator of editor-app!
