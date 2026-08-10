# Voorstel Herziening Component Beschrijvingen (`config/components_metadata.json`)

Dit document bevat het volledige overzicht en voorstel voor het verbeteren van de `description` velden van de services in `config/components_metadata.json`.

---

## 1. Samenvatting van de Analyse

Na een grondige inspectie van alle **52 componenten** in `config/components_metadata.json` zijn de volgende categorieën problemen ontdekt:

1. **Ontbrekende beschrijving (1 component):**
   - `lora-service`: Heeft een lege string (`""`).
2. **Onprofessionele of interne notities (2 componenten):**
   - `conduit`: Bevat een notitie over ontbrekende tools op Raspberry Pi ("*But no working management tool available for on the Raspberry Pi.*").
   - `web-notepad`: Verwijst naar een interne post-install functionaliteit ("*Simple notepad to display the post-install summary.*").
3. **Opmaak- & Typefouten (2 componenten):**
   - `uptime-kuma`: Begint met een spatie (`" A self-hosted..."`) en mist een punt op het einde.
   - `grafana`: Mist een punt op het einde.
4. **Te korte / magere beschrijvingen (25 componenten):**
   - Diverse services zoals `radarr` ("*A fork of Sonarr to work with movies.*"), `frigate`, `scrypted`, `sonarr`, `qbittorrent` en `pi-hole` hebben erg beknopte zinnen die onvoldoende context bieden voor de eindgebruiker.

---

## 2. Gedetailleerd Overzicht van Voorstellen

### Categorie A: Kritieke Aanpassingen (Ontbrekend, Opmerkingen of Fouten)

| Component ID | Service Naam | Huidige Beschrijving | Voorgestelde Nieuwe Beschrijving | Reden van aanpassing |
| :--- | :--- | :--- | :--- | :--- |
| `lora-service` | LoRa Letterbox Notifier | `""` | `A smart home IoT notification service that monitors LoRa-enabled mailbox sensors and sends real-time alert notifications when physical mail is delivered.` | Beschrijving ontbrak volledig. |
| `conduit` | Conduit (Matrix Server) | `A lightweight, next-generation Matrix homeserver, ideal for Raspberry Pi. But no working management tool available for on the Raspberry Pi.` | `A high-performance, lightweight Matrix chat homeserver written in Rust, specifically optimized for low-resource environments like the Raspberry Pi.` | Verwijdering van niet-professionele opmerking en verduidelijking van de technologie (Rust). |
| `uptime-kuma` | Uptime Kuma | ` A self-hosted monitoring tool for proactive health checks and notifications via email, Telegram, and more` | `A feature-rich, self-hosted monitoring tool providing real-time status pages, HTTP/ping health checks, and alerts via multiple notification channels.` | Verwijdering voorste spatie, toevoegen leesteken en verrijking van functies. |
| `grafana` | Grafana Stack | `The open-source platform for monitoring and observability` | `An open-source visualization and analytics platform that turns metrics and logs into dynamic, interactive dashboards for comprehensive system observability.` | Leesteken toegevoegd en verduidelijking van de dashboarding-functionaliteit. |
| `web-notepad` | Web Notepad | `Simple notepad to display the post-install summary.` | `A minimal, web-based notepad application for quick note-taking, text sharing, and viewing system post-deployment summaries.` | Verwijdering van te specifieke interne focus. |

---

### Categorie B: Inhoudelijke Verrijking van Beknopte Services

| Component ID | Service Naam | Huidige Beschrijving | Voorgestelde Nieuwe Beschrijving | Reden van aanpassing |
| :--- | :--- | :--- | :--- | :--- |
| `radarr` | Radarr | `A fork of Sonarr to work with movies.` | `An automated movie collection manager and PVR that monitors RSS feeds for new releases, triggers download clients, and automatically organizes media files.` | Meer context over PVR en geautomatiseerde functies. |
| `sonarr` | Sonarr | `Smart PVR for newsgroup and bittorrent users to manage and download TV shows.` | `An automated TV series collection manager and PVR that tracks upcoming episodes, triggers downloads via Usenet or BitTorrent, and organizes show libraries.` | Professionelere formulering en duidelijke functionaliteit. |
| `qbittorrent` | qBittorrent | `A lightweight and powerful BitTorrent client.` | `A lightweight, open-source BitTorrent download client featuring a full-featured web interface, bandwidth scheduling, and built-in search engines.` | Meer specificatie van de web UI en zoekmogelijkheden. |
| `sabnzbd` | SABnzbd | `The popular and easy-to-use Usenet download client.` | `An automated Usenet binary newsreader and download manager featuring automatic repair, unpacking, and seamless PVR stack integration.` | Uitleg van automatische uitpak- en herstel functionaliteit. |
| `frigate` | Frigate | `NVR with real-time object detection for IP cameras.` | `A high-performance Network Video Recorder (NVR) with local, real-time AI object detection using Coral TPU or CPU for IP security cameras.` | Verduidelijking van AI objectdetectie (Coral TPU/CPU). |
| `scrypted` | Scrypted | `High-performance video integration platform for smart homes.` | `A high-performance smart home video integration platform that bridges IP camera feeds to Apple HomeKit, Google Home, and Alexa with hardware acceleration.` | Specificeert platformen (HomeKit, Google Home, Alexa). |
| `portainer` | Portainer | `A powerful management UI for Docker environments.` | `A powerful, user-friendly management UI that simplifies configuring, monitoring, and deploying Docker containers, stacks, and persistent volumes.` | Meer detail over wat er via de UI beheerd wordt. |
| `heimdall` | Heimdall | `A simple and elegant application dashboard.` | `An elegant, customizable application dashboard for organizing shortcuts and status widgets for all your self-hosted web services.` | Verrijking van de dashboard functionaliteit. |
| `homarr` | Homarr | `A simple, yet powerful dashboard for your server.` | `A modern, customizable server dashboard with direct integrations for monitoring homelab services, Docker container statuses, and media clients.` | Duidelijkere beschrijving van integraties. |
| `homer` | Homer | `A dead simple, static homepage for your server.` | `A lightweight, static application dashboard configured via YAML, designed for fast landing-page access to all your homelab services.` | Vervanging van informeel taalgebruik ("dead simple"). |
| `organizr` | Organizr | `A full-featured server organizer with a tabbed interface.` | `A unified server management portal that organizes all your self-hosted applications into a single tabbed interface with custom user permissions.` | Meer detail over de portal- en rechtenstructuur. |
| `pi-hole` | Pi-hole | `A network-wide ad blocker that acts as a DNS sinkhole.` | `A network-wide ad and tracker blocker that functions as a DNS sinkhole, protecting all local network devices without requiring client-side software.` | Duidelijker effect op alle netwerkapparaten. |
| `unbound` | Unbound | `A validating, recursive, and caching DNS resolver for maximum privacy.` | `A secure, validating, recursive, and caching DNS resolver designed for privacy, preventing upstream ISP DNS logging when paired with Pi-hole or AdGuard.` | Contextuele toevoeging over privacy i.c.m. Pi-hole/AdGuard. |
| `unifi-controller` | UniFi Controller | `Manage your UniFi networking devices from a central controller.` | `A centralized management software suite for configuring, monitoring, and updating Ubiquiti UniFi network devices such as access points, switches, and gateways.` | Verduidelijking van Ubiquiti apparatuur. |
| `zigbee2mqtt` | Zigbee2MQTT | `Bridge the gap between your Zigbee devices and your MQTT broker.` | `A lightweight bridge that connects Zigbee smart home devices directly to an MQTT broker, enabling local control via Home Assistant or custom automation software.` | Verduidelijking van de integratie met smart home systemen. |
| `phpmyadmin` | phpMyAdmin | `Web interface for managing MySQL and MariaDB databases.` | `A comprehensive web-based administration tool for managing MySQL and MariaDB databases, executing SQL queries, and managing user access control.` | Uitgebreidere omschrijving van de functies. |
| `nextcloud` | Nextcloud | `File storage, sharing, productivity and collaboration platform.` | `A comprehensive self-hosted productivity and collaboration suite offering secure file storage, online document editing, calendar, and contacts synchronization.` | Toevoeging van specifieke functies (documenten, agenda, contacten). |
| `nextcloud-db` | Nextcloud MariaDB | `Relational MariaDB database tailored for Nextcloud.` | `A dedicated, pre-configured MariaDB relational database server optimized for Nextcloud persistent data storage and high query performance.` | Meer achtergrond over optimalisatie. |
| `nextcloud-db-dumper` | Nextcloud DB Dumper | `Automated backup container for Nextcloud MariaDB database.` | `An automated backup utility container that periodically exports SQL dumps of the Nextcloud MariaDB database for disaster recovery.` | Meer achtergrond over SQL dumps en disaster recovery. |
| `nextcloud-redis` | Nextcloud Redis Cache | `In-memory caching and lock broker for Nextcloud.` | `An in-memory Redis datastore configured as a high-performance transactional file locking broker and caching layer for Nextcloud.` | Duidelijkere technische omschrijving. |
| `octoprint` | OctoPrint | `The snappy web interface for your 3D printer.\nSee https://octoprint.org for more information.` | `A web-based interface for remote 3D printer management, providing real-time print monitoring, G-code visualization, and live camera streaming.` | Schonen van URL en toevoegen van functies (G-code, webcam). |
| `filebrowser` | Filebrowser | `Web-based file manager for managing your self-hosted data files and Caddyfile.` | `A lightweight web-based file manager allowing users to upload, edit, delete, preview, and share files on server storage volumes.` | Verwijdering van specifieke Caddyfile notitie voor algemenere inzetbaarheid. |
| `audiobookshelf` | Audiobookshelf | `Self-hosted audiobook and podcast server to manage and play your audiobooks and podcasts.` | `A self-hosted audiobook and podcast server for organizing, streaming, and tracking playback progress across your personal audio media library.` | Schonen van dubbele woorden en verrijken van progressie tracking. |
| `gluetun` | Gluetun | `Lightweight swiss-army-knife-like VPN client to multiple VPN service providers.` | `A lightweight, multi-provider VPN client container supporting OpenVPN and WireGuard protocols to route Docker service traffic securely.` | Vervanging informeel taalgebruik door technische specificaties (OpenVPN/WireGuard). |
| `njorddeploy-service-maintenance` | Service Maintenance | `Monitor status, updates and vulnerabilities.` | `A system management component for monitoring service health, checking software updates, and auditing container vulnerabilities across NjordDeploy services.` | Omzetten van zinsfragment naar volledige zinsbouw. |

---

### Categorie C: Reeds Volledige / Goede Beschrijvingen (Geen wijziging nodig)

De volgende 22 componenten hebben reeds een uitstekende, accurate en voldoende gedetailleerde beschrijving in de metadata:

- `adguard-home`
- `adminer`
- `caddy`
- `docker-jitsi-meet`
- `gitlab`
- `homeassistant`
- `homepage`
- `jellyfin`
- `microbin`
- `n8n`
- `nginx-proxy-manager`
- `notify-push`
- `open-webui`
- `pish-fluffychat-web`
- `prometheus`
- `prosody`
- `prowlarr`
- `semaphore`
- `stirling-pdf`
- `traefik`
- `vaultwarden`
- `voicebox`

---

## 3. Uitvoeringsplan na Goedgekeurd Voorstel

Zodra je dit voorstel goedkeurt, kan de update automatisch worden uitgevoerd door middel van een Python script dat `config/components_metadata.json` op een schone, geformatteerde (JSON met 4 spaties inspringen) wijze bijwerkt.
