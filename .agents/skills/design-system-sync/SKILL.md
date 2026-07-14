---
name: design-system-sync
description: Handelingen voor het wijzigen van UI-stijlen in njorddeploy-design-system en het synchroniseren hiervan naar de NjordDeploy-app.
---

# UI Stijlen & Design System Synchronisatie

Gebruik deze skill wanneer de gebruiker vraagt om UI-stijlen, CSS, of design-system wijzigingen door te voeren.

## Belangrijke Richtlijnen:
1. **Pas NOOIT direct** `njorddeploy-style.css` aan in de configurator of editor app van `NjordDeploy`.
2. Alle stijlaanpassingen moeten worden gedaan in de repository `njorddeploy-design-system`.
3. Na het aanpassen van de stijlen in `njorddeploy-design-system`, moet je het synchronisatiescript uitvoeren om de wijzigingen over te zetten.

## Synchronisatie Workflow:
1. Navigeer naar het project `NjordDeploy`.
2. Voer het script uit met het volgende commando:
   ```bash
   python scripts/fetch_assets.py
   ```
3. Controleer of de bestanden in `NjordDeploy/src/configurator_app/static/css/` correct zijn bijgewerkt.
4. Commit de wijzigingen in beide repositories als dat nodig is.
