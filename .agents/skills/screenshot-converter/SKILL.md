---
name: screenshot-converter
description: Automatisch converteren van BMP/bitmap screenshots naar PNG om MIME-type leesfouten te voorkomen.
---

# Screenshot Converter (BMP to PNG)

Gebruik deze skill om te bepalen hoe om te gaan met geüploade afbeeldingen die niet direct worden ondersteund door `view_file` (zoals `.bmp` bestanden).

## Werkwijze bij het ontvangen van een BMP/Bitmap screenshot:

Als de gebruiker een afbeelding uploadt met de extensie `.bmp` (of een ander niet-ondersteund formaat), mag je **niet** direct proberen deze met `view_file` te bekijken (dit veroorzaakt een MIME-type fout). Volg in plaats daarvan de volgende stappen:

### 1. Converteer de afbeelding via het script:
Voer het conversiescript uit in de terminal:
```bash
python3 .agents/skills/screenshot-converter/scripts/convert.py "/absolute/pad/naar/bestand.bmp"
```

### 2. Open het geconverteerde PNG-bestand:
Gebruik hierna de `view_file` tool om het nieuw gegenereerde `.png` bestand te bekijken.

### 3. Rapporteer/antwoord aan de gebruiker:
Beantwoord de vraag van de gebruiker direct aan de hand van de geconverteerde screenshot, zonder dat de gebruiker hier extra actie voor hoeft te ondernemen of handmatig toestemming hoeft te geven.
