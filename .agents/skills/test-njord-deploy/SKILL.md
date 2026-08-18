---
name: test-njord-deploy
description: Procedure en instructies voor het automatisch testen van de nieuwste release van NjordDeploy (bijv. v0.5.7-Alpha) op een Proxmox server via Ansible. De skill presenteert een menu om te kiezen op basis van welk Proxmox VM template (bijv. debian-clean-template, debian-12-template, pi-master-template) de test-VM uitgerold moet worden.
---

# Skill: Test NjordDeploy Release op Proxmox (`test-njord-deploy`)

Deze skill automatiseert het testen van een specifieke of de meest recente GitHub release van **NjordDeploy** ([HenkVanHoek/njord-deploy](https://github.com/HenkVanHoek/njord-deploy/releases)) op een Proxmox hypervisor-omgeving met behulp van het Ansible playbook.

Wanneer deze skill wordt geactiveerd, presenteert de AI-assistent een **interactief keuzemenu** aan de gebruiker om het gewenste Proxmox VM-sjabloon (template) te selecteren.

---

## 1. Beschikbare Templates op Proxmox

Op de Proxmox server (`proxmox` / `192.168.178.51`) zijn de volgende vooraf geconfigureerde templates beschikbaar:

| Template Naam | VMID | Omschrijving | Aanbevolen |
| :--- | :--- | :--- | :--- |
| **`debian-clean-template`** | `902` | Schoon Debian 12 sjabloon met cloud-init & QEMU guest agent | **Ja (Standaard)** |
| **`debian-12-template`** | `900` | Minimale Debian 12 base VM | Nee |
| **`pi-master-template`** | `105` | Custom Raspberry Pi master-omgeving template | Nee |

---

## 2. Stapsgewijze Procedure

### Stap 1: Toon Keuzemenu voor Template Selectie

De agent vraagt de gebruiker (via de `ask_question` tool of een genummerde keuzelijst in de chat) welk template gebruikt moet worden:

> **Welk Proxmox template wil je gebruiken voor het testen van NjordDeploy release v0.5.7-Alpha?**
> 1. (Aanbevolen) `debian-clean-template` (VMID: 902) - Schoon Debian 12 met cloud-init
> 2. `debian-12-template` (VMID: 900) - Basis minimale Debian 12 OS template
> 3. `pi-master-template` (VMID: 105) - Pi master omgeving template
> 4. Dynamisch scannen via `qm list` op Proxmox host

---

### Stap 2: Voer het Ansible Test Playbook uit

Zodra de gebruiker de template kiest (bijvoorbeeld `902`), voert de agent het playbook `ansible/test-njord-deploy.yaml` uit met de relevante variabelen:

```bash
ansible-playbook -i inventory/hosts.yaml ansible/test-njord-deploy.yaml -e "template_vmid=902 njord_tag=v0.5.7-Alpha"
```

#### Wat het playbook op Proxmox uitvoert:
1. **Klonen:** Kloont het gekozen template (bijv. VM 902) naar een tijdelijke test VM (standaard VMID `999`, genaamd `njord-test-v0-5-7-Alpha`).
2. **Starten:** Start VM 999 en wacht op de QEMU guest agent en netwerk.
3. **Ophalen Release:** Downloadt de Linux binary van release `v0.5.7-Alpha` direct van GitHub:
   `https://github.com/HenkVanHoek/njord-deploy/releases/download/v0.5.7-Alpha/NjordDeploy-Linux.zip`
4. **Uitvoeren:** Pak het zip-bestand uit en start `./NjordDeploy-Linux` in de test VM.
5. **Verificatie:** Controleert via `curl` de HTTP statusrespons op poort `5001` (`http://127.0.0.1:5001`).

---

### Stap 3: Rapporteer Testresultaten

De agent verzamelt de output van het playbook en presenteert een overzichtelijke samenvatting:
* **Release Tag:** `v0.5.7-Alpha`
* **Gekozen Template:** `debian-clean-template` (VMID 902)
* **Test VMID:** `999` (`njord-test-v0-5-7-Alpha`)
* **Status Application:** Up and Running (HTTP 200 OK op poort 5001)
* **Log Output:** `/tmp/configurator.log` op de test VM

---

### Stap 4: Keuze voor Opruimen of Behoud

Na het testen vraagt de agent of de test VM opgeruimd moet worden of actief moet blijven voor verdere inspectie:

* **Opruimen (Standaard):**
  ```bash
  ansible proxmox -i inventory/hosts.yaml -m shell -a "qm stop 999 && qm destroy 999 --purge"
  ```
* **Behouden:** Laat VM 999 actief op Proxmox.

---

## 3. Handmatige Commando's & Commands Reference

Om de test handmatig te starten voor een andere release tag (bijv. `v0.5.9-Alpha`):

```bash
ansible-playbook -i inventory/hosts.yaml ansible/test-njord-deploy.yaml -e "template_vmid=902 njord_tag=v0.5.9-Alpha"
```

Om live logs te bekijken van de test VM:
```bash
ansible proxmox -i inventory/hosts.yaml -m command -a "qm guest exec 999 -- cat /tmp/configurator.log"
```
