# NjordDeploy Component & Stack Catalog

This catalog contains all 100% test-verified self-hosted software components
and turnkey application packages available in the NjordDeploy ecosystem.
Each component folder includes its own dedicated `README.md` with
architecture details, default ports, volume specifications, and quick start guides.

---

## 📦 Turnkey Application Stacks

| Stack | Bundle Tier | Components | Description |
|---|---|---|---|
| [Agile Operations & Secure Chat](stacks/agile-ops/README.md) | MSP Turnkey Bundle | [`vikunja`](component_templates/vikunja/README.md), [`focalboard`](component_templates/focalboard/README.md), [`gitea`](component_templates/gitea/README.md), [`conduit`](component_templates/conduit/README.md), [`memos`](component_templates/memos/README.md) | Agile project execution and encrypted collaboration workstation bundling Vikunja task management, Focalboard Kanban s... |
| [Reverse Proxy & Remote Workspace](stacks/caddy-filebrowser-stack/README.md) | Web & Utilities | [`caddy`](component_templates/caddy/README.md), [`filebrowser`](component_templates/filebrowser/README.md) | Caddy automated HTTPS reverse proxy paired with FileBrowser for instant web-based file and configuration management. |
| [Digital Archive & Document Compliance](stacks/digital-archive/README.md) | MSP Turnkey Bundle | [`paperless-ngx`](component_templates/paperless-ngx/README.md), [`stirling-pdf`](component_templates/stirling-pdf/README.md), [`actual-budget`](component_templates/actual-budget/README.md), [`nocodb`](component_templates/nocodb/README.md) | Paperless office and compliance workstation bundling Paperless-ngx automated OCR document scanning, Stirling-PDF sove... |
| [DNS & Ad-Blocking Privacy Shield](stacks/dns-shield-stack/README.md) | Security & Privacy | [`adguard-home`](component_templates/adguard-home/README.md), [`unbound`](component_templates/unbound/README.md) | Network-wide privacy barrier bundling AdGuard Home DNS sinkhole with Unbound recursive DNS resolver for zero-ISP trac... |
| [Immich Photo & Kiosk Suite](stacks/immich-stack/README.md) | Photo Hub | [`immich`](component_templates/immich/README.md), [`immich-kiosk`](component_templates/immich-kiosk/README.md) | Sovereign AI-powered photo and video management with Immich, paired with Immich Kiosk for ambient digital photo frame... |
| [Media Streaming & Servarr Suite](stacks/media-stack/README.md) | Media Suite | [`jellyfin`](component_templates/jellyfin/README.md), [`radarr`](component_templates/radarr/README.md), [`sonarr`](component_templates/sonarr/README.md), [`prowlarr`](component_templates/prowlarr/README.md), [`jellyseerr`](component_templates/jellyseerr/README.md), [`qbittorrent`](component_templates/qbittorrent/README.md), [`bazarr`](component_templates/bazarr/README.md) | Unified sovereign media streaming pipeline bundling Jellyfin media server, Radarr (movies), Sonarr (TV shows), Prowla... |
| [The Modern Sovereign Workplace](stacks/modern-workplace/README.md) | MSP Turnkey Bundle | [`nextcloud`](component_templates/nextcloud/README.md), [`nextcloud-db`](component_templates/nextcloud-db/README.md), [`nextcloud-redis`](component_templates/nextcloud-redis/README.md), [`nextcloud-db-dumper`](component_templates/nextcloud-db-dumper/README.md), [`notify-push`](component_templates/notify-push/README.md), [`vaultwarden`](component_templates/vaultwarden/README.md) | Turnkey Microsoft 365 & Google Workspace alternative bundling enterprise Nextcloud Hub, dedicated MariaDB, Redis cach... |
| [Observability & Privacy Analytics](stacks/observability-analytics/README.md) | MSP Turnkey Bundle | [`beszel`](component_templates/beszel/README.md), [`prometheus`](component_templates/prometheus/README.md), [`grafana`](component_templates/grafana/README.md), [`plausible`](component_templates/plausible/README.md), [`uptime-kuma`](component_templates/uptime-kuma/README.md) | Full-stack server fleet observability and GDPR-compliant website analytics bundling Beszel lightweight metrics, Prome... |
| [Open WebUI & Ollama AI Studio](stacks/open-webui-ollama/README.md) | AI & LLM Stack | [`ollama`](component_templates/ollama/README.md), [`open-webui`](component_templates/open-webui/README.md), [`litellm`](component_templates/litellm/README.md) | Integrated sovereign AI chatbot and inference platform combining Open WebUI with the local Ollama LLM engine and Lite... |
| [Sovereign Smart Home Hub](stacks/smarthome-stack/README.md) | Smart Home & IoT | [`homeassistant`](component_templates/homeassistant/README.md), [`esphome`](component_templates/esphome/README.md), [`node-red`](component_templates/node-red/README.md), [`scrypted`](component_templates/scrypted/README.md) | Local home automation workstation combining Home Assistant, ESPHome firmware builder, Node-RED visual logic orchestra... |

---

## 🧩 Individual Components Catalog

### AI & LLM Services

| Component | Description | Upstream | Dedicated README |
|---|---|---|---|
| `librechat` | LibreChat is a self-hosted AI chat platform that unifies all major AI providers in a single, privacy-focuse... | LibreChat | [View README](component_templates/librechat/README.md) |
| `litellm` | LiteLLM is an AI gateway and LLM proxy that unifies access to 100+ Large Language Models (OpenAI, Gemini, A... | [LiteLLM AI Gateway](https://github.com/BerriAI/litellm) | [View README](component_templates/litellm/README.md) |
| `ollama` | Ollama is an open-source, lightweight, and extensible framework for running Large Language Models (LLMs) lo... | Ollama LLM Engine | [View README](component_templates/ollama/README.md) |
| `open-webui` | Open WebUI is an extensible, feature-rich, and user-friendly web interface for AI models and LLMs, supporti... | [Open WebUI](https://openwebui.com/) | [View README](component_templates/open-webui/README.md) |

### DNS Blocker

| Component | Description | Upstream | Dedicated README |
|---|---|---|---|
| `adguard-home` | AdGuard Home is a free and open-source network-wide software for blocking ads and tracking. It operates as ... | [AdGuard Home](https://adguard.com/en/adguard-home/overview.html) | [View README](component_templates/adguard-home/README.md) |
| `pi-hole` | A network-wide ad and tracker blocker that functions as a DNS sinkhole, protecting all local network device... | [Pi-hole](https://pi-hole.net/) | [View README](component_templates/pi-hole/README.md) |
| `technitium-dns` | Technitium DNS Server is an open source authoritative and recursive DNS server for privacy & security. It f... | [Technitium DNS Server](https://technitium.com/dns/) | [View README](component_templates/technitium-dns/README.md) |

### General Components

| Component | Description | Upstream | Dedicated README |
|---|---|---|---|
| `conduit` | A high-performance, lightweight Matrix chat homeserver written in Rust, specifically optimized for low-reso... | [Conduit (Matrix Server)](https://conduit.rs/) | [View README](component_templates/conduit/README.md) |
| `lora-service` | A smart home IoT notification service that monitors LoRa-enabled mailbox sensors and sends real-time alert ... | [LoRa Letterbox Notifier](https://github.com/HenkVanHoek/lora-letterbox-notifier) | [View README](component_templates/lora-service/README.md) |
| `octoprint` | A web-based interface for remote 3D printer management, providing real-time print monitoring, G-code visual... | [OctoPrint](https://octoprint.org/) | [View README](component_templates/octoprint/README.md) |
| `prosody` | Prosody is a modern, lightweight XMPP (Jabber) communication server designed for efficiency and extensibili... | [Prosody](https://prosody.im/) | [View README](component_templates/prosody/README.md) |

### Smart Home & Iot

| Component | Description | Upstream | Dedicated README |
|---|---|---|---|
| `mosquitto` | Lightweight and widely used open source MQTT message broker for IoT, Home Assistant, and smart home sensor ... | [Eclipse Mosquitto](https://mosquitto.org/) | [View README](component_templates/mosquitto/README.md) |
| `evcc` | Extensible EV Charge Controller with support for solar/PV charging and dynamic tariffs. | [evcc](https://evcc.io/) | [View README](component_templates/evcc/README.md) |
| `frigate` | A high-performance Network Video Recorder (NVR) with local, real-time AI object detection using Coral TPU o... | [Frigate](https://docs.frigate.video/) | [View README](component_templates/frigate/README.md) |
| `homeassistant` | Open source home automation that puts local control and privacy first. | [Home Assistant](https://www.home-assistant.io/) | [View README](component_templates/homeassistant/README.md) |
| `homebridge` | Lightweight NodeJS server that emulates the iOS HomeKit API for non-supported smart home accessories. | [Homebridge](https://homebridge.io/) | [View README](component_templates/homebridge/README.md) |
| `scrypted` | A high-performance smart home video integration platform that bridges IP camera feeds to Apple HomeKit, Goo... | [Scrypted](https://www.scrypted.app/) | [View README](component_templates/scrypted/README.md) |
| `teslamate` | Self-hosted data logger for your Tesla vehicle with detailed driving, battery, and charging analytics. | [TeslaMate](https://docs.teslamate.org/) | [View README](component_templates/teslamate/README.md) |
| `unifi-controller` | A centralized management software suite for configuring, monitoring, and updating Ubiquiti UniFi network de... | [UniFi Controller](https://ui.com/wi-fi) | [View README](component_templates/unifi-controller/README.md) |
| `zigbee2mqtt` | A lightweight bridge that connects Zigbee smart home devices directly to an MQTT broker, enabling local con... | [Zigbee2MQTT](https://www.zigbee2mqtt.io/) | [View README](component_templates/zigbee2mqtt/README.md) |

### Dashboard & Homepages

| Component | Description | Upstream | Dedicated README |
|---|---|---|---|
| `heimdall` | An elegant, customizable application dashboard for organizing shortcuts and status widgets for all your sel... | [Heimdall](https://heimdall.site/) | [View README](component_templates/heimdall/README.md) |
| `homarr` | A modern, customizable server dashboard with direct integrations for monitoring homelab services, Docker co... | [Homarr](https://homarr.dev/) | [View README](component_templates/homarr/README.md) |
| `homepage` | A modern, fully static, fast, secure fully proxied, highly customizable application dashboard with integrat... | [Homepage](https://gethomepage.dev/) | [View README](component_templates/homepage/README.md) |
| `homer` | A lightweight, static application dashboard configured via YAML, designed for fast landing-page access to a... | [Homer](https://github.com/bastienwirtz/homer) | [View README](component_templates/homer/README.md) |
| `organizr` | A unified server management portal that organizes all your self-hosted applications into a single tabbed in... | [Organizr](https://organizr.app/) | [View README](component_templates/organizr/README.md) |

### Media Stack

| Component | Description | Upstream | Dedicated README |
|---|---|---|---|
| `calibre-web` | Web app for browsing, reading and downloading eBooks. | Calibre-Web | [View README](component_templates/calibre-web/README.md) |
| `gluetun` | A lightweight, multi-provider VPN client container supporting OpenVPN and WireGuard protocols to route Dock... | [Gluetun](https://github.com/qdm12/gluetun) | [View README](component_templates/gluetun/README.md) |
| `jellyfin` | A Free Software Media System that puts you in control of your media. | [Jellyfin](https://jellyfin.org/) | [View README](component_templates/jellyfin/README.md) |
| `prowlarr` | Prowlarr is an indexer manager/proxy built on the popular *arr .net/reactjs base stack to integrate with yo... | [Prowlarr](https://prowlarr.com/) | [View README](component_templates/prowlarr/README.md) |
| `qbittorrent` | A lightweight, open-source BitTorrent download client featuring a full-featured web interface, bandwidth sc... | [qBittorrent](https://www.qbittorrent.org/) | [View README](component_templates/qbittorrent/README.md) |
| `radarr` | An automated movie collection manager and PVR that monitors RSS feeds for new releases, triggers download c... | [Radarr](https://radarr.video/) | [View README](component_templates/radarr/README.md) |
| `sabnzbd` | An automated Usenet binary newsreader and download manager featuring automatic repair, unpacking, and seaml... | [SABnzbd](https://sabnzbd.org/) | [View README](component_templates/sabnzbd/README.md) |
| `sonarr` | An automated TV series collection manager and PVR that tracks upcoming episodes, triggers downloads via Use... | [Sonarr](https://sonarr.tv/) | [View README](component_templates/sonarr/README.md) |

### Databases

| Component | Description | Upstream | Dedicated README |
|---|---|---|---|
| `adminer` | Database management in a single PHP file. Supports MySQL, MariaDB, PostgreSQL, SQLite, MS SQL, Oracle, Simp... | [Adminer](https://www.adminer.org/) | [View README](component_templates/adminer/README.md) |
| `nextcloud-db-dumper` | An automated backup utility container that periodically exports SQL dumps of the Nextcloud MariaDB database... | Nextcloud DB Dumper | [View README](component_templates/nextcloud-db-dumper/README.md) |
| `nextcloud-db` | A dedicated, pre-configured MariaDB relational database server optimized for Nextcloud persistent data stor... | Nextcloud MariaDB | [View README](component_templates/nextcloud-db/README.md) |
| `phpmyadmin` | A comprehensive web-based administration tool for managing MySQL and MariaDB databases, executing SQL queri... | [phpMyAdmin](https://www.phpmyadmin.net/) | [View README](component_templates/phpmyadmin/README.md) |

### Utilities

| Component | Description | Upstream | Dedicated README |
|---|---|---|---|
| `notify-push` | Realtime notification and file-sync daemon for Nextcloud written in Rust. | Nextcloud High-Performance Push | [View README](component_templates/notify-push/README.md) |
| `nextcloud-redis` | An in-memory Redis datastore configured as a high-performance transactional file locking broker and caching... | Nextcloud Redis Cache | [View README](component_templates/nextcloud-redis/README.md) |

### Reverse Proxy

| Component | Description | Upstream | Dedicated README |
|---|---|---|---|
| `caddy` | Caddy is a powerful, enterprise-ready, open source web server with automatic HTTPS written in Go. | [Caddy](https://github.com/caddyserver/caddy) | [View README](component_templates/caddy/README.md) |
| `nginx-proxy-manager` | An easy-to-use, Docker-based interface for managing Nginx proxy hosts with free SSL certificate support. | [Nginx Proxy Manager](https://nginxproxymanager.com/) | [View README](component_templates/nginx-proxy-manager/README.md) |
| `traefik` | A modern, cloud-native reverse proxy and load balancer that automatically discovers services. | [Traefik](https://traefik.io/traefik/) | [View README](component_templates/traefik/README.md) |

### System Tools

| Component | Description | Upstream | Dedicated README |
|---|---|---|---|
| `filebrowser` | A lightweight web-based file manager allowing users to upload, edit, delete, preview, and share files on se... | [Filebrowser](https://filebrowser.org/) | [View README](component_templates/filebrowser/README.md) |
| `grafana` | An open-source visualization and analytics platform that turns metrics and logs into dynamic, interactive d... | [Grafana Stack](https://grafana.com/) | [View README](component_templates/grafana/README.md) |
| `portainer` | A powerful, user-friendly management UI that simplifies configuring, monitoring, and deploying Docker conta... | [Portainer](https://www.portainer.io/) | [View README](component_templates/portainer/README.md) |
| `prometheus` | Prometheus, a Cloud Native Computing Foundation project, is a systems and service monitoring system. It col... | [Prometheus Stack](https://prometheus.io/) | [View README](component_templates/prometheus/README.md) |
| `semaphore` | Modern UI for Ansible, Terraform/OpenTofu/Terragrunt, PowerShell and other DevOps tools. | [Semaphore UI](https://semaphoreui.com/) | [View README](component_templates/semaphore/README.md) |
| `uptime-kuma` | A feature-rich, self-hosted monitoring tool providing real-time status pages, HTTP/ping health checks, and ... | [Uptime Kuma](https://uptime.kuma.pet/) | [View README](component_templates/uptime-kuma/README.md) |

### Security & Utilities

| Component | Description | Upstream | Dedicated README |
|---|---|---|---|
| `netwatch` | A network presence and device monitoring system featuring active and passive scanning, timeline analysis, c... | [Netwatch](https://github.com/emanuele-f/netwatch) | [View README](component_templates/netwatch/README.md) |
| `unbound` | A secure, validating, recursive, and caching DNS resolver designed for privacy, preventing upstream ISP DNS... | [Unbound](https://www.nlnetlabs.nl/projects/unbound/about/) | [View README](component_templates/unbound/README.md) |
| `vaultwarden` | A lightweight, self-hosted password manager compatible with Bitwarden clients. It provides almost all of th... | [Vaultwarden](https://github.com/dani-garcia/vaultwarden) | [View README](component_templates/vaultwarden/README.md) |
| `web-notepad` | A minimal, web-based notepad application for quick note-taking, text sharing, and viewing system post-deplo... | [Web Notepad](https://github.com/pajikos/minimalist-web-notepad) | [View README](component_templates/web-notepad/README.md) |

### Communication

| Component | Description | Upstream | Dedicated README |
|---|---|---|---|
| `chatwoot` | Customer engagement suite, omnichannel support and live chat platform. | [Chatwoot](https://www.chatwoot.com) | [View README](component_templates/chatwoot/README.md) |
| `gotify` | A simple server for sending and receiving messages in real-time per web socket with push notifications. | Gotify | [View README](component_templates/gotify/README.md) |
| `docker-jitsi-meet` | Jitsi Meet is a collection of open-source projects that provides a secure, simple, and scalable video confe... | [jitsi-meet](https://jitsi.org/) | [View README](component_templates/docker-jitsi-meet/README.md) |

### Messaging

| Component | Description | Upstream | Dedicated README |
|---|---|---|---|
| `pish-fluffychat-web` | A modern, cute, and cross-platform Matrix client web interface, packaged as a NjordDeploy component. | [FluffyChat Web](https://fluffychat.im/) | [View README](component_templates/pish-fluffychat-web/README.md) |

### Utilities

| Component | Description | Upstream | Dedicated README |
|---|---|---|---|
| `changedetection` | Self-hosted website change detection, website monitor, restock alerts and notification service. | ChangeDetection.io | [View README](component_templates/changedetection/README.md) |
| `cyberchef` | The Cyber Swiss Army Knife - a web app for encryption, encoding, compression, and data analysis. | CyberChef | [View README](component_templates/cyberchef/README.md) |
| `geolens` | Self-hosted geospatial data catalog and interactive web map builder with PostGIS, vector tiles, OGC API sup... | [GeoLens](https://getgeolens.com) | [View README](component_templates/geolens/README.md) |
| `grocy` | ERP beyond your fridge - self-hosted grocery, household management and inventory solution. | Grocy | [View README](component_templates/grocy/README.md) |
| `headscale` | An open source, self-hosted implementation of the Tailscale control server, providing a private network for... | Headscale | [View README](component_templates/headscale/README.md) |
| `microbin` | Ultra-lightweight, configurable, feature-rich, self-hosted pastebin service. | [Microbin](https://microbin.eu/) | [View README](component_templates/microbin/README.md) |
| `ntfy` | ntfy (pronounced 'notify') is a simple HTTP-based pub-sub notification service. With ntfy, you can send not... | ntfy | [View README](component_templates/ntfy/README.md) |
| `plausible` | Plausible is a lightweight, open-source and privacy-friendly Google Analytics alternative without cookies a... | [Plausible Analytics](https://plausible.io/) | [View README](component_templates/plausible/README.md) |
| `searxng` | Privacy-respecting metasearch engine. | SearXNG | [View README](component_templates/searxng/README.md) |
| `shlink` | Self-hosted URL shortener with REST API, rich statistics and QR code generation. | Shlink | [View README](component_templates/shlink/README.md) |
| `speedtest-tracker` | Self-hosted internet speedtest tracker that runs speedtests periodically and visualizes latency and bandwidth. | Speedtest Tracker | [View README](component_templates/speedtest-tracker/README.md) |
| `umami` | Umami is an open-source, privacy-focused alternative to Google Analytics. It provides lightweight web analy... | [Umami Analytics](https://umami.is/) | [View README](component_templates/umami/README.md) |

### Productivity

| Component | Description | Upstream | Dedicated README |
|---|---|---|---|
| `actual-budget` | Privacy-first personal finance and envelope budgeting app. It is 100% free and open-source, written in Node... | Actual Budget | [View README](component_templates/actual-budget/README.md) |
| `bookstack` | Simple, self-hosted, easy-to-use platform for organizing and storing documentation and wikis in book format. | [BookStack](https://www.bookstackapp.com/) | [View README](component_templates/bookstack/README.md) |
| `docmost` | Modern open-source collaborative wiki and knowledge-base alternative to Notion and Confluence. | [Docmost](https://docmost.com/) | [View README](component_templates/docmost/README.md) |
| `drawio` | Security-first diagramming application for creating architecture diagrams, flowcharts, and mind maps. | Draw.io | [View README](component_templates/drawio/README.md) |
| `etherpad` | Highly customizable open source online editor providing collaborative real-time editing. | [Etherpad Lite](https://etherpad.org/) | [View README](component_templates/etherpad/README.md) |
| `excalidraw` | Virtual collaborative whiteboard for sketching diagrams with a hand-drawn, paper-like feel. | Excalidraw | [View README](component_templates/excalidraw/README.md) |
| `firefly-iii` | Free and open source personal finance manager to track expenses, income, budgets, and bank accounts. | [Firefly III](https://www.firefly-iii.org/) | [View README](component_templates/firefly-iii/README.md) |
| `flatnotes` | A self-hosted, database-less flat-file markdown note taking web app with fast search and wikilinks. | Flatnotes | [View README](component_templates/flatnotes/README.md) |
| `focalboard` | Open source, multilingual project management and personal task board alternative to Trello, Notion, and Asana. | Focalboard | [View README](component_templates/focalboard/README.md) |
| `hatchdoor` | Agent-native web app and Model Context Protocol (MCP) server for Obsidian-style Markdown vaults with semant... | [Hatchdoor](https://github.com/BattermanZ/Hatchdoor) | [View README](component_templates/hatchdoor/README.md) |
| `it-tools` | Useful web tools for developers and sysadmins. | IT Tools | [View README](component_templates/it-tools/README.md) |
| `mealie` | A self-hosted recipe manager, meal planner, and shopping list with a RestAPI backend and a reactive fronten... | Mealie | [View README](component_templates/mealie/README.md) |
| `memos` | A privacy-first, lightweight note-taking service with markdown support and social timeline view. | Memos | [View README](component_templates/memos/README.md) |
| `n8n` | Fair-code platform to build and deploy AI agents and workflows. Combine a visual canvas with custom code, r... | [n8n](https://n8n.io/) | [View README](component_templates/n8n/README.md) |
| `nextcloud` | A comprehensive self-hosted productivity and collaboration suite offering secure file storage, online docum... | [Nextcloud](https://nextcloud.com/) | [View README](component_templates/nextcloud/README.md) |
| `paperless-ngx` | A document management system that transforms your physical documents into a searchable online archive so yo... | Paperless-ngx | [View README](component_templates/paperless-ngx/README.md) |
| `silverbullet` | Extensible, open-source personal knowledge management system written in clean TypeScript. | [SilverBullet](https://silverbullet.md/) | [View README](component_templates/silverbullet/README.md) |
| `stirling-pdf` | A powerful, open-source PDF editing platform for editing, signing, redacting, converting, and automating PDFs. | [Stirling PDF](https://stirlingpdf.com/) | [View README](component_templates/stirling-pdf/README.md) |
| `trilium` | Hierarchical note taking application with focus on building large personal knowledge bases. | Trilium Next | [View README](component_templates/trilium/README.md) |
| `vikunja` | The to-do app to organize your life with Kanban boards, Gantt charts, lists and table views. | Vikunja | [View README](component_templates/vikunja/README.md) |
| `wallabag` | Self-hosted application for saving web pages and articles to read later on any device. | Wallabag | [View README](component_templates/wallabag/README.md) |
| `wallos` | Open-source, self-hosted personal subscription tracker to monitor recurring payments and costs. | [Wallos](https://github.com/ellite/Wallos) | [View README](component_templates/wallos/README.md) |

### Media Servers

| Component | Description | Upstream | Dedicated README |
|---|---|---|---|
| `audiobookshelf` | A self-hosted audiobook and podcast server for organizing, streaming, and tracking playback progress across... | [Audiobookshelf](https://www.audiobookshelf.org/) | [View README](component_templates/audiobookshelf/README.md) |
| `immich` | Immich is a high-performance self-hosted photo and video management solution. It consists of multiple servi... | Immich | [View README](component_templates/immich/README.md) |
| `immich-kiosk` | Immich Kiosk is an ambient digital photo frame and slideshow client designed for smart TVs, tablets, and wa... | [Immich Kiosk](https://github.com/damongolding/immich-kiosk) | [View README](component_templates/immich-kiosk/README.md) |
| `kavita` | Kavita is a fast, feature rich, cross platform reading server. Built with a focus for being a full solution... | Kavita | [View README](component_templates/kavita/README.md) |
| `navidrome` | Navidrome is an open source web-based music collection server and streamer. It gives you freedom to listen ... | Navidrome Music Server | [View README](component_templates/navidrome/README.md) |

### Media

| Component | Description | Upstream | Dedicated README |
|---|---|---|---|
| `bazarr` | Companion application to Sonarr and Radarr that manages and downloads subtitles based on your requirements. | Bazarr | [View README](component_templates/bazarr/README.md) |
| `jellyseerr` | Free and open source software application for managing requests for your media library (Jellyfin, Emby, Plex). | Jellyseerr | [View README](component_templates/jellyseerr/README.md) |
| `lidarr` | Music collection manager for Usenet and BitTorrent users, tracking multiple RSS feeds for new tracks. | Lidarr | [View README](component_templates/lidarr/README.md) |
| `romm` | A web-based retro ROMs manager and player for managing your game library. | RomM | [View README](component_templates/romm/README.md) |
| `tautulli` | A python based web application for monitoring, analytics and notifications for Plex Media Server. | Tautulli | [View README](component_templates/tautulli/README.md) |

### Developer

| Component | Description | Upstream | Dedicated README |
|---|---|---|---|
| `forgejo` | Beyond coding. We forge. Self-hosted lightweight software forge, hard fork of Gitea. | Forgejo | [View README](component_templates/forgejo/README.md) |
| `gitea` | A painless, self-hosted Git service written in Go with repository management, code review, issues, and wikis. | Gitea | [View README](component_templates/gitea/README.md) |
| `gitlab` | A complete DevOps platform for project planning, source code management, CI/CD, and monitoring. | [GitLab](https://about.gitlab.com/) | [View README](component_templates/gitlab/README.md) |
| `nocodb` | Open Source Airtable Alternative that turns any SQL database into a smart spreadsheet. | NocoDB | [View README](component_templates/nocodb/README.md) |
| `woodpecker-ci` | Simple yet powerful community-driven continuous integration engine with container-native pipelines. | Woodpecker CI | [View README](component_templates/woodpecker-ci/README.md) |

### Management

| Component | Description | Upstream | Dedicated README |
|---|---|---|---|
| `dockge` | A fancy, easy-to-use and reactive self-hosted docker compose stack-oriented manager by LouisLam. | Dockge | [View README](component_templates/dockge/README.md) |

### Storage

| Component | Description | Upstream | Dedicated README |
|---|---|---|---|
| `minio` | High-performance, S3-compatible enterprise object storage system. | MinIO S3 Storage | [View README](component_templates/minio/README.md) |
| `syncthing` | Open Source Continuous File Synchronization program that synchronizes files between two or more computers i... | Syncthing | [View README](component_templates/syncthing/README.md) |

### Monitoring

| Component | Description | Upstream | Dedicated README |
|---|---|---|---|
| `beszel` | Lightweight server monitoring hub with historical resource metrics and alerts. | Beszel | [View README](component_templates/beszel/README.md) |
| `netdata` | Real-time performance and health monitoring for systems, hardware, containers, and applications. | Netdata | [View README](component_templates/netdata/README.md) |

### News & Media

| Component | Description | Upstream | Dedicated README |
|---|---|---|---|
| `freshrss` | A free, self-hostable aggregator for RSS and Atom feeds with responsive web interface and multi-user support. | FreshRSS | [View README](component_templates/freshrss/README.md) |

### Smart Home

| Component | Description | Upstream | Dedicated README |
|---|---|---|---|
| `esphome` | System to control your ESP8266 and ESP32 boards by simple and powerful configuration files and control them... | ESPHome | [View README](component_templates/esphome/README.md) |
| `node-red` | Low-code programming for event-driven applications, connecting hardware devices, APIs and online services. | Node-RED | [View README](component_templates/node-red/README.md) |

### Database Management

| Component | Description | Upstream | Dedicated README |
|---|---|---|---|
| `pgadmin4` | Comprehensive open source administration and management tool for PostgreSQL databases. | pgAdmin 4 | [View README](component_templates/pgadmin4/README.md) |

### Dashboards

| Component | Description | Upstream | Dedicated README |
|---|---|---|---|
| `dashdot` | Modern server dashboard for displaying CPU, RAM, storage, and network statistics. | [Dashdot](https://getdashdot.com/) | [View README](component_templates/dashdot/README.md) |
| `dynacat` | A modern, real-time homelab dashboard and Glance fork featuring WebSockets, dynamic widgets, live feed aggr... | [Dynacat](https://github.com/Panonim/dynacat) | [View README](component_templates/dynacat/README.md) |
| `glance` | Extremely fast, self-contained dashboard written in Go for server feeds, weather, bookmarks, and services. | [Glance Dashboard](https://github.com/glanceapp/glance) | [View README](component_templates/glance/README.md) |

### System & Tools

| Component | Description | Upstream | Dedicated README |
|---|---|---|---|
| `apprise` | Push notification gateway for over 90 notification services (Telegram, Discord, Pushover, etc.). | [Apprise API](https://github.com/caronc/apprise-api) | [View README](component_templates/apprise/README.md) |
| `diun` | CLI application to analyze Docker images and send notifications when image updates are published. | [Diun (Update Notifier)](https://crazymax.dev/diun/) | [View README](component_templates/diun/README.md) |
| `dozzle` | Real-time, lightweight log viewer for Docker containers with web UI and live search. | [Dozzle](https://dozzle.dev/) | [View README](component_templates/dozzle/README.md) |
| `privatebin` | Zero-knowledge, client-side encrypted minimalist pastebin application. | [PrivateBin](https://privatebin.info/) | [View README](component_templates/privatebin/README.md) |
| `rustdesk-server` | Self-hosted rendezvous and relay server for RustDesk remote desktop clients. | [RustDesk Server](https://rustdesk.com/) | [View README](component_templates/rustdesk-server/README.md) |
| `scrutiny` | WebUI for smartd S.M.A.R.T. monitoring and hard drive health inspection. | [Scrutiny](https://github.com/AnalogJ/scrutiny) | [View README](component_templates/scrutiny/README.md) |

### Cloud & Storage

| Component | Description | Upstream | Dedicated README |
|---|---|---|---|
| `duplicati` | Encrypted, incremental, and deduplicated backup client for cloud storage and local drives. | [Duplicati](https://www.duplicati.com/) | [View README](component_templates/duplicati/README.md) |
| `pairdrop` | Local file sharing in your browser across devices, fully compatible with Apple AirDrop workflows. | [PairDrop](https://pairdrop.net/) | [View README](component_templates/pairdrop/README.md) |
| `sftpgo` | Fully featured and highly configurable event-driven SFTP, FTP, and WebDAV server. | [SFTPGo](https://sftpgo.com/) | [View README](component_templates/sftpgo/README.md) |

### Media & Streaming

| Component | Description | Upstream | Dedicated README |
|---|---|---|---|
| `komga` | Free and open source media server for your comics, mangas, BDs, and book collections. | [Komga](https://komga.org/) | [View README](component_templates/komga/README.md) |
| `metube` | Web GUI for yt-dlp with playlist support and audio/video download format selection. | [MeTube](https://github.com/alexta69/metube) | [View README](component_templates/metube/README.md) |
| `transmission` | Fast, lightweight, and reliable BitTorrent client with a clean web interface. | [Transmission](https://transmissionbt.com/) | [View README](component_templates/transmission/README.md) |
| `unpackerr` | Automatically extracts downloaded archives for Radarr, Sonarr, Lidarr, and torrent downloads. | [Unpackerr](https://unpackerr.zip/) | [View README](component_templates/unpackerr/README.md) |

### News & Bookmarks

| Component | Description | Upstream | Dedicated README |
|---|---|---|---|
| `linkding` | Minimal, fast, and privacy-focused bookmark manager designed for speed. | [linkding](https://github.com/sissbruecker/linkding) | [View README](component_templates/linkding/README.md) |
| `miniflux` | Minimalist, fast, and opinionated RSS feed reader written in Go. | [Miniflux](https://miniflux.app/) | [View README](component_templates/miniflux/README.md) |

### Network

| Component | Description | Upstream | Dedicated README |
|---|---|---|---|
| `wg-easy` | All-in-one WireGuard VPN server with a web UI for managing clients and configuration. Requires root privile... | WireGuard Easy | [View README](component_templates/wg-easy/README.md) |
