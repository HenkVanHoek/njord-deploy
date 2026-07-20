---
name: code-quality
description: Richtlijnen en commando's voor codekwaliteit, linting en unit-testing met pytest, flake8, mypy en pre-commit specifiek voor NjordDeploy.
---

# Code Kwaliteit & Unit Testing (NjordDeploy)

Gebruik deze skill om codekwaliteit te garanderen en tests uit te voeren binnen het NjordDeploy project.

### Alles-in-één Code Kwaliteit Check (Python & JavaScript)
Je kunt de volledige controle lokaal en token-vrij uitvoeren met het meegeleverde script:
```bash
./scripts/check_code_quality.sh
```
Dit script voert alle Python-checks uit (via pre-commit) en controleert vervolgens alle JavaScript-bestanden met ESLint. Dit is de snelste en meest token-efficiënte methode om te controleren of alle code clean is.

## Python Code Richtlijnen:
* PEP 8 conformiteit.
* Maximale regellengte: 88 karakters.
* Code moet alle `flake8`- en `mypy`-controles doorstaan.

## JavaScript Code Richtlijnen:
* Geen inline JavaScript. Logica moet altijd in externe `.js`-bestanden worden geplaatst.
* JavaScript moet linter-clean zijn.

## Commando's voor controle:

### 1. Testen draaien (Pytest):
```bash
.venv/bin/pytest
```

### 2. Linting (Flake8):
```bash
.venv/bin/flake8
```

### 3. Statische Analyse (Mypy):
```bash
.venv/bin/mypy .
```

### 4. Pre-commit Checks:
```bash
.venv/bin/pre-commit run --all-files
```

### 5. PyCharm IDE Diagnostics (JetBrains Companion):
Als de agent gebruikmaakt van de JetBrains Companion MCP-server, kan de agent live diagnostische waarschuwingen, type-fouten en inspecties rechtstreeks uit de IDE ophalen met de tool:
* Tool: `ide_get_diagnostics` (MCP server: `jetbrains-companion-py-dbb56c69`)
* Parameter: `file_path` (optioneel, absolute pad naar het bestand om te inspecteren. Indien weggelaten, wordt de actieve editor gebruikt)

Dit stelt de agent in staat om live IDE-waarschuwingen op te vragen en direct op te lossen.

*Belangrijke opmerking bij grote bestanden:* De uitvoer van `ide_get_diagnostics` is gelimiteerd tot maximaal 100 meldingen. Als een bestand veel syntax-highlighting of JSDoc type-informatie (`INFO`) bevat, worden waarschuwingen/fouten verderop in het bestand mogelijk niet gerapporteerd doordat de limiet is bereikt. Gebruik in dat geval aanvullende lokale tools (zoals ESLint).

### 6. Veelvoorkomende PyCharm waarschuwingen & oplossingen:
Bij het oplossen van type- en inspectiewaarschuwingen uit PyCharm gelden de volgende richtlijnen:

#### Python-specifiek:
1. **Access to a protected member (bijv. `_get_or_create_key`):**
   * *Oplossing:* Exposeer de methode als een publieke wrapper op de klasse (bijv. `get_ssh_key()`) in plaats van de private `_` methode direct aan te roepen vanaf een extern script.
2. **Member 'None' of 'Any | None' does not have attribute 'get':**
   * *Oplossing:* Gebruik `isinstance(variable, dict)` als guard om het type voor PyCharm's analyzer te vernauwen naar een dictionary.
3. **Expected type 'str', got 'Any | None' instead:**
   * *Oplossing:* Gebruik `isinstance(variable, str)` als guard om het type voor PyCharm te specificeren en te garanderen dat het een string is.
4. **Too broad exception clause:**
   * *Oplossing:* Plaats `# noinspection PyBroadException` direct **boven het bijbehorende `try:`-blok** (niet boven het `except:`-blok).
5. **Shadows name '...' from outer scope:**
   * *Oplossing:* Hernoem de lokale variabele om te voorkomen dat deze een functienaam of variabele uit een buitenliggende scope (bijv. de `create_app` factory scope) overschrijft.
6. **Expected type 'str | PathLike[str]', got 'str | bytes' instead (bijv. bij `os.path.realpath`):**
   * *Oplossing:* Gebruik `pathlib` methoden zoals `Path.resolve()` en zet dit zo nodig om met `str(path)` of `str(path.resolve())` in plaats van `os.path.realpath`. Dit voorkomt dat de type-checker van PyCharm vermoedt dat er `bytes` kunnen worden geretourneerd.
7. **Redundant parentheses (bijv. rondom string-concatenatie):**
   * *Oplossing:* Haakjes rondom twee opeenvolgende string literals die door Python automatisch worden samengevoegd (bijv. `("a" "b")`) zijn overbodig voor de IDE en moeten worden weggelaten.

#### JavaScript- & JSDoc-specifiek:
1. **Redundant CSS unit in style attributes (bijv. `0%` of `0px`):**
   * *Oplossing:* De CSS-inspectie waarschuwt dat `0` geen eenheid nodig heeft. Pas bijvoorbeeld `style="width: 0%;"` aan naar `style="width: 0;"`.
2. **Argument type number is not assignable to parameter type string (bijv. bij `setAttribute`):**
   * *Oplossing:* `element.setAttribute(name, value)` vereist dat de value een string is. Converteer getallen expliciet naar strings met `String(value)` of door string-interpolatie (bijv. `'100'`).
3. **Assigned expression type { ... } is not assignable to type X (JSDoc type mismatch):**
   * *Oplossing:* Als een object wordt geïnitialiseerd zonder bepaalde eigenschappen die wel in de `@typedef` van type `X` zijn gedefinieerd, geeft PyCharm een type-fout. Maak optionele eigenschappen in de `@typedef` optioneel met vierkante haken (bijv. `* @property {string} [mac]` of `* @property {DiskInfo[]} [disks]`).
4. **Ignored promise returned from async function:**
   * *Oplossing:* Maak de event-listeners of callbacks asynchroon (`async () => { ... }`) en roep de methode aan met `await` (bijv. `await showDiffForComponent(...)` of `await setupGitSyncFeatures()`).

### 7. Handmatige JavaScript linting (ESLint):
Mochten er geen pre-commit hooks voor JavaScript geactiveerd zijn, dan kan ESLint handmatig gedraaid worden met een tijdelijk `.eslintrc.json` bestand in de root:
```bash
# Draai eslint op alle js bestanden
eslint src/editor_app/static/*.js src/configurator_app/static/js/*.js
```
