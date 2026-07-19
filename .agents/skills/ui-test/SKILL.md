---
name: ui-test
description: Workflows en instructies voor het automatisch testen van alle nog niet geteste componenten met een web UI.
---

# Generiek Testen van Componenten met een Web UI

Gebruik deze skill om in één keer alle componenten te testen die een web-interface hebben (`has_ui`) en waarvan de status in de docker-compose template nog niet gemarkeerd is als `"tested"`.

---

## 1. Hoe het Werkt (De Workflow)

De test-runner (`proxmox_test_runner.py`) is voorzien van een `--untested-ui` parameter. Wanneer deze wordt uitgevoerd:

1. **Detectie**: Het script scant alle componenten in `config/components_metadata.json` en filtert op componenten met `"has_ui": true`.
2. **Status Check**: Voor elk UI-component leest het script de statusheader `# status:` uit de bijbehorende `docker-compose.template.yml` file.
3. **Selectie**: Alleen componenten met een status die **niet** `"tested"` is (zoals `"untested"` of `"testing"`) worden geselecteerd voor de testrun.
4. **Provisionering & Run**: De geselecteerde componenten worden achter elkaar gedeployd op een tijdelijke Proxmox LXC-container (of VM).
5. **Gezondheidsverificatie**: De test-runner voert een HTTP-gezondheidscontrole (met automatische retries) uit op de externe UI-poort.
6. **Resultaat & Teardown**: Bij succes wordt de status in de docker-compose template automatisch bijgewerkt naar `"tested"`, waarna de container direct netjes wordt opgeruimd om Proxmox-resources te sparen.

---

## 2. Uitvoeren

### A. Test alle nog niet geteste UI-componenten (LXC-modus, aanbevolen):
```bash
.venv/bin/python scripts/proxmox_test_runner.py --untested-ui --mode lxc
```
*Dit spint achter elkaar tijdelijke containers op voor alle niet-geteste UI-services, valideert de web-interfaces en ruimt ze direct op.*

### B. Test alle nog niet geteste UI-componenten via VM-modus:
```bash
.venv/bin/python scripts/proxmox_test_runner.py --untested-ui --mode vm --template-id 105
```

---

## 3. Playwright E2E UI Verificatie (Optioneel)

Naast de standaard HTTP-poortcontrole van de test-runner, kun je voor componenten complexere interacties testen met Playwright (bijvoorbeeld inloggen of formulieracties controleren).

* UI-testscripts bevinden zich in `tests/ui_verification/` en gebruiken het actieve IP-adres uit `tests/proxmox_results.json`.
* **Playwright test uitvoeren voor een specifiek component**:
  ```bash
  .venv/bin/pytest tests/ui_verification/ -k <component_id>
  ```
