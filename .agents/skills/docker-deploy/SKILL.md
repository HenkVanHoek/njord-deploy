---
name: docker-deploy
description: Workflows for validating and deploying Docker services via SSH on a remote machine for NjordDeploy.
---

# Docker Deploy Workflow (NjordDeploy)

Use this skill when the user asks to deploy, verify, or manage Docker containers or configurations on a remote machine.

## Location on Remote Server:
* User/Host: `<remote_user>@<remote_ip>`
* Target Directory: `/home/<remote_user>/docker/`

## Deployment Steps:
1. **Copy Files**: Copy the required configuration files (such as `docker-compose.yaml` or `verify_env.sh`) to the server:
   ```bash
   scp verify_env.sh docker-compose.yaml <remote_user>@<remote_ip>:/home/<remote_user>/docker/
   ```
2. **Validate Environment**: Run the verification script via SSH to verify that all environment variables are correctly set:
   ```bash
   ssh <remote_user>@<remote_ip> "cd /home/<remote_user>/docker && ./verify_env.sh"
   ```
3. **Start/Update Containers**: Start or restart the containers:
   ```bash
   ssh <remote_user>@<remote_ip> "cd /home/<remote_user>/docker && docker compose up -d"
   ```
4. **Verify Status**: Check if the containers are running correctly:
   ```bash
   ssh <remote_user>@<remote_ip> "docker ps -a"
   ```
