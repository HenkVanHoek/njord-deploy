---
name: code-quality
description: Richtlijnen en commando's voor codekwaliteit, linting en unit-testing met pytest, flake8, mypy en pre-commit specifiek voor NjordDeploy.
---

# Code Kwaliteit & Unit Testing (NjordDeploy)

Gebruik deze skill om codekwaliteit te garanderen en tests uit te voeren binnen het NjordDeploy project.

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
