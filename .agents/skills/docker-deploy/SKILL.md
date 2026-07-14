---
name: docker-deploy
description: Workflows voor het valideren en deployen van Docker-services via SSH op een remote machine voor NjordDeploy.
---

# Docker Deploy Workflow (NjordDeploy)

Gebruik deze skill wanneer de gebruiker vraagt om Docker-containers of configuraties te deployen, verifiëren of te beheren op een remote machine.

## Locatie op Remote Server:
* Gebruiker/Host: `<remote_user>@<remote_ip>`
* Doelmap: `/home/<remote_user>/docker/`

## Deployment Stappenplan:
1. **Kopieer Bestanden**: Kopieer de benodigde configuratiebestanden (zoals `docker-compose.yaml` of `verify_env.sh`) naar de server:
   ```bash
   scp verify_env.sh docker-compose.yaml <remote_user>@<remote_ip>:/home/<remote_user>/docker/
   ```
2. **Valideer de Omgeving**: Voer het verificatiescript uit via SSH om te controleren of alle omgevingsvariabelen correct zijn ingesteld:
   ```bash
   ssh <remote_user>@<remote_ip> "cd /home/<remote_user>/docker && ./verify_env.sh"
   ```
3. **Start/Update Containers**: Start of herstart de containers:
   ```bash
   ssh <remote_user>@<remote_ip> "cd /home/<remote_user>/docker && docker compose up -d"
   ```
4. **Verifieer Status**: Controleer of de containers correct draaien:
   ```bash
   ssh <remote_user>@<remote_ip> "docker ps -a"
   ```
