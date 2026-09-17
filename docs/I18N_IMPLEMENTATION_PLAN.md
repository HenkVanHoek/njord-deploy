# Architectuur- & Implementatieplan: Meertaligheid (i18n / l10n) NjordDeploy

## 1. Doel & Visie
Het doel is om de NjordDeploy webapplicatie (Configurator & Editor) meertalig te maken, te beginnen met **Nederlands (NL)** en **Engels (EN)**.
Dit sluit naadloos aan op de reeds meertalige marketingwebsite (`njorddeploy.com`) en de AI-chatbot, waardoor de gebruikerservaring uniform en toegankelijk wordt voor zowel Nederlandse homelabbers/IT-beheerders als de internationale community.

---

## 2. Kernprincipes (KISS & Air Traffic Control)
1. **Keep It Simple, Stupid (KISS)**:
   - Geen onnodig zware dependencies of complexe compilatiestappen voor vertaalbestanden als een lichte JSON/dictionary-gebaseerde i18n-engine of Flask-Babel volstaat.
   - Snelle en transparante lookup met fallback naar Engels (EN).
2. **Geen breekbare wijzigingen in API-contracten**:
   - De technische ID's, component-sleutels en configuratiedata (`components_metadata.json`, Docker Compose-variabelen) blijven **100% identiek** en Engelstalig.
   - Alleen presentatielagen (UI-labels, knoppen, categorieën, beschrijvingen en meldingen) worden vertaald.
3. **Persistente Taalkeuze**:
   - Automatische herkenning via de browser-header (`Accept-Language`).
   - Expliciete overschrijving via een taalschakelaar in de navigatiebalk (vlaggetjes 🇬🇧 / 🇳🇱), opgeslagen in `session['lang']` en een cookie.

---

## 3. Fasering van het Project

### Fase 1: De i18n Core Engine & Sessiebeheer (Backend)
- **Doel**: Een centrale `TranslationManager` of `Flask-Babel` integratie opzetten in `src/utils/i18n.py`.
- **Functies**:
  - `get_locale()`: Bepaalt de actieve taal (Sessie > Cookie > Accept-Language header > Default `'en'`).
  - Jinja2 context processor: Registreert `{{ _('Key') }}` en `{{ current_locale }}` in alle templates.
  - API endpoint `/api/v1/set-language/<lang_code>` om direct te wisselen zonder herlaadproblemen.
- **Vertaalbron**:
  - Eenvoudige, versiebeheerde JSON-bestanden onder `src/locales/en.json` en `src/locales/nl.json`.

### Fase 2: Navigatiebalk & Basis UI Sjablonen (Frontend)
- **Doel**: De algemene interface (kopteksten, menu's, statussen en knoppen) vertalen.
- **Acties**:
  - Taalschakelaar toevoegen aan de navigatiebalk in `src/configurator_app/templates/base.html` en `src/editor_app/templates/base.html` (met de bestaande SVG vlaggen van de website: `en.svg`, `nl.svg`).
  - Algemene strings vervangen door `{{ _('...') }}` in:
    - Navigatie (Deploy, Editor, Backups, MSP / Fleet, Terminal, Logs, Settings).
    - Statusbalken (Verbonden, Offline, Installeren, Voltooid).
    - Modals (Bevestiging voor deployment, backup-herstel, herstarten).

### Fase 3: Componentcatalogus & Metadata Lokalisatie
- **Doel**: Vriendelijke en begrijpelijke beschrijvingen voor de 100+ componenten in het Nederlands.
- **Architectuur**:
  - Voorkomen dat `components_metadata.json` vervuild raakt: we voegen een vertaallayer toe (bijv. `src/locales/components_nl.json` of optionele velden `description_nl` / `display_name_nl`).
  - Bij weergave in de Configurator filtert de `ComponentManager` automatisch op de actieve sessietaal.

### Fase 4: JavaScript Notificaties & Client-side Strings
- **Doel**: Dynamische popups (SweetAlert2, error toasts, validatiemeldingen) vertalen.
- **Acties**:
  - Een lichtgewicht client-side mapping object injecteren via `window.NJORD_I18N`.
  - JS-hulpfunctie `window.t('key')` voor dynamische meldingen in `main.js` en `configurator.js`.

---

## 4. Verificatie & Test-Driven Development (TDD)
- Unit tests toevoegen in `tests/test_i18n.py`:
  - Test taalwissel via sessie en endpoint.
  - Test fallback naar Engels bij ontbrekende vertaalsleutels.
  - Test formatting met parameters (bv. `_('Installing {component}...', component='AdGuard')`).
- Playwright UI-verificatie op Proxmox / lokale browser:
  - Controle van de weergave en persistentie van de taalschakelaar.
