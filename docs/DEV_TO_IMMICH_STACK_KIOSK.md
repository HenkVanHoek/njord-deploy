---
title: From Cold Storage to Living Room Wall: Why Immich + Immich Kiosk is the Ultimate Self-Hosted Photo Stack
published: false
description: A practical deep dive into deploying a turnkey Immich & Immich Kiosk stack. How we solved homelab port conflicts, bypassed strict Go Viper directory permission crashes, and validated the multi-container suite on Proxmox VE.
tags: selfhosted, docker, devops, opensource
canonical_url: https://njorddeploy.com/stacks/immich-stack/
cover_image: https://raw.githubusercontent.com/HenkVanHoek/njord-deploy/main/src/configurator_app/static/images/njorddeploy-icon512x512.png
---

# From Cold Storage to Living Room Wall: Why Immich + Immich Kiosk is the Ultimate Self-Hosted Photo Stack

In my previous article on DEV Community, [*"How I Built an Agentless Self-Hosting Orchestrator with 100+ Tested Stacks & 100% Local AI"*](https://dev.to/henk_van_hoek/how-i-built-an-agentless-self-hosting-orchestrator-with-100-tested-stacks-100-local-ai-37cf), I shared the architectural principles behind **[NjordDeploy](https://njorddeploy.com)**: keeping target hardware completely pure, avoiding heavy background agents, and validating multi-container stacks against real-world hypervisor environments.

Today, I want to talk about one of the most beloved self-hosted applications in the entire homelab ecosystem: **[Immich](https://immich.app)** — and how pairing it with **Immich Kiosk** transforms your family photos from cold, static storage on a hard drive into a dynamic, living ambient photo frame for your home or office.

Along the way, we will dissect the real-world engineering pitfalls we uncovered while orchestrating this suite — including **homelab port collisions**, a **strict Go Viper directory permission failure**, and how we cross-validated the entire bundle on Debian 12 with automated Playwright browser tests.

---

## 📸 The Problem: The "Digital Shoe Box" Syndrome

When self-hosters migrate away from Google Photos or Apple iCloud to regain digital sovereignty, **Immich** is usually the first choice. And for good reason:
- Lightning-fast timeline scrolling.
- Local machine learning for facial recognition, object detection, and vector clip search.
- Seamless automatic background uploads from iOS and Android devices.
- Native multi-user isolation and partner sharing.

**Yet, a subtle psychological problem emerges:**
Once your 80,000 photos and videos are safely backed up to your home server, they often sit there untouched. Unless you actively open the smartphone app or log into the web interface, your most precious family memories stay locked away in a "digital shoe box."

Historically, families had framed photographs on walls, mantelpieces, and desks. We wanted that same warmth back — but powered entirely by our self-hosted server without relying on cloud-connected commercial digital frames that harvest telemetry or go obsolete when an external vendor shuts down their servers.

Enter **[Immich Kiosk](https://github.com/damongolding/immich-kiosk)** by Damon Golding.

---

## 🖼️ What is Immich Kiosk?

`immich-kiosk` is a lightweight, dedicated web client designed specifically for ambient displays, low-power wall tablets, smart TVs, and dedicated digital photo frames.

```
+-------------------------------------------------------------------+
|                     Your Living Room / Office                     |
|                                                                   |
|   +-----------------------------------------------------------+   |
|   |  [Wall Tablet / Smart TV / Raspberry Pi Display]          |   |
|   |                                                           |   |
|   |      +---------------------------------------------+      |   |
|   |      |                                             |      |   |
|   |      |            [High-Res Family Photo]          |      |   |
|   |      |                                             |      |   |
|   |      |   📍 Kyoto, Japan        📅 April 14, 2024  |      |   |
|   |      |   📷 Sony A7IV           ⏱️ 1/500s f/2.8     |      |   |
|   |      +---------------------------------------------+      |   |
|   |      | 🕒 16:45  🌤️ 19°C Amsterdam   | Album: Favorites|  |
|   +------+---------------------------------------------+------+   |
|                                 │                                 |
+---------------------------------┼---------------------------------+
                                  │ HTTP Port 2284
                                  ▼
+-------------------------------------------------------------------+
|               NjordDeploy Sovereign Host / Proxmox VM             |
|                                                                   |
|   +-----------------------+       +---------------------------+   |
|   |      immich-kiosk     | ----> |       immich-server       |   |
|   |   (damongolding/...)  |       |   (API & Media Engine)    |   |
|   +-----------------------+       +---------------------------+   |
|                                                 │                 |
|                   +-----------------------------+                 |
|                   ▼                             ▼                 |
|       +-----------------------+     +-----------------------+     |
|       |  PostgreSQL + pgvector|     |      Redis Cache      |     |
|       +-----------------------+     +-----------------------+     |
+-------------------------------------------------------------------+
```

Instead of simply loading the standard Immich web UI in fullscreen mode (which exposes navigation sidebars, editing tools, and admin controls), Immich Kiosk provides:
1. **Curated Album Slideshows**: Point it to a specific album (e.g., *"Best of 2025"*, *"Kids & Grandkids"*, or *"Wall Display"*).
2. **Ambient EXIF Data Overlay**: Displays the date taken, location name, and camera lens settings without obscuring the image.
3. **Smart Aspect Ratio Handling**: Gracefully presents landscape and portrait shots with gentle blurred background fills or split views.
4. **Zero User Interaction Required**: Auto-starts in fullscreen kiosk mode, rotates through photos with customizable transition intervals, and gracefully reconnects if the network blips.

---

## 🛠️ The DevOps Hurdles: 3 Practical Lessons Learned

When packaging `immich-kiosk` into a turnkey, 1-click stack in NjordDeploy, we ran into three real-world deployment challenges that every homelabber and DevOps engineer should be aware of.

### 1. The Homelab Port 3000 Collision

By default, Immich Kiosk listens on port `3000`. In isolation, that is completely standard for Node or Go web applications.

However, in any realistic multi-service homelab, **port 3000 is a high-conflict hotspot**:
- AdGuard Home (initial setup wizard)
- Grafana (standard dashboard port)
- Gitea / Forgejo (frequently mapped to 3000)
- Nocodb

**The Solution:**
In NjordDeploy, all ports are centrally negotiated via a deterministic port allocation contract. Immich itself uses port `2283`. To maintain clean mnemonic consistency, we assigned external port **`2284`** to Immich Kiosk, mapping directly to container port `3000`:

```yaml
services:
  immich-kiosk:
    image: ghcr.io/damongolding/immich-kiosk:0.44.1
    container_name: immich-kiosk
    restart: unless-stopped
    ports:
      - "{{ KIOSK_PORT | default('2284') }}:3000"
    networks:
      - njorddeploy_net
```

Both containers communicate over the isolated `njorddeploy_net` bridge network, allowing Kiosk to query Immich's API internally without hairpinned traffic through external routers.

---

### 2. The Strict Go Viper Directory Permission Trap

This was by far the most intriguing issue during our test cycle.

Immich Kiosk is written in Go and uses the popular `spf13/viper` library for configuration management. In `config_validation.go`, the application checks the Linux permissions of its configuration directory (`./config`).

When provisioning containers via automated orchestration tools (such as Ansible, cloud-init, or permissive volume creation scripts), host bind directories often inherit a `0777` permission mask to avoid UID/GID access issues.

**The Fatal Crash:**
When `immich-kiosk` booted with a mounted `./config` directory with `777` permissions, it immediately terminated with:

```text
fatal error: config directory permission is 777, it should be 755
exit status 1
```

If you fix the directory to `755`, but the container runs under a non-root UID, it might fail to write state.

**The Architectural Insight: KISS & Stateless Design**
Looking deeper into the source code, we noticed that if the `./config` folder is *not* mounted, Kiosk logs:
```text
[INFO] Not using config.yaml, reading from environment variables
```
Since Immich Kiosk is fundamentally a display consumer (all persistent state, albums, photos, and embeddings live inside PostgreSQL and the Immich storage volume), **Kiosk is completely stateless!**

Mounting a host volume for a stateless presentation layer violated the Keep It Simple, Stupid (KISS) principle. We eliminated the volume mount entirely and passed all settings through declarative environment variables:

```yaml
    environment:
      - KIOSK_IMMICH_URL={{ KIOSK_IMMICH_URL | default('http://immich-server:2283') }}
      - KIOSK_IMMICH_API_KEY={{ KIOSK_IMMICH_API_KEY | default('initial_setup_token') }}
      - KIOSK_INTERVAL={{ KIOSK_INTERVAL | default('30') }}
      - KIOSK_TRANSITION={{ KIOSK_TRANSITION | default('fade') }}
```

Zero volume mounts. Zero file lock contention. Zero directory permission crashes. The container spins up in under 300 milliseconds.

---

### 3. The Required API Key Startup Contract

In Go applications with strict configuration schemas, startup validators can prevent the web server from binding if a required token is missing.

`immich-kiosk` checks for `KIOSK_IMMICH_API_KEY`. If left completely blank, the container halts during boot before even presenting its setup interface.

To ensure an out-of-the-box seamless user experience, we defaulted `KIOSK_IMMICH_API_KEY` to an explicit bootstrap token (`initial_setup_token`). When first launched, Kiosk boots cleanly, binds port `2284`, and serves a friendly web page directing the user to generate an API key inside Immich and paste it into the UI.

---

## 📦 Turnkey Orchestration: The `immich-stack` Package

Rather than requiring users to manually select and wire up individual services, NjordDeploy packages this combination into a single-click turnkey bundle called **`immich-stack`**:

```json
{
  "immich-stack": {
    "name": "Immich Photo & Kiosk Suite",
    "badge": "Photo Hub",
    "description": "High-performance self-hosted photo & video backup vault combined with an ambient smart digital frame kiosk.",
    "components": [
      "immich",
      "immich-kiosk"
    ]
  }
}
```

When you deploy `immich-stack`, NjordDeploy automatically:
1. Provisions PostgreSQL with the `pgvector` extension for semantic image searching.
2. Configures Redis for job queuing, thumbnail generation, and metadata extraction.
3. Launches Immich Server and Immich Machine Learning microservices.
4. Spins up Immich Kiosk on port `2284`, pre-wired to Immich's internal DNS endpoint.
5. Verifies container health and port bindings before declaring the deployment complete.

---

## 🧪 Validating on Proxmox VE: Automated Test Dossiers

At 55+ years in computing, one lesson stands above all others: **if you haven't tested it in an isolated environment that mirrors production, it doesn't work.**

We validated the new `immich-kiosk` template and the `immich-stack` turnkey package on our Proxmox VE test cluster using clean Debian 12 Bookworm VMs running Docker Engine:

```text
================================================================================
Test Dossier: immich-stack (Debian 12 QEMU VM / Docker CE)
================================================================================
Target Host:            192.168.1.100 (Debian 12 Bookworm, Kernel 6.1)
Containers Deployed:    immich-server, immich-machine-learning,
                        immich-postgres, immich-redis, immich-kiosk
Convergence Time:       42 seconds

Endpoint Verification:
  [2283/tcp] Immich Web UI    --> HTTP/1.1 200 OK (Rendered in 184ms)
  [2284/tcp] Immich Kiosk UI  --> HTTP/1.1 200 OK (Rendered in 42ms)

Playwright Verification:
  📸 Captured UI Screenshot: pkg_immich_vm_docker_20260927.png
  📸 Captured UI Screenshot: pkg_immich-kiosk_vm_docker_20260927.png
Status: ✅ PASSED (Zero Errors, Zero Leaks)
================================================================================
```

Both endpoints were verified with automated headless Chromium browser runs via Playwright, ensuring that the DOM rendered properly, CSS loaded, and no JavaScript console exceptions occurred.

---

## 💡 Practical Takeaways for Your Homelab

If you are running Immich today or planning your photo backup strategy:

1. **Liberate your photos from the phone screen**: Even an old iPad 2, Fire Tablet, or Raspberry Pi hooked up to a secondary PC monitor can become an extraordinary family photo frame with `immich-kiosk`.
2. **Keep helper containers stateless**: Don't bind host directories for applications that don't own persistent data. Pass configuration through environment variables whenever possible.
3. **Be mindful of port 3000**: When building modular compose files, anticipate collisions before they break your existing reverse proxy or DNS filters.
4. **Separate storage from compute**: Keep your original photo library on redundant storage (ZFS RAID-Z2, mirrored pools, or NAS NFS mounts), but run your application microservices on fast NVMe storage for instant search indexing.

---

## 🔗 Try It Out

Both the `immich-kiosk` template and the `immich-stack` package are fully open source and ready to deploy:

- 🌐 **NjordDeploy Official Website:** [njorddeploy.com](https://njorddeploy.com)
- 🖼️ **Immich Stack Overview:** [njorddeploy.com/stacks/immich-stack/](https://njorddeploy.com/stacks/immich-stack/)
- 📺 **Immich Kiosk Component:** [njorddeploy.com/components/immich-kiosk/](https://njorddeploy.com/components/immich-kiosk/)
- 🐙 **Core GitHub Repository:** [HenkVanHoek/njord-deploy](https://github.com/HenkVanHoek/njord-deploy)
- 📦 **Component Catalog Repo:** [HenkVanHoek/njord-deploy-components](https://github.com/HenkVanHoek/njord-deploy-components)

*How are you displaying your self-hosted photos at home? Have you experimented with digital frames or ambient kiosks? Let's discuss in the comments below!*
