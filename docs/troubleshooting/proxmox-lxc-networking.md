# Proxmox LXC Container Networking and SSH Troubleshooting Guide

This document details the configuration issues, root causes, and fixes applied to resolve DHCP/DNS network conflicts, packet loss during container image retrieval, SSH host key mismatch errors, and n8n secure cookie blocks in self-hosted Proxmox LXC container environments.

---

## 1. DHCP Hostname Conflicts (DNS UDP Timeout)

### 1.1 Symptoms
During deployment operations (such as running `docker compose pull`), the task fails with:
```
failed to copy: httpReadSeeker: failed open: failed to do request: Get "https://pkg-containers.githubusercontent.com/...": dial tcp: lookup pkg-containers.githubusercontent.com on 192.168.1.118:53: read udp 192.168.1.91:46161->192.168.1.118:53: i/o timeout
```

### 1.2 Root Cause
If multiple LXC containers share the same hostname (e.g. `njorddeploy-n8n`), they attempt to register their DNS names against the local network DHCP/DNS server (`192.168.1.118`) under the same name. This causes ARP table collisions, lease conflicts, and packet drops/latency.

### 1.3 Fix
We added a pre-flight validation check to both the configurator web-app (`src/configurator_app/app.py`) and the CLI script (`scripts/create_proxmox_lxc.py`). If a container with the same hostname already exists on the Proxmox node, creation is aborted with a `409 Conflict` error displaying the conflicting VMIDs.

---

## 2. Proxmox Virtual Interface Firewall (`firewall=0`)

### 2.1 Symptoms
High-volume concurrent network traffic (such as downloading multiple Docker image layers in parallel) causes connection timeout drops and DNS query failures inside the LXC container.

### 2.2 Root Cause
Enabling the Proxmox firewall (`firewall=1`) on the container's network interface enables connection tracking (`nf_conntrack`) on the host. Under high concurrency, the connection tracking table can overflow, dropping UDP/TCP packets as "invalid". Additionally, the firewall blocks incoming container ports unless specific rules are configured.

### 2.3 Fix
We updated the container network configuration string from `firewall=1` to `firewall=0` in `app.py`, `create_proxmox_lxc.py`, and the test runners. Self-hosted services in the secure local LAN do not require Proxmox-level virtual interface firewalls, and setting it to `0` resolves packet dropping issues under load.

---

## 3. SSH Host Key Mismatch (Reused DHCP IPs)

### 3.1 Symptoms
The configurator UI or logs display:
```
An error occurred: Failed to connect to container via SSH: Host key for server '192.168.1.91' does not match: got 'AAAAC3NzaC...', expected 'AAAAC3NzaC...'
```

### 3.2 Root Cause
DHCP leases are often reassigned or reused. When a new container is provisioned on a previously used IP, the host key of the new container differs from the previous container's host key stored in the developer's system `known_hosts` file.

### 3.3 Fix
During LXC creation and docker log retrieval, we instantiate the `SSHManager` with:
- `allow_auto_add=True`
- `load_system_keys=False`

This prevents the SSH client from loading the local system's `known_hosts` file and checks against stale keys, allowing seamless connection to brand-new target environments.

---

## 4. n8n Secure Cookie Block (HTTP Local IP Access)

### 4.1 Symptoms
After successfully launching n8n, accessing it via HTTP (e.g. `http://192.168.1.91:5678`) redirects to an error page:
```
Your n8n server is configured to use a secure cookie, however you are either visiting this via an insecure URL, or using Safari.
```

### 4.2 Root Cause
By default, modern n8n configurations require secure cookies (`N8N_SECURE_COOKIE=true`), which prevents cookie transmissions over unencrypted HTTP (except on `localhost`). This blocks access when navigating to n8n via a local LAN IP address.

### 4.3 Fix
We updated the n8n docker-compose template (`component_templates/n8n/docker-compose.template.yml`) to inject `N8N_SECURE_COOKIE=false` as an environment variable, allowing users to log in securely over local HTTP network connections.
