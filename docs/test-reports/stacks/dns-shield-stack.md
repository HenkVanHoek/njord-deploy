# 📦 Stack Verification Report: DNS & Ad-Blocking Privacy Shield

> **Stack ID:** `dns-shield-stack` | **Status:** ⚠️ VERIFIED | **Last Verified:** Pending test run

## Overview & Purpose

Network-wide privacy barrier bundling AdGuard Home DNS sinkhole with Unbound recursive DNS resolver for zero-ISP tracking.

### Test Environment & Parameters
- **Hypervisor / Platform:** Proxmox VE 8.x
- **Execution Target:** `Proxmox` (DOCKER)
- **Host Bridge / Network:** Isolated Subnet (`10.99.0.x`)
- **Services in Stack:** 2 modular containers

## Stack Services Matrix

| Service / Component | Status | Container | HTTP / Web UI | Log Validation | Details |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **AdGuard Home** (`adguard-home`) | ✅ Ready | Running | OK | Clean (No errors) | [Inspect](#details-adguard-home) |
| **Unbound** (`unbound`) | ✅ Ready | Running | N/A | Clean (No errors) | [Inspect](#details-unbound) |

---

## Detailed Service Inspection & Upstream Guides

Expand each section below to inspect ports, auth protocol, and upstream project links for post-installation configuration.

<details id="details-adguard-home">
<summary>🔍 <b>Component Inspection: AdGuard Home (<code>adguard-home</code>)</b></summary>

**Description:** AdGuard Home is a free and open-source network-wide software for blocking ads and tracking. It operates as a DNS server that re-routes tracking domains to a “black hole”, thus preventing your devices from connecting to those servers. It provides a web UI for configuration and monitoring. AdGuard Home is capable of running without root privileges, but for persistent volume access, the container is set to run as root (user: 0:0).

#### Upstream Project & Configuration Docs:
- 🌐 **Official Website / Repo:** [https://adguard.com/en/adguard-home/overview.html](https://adguard.com/en/adguard-home/overview.html)
- 📖 **Configuration Manual:** [https://github.com/AdguardTeam/AdGuardHome/wiki/Getting-Started](https://github.com/AdguardTeam/AdGuardHome/wiki/Getting-Started)
- 💡 **Post-Install Guide:** *Access the setup wizard to configure the listening DNS port, web management interface, and create administrator credentials.*

#### Deployment Runtime Parameters:
- **Port Bindings:** `Host/Standard`
- **Web UI Endpoint:** `http://10.99.0.199:3000`
- **Onboarding / Auth Protocol:** `wizard`
- **Volume Mapping:** Isolated Persistent Storage (`/opt/njorddeploy/adguard-home`)

#### Web UI Screenshot:
![AdGuard Home Web UI](../../images/test_screenshots/adguard-home_vm_podman_20260914_122029.png)


```yaml
# NjordDeploy verified configuration preview for adguard-home
service: adguard-home
status: healthy
restart_policy: unless-stopped
```
</details>

<details id="details-unbound">
<summary>🔍 <b>Component Inspection: Unbound (<code>unbound</code>)</b></summary>

**Description:** A secure, validating, recursive, and caching DNS resolver designed for privacy, preventing upstream ISP DNS logging when paired with Pi-hole or AdGuard.

#### Upstream Project & Configuration Docs:
- 🌐 **Official Website / Repo:** [https://www.nlnetlabs.nl/projects/unbound/about/](https://www.nlnetlabs.nl/projects/unbound/about/)
- 💡 **Post-Install Guide:** *Background service operating without an independent web interface.*

#### Deployment Runtime Parameters:
- **Port Bindings:** `Host/Standard`
- **Web UI Endpoint:** `Configured dynamically`
- **Onboarding / Auth Protocol:** `none`
- **Volume Mapping:** Isolated Persistent Storage (`/opt/njorddeploy/unbound`)

```yaml
# NjordDeploy verified configuration preview for unbound
service: unbound
status: healthy
restart_policy: unless-stopped
```
</details>

---

## 🖼️ Verified Web UI Screenshots Gallery

The following live screenshots were automatically captured during the test run:

### AdGuard Home (`adguard-home`)
- **Endpoint:** [http://10.99.0.199:3000](http://10.99.0.199:3000)

![AdGuard Home Web UI](../../images/test_screenshots/adguard-home_vm_podman_20260914_122029.png)

---
[⬅️ Back to Master Test Dashboard](../LATEST_RUN.md)
