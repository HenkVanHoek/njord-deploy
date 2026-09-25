# 🏗️ NjordDeploy: Technitium DNS Server

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-dns_blocker-purple.svg)]()

> Technitium DNS Server is an open source authoritative and recursive DNS server for privacy & security. It features built-in ad and malware blocking, supports DNS-over-TLS (DoT), DNS-over-HTTPS (DoH), and DNS-over-QUIC (DoQ), and provides a comprehensive web management console.

- **Upstream Project:** [Technitium DNS Server](https://technitium.com/dns/)
- **Source Repository:** [github.com/technitium/dns-server](https://github.com/technitium/dns-server)
- **Container Image:** `technitium/dns-server`

---

## ✨ Why this Configuration?

- **True Data Sovereignty:** 100% GDPR/AVG-compliant on-premises deployment.
  You own your configuration, local persistent data, and operational audit
  trail without Big Tech vendor lock-in.
- **Hardware Agnostic:** Optimized and verified across low-power ARM64 Single
  Board Computers (Raspberry Pi 5) and x86_64 hypervisors (Proxmox VE LXC & VM).
- **Engine Freedom:** Tested and supported under standard **Docker Engine**
  as well as unprivileged rootless **Podman** environments.
- **Resource Footprint:**
  - **RAM Profile:** Medium
  - **CPU Profile:** Medium
  - **Storage:** Persistent
> **Platform Verification Notes:**
> Tested on Proxmox LXC: docker (24.04, 2026-09-14), podman (24.04, 2026-09-14); Proxmox VM: docker (24.04, 2026-09-14), podman (24.04, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  technitium-dns:
    container_name: njorddeploy-technitium-dns
    hostname: dns-server
    image: "technitium/dns-server:latest"
    ports:
      - "5380:5380/tcp"
      - "53:53/udp"
      - "53:53/tcp"
      - "853:853/tcp"
      - "443:443/tcp"
      - "853:853/udp"
    environment:
      - "DNS_SERVER_DOMAIN=dns-server.local"
      - "DNS_SERVER_ADMIN_PASSWORD=AdminPassword123!"
      - "DNS_SERVER_WEB_SERVICE_HTTP_PORT=5380"
      - "DNS_SERVER_LOG_FOLDER_PATH=/var/log/technitium/dns"
      - "DNS_SERVER_ENABLE_BLOCKING=true"
      - "DNS_SERVER_BLOCK_LIST_URLS=https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"
      - "DNS_SERVER_FORWARDERS=1.1.1.1, 8.8.8.8"
      - "DNS_SERVER_FORWARDER_PROTOCOL=Https"
      - "DNS_SERVER_RECURSION=AllowOnlyForPrivateNetworks"
      - "DNS_SERVER_RECURSION_NETWORK_ACL=172.16.0.0/12, 192.168.0.0/16, 10.0.0.0/8"
      - "DNS_SERVER_LOG_USING_LOCAL_TIME=true"
      - "DNS_SERVER_LOG_MAX_LOG_FILE_DAYS=30"
      - "DNS_SERVER_PREFER_IPV6=false"
    volumes:
      - "./data/technitium-dns/config:/etc/dns"
      - "./data/technitium-dns/logs:/var/log/technitium/dns"
    user: "0:0"
    restart: unless-stopped
    networks:
      - njorddeploy_net

networks:
  njorddeploy_net:
```

Start the service:
```bash
docker compose up -d
```

---

## ⚙️ Configuration & Environment Variables

| Variable | Default Value | Description |
|---|---|---|
| `DNS_WEB_CONSOLE_PORT` | `5380` | The host port for accessing the Technitium DNS Server web console via HTTP. |
| `DNS_UDP_PORT` | `53` | The host port for the standard DNS service over UDP. Typically port 53. |
| `DNS_TCP_PORT` | `53` | The host port for the standard DNS service over TCP. Typically port 53. |
| `DNS_DOT_PORT` | `853` | The host port for the DNS-over-TLS (DoT) service. Typically port 853. |
| `DNS_DOH_PORT` | `443` | The host port for the DNS-over-HTTPS (DoH) service. Typically port 443. |
| `DNS_DOQ_PORT` | `853` | The host port for the DNS-over-QUIC (DoQ) service. Typically port 853. |
| `DNS_SERVER_DOMAIN` | `dns-server.local` | The primary fully qualified domain name used by this DNS Server to identify itself. |
| `DNS_ADMIN_PASSWORD` | `AdminPassword123!` | The password for the DNS web console admin user. This is set on first run. |
| `DNS_ENABLE_BLOCKING` | `true` | Set to 'true' to enable blocking of domain names using Blocked Zone and Block List Zone features. |
| `DNS_BLOCK_LIST_URLS` | `https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts` | A comma-separated list of URLs for block lists (e.g., hosts files) to be used for ad and malware blocking. |
| `DNS_FORWARDERS` | `1.1.1.1, 8.8.8.8` | A comma-separated list of IP addresses for upstream DNS forwarders (e.g., Cloudflare, Google DNS). |
| `DNS_FORWARDER_PROTOCOL` | `Https` | The protocol to use for upstream DNS forwarders. Options: Udp, Tcp, Tls, Https, HttpsJson. |
| `DNS_RECURSION_MODE` | `AllowOnlyForPrivateNetworks` | Defines who can use the DNS server for recursive queries. Options: Allow, Deny, AllowOnlyForPrivateNetworks, UseSpecifiedNetworkACL. |
| `DNS_RECURSION_ACL` | `172.16.0.0/12, 192.168.0.0/16, 10.0.0.0/8` | Comma-separated list of IP addresses or network addresses (CIDR) to allow/deny recursion. Only valid for 'UseSpecifiedNetworkACL' recursion mode. Prefix with '!' to deny. |
| `DNS_LOG_MAX_DAYS` | `30` | Maximum number of days to keep log files. Log files older than this will be deleted automatically. Set to 0 to disable auto-delete. |
| `DNS_PREFER_IPV6` | `false` | Set to 'true' to make the DNS Server prefer IPv6 for querying whenever possible. |

---

## 🔑 First-Run Onboarding Guide

Open Technitium DNS Server web UI and complete the initial onboarding setup.

- **Upstream Setup Guide:** [https://technitium.com/dns/](https://technitium.com/dns/)

---
## 🔌 Ecosystem Integration with NjordDeploy

While this service can be run standalone, it integrates seamlessly into
the **NjordDeploy** self-hosting ecosystem:
- **Zero-Trust Network Isolation:** Isolated container bridge networks
  prevent direct external exposure of private database or caching layers.
- **Automated SSL & Ingress:** Plug-and-play reverse proxy integration with
  **Nginx Proxy Manager**, **Caddy**, or **Traefik** with automated Let's Encrypt certificates.
- **Disaster Recovery:** Integrated into NjordDeploy's backup engine with
  scheduled volume snapshots and atomic state restoration.
- **Observability:** Compatible with Prometheus, Grafana, and Uptime Kuma
  health probes.

---

## 🧪 Verified Quality & Proxmox Test Matrix

This component is part of the NjordDeploy automated hypervisor test harness:
- **Proxmox LXC (Docker Engine):** Tested & Passed
- **Proxmox LXC (Rootless Podman):** Tested & Passed
- **Proxmox QEMU VM (Docker Engine):** Tested & Passed
- **Proxmox QEMU VM (Rootless Podman):** Tested & Passed

View the latest multi-environment test results in the [Fleet Health Dashboard](/docs/test-reports/LATEST_RUN.md).

---

## 📦 Deploy with NjordDeploy (Recommended)

Don't want to manage passwords, volume permissions, SSL certificates, and network bindings manually?

Deploy **Technitium DNS Server** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
