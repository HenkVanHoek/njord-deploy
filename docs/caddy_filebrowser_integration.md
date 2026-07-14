# Handleiding: Caddy en FileBrowser integratie voor Sovereign Stack

Deze instructie beschrijft hoe je zowel de Caddy-server als een visuele beheeromgeving opzet. Caddy en FileBrowser zijn nu gedefinieerd als twee afzonderlijke componenten. Dit biedt de flexibiliteit om FileBrowser ook los te installeren, of ze samen te installeren via het **Caddy & Filebrowser Stack** package.

### 1. De Architectuur

We koppelen de FileBrowser-container aan de gedeelde data-map (`DATA_ROOT`) van de Sovereign Stack op het host-systeem.

* **Caddy:** Draait als de reverse proxy. De configuratiebestanden bevinden zich in `{{ DATA_ROOT }}/caddy/`.
* **FileBrowser:** Draait als een visuele bestandsbeheerder en geeft toegang tot de gehele `{{ DATA_ROOT }}`-map op de host, inclusief de configuratiemap van Caddy.

### 2. Component Templates

Wanneer beide componenten worden geselecteerd (of via het package), genereert de Sovereign Stack een samengevoegde `docker-compose.yml` met daarin de volgende definities:

#### Caddy Service Fragment:
```yaml
services:
  caddy:
    image: caddy:latest
    container_name: caddy
    restart: unless-stopped
    ports:
      - "{{ CADDY_HTTP_PORT }}:80"
      - "{{ CADDY_HTTPS_PORT }}:443"
      - "{{ CADDY_HTTPS_PORT }}:443/udp"
    volumes:
      - "{{ DATA_ROOT }}/caddy/Caddyfile:/etc/caddy/Caddyfile"
      - "{{ DATA_ROOT }}/caddy/data:/data"
      - "{{ DATA_ROOT }}/caddy/config:/config"
    networks:
      - njorddeploy_net
```

#### FileBrowser Service Fragment:
```yaml
services:
  filebrowser:
    image: filebrowser/filebrowser:latest
    container_name: filebrowser
    restart: unless-stopped
    environment:
      - FB_DATABASE=/database/filebrowser.db
    volumes:
      - "{{ DATA_ROOT }}:/srv"
      - "{{ DATA_ROOT }}/filebrowser/database:/database"
      - "{{ DATA_ROOT }}/filebrowser/config:/config"
    ports:
      - "{{ FILEBROWSER_WEB_PORT }}:80"
    networks:
      - njorddeploy_net
```

### 3. Instructies voor de gebruiker

Wanneer de services zijn geïnstalleerd, kan de gebruiker de volgende stappen volgen:

* **Toegang:** Navigeer naar het IP-adres van de Raspberry Pi op de poort die is ingesteld voor FileBrowser (standaard `8080`).
* **Inloggen:** De standaard inloggegevens zijn `admin` / `adminadminadmin` (vanwege de minimale wachtwoordlengte van 12 tekens). (Advies: verander dit direct na de eerste keer inloggen via Settings).
* **Configuratie bewerken:**
1. Navigeer in FileBrowser naar de map `caddy/`.
2. Open de `Caddyfile` door erop te klikken.
3. Voer de gewenste wijzigingen of reverse proxy routes in.
4. Klik op Save.

* **Herladen van Caddy:**
* Voer in de terminal van de host uit: `docker exec caddy caddy reload`.
* Indien FileBrowser is geconfigureerd met command execution, kan dit ook via een Custom Command in de FileBrowser-interface.

### 4. Belangrijke notitie voor de beheerder

* **Persistentie:** Alle wijzigingen die je in de Caddyfile of andere configuratiebestanden maakt via FileBrowser worden direct weggeschreven naar de host-machine. Deze blijven behouden na een container-restart.
* **SST Waarschuwing:** Handmatige wijzigingen in de Caddyfile via FileBrowser worden niet automatisch teruggekoppeld naar de Sovereign Stack configuratie-database. Gebruik FileBrowser met name voor ad-hoc aanpassingen of als u volledig overgaat op handmatig beheer.
