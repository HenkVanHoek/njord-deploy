---
name: ui-test
description: Richtlijnen en workflows voor het geautomatiseerd testen van component-UI's met Playwright.
---

# UI Verification Testing for Deployed Components

Gebruik deze skill om Playwright E2E-testen te schrijven en uit te voeren voor NjordDeploy componenten die een web-interface hebben (zoals Uptime Kuma, AdGuard Home, Pi-hole, enzovoort).

---

## 1. Hoe het Werkt (Architectuur)

Omdat de Proxmox test-runner componenten op dynamisch aangemaakte VM's of LXC-containers deployt, is het IP-adres van tevoren niet bekend. Daarom gebruiken we de volgende workflow:

1. **Deployment & Opslag**: De Proxmox test-runner (`proxmox_test_runner.py`) deployt het component en slaat het actieve IP-adres op in `tests/proxmox_results.json`.
2. **IP Resolving**: Onze UI-test scripts lezen `tests/proxmox_results.json` uit om het dynamische IP-adres en de poort van de actieve service te achterhalen.
3. **Playwright E2E**: Playwright start een browser, navigeert naar het adres, en voert de UI-controles uit (zoals het controleren of de setup-pagina laadt of dat er geen JS-fouten in de console verschijnen).

---

## 2. Testen Schrijven (Python + Pytest-Playwright)

Plaats UI-verificatietesten in de map `tests/ui_verification/` en gebruik de naamgeving `<component_id>_ui_test.py`.

### Voorbeeld: `tests/ui_verification/uptime_kuma_ui_test.py`

```python
import json
import re
from pathlib import Path
from playwright.sync_api import Page, expect

def get_deployed_component_ip(component_id: str) -> str:
    """Leest het dynamische IP-adres van het component uit de testresultaten."""
    results_path = Path(__file__).resolve().parent.parent / "proxmox_results.json"
    if not results_path.exists():
        raise FileNotFoundError(
            f"Testresultaten niet gevonden op {results_path}. "
            "Voer eerst de proxmox test-runner uit."
        )

    with open(results_path, "r", encoding="utf-8") as f:
        results = json.load(f)

    for record in results:
        if record.get("component_id") == component_id:
            if record.get("status") == "success" and record.get("ip"):
                return record["ip"]

    raise ValueError(f"Component {component_id} is niet succesvol gedeployed in de laatste run.")

def test_uptime_kuma_ui(page: Page):
    # 1. Haal IP op van de actieve test-container
    ip = get_deployed_component_ip("uptime-kuma")
    url = f"http://{ip}:3001"

    # 2. Navigeer naar de Uptime Kuma setup-pagina
    page.goto(url, timeout=10000)

    # 3. Valideer de UI elementen
    # Controleer of de setup/taalkeuze pagina laadt (Uptime Kuma setup)
    expect(page).to_have_title(re.compile("Uptime Kuma", re.IGNORECASE))

    # Controleer of specifieke formulier-elementen of knoppen aanwezig zijn
    expect(page.locator("select")).to_be_visible()
```

---

## 3. UI Testen Uitvoeren

Zorg er eerst voor dat het component actief is op Proxmox (bijv. via de test-runner in LXC-modus zonder teardown, of direct na een run):

```bash
# 1. Start de Proxmox test-runner (LXC-modus slaat de IP op in json)
.venv/bin/python scripts/proxmox_test_runner.py --components uptime-kuma --mode lxc

# 2. Voer de Playwright UI-test uit
.venv/bin/pytest tests/ui_verification/ -k uptime_kuma
```

---

## 4. Richtlijnen voor UI Testen

* **Geen hardcoded IP's**: Haal het IP-adres altijd dynamisch op via `get_deployed_component_ip`.
* **Headless execution**: Testen draaien standaard in headless-modus. Als je visueel wilt debuggen tijdens ontwikkeling, gebruik dan de `--headed` vlag:
  ```bash
  .venv/bin/pytest tests/ui_verification/ -k uptime_kuma --headed
  ```
* **Foutafhandeling**: Controleer op foutmeldingen in de console (bijvoorbeeld met `page.on("console", ...)` in Playwright) om verborgen Javascript-crashes te detecteren.
* **Teardown**: Aangezien de Proxmox test-runner de container direct weer vernietigt na de run, is het voor UI-testen handig om de container tijdelijk te behouden (bijvoorbeeld door een debug-modus in te schakelen) als je handmatig of met Playwright langere sessies wilt simuleren.
