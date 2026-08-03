<div align="center" dir="auto"><img width="150" height="150" style="max-width: 100%; height: auto; max-height: 150px;" alt="njorddeploy-icon512x512" src="https://github.com/HenkVanHoek/assets/63ed723a-578f-47f9-b40b-e241c4c5935b" /></div>

# Njord-Deploy

Welcome to NjordDeploy! This project provides a user-friendly system to deploy and manage a suite of self-hosted services on a Raspberry Pi (or any Linux-based system) using Docker. Our goal is to make self-hosting powerful, accessible, and easy to maintain.

## 🌟 Key Features

- **Fully Browser-Based Installer**: A simple, local web application guides you through every step, from device discovery to watching the live installation log.
- **Modular & Flexible**: Choose only the services you want from a curated list of popular applications (see the list of [Supported Services](docs/SUPPORTED_SERVICES.md)).
- **Dockerized & Isolated**: Every service runs in its own Docker container, making the system clean, secure, and easy to manage.
- **Component Editor**: A powerful web-based tool for developers to add, manage, and configure all components in the NjordDeploy ecosystem.
- **AI-Assisted Component Generator**: Leverage the Google Gemini API (using the GEMINI_API_KEY environment variable) to automatically bootstrap new components by providing just a GitHub repository URL and custom instructions.

## 🏛️ How It Works

A user downloads a single installer package from GitHub Releases. The installer runs a local web-based "Configurator" for device discovery and component selection, which then generates the necessary Docker Compose files and streams the installation process directly into the browser for the user.

## 📋 System Requirements

**On Your Main Computer (where you run the installer):**
- Windows, macOS, or Linux.
- **Linux Users**: Install the **nmap**, **sshpass**, and **OpenSSH client** packages.
  For Debian/Ubuntu:

      sudo apt install -y nmap sshpass openssh-client

**On Your Target Server (e.g., Raspberry Pi):**
- A Raspberry Pi 4 or newer is recommended.
- Or, use a Debian-based server, such as the one provided by [pi-server-vm](https://github.com/HenkVanHoek/pi-server-vm).
- Docker Engine and the Docker Compose plugin are required. The tool can
  install or upgrade them automatically as described below.
- SSH access must be enabled.

## Docker management on the target device

- Compose Spec is used. Compose files do not include a version key.
- Supported runtime: latest stable Docker Engine with the Docker Compose plugin.
- Minimum baseline: Docker Engine 20.10.0 or newer.

Behavior during deployment
1. Detect Docker Engine and Compose plugin.
2. If missing, install the latest Engine via the official installer, enable and
   start the docker service, and ensure the docker-compose-plugin package.
3. If an older Engine is detected, deployment stops with a clear error unless
   upgrade is allowed. To allow upgrade, provide one of the following variables
   in the deployment globals. The tool will remove older packages and install
   the latest Engine and Compose plugin. This upgrade is destructive on Docker
   state and removes local images and containers on the target device.

     ALLOW_DOCKER_UPGRADE=true
     # or
     GLOBAL_ALLOW_DOCKER_UPGRADE=true

4. Permissions: the remote user is added to the docker group for future
   sessions. During the current session, docker commands run with sudo if
   required.

## Host OS runtime policy

- Do not install or depend on a system Python interpreter or compiler on the
  target device for new NjordDeploy functionality.
- If Python is required for new automation or utilities, run it inside
  containers. Deliver it as a Docker image and execute it using Docker, including
  init container patterns when needed.
- Deployment and maintenance operations must not install Python onto the host.
  Remote steps are limited to shell, Docker, and core OS tooling.

## 🚀 Quick Start Guide

1.  **Download the Installer**: Go to the [GitHub Releases page](https://github.com/HenkVanHoek/njord-deploy/releases) and download the latest installer for your operating system.
2.  **Run the Installer**: Unzip the file and run the `NjordDeploy-Configurator` executable.
3.  **Configure**: Your web browser will open to the configurator UI. Follow the on-screen steps to discover your device, select software, and provide any required configuration.
4.  **Deploy**: After confirming your selections, the system will generate the necessary files and allow you to deploy them to your target device, with a live log of the entire process.

### One-Time Setup for Linux Users

If you are running the installer on a `Linux desktop`, you must perform a one-time setup to grant the scanner the necessary network permissions. Replace `your_username` with your actual Linux username.

    echo "your_username ALL=(ALL) NOPASSWD: /usr/bin/nmap" | sudo tee /etc/sudoers.d/99-njorddeploy
    sudo chmod 0440 /etc/sudoers.d/99-njorddeploy

## Project Directory Structure

The following tree represents the current physical layout of the project:
```
.
├── ansible
│   └── playbook.yml
├── component_templates
│   ├── adguard-home
│   ├── homeassistant
│   ├── pi-hole
│   ├── traefik
│   └── [other service templates...]
├── config
│   ├── components_metadata.json
│   └── raspberry_pi_oui.json
├── docs
│   ├── ARCHITECTURE.md
│   ├── DATA_CONTRACTS.md
│   ├── FUNCTIONAL_SPEC.md
│   └── sovereign_home_server.md
├── linux
│   ├── install.sh
│   └── njorddeploy-Configurator.desktop
├── pyproject.toml
├── README.md
├── run_editor.py
├── src
│   ├── configurator_app
│   │   ├── app.py
│   │   ├── static (base.css, configurator.css, images, js)
│   │   └── templates (base.html, index.html, help.html, etc.)
│   ├── editor_app
│   │   ├── app.py
│   │   ├── static (editor.v2.js, ui_render_utils.js)
│   │   └── templates (editor.html)
│   ├── management_tools
│   │   ├── logic.py
│   │   ├── routes.py
│   │   └── templates (backup_ui.html)
│   ├── managers
│   │   ├── component_manager.py
│   │   ├── deployment_manager.py
│   │   ├── setup_manager.py
│   │   └── ssh_manager.py
│   ├── config_tools
│   │   └── config_manager.py
│   ├── pi_scanner.py
│   └── utils
│       ├── auth_utils.py
│       ├── dashy_updater.py
│       ├── frigate_camera_config_tool.py
│       ├── generation_logger.py
│       └── resource_utils.py
├── tests
│   ├── configurator_app
│   ├── editor_app
│   ├── test_component_manager.py
│   ├── test_deployment_manager.py
│   ├── test_pi_scanner.py
│   └── test_setup_manager.py
└── windows
    └── start.bat
```
## 📚 Background and Articles

For a detailed case study on running a sovereign stack (including Nextcloud, Euro-Office, and Frigate) on a Raspberry Pi 5 with ZRAM and Google Coral TPU optimizations, please refer to:
- The article on DEV Community: [Building a Sovereign Home Server: Lessons Learned Running Nextcloud, Euro-Office, and Frigate on a Raspberry Pi 5](https://dev.to/henk_van_hoek/building-a-sovereign-home-server-lessons-learned-running-nextcloud-euro-office-and-frigate-on-a-1kbc)
- Our local summary of the lessons learned: [sovereign_home_server.md](file:///home/hvhoek/PycharmProjects/NjordDeploy/docs/sovereign_home_server.md)

## 🤝 Contributing
We welcome contributions! For guidelines on how to get started with development, please see our "CONTRIBUTING.md" file. To understand the core design principles and data contracts of the project, please review the "ARCHITECTURE.md" file. For detailed setup and usage instructions regarding separate components repository synchronization, Gemini AI integration, and the local Ollama LLM setup, see the [Developer AI and Sync Guide](docs/DEVELOPER_AI_AND_SYNC_GUIDE.md).

## 📄 License

This project is open-source and available under the MIT License.

You can also find more information about this project on my GitHub page: [HenkVanHoek/njord-deploy](https://github.com/HenkVanHoek/njord-deploy).
