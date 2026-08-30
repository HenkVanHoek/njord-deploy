# Supported Services

This document is automatically generated from the project metadata. It lists the open-source software packages that can be deployed using NjordDeploy, along with links to their official repositories and homepages.

## AI & LLM Services

| Service | Description | Project Homepage / Repository |
|---|---|---|
| LibreChat | LibreChat is a self-hosted AI chat platform that unifies all major AI providers in a single, privacy-focused interface. It features AI Agents, Code Interpreter, custom actions, conversation search, and enterprise-ready multi-user authentication. The service runs as root (user: 0:0) to manage volume permissions. | N/A |
| LiteLLM AI Gateway | LiteLLM is an AI gateway and LLM proxy that unifies access to 100+ Large Language Models (OpenAI, Gemini, Anthropic, Ollama, Azure, Bedrock, HostYourAI) behind a single OpenAI-compatible API format. | [Link](https://github.com/BerriAI/litellm) |
| Ollama LLM Engine | Ollama is an open-source, lightweight, and extensible framework for running Large Language Models (LLMs) locally, such as Llama 3, Qwen, Mistral, and DeepSeek. | N/A |
| Open WebUI | Open WebUI is an extensible, feature-rich, and user-friendly web interface for AI models and LLMs, supporting Ollama and OpenAI-compatible APIs with chat, voice, and RAG capabilities. | [Link](https://openwebui.com/) |

## Communication & Chat

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Conduit (Matrix Server) | A high-performance, lightweight Matrix chat homeserver written in Rust, specifically optimized for low-resource environments like the Raspberry Pi. | [Link](https://conduit.rs/) |
| FluffyChat Web | A modern, cute, and cross-platform Matrix client web interface, packaged as a NjordDeploy component. | [Link](https://fluffychat.im/) |
| Gotify | A simple server for sending and receiving messages in real-time per web socket with push notifications. | N/A |
| jitsi-meet | Jitsi Meet is a collection of open-source projects that provides a secure, simple, and scalable video conferencing solution. This component sets up a complete Jitsi Meet instance with optional Etherpad collaboration and recording capabilities. | [Link](https://jitsi.org/) |
| Prosody | Prosody is a modern, lightweight XMPP (Jabber) communication server designed for efficiency and extensibility. Within the NjordDeploy ecosystem, this component provides a private and secure instant messaging platform. It allows users to host their own chat services, including: One-to-one messaging: Secure, real-time private conversations. Multi-User Chat (MUC): Group chat capabilities for family or teams. HTTP File Upload: Seamless sharing of photos and files directly from your own hardware. Modern Security: Automated TLS encryption using Let's Encrypt certificates via Nginx Proxy Manager. Note: This service requires port 5222 (client-to-server) and 5269 (server-to-server) to be forwarded in your router for external access. | [Link](https://prosody.im/) |

## Dashboards & Homepages

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Heimdall | An elegant, customizable application dashboard for organizing shortcuts and status widgets for all your self-hosted web services. | [Link](https://heimdall.site/) |
| Homarr | A modern, customizable server dashboard with direct integrations for monitoring homelab services, Docker container statuses, and media clients. | [Link](https://homarr.dev/) |
| Homepage | A modern, fully static, fast, secure fully proxied, highly customizable application dashboard with integrations for over 100 services and translations into multiple languages. Easily configured via YAML files or through docker label discovery. Homepage does not include an authentication layer itself; it is recommended to place it behind a reverse proxy with authentication if exposed to untrusted networks. For optimal file permissions on mounted volumes, the container is configured to run as root (user: 0:0) by default, overriding the PUID/PGID environment variables if set. Note: Docker integration requiring access to /var/run/docker.sock is not enabled by default for security reasons. Users can manually add this volume mount if needed. | [Link](https://gethomepage.dev/) |
| Homer | A lightweight, static application dashboard configured via YAML, designed for fast landing-page access to all your homelab services. | [Link](https://github.com/bastienwirtz/homer) |
| Organizr | A unified server management portal that organizes all your self-hosted applications into a single tabbed interface with custom user permissions. | [Link](https://organizr.app/) |

## Databases & Caching

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Adminer | Database management in a single PHP file. Supports MySQL, MariaDB, PostgreSQL, SQLite, MS SQL, Oracle, SimpleDB, Elasticsearch, MongoDB. | [Link](https://www.adminer.org/) |
| Nextcloud DB Dumper | An automated backup utility container that periodically exports SQL dumps of the Nextcloud MariaDB database for disaster recovery. | [Link](https://github.com/HenkVanHoek/njord-deploy) |
| Nextcloud MariaDB | A dedicated, pre-configured MariaDB relational database server optimized for Nextcloud persistent data storage and high query performance. | [Link](https://mariadb.org/) |
| Nextcloud Redis Cache | An in-memory Redis datastore configured as a high-performance transactional file locking broker and caching layer for Nextcloud. | [Link](https://redis.io/) |
| pgAdmin 4 | Comprehensive open source administration and management tool for PostgreSQL databases. | N/A |
| phpMyAdmin | A comprehensive web-based administration tool for managing MySQL and MariaDB databases, executing SQL queries, and managing user access control. | [Link](https://www.phpmyadmin.net/) |

## Developer Tools

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Gitea | A painless, self-hosted Git service written in Go with repository management, code review, issues, and wikis. | N/A |
| GitLab | A complete DevOps platform for project planning, source code management, CI/CD, and monitoring. | [Link](https://about.gitlab.com/) |
| NocoDB | Open Source Airtable Alternative that turns any SQL database into a smart spreadsheet. | N/A |
| Woodpecker CI | Simple yet powerful community-driven continuous integration engine with container-native pipelines. | N/A |

## DNS & Ad Blocking

| Service | Description | Project Homepage / Repository |
|---|---|---|
| AdGuard Home | AdGuard Home is a free and open-source network-wide software for blocking ads and tracking. It operates as a DNS server that re-routes tracking domains to a “black hole”, thus preventing your devices from connecting to those servers. It provides a web UI for configuration and monitoring. AdGuard Home is capable of running without root privileges, but for persistent volume access, the container is set to run as root (user: 0:0). | [Link](https://adguard.com/en/adguard-home/overview.html) |
| Pi-hole | A network-wide ad and tracker blocker that functions as a DNS sinkhole, protecting all local network devices without requiring client-side software. | [Link](https://pi-hole.net/) |
| Technitium DNS Server | Technitium DNS Server is an open source authoritative and recursive DNS server for privacy & security. It features built-in ad and malware blocking, supports DNS-over-TLS (DoT), DNS-over-HTTPS (DoH), and DNS-over-QUIC (DoQ), and provides a comprehensive web management console. | [Link](https://technitium.com/dns/) |

## Media & Streaming

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Audiobookshelf | A self-hosted audiobook and podcast server for organizing, streaming, and tracking playback progress across your personal audio media library. | [Link](https://www.audiobookshelf.org/) |
| Bazarr | Companion application to Sonarr and Radarr that manages and downloads subtitles based on your requirements. | N/A |
| Calibre-Web | Web app for browsing, reading and downloading eBooks. | N/A |
| FreshRSS | A free, self-hostable aggregator for RSS and Atom feeds with responsive web interface and multi-user support. | N/A |
| Gluetun | A lightweight, multi-provider VPN client container supporting OpenVPN and WireGuard protocols to route Docker service traffic securely. | [Link](https://github.com/qdm12/gluetun) |
| Immich | Immich is a high-performance self-hosted photo and video management solution. It consists of multiple services (server, microservices, machine learning, proxy) and requires a PostgreSQL database and Redis for operation. It is recommended to follow a 3-2-1 backup plan for your precious photos and videos. The Immich services are configured to run as root (`user: "0:0"`) to prevent common permission issues with mounted volumes. | N/A |
| Jellyfin | A Free Software Media System that puts you in control of your media. | [Link](https://jellyfin.org/) |
| Jellyseerr | Free and open source software application for managing requests for your media library (Jellyfin, Emby, Plex). | N/A |
| Kavita | Kavita is a fast, feature rich, cross platform reading server. Built with a focus for being a full solution for all your reading needs. Setup your own server and share your reading collection with your friends and family! The container runs as root (user: 0:0) to ensure proper file permissions for mounted volumes. | N/A |
| Lidarr | Music collection manager for Usenet and BitTorrent users, tracking multiple RSS feeds for new tracks. | N/A |
| Navidrome Music Server | Navidrome is an open source web-based music collection server and streamer. It gives you freedom to listen to your music collection from any browser or mobile device. It's like your personal Spotify! The container runs as root (user: 0:0) to ensure proper file permissions for mounted volumes. | N/A |
| Prowlarr | Prowlarr is an indexer manager/proxy built on the popular *arr .net/reactjs base stack to integrate with your various PVR apps. Prowlarr supports management of both Torrent Trackers and Usenet Indexers. | [Link](https://prowlarr.com/) |
| qBittorrent | A lightweight, open-source BitTorrent download client featuring a full-featured web interface, bandwidth scheduling, and built-in search engines. | [Link](https://www.qbittorrent.org/) |
| Radarr | An automated movie collection manager and PVR that monitors RSS feeds for new releases, triggers download clients, and automatically organizes media files. | [Link](https://radarr.video/) |
| RomM | A web-based retro ROMs manager and player for managing your game library. | N/A |
| SABnzbd | An automated Usenet binary newsreader and download manager featuring automatic repair, unpacking, and seamless PVR stack integration. | [Link](https://sabnzbd.org/) |
| Sonarr | An automated TV series collection manager and PVR that tracks upcoming episodes, triggers downloads via Usenet or BitTorrent, and organizes show libraries. | [Link](https://sonarr.tv/) |
| Tautulli | A python based web application for monitoring, analytics and notifications for Plex Media Server. | N/A |

## Monitoring & Analytics

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Beszel | Lightweight server monitoring hub with historical resource metrics and alerts. | N/A |
| Grafana Stack | An open-source visualization and analytics platform that turns metrics and logs into dynamic, interactive dashboards for comprehensive system observability. | [Link](https://grafana.com/) |
| Netdata | Real-time performance and health monitoring for systems, hardware, containers, and applications. | N/A |
| Plausible Analytics | Plausible is a lightweight, open-source and privacy-friendly Google Analytics alternative without cookies and fully compliant with GDPR, CCPA and PECR. | [Link](https://plausible.io/) |
| Prometheus Stack | Prometheus, a Cloud Native Computing Foundation project, is a systems and service monitoring system. It collects metrics from configured targets at given intervals, evaluates rule expressions, displays the results, and can trigger alerts when specified conditions are observed. This stack includes Prometheus, Node Exporter, and cAdvisor for comprehensive system and container monitoring. | [Link](https://prometheus.io/) |
| Speedtest Tracker | Self-hosted internet speedtest tracker that runs speedtests periodically and visualizes latency and bandwidth. | N/A |
| Umami Analytics | Umami is an open-source, privacy-focused alternative to Google Analytics. It provides lightweight web analytics without collecting personal data or using tracking cookies. | [Link](https://umami.is/) |
| Uptime Kuma | A feature-rich, self-hosted monitoring tool providing real-time status pages, HTTP/ping health checks, and alerts via multiple notification channels. | [Link](https://uptime.kuma.pet/) |

## Network & VPN

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Headscale | An open source, self-hosted implementation of the Tailscale control server, providing a private network for your devices. | N/A |
| Unbound | A secure, validating, recursive, and caching DNS resolver designed for privacy, preventing upstream ISP DNS logging when paired with Pi-hole or AdGuard. | [Link](https://www.nlnetlabs.nl/projects/unbound/about/) |

## Productivity & Notes

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Actual Budget | Privacy-first personal finance and envelope budgeting app. It is 100% free and open-source, written in NodeJS, it has a synchronization element so that all your changes can move between devices without any heavy lifting. The application stores its data in the /data volume. | N/A |
| Draw.io | Security-first diagramming application for creating architecture diagrams, flowcharts, and mind maps. | N/A |
| Excalidraw | Virtual collaborative whiteboard for sketching diagrams with a hand-drawn, paper-like feel. | N/A |
| Flatnotes | A self-hosted, database-less flat-file markdown note taking web app with fast search and wikilinks. | N/A |
| Focalboard | Open source, multilingual project management and personal task board alternative to Trello, Notion, and Asana. | N/A |
| IT Tools | Useful web tools for developers and sysadmins. | N/A |
| Mealie | A self-hosted recipe manager, meal planner, and shopping list with a RestAPI backend and a reactive frontend built in Vue for a pleasant user experience for the whole family. Easily add recipes into your database by providing the URL and Mealie will automatically import the relevant data, or add a family recipe with the UI editor. The Mealie Docker image often supports PUID/PGID environment variables for file ownership within the container, even if the container runs as root. | N/A |
| Memos | A privacy-first, lightweight note-taking service with markdown support and social timeline view. | N/A |
| n8n | Fair-code platform to build and deploy AI agents and workflows. Combine a visual canvas with custom code, run it self-hosted, and connect to 1500+ integrations. | [Link](https://n8n.io/) |
| Nextcloud | A comprehensive self-hosted productivity and collaboration suite offering secure file storage, online document editing, calendar, and contacts synchronization. | [Link](https://nextcloud.com/) |
| Paperless-ngx | A document management system that transforms your physical documents into a searchable online archive so you can keep, well, less paper. It automatically imports, tags, and archives your scanned documents. | N/A |
| Stirling PDF | A powerful, open-source PDF editing platform for editing, signing, redacting, converting, and automating PDFs. | [Link](https://stirlingpdf.com/) |
| Trilium Next | Hierarchical note taking application with focus on building large personal knowledge bases. | N/A |
| Vikunja | The to-do app to organize your life with Kanban boards, Gantt charts, lists and table views. | N/A |
| Voicebox | The open-source AI voice studio. Clone any voice. Generate speech. Dictate into any app. Talk to agents in voices you own. The full voice I/O stack, running locally on your machine. | [Link](https://github.com/HenkVanHoek/njord-deploy) |
| Wallabag | Self-hosted application for saving web pages and articles to read later on any device. | N/A |
| Web Notepad | A minimal, web-based notepad application for quick note-taking, text sharing, and viewing system post-deployment summaries. | [Link](https://github.com/pajikos/minimalist-web-notepad) |

## Reverse Proxy

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Caddy | Caddy is a powerful, enterprise-ready, open source web server with automatic HTTPS written in Go. | [Link](https://github.com/caddyserver/caddy) |
| Nginx Proxy Manager | An easy-to-use, Docker-based interface for managing Nginx proxy hosts with free SSL certificate support. | [Link](https://nginxproxymanager.com/) |
| Traefik | A modern, cloud-native reverse proxy and load balancer that automatically discovers services. | [Link](https://traefik.io/traefik/) |

## Security & Secrets

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Vaultwarden | A lightweight, self-hosted password manager compatible with Bitwarden clients. It provides almost all of the features of the official server without the resource-heavy footprint. | [Link](https://github.com/dani-garcia/vaultwarden) |

## Smart Home & IoT

| Service | Description | Project Homepage / Repository |
|---|---|---|
| ESPHome | System to control your ESP8266 and ESP32 boards by simple and powerful configuration files and control them remotely. | N/A |
| Frigate | A high-performance Network Video Recorder (NVR) with local, real-time AI object detection using Coral TPU or CPU for IP security cameras. | [Link](https://docs.frigate.video/) |
| Home Assistant | Open source home automation that puts local control and privacy first. | [Link](https://www.home-assistant.io/) |
| LoRa Letterbox Notifier | A smart home IoT notification service that monitors LoRa-enabled mailbox sensors and sends real-time alert notifications when physical mail is delivered. | [Link](https://github.com/HenkVanHoek/lora-letterbox-notifier) |
| Node-RED | Low-code programming for event-driven applications, connecting hardware devices, APIs and online services. | N/A |
| Scrypted | A high-performance smart home video integration platform that bridges IP camera feeds to Apple HomeKit, Google Home, and Alexa with hardware acceleration. | [Link](https://www.scrypted.app/) |
| UniFi Controller | A centralized management software suite for configuring, monitoring, and updating Ubiquiti UniFi network devices such as access points, switches, and gateways. | [Link](https://ui.com/wi-fi) |
| Zigbee2MQTT | A lightweight bridge that connects Zigbee smart home devices directly to an MQTT broker, enabling local control via Home Assistant or custom automation software. | [Link](https://www.zigbee2mqtt.io/) |

## Storage & Sync

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Filebrowser | A lightweight web-based file manager allowing users to upload, edit, delete, preview, and share files on server storage volumes. | [Link](https://filebrowser.org/) |
| MinIO S3 Storage | High-performance, S3-compatible enterprise object storage system. | N/A |
| Syncthing | Open Source Continuous File Synchronization program that synchronizes files between two or more computers in real time. | N/A |

## System Management & Automation

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Dockge | A fancy, easy-to-use and reactive self-hosted docker compose stack-oriented manager by LouisLam. | N/A |
| Portainer | A powerful, user-friendly management UI that simplifies configuring, monitoring, and deploying Docker containers, stacks, and persistent volumes. | [Link](https://www.portainer.io/) |
| Semaphore UI | Modern UI for Ansible, Terraform/OpenTofu/Terragrunt, PowerShell and other DevOps tools. | [Link](https://semaphoreui.com/) |
| Service Maintenance | A system management component for monitoring service health, checking software updates, and auditing container vulnerabilities across NjordDeploy services. | [Link](https://github.com/HenkVanHoek/njord-deploy) |

## Utilities

| Service | Description | Project Homepage / Repository |
|---|---|---|
| ChangeDetection.io | Self-hosted website change detection, website monitor, restock alerts and notification service. | N/A |
| CyberChef | The Cyber Swiss Army Knife - a web app for encryption, encoding, compression, and data analysis. | N/A |
| Grocy | ERP beyond your fridge - self-hosted grocery, household management and inventory solution. | N/A |
| Microbin | Ultra-lightweight, configurable, feature-rich, self-hosted pastebin service. | [Link](https://microbin.eu/) |
| Nextcloud High-Performance Push | Realtime notification and file-sync daemon for Nextcloud written in Rust. | [Link](https://github.com/nextcloud/notify_push) |
| ntfy | ntfy (pronounced 'notify') is a simple HTTP-based pub-sub notification service. With ntfy, you can send notifications to your phone or desktop via scripts from any computer, without having to sign up or pay any fees. It runs as root (0:0) to manage file permissions on mounted volumes. | N/A |
| OctoPrint | A web-based interface for remote 3D printer management, providing real-time print monitoring, G-code visualization, and live camera streaming. | [Link](https://octoprint.org/) |
| SearXNG | Privacy-respecting metasearch engine. | N/A |
| Shlink | Self-hosted URL shortener with REST API, rich statistics and QR code generation. | N/A |
