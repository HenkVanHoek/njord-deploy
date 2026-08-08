# Supported Services

This document is automatically generated from the project metadata. It lists the open-source software packages that can be deployed using NjordDeploy, along with links to their official repositories and homepages.

## DNS Blocker

| Service | Description | Project Homepage / Repository |
|---|---|---|
| AdGuard Home | Network-wide ad & tracker blocking DNS server. An alternative to Pi-hole. | [Link](https://github.com/AdguardTeam/AdGuardHome) |
| Pi-hole | A network-wide ad blocker that acts as a DNS sinkhole. | [Link](https://pi-hole.net/) |

## General Components

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Conduit (Matrix Server) | A lightweight, next-generation Matrix homeserver, ideal for Raspberry Pi. But no working management tool available for on the Raspberry Pi. | [Link](https://conduit.rs/) |
| LoRa Letterbox Notifier |  | [Link](https://github.com/HenkVanHoek/lora-letterbox-notifier) |
| OctoPrint | The snappy web interface for your 3D printer. See https://octoprint.org for more information. | [Link](https://octoprint.org/) |
| Prosody | Prosody is a modern, lightweight XMPP (Jabber) communication server designed for efficiency and extensibility. Within the NjordDeploy ecosystem, this component provides a private and secure instant messaging platform. It allows users to host their own chat services, including: One-to-one messaging: Secure, real-time private conversations. Multi-User Chat (MUC): Group chat capabilities for family or teams. HTTP File Upload: Seamless sharing of photos and files directly from your own hardware. Modern Security: Automated TLS encryption using Let's Encrypt certificates via Nginx Proxy Manager. Note: This service requires port 5222 (client-to-server) and 5269 (server-to-server) to be forwarded in your router for external access. | [Link](https://prosody.im/) |

## Smart Home & Iot

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Frigate | NVR with real-time object detection for IP cameras. | [Link](https://docs.frigate.video/) |
| Home Assistant | Open source home automation that puts local control and privacy first. | [Link](https://www.home-assistant.io/) |
| Scrypted | High-performance video integration platform for smart homes. | [Link](https://www.scrypted.app/) |
| UniFi Controller | Manage your UniFi networking devices from a central controller. | [Link](https://ui.com/wi-fi) |
| Zigbee2MQTT | Bridge the gap between your Zigbee devices and your MQTT broker. | [Link](https://www.zigbee2mqtt.io/) |

## Development Tools

| Service | Description | Project Homepage / Repository |
|---|---|---|
| GitLab | A complete DevOps platform for project planning, source code management, CI/CD, and monitoring. | [Link](https://about.gitlab.com/) |

## Dashboard & Homepages

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Heimdall | A simple and elegant application dashboard. | [Link](https://heimdall.site/) |
| Homarr | A simple, yet powerful dashboard for your server. | [Link](https://homarr.dev/) |
| Homepage | A modern, fully static, fast, secure fully proxied, highly customizable application dashboard with integrations for over 100 services and translations into multiple languages. Easily configured via YAML files or through docker label discovery. Homepage does not include an authentication layer itself; it is recommended to place it behind a reverse proxy with authentication if exposed to untrusted networks. For optimal file permissions on mounted volumes, the container is configured to run as root (user: 0:0) by default, overriding the PUID/PGID environment variables if set. Note: Docker integration requiring access to /var/run/docker.sock is not enabled by default for security reasons. Users can manually add this volume mount if needed. | N/A |
| Homer | A dead simple, static homepage for your server. | [Link](https://github.com/bastienwirtz/homer) |
| Organizr | A full-featured server organizer with a tabbed interface. | [Link](https://organizr.app/) |

## Media Stack

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Gluetun | Lightweight swiss-army-knife-like VPN client to multiple VPN service providers. | N/A |
| Jellyfin | A Free Software Media System that puts you in control of your media. | [Link](https://jellyfin.org/) |
| Prowlarr | Prowlarr is an indexer manager/proxy built on the popular *arr .net/reactjs base stack to integrate with your various PVR apps. Prowlarr supports management of both Torrent Trackers and Usenet Indexers. | N/A |
| qBittorrent | A lightweight and powerful BitTorrent client. | [Link](https://www.qbittorrent.org/) |
| Radarr | A fork of Sonarr to work with movies. | [Link](https://radarr.video/) |
| SABnzbd | The popular and easy-to-use Usenet download client. | [Link](https://sabnzbd.org/) |
| Sonarr | Smart PVR for newsgroup and bittorrent users to manage and download TV shows. | [Link](https://sonarr.tv/) |

## Databases

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Adminer | Database management in a single PHP file. Supports MySQL, MariaDB, PostgreSQL, SQLite, MS SQL, Oracle, SimpleDB, Elasticsearch, MongoDB. | [Link](https://www.adminer.org/) |
| Nextcloud DB Dumper | Automated backup container for Nextcloud MariaDB database. | [Link](https://github.com/HenkVanHoek/njord-deploy) |
| Nextcloud MariaDB | Relational MariaDB database tailored for Nextcloud. | [Link](https://mariadb.org/) |
| phpMyAdmin | Web interface for managing MySQL and MariaDB databases. | [Link](https://www.phpmyadmin.net/) |

## Utilities

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Nextcloud High-Performance Push | Realtime notification and file-sync daemon for Nextcloud written in Rust. | [Link](https://github.com/nextcloud/notify_push) |
| Nextcloud Redis Cache | In-memory caching and lock broker for Nextcloud. | [Link](https://redis.io/) |

## Reverse Proxy

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Caddy | Caddy is a powerful, enterprise-ready, open source web server with automatic HTTPS written in Go. | [Link](https://github.com/caddyserver/caddy) |
| Nginx Proxy Manager | An easy-to-use, Docker-based interface for managing Nginx proxy hosts with free SSL certificate support. | [Link](https://nginxproxymanager.com/) |
| Traefik | A modern, cloud-native reverse proxy and load balancer that automatically discovers services. | [Link](https://traefik.io/traefik/) |

## System Tools

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Filebrowser | Web-based file manager for managing your self-hosted data files and Caddyfile. | [Link](https://filebrowser.org/) |
| Grafana Stack | The open-source platform for monitoring and observability | N/A |
| Portainer | A powerful management UI for Docker environments. | [Link](https://www.portainer.io/) |
| Prometheus Stack | Prometheus, a Cloud Native Computing Foundation project, is a systems and service monitoring system. It collects metrics from configured targets at given intervals, evaluates rule expressions, displays the results, and can trigger alerts when specified conditions are observed. This stack includes Prometheus, Node Exporter, and cAdvisor for comprehensive system and container monitoring. | N/A |
| Semaphore UI | Modern UI for Ansible, Terraform/OpenTofu/Terragrunt, PowerShell and other DevOps tools. | N/A |
| Service Maintenance | Monitor status, updates and vulnerabilities. | [Link](https://github.com/HenkVanHoek/njord-deploy) |
| Uptime Kuma | A self-hosted monitoring tool for proactive health checks and notifications via email, Telegram, and more | [Link](https://github.com/louislam/uptime-kuma) |

## Security & Utilities

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Unbound | A validating, recursive, and caching DNS resolver for maximum privacy. | [Link](https://www.nlnetlabs.nl/projects/unbound/about/) |
| Vaultwarden | A lightweight, self-hosted password manager compatible with Bitwarden clients. It provides almost all of the features of the official server without the resource-heavy footprint. | [Link](https://github.com/dani-garcia/vaultwarden) |
| Web Notepad | Simple notepad to display the post-install summary. | [Link](https://github.com/pajikos/minimalist-web-notepad) |

## Messaging

| Service | Description | Project Homepage / Repository |
|---|---|---|
| FluffyChat Web | A modern, cute, and cross-platform Matrix client web interface, packaged as a NjordDeploy component. | N/A |

## Communications

| Service | Description | Project Homepage / Repository |
|---|---|---|
| jitsi-meet | Jitsi Meet is a collection of open-source projects that provides a secure, simple, and scalable video conferencing solution. This component sets up a complete Jitsi Meet instance with optional Etherpad collaboration and recording capabilities. | N/A |

## Utilities

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Microbin | Ultra-lightweight, configurable, feature-rich, self-hosted pastebin service. | N/A |

## Productivity

| Service | Description | Project Homepage / Repository |
|---|---|---|
| n8n | Fair-code platform to build and deploy AI agents and workflows. Combine a visual canvas with custom code, run it self-hosted, and connect to 1500+ integrations. | N/A |
| Nextcloud | File storage, sharing, productivity and collaboration platform. | [Link](https://nextcloud.com/) |
| Open WebUI with Ollama | Open WebUI is an extensible, feature-rich, and user-friendly self-hosted AI platform designed to operate entirely offline. It supports various LLM runners like Ollama and OpenAI-compatible APIs, with built-in inference engine for RAG. This component bundles Open WebUI with Ollama for a complete, self-contained AI solution. Both services run as root (user: 0:0) to ensure proper file permissions for persistent data volumes. | N/A |
| Stirling PDF | A powerful, open-source PDF editing platform for editing, signing, redacting, converting, and automating PDFs. | N/A |
| Voicebox | The open-source AI voice studio. Clone any voice. Generate speech. Dictate into any app. Talk to agents in voices you own. The full voice I/O stack, running locally on your machine. | N/A |

## Media Servers

| Service | Description | Project Homepage / Repository |
|---|---|---|
| Audiobookshelf | Self-hosted audiobook and podcast server to manage and play your audiobooks and podcasts. | N/A |
