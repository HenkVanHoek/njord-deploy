# Supported Services

This document is automatically generated from the project metadata. It lists the open-source software packages that can be deployed using NjordDeploy, along with links to their official repositories and homepages.

## DNS Blocker

| Service | Description | Project Homepage / Repository |
|---|---|---|
| AdGuard Home | AdGuard Home is a free and open-source network-wide software for blocking ads and tracking. It operates as a DNS server that re-routes tracking domains to a “black hole”, thus preventing your devices from connecting to those servers. It provides a web UI for configuration and monitoring. AdGuard Home is capable of running without root privileges, but for persistent volume access, the container is set to run as root (user: 0:0). | [Link](https://adguard.com/en/adguard-home/overview.html) |
| Pi-hole | A network-wide ad and tracker blocker that functions as a DNS sinkhole, protecting all local network devices without requiring client-side software. | [Link](https://pi-hole.net/) |

## General Components

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Conduit (Matrix Server) | A high-performance, lightweight Matrix chat homeserver written in Rust, specifically optimized for low-resource environments like the Raspberry Pi. | [Link](https://conduit.rs/) |
| LoRa Letterbox Notifier | A smart home IoT notification service that monitors LoRa-enabled mailbox sensors and sends real-time alert notifications when physical mail is delivered. | [Link](https://github.com/HenkVanHoek/lora-letterbox-notifier) |
| OctoPrint | A web-based interface for remote 3D printer management, providing real-time print monitoring, G-code visualization, and live camera streaming. | [Link](https://octoprint.org/) |
| Prosody | Prosody is a modern, lightweight XMPP (Jabber) communication server designed for efficiency and extensibility. Within the NjordDeploy ecosystem, this component provides a private and secure instant messaging platform. It allows users to host their own chat services, including: One-to-one messaging: Secure, real-time private conversations. Multi-User Chat (MUC): Group chat capabilities for family or teams. HTTP File Upload: Seamless sharing of photos and files directly from your own hardware. Modern Security: Automated TLS encryption using Let's Encrypt certificates via Nginx Proxy Manager. Note: This service requires port 5222 (client-to-server) and 5269 (server-to-server) to be forwarded in your router for external access. | [Link](https://prosody.im/) |

## Smart Home & Iot

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Frigate | A high-performance Network Video Recorder (NVR) with local, real-time AI object detection using Coral TPU or CPU for IP security cameras. | [Link](https://docs.frigate.video/) |
| Home Assistant | Open source home automation that puts local control and privacy first. | [Link](https://www.home-assistant.io/) |
| Scrypted | A high-performance smart home video integration platform that bridges IP camera feeds to Apple HomeKit, Google Home, and Alexa with hardware acceleration. | [Link](https://www.scrypted.app/) |
| UniFi Controller | A centralized management software suite for configuring, monitoring, and updating Ubiquiti UniFi network devices such as access points, switches, and gateways. | [Link](https://ui.com/wi-fi) |
| Zigbee2MQTT | A lightweight bridge that connects Zigbee smart home devices directly to an MQTT broker, enabling local control via Home Assistant or custom automation software. | [Link](https://www.zigbee2mqtt.io/) |

## Development Tools

| Service | Description | Project Homepage / Repository |
|---|---|---|
| GitLab | A complete DevOps platform for project planning, source code management, CI/CD, and monitoring. | [Link](https://about.gitlab.com/) |

## Dashboard & Homepages

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Heimdall | An elegant, customizable application dashboard for organizing shortcuts and status widgets for all your self-hosted web services. | [Link](https://heimdall.site/) |
| Homarr | A modern, customizable server dashboard with direct integrations for monitoring homelab services, Docker container statuses, and media clients. | [Link](https://homarr.dev/) |
| Homepage | A modern, fully static, fast, secure fully proxied, highly customizable application dashboard with integrations for over 100 services and translations into multiple languages. Easily configured via YAML files or through docker label discovery. Homepage does not include an authentication layer itself; it is recommended to place it behind a reverse proxy with authentication if exposed to untrusted networks. For optimal file permissions on mounted volumes, the container is configured to run as root (user: 0:0) by default, overriding the PUID/PGID environment variables if set. Note: Docker integration requiring access to /var/run/docker.sock is not enabled by default for security reasons. Users can manually add this volume mount if needed. | [Link](https://gethomepage.dev/) |
| Homer | A lightweight, static application dashboard configured via YAML, designed for fast landing-page access to all your homelab services. | [Link](https://github.com/bastienwirtz/homer) |
| Organizr | A unified server management portal that organizes all your self-hosted applications into a single tabbed interface with custom user permissions. | [Link](https://organizr.app/) |

## Media Stack

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Gluetun | A lightweight, multi-provider VPN client container supporting OpenVPN and WireGuard protocols to route Docker service traffic securely. | [Link](https://github.com/qdm12/gluetun) |
| Jellyfin | A Free Software Media System that puts you in control of your media. | [Link](https://jellyfin.org/) |
| Prowlarr | Prowlarr is an indexer manager/proxy built on the popular *arr .net/reactjs base stack to integrate with your various PVR apps. Prowlarr supports management of both Torrent Trackers and Usenet Indexers. | [Link](https://prowlarr.com/) |
| qBittorrent | A lightweight, open-source BitTorrent download client featuring a full-featured web interface, bandwidth scheduling, and built-in search engines. | [Link](https://www.qbittorrent.org/) |
| Radarr | An automated movie collection manager and PVR that monitors RSS feeds for new releases, triggers download clients, and automatically organizes media files. | [Link](https://radarr.video/) |
| SABnzbd | An automated Usenet binary newsreader and download manager featuring automatic repair, unpacking, and seamless PVR stack integration. | [Link](https://sabnzbd.org/) |
| Sonarr | An automated TV series collection manager and PVR that tracks upcoming episodes, triggers downloads via Usenet or BitTorrent, and organizes show libraries. | [Link](https://sonarr.tv/) |

## Databases

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Adminer | Database management in a single PHP file. Supports MySQL, MariaDB, PostgreSQL, SQLite, MS SQL, Oracle, SimpleDB, Elasticsearch, MongoDB. | [Link](https://www.adminer.org/) |
| Nextcloud DB Dumper | An automated backup utility container that periodically exports SQL dumps of the Nextcloud MariaDB database for disaster recovery. | [Link](https://github.com/HenkVanHoek/njord-deploy) |
| Nextcloud MariaDB | A dedicated, pre-configured MariaDB relational database server optimized for Nextcloud persistent data storage and high query performance. | [Link](https://mariadb.org/) |
| phpMyAdmin | A comprehensive web-based administration tool for managing MySQL and MariaDB databases, executing SQL queries, and managing user access control. | [Link](https://www.phpmyadmin.net/) |

## Utilities

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Nextcloud High-Performance Push | Realtime notification and file-sync daemon for Nextcloud written in Rust. | [Link](https://github.com/nextcloud/notify_push) |
| Nextcloud Redis Cache | An in-memory Redis datastore configured as a high-performance transactional file locking broker and caching layer for Nextcloud. | [Link](https://redis.io/) |

## Reverse Proxy

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Caddy | Caddy is a powerful, enterprise-ready, open source web server with automatic HTTPS written in Go. | [Link](https://github.com/caddyserver/caddy) |
| Nginx Proxy Manager | An easy-to-use, Docker-based interface for managing Nginx proxy hosts with free SSL certificate support. | [Link](https://nginxproxymanager.com/) |
| Traefik | A modern, cloud-native reverse proxy and load balancer that automatically discovers services. | [Link](https://traefik.io/traefik/) |

## System Tools

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Filebrowser | A lightweight web-based file manager allowing users to upload, edit, delete, preview, and share files on server storage volumes. | [Link](https://filebrowser.org/) |
| Grafana Stack | An open-source visualization and analytics platform that turns metrics and logs into dynamic, interactive dashboards for comprehensive system observability. | [Link](https://grafana.com/) |
| Portainer | A powerful, user-friendly management UI that simplifies configuring, monitoring, and deploying Docker containers, stacks, and persistent volumes. | [Link](https://www.portainer.io/) |
| Prometheus Stack | Prometheus, a Cloud Native Computing Foundation project, is a systems and service monitoring system. It collects metrics from configured targets at given intervals, evaluates rule expressions, displays the results, and can trigger alerts when specified conditions are observed. This stack includes Prometheus, Node Exporter, and cAdvisor for comprehensive system and container monitoring. | [Link](https://prometheus.io/) |
| Semaphore UI | Modern UI for Ansible, Terraform/OpenTofu/Terragrunt, PowerShell and other DevOps tools. | [Link](https://semaphoreui.com/) |
| Service Maintenance | A system management component for monitoring service health, checking software updates, and auditing container vulnerabilities across NjordDeploy services. | [Link](https://github.com/HenkVanHoek/njord-deploy) |
| Uptime Kuma | A feature-rich, self-hosted monitoring tool providing real-time status pages, HTTP/ping health checks, and alerts via multiple notification channels. | [Link](https://uptime.kuma.pet/) |

## Security & Utilities

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Unbound | A secure, validating, recursive, and caching DNS resolver designed for privacy, preventing upstream ISP DNS logging when paired with Pi-hole or AdGuard. | [Link](https://www.nlnetlabs.nl/projects/unbound/about/) |
| Vaultwarden | A lightweight, self-hosted password manager compatible with Bitwarden clients. It provides almost all of the features of the official server without the resource-heavy footprint. | [Link](https://github.com/dani-garcia/vaultwarden) |
| Web Notepad | A minimal, web-based notepad application for quick note-taking, text sharing, and viewing system post-deployment summaries. | [Link](https://github.com/pajikos/minimalist-web-notepad) |

## Messaging

| Service | Description | Project Homepage / Repository |
|---|---|---|
| FluffyChat Web | A modern, cute, and cross-platform Matrix client web interface, packaged as a NjordDeploy component. | [Link](https://fluffychat.im/) |

## Communications

| Service | Description | Project Homepage / Repository |
|---|---|---|
| jitsi-meet | Jitsi Meet is a collection of open-source projects that provides a secure, simple, and scalable video conferencing solution. This component sets up a complete Jitsi Meet instance with optional Etherpad collaboration and recording capabilities. | [Link](https://jitsi.org/) |

## Utilities

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Microbin | Ultra-lightweight, configurable, feature-rich, self-hosted pastebin service. | [Link](https://microbin.eu/) |

## Productivity

| Service | Description | Project Homepage / Repository |
|---|---|---|
| n8n | Fair-code platform to build and deploy AI agents and workflows. Combine a visual canvas with custom code, run it self-hosted, and connect to 1500+ integrations. | [Link](https://n8n.io/) |
| Nextcloud | A comprehensive self-hosted productivity and collaboration suite offering secure file storage, online document editing, calendar, and contacts synchronization. | [Link](https://nextcloud.com/) |
| Open WebUI with Ollama | Open WebUI is an extensible, feature-rich, and user-friendly self-hosted AI platform designed to operate entirely offline. It supports various LLM runners like Ollama and OpenAI-compatible APIs, with built-in inference engine for RAG. This component bundles Open WebUI with Ollama for a complete, self-contained AI solution. Both services run as root (user: 0:0) to ensure proper file permissions for persistent data volumes. | [Link](https://openwebui.com/) |
| Stirling PDF | A powerful, open-source PDF editing platform for editing, signing, redacting, converting, and automating PDFs. | [Link](https://stirlingpdf.com/) |
| Voicebox | The open-source AI voice studio. Clone any voice. Generate speech. Dictate into any app. Talk to agents in voices you own. The full voice I/O stack, running locally on your machine. | [Link](https://github.com/HenkVanHoek/njord-deploy) |

## Media Servers

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Audiobookshelf | A self-hosted audiobook and podcast server for organizing, streaming, and tracking playback progress across your personal audio media library. | [Link](https://www.audiobookshelf.org/) |
