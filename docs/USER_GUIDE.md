# NjordDeploy User & Network Setup Guide

This guide provides instructions for discovering target machines, configuring network connections, and setting up SSH key authentication for self-hosting services with NjordDeploy.

> [!TIP]
> **Are you new to self-hosting or looking for a fast 5-minute overview?**
> Check out the **[Beginner's Guide (Quick Start for Dummies)](GETTING_STARTED_FOR_BEGINNERS.md)** for a simple, visual step-by-step tutorial.

---

## 1. Network Discovery Methods

NjordDeploy supports multiple network discovery methods to find and connect to target Linux machines:

### 1.1 L2 Auto-Detect Subnet Scan
* **Best for:** Local Raspberry Pi, Orange Pi, ODROID, or SBC devices connected directly to your local Ethernet or Wi-Fi router.
* **Mechanism:** Uses L2 ARP broadcast sweeping (`nmap -sn -PR`) to scan your primary local IPv4 subnet (e.g., `192.168.1.0/24`).
* **Prerequisites:** `nmap` must be installed on the machine running NjordDeploy (`sudo apt install nmap`).

### 1.2 Custom Subnet Sweep (Manual CIDR)
* **Best for:** Multi-VLAN environments, isolated IoT networks, or custom sub-routers.
* **Mechanism:** Allows specifying a custom CIDR notation (e.g., `10.0.0.0/24` or `192.168.2.0/24`) to scan subnets outside your immediate primary interface.

### 1.3 Direct Target Deployment (IP / Hostname / MAC)
* **Best for:** Single static IP targets, Tailscale IPs (`100.x.y.z`), local DNS domain names (`my-server.local`), or explicit MAC addresses.
* **Mechanism:** Direct connection bypassing broadcast scans entirely.

### 1.4 Tailscale / Headscale Overlay Mesh Discovery
* **Best for:** Remote nodes, off-site servers, cloud VPS instances, or devices connected via Tailscale / Headscale WireGuard mesh networks.
* **Mechanism:** Queries your local Tailscale CLI daemon status (`tailscale status --json`) to list all active, online mesh peers automatically.
* **Advantages:** Instant 1-click discovery without needing local L2 ARP sweeps or public IP forwarding.

### 1.5 Proxmox VE Provisioning (LXC & QEMU VMs)
* **Best for:** Automatically creating fresh Debian LXC containers or cloning QEMU Cloud-Init VMs on a Proxmox VE server.
* **Mechanism:** Connects to Proxmox VE via API/SSH, provisions target containers/VMs, installs Docker Engine automatically, and returns ready-to-deploy IP addresses.

---

## 2. SSH Key Authentication Setup

NjordDeploy connects to target nodes via SSH to run provisioning scripts, install Docker stacks, and configure services.

### 2.1 Why Use SSH Key Authentication?
* **Security:** Eliminates plaintext passwords over SSH.
* **Passwordless Login:** Enables smooth, automated deployment without prompting for passwords repeatedly.
* **Key-Only Servers:** Essential for target servers where password login is disabled (`PasswordAuthentication no` in `/etc/ssh/sshd_config`).

### 2.2 Authorizing your Public Key (`ssh-copy-id`)
To authorize your local SSH public key on a target node:

1. Generate an SSH key pair on your deployer machine if you don't already have one:
   ```bash
   ssh-keygen -t ed25519 -C "njorddeploy"
   ```
2. Copy your public key to the target node:
   ```bash
   ssh-copy-id username@target-ip
   ```
   *(Example for Raspberry Pi: `ssh-copy-id pi@192.168.1.50` or Tailscale node `ssh-copy-id admin@100.121.216.150`)*
3. Test SSH connection without password:
   ```bash
   ssh username@target-ip
   ```

---

## 3. Target Machine Requirements

Every target machine must meet the following minimum requirements:
* **Operating System:** Debian 11/12, Ubuntu 22.04/24.04, or Raspberry Pi OS (64-bit recommended).
* **Architecture:** `x86_64` (amd64) or `aarch64` (arm64).
* **User Privileges:** Standard user with `sudo` permissions or `root`.
* **Network:** Open SSH port (`poort 22`) and outbound internet access to pull Docker container images.

---

## 4. Troubleshooting Common Connection Issues

* **`nmap` Not Installed:** Install nmap via your package manager: `sudo apt install nmap` or `sudo apk add nmap`.
* **Host Key Changed:** If target VM or LXC container was reinstalled, clear old host key with: `ssh-keygen -R target-ip`.
* **Tailscale Inactive:** Ensure Tailscale daemon is running: `sudo tailscale up`.

---

## 5. AI Failure Diagnostics & Multi-Provider LLM Configuration

NjordDeploy includes AI-powered failure diagnostics and automatic stack bootstrapping. You can configure your preferred LLM provider in the **Settings** menu (`/settings`) or directly in your `.env` file.

### Supported Providers & API Key Sources:
* **Google Gemini:** Recommended default (`gemini-2.5-flash`). Get key: [Google AI Studio](https://aistudio.google.com/app/apikey) (`GEMINI_API_KEY`).
* **OpenAI:** (`gpt-4o-mini`). Get key: [OpenAI Platform](https://platform.openai.com/api-keys) (`OPENAI_API_KEY`).
* **Anthropic Claude:** (`claude-3-5-sonnet-20241022`). Get key: [Anthropic Console](https://console.anthropic.com/settings/keys) (`ANTHROPIC_API_KEY`).
* **HostYourAI / Loes (EU):** GDPR and EU AI Act compliant European private cloud. Portal: [HostYourAI](https://hostyourai.com) (`HOSTYOURAI_API_KEY`).
* **Ollama Local (Offline):** 100% private, offline LLMs running locally without API keys. Download: [Ollama](https://ollama.com) (`OLLAMA_BASE_URL=http://localhost:11434/v1`).
* **Custom Endpoints:** Compatible with any OpenAI-standard chat completion API (`CUSTOM_AI_BASE_URL`, `CUSTOM_AI_API_KEY`).
