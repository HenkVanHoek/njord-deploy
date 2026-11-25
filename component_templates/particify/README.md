# 🏗️ NjordDeploy: Particify

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-Productivity-purple.svg)]()

> Open-source audience response system (ARSnova) and privacy-friendly Mentimeter / Slido alternative for live polls, Q&A, quizzes, and interactive presentations.

- **Upstream Project:** [Particify](https://particify.de)
- **Source Repository:** [github.com/particify/arsnova-server](https://github.com/particify/arsnova-server)
- **Container Image:** `particify/arsnova-proxy:3`

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
  - **RAM Profile:** High
  - **CPU Profile:** High
  - **Storage:** Persistent
> **Platform Verification Notes:**
> Tested on Proxmox LXC: docker (3.14.20261123, 2026-11-25).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  particify:
    image: particify/arsnova-proxy:3
    container_name: njorddeploy-particify
    restart: unless-stopped
    ports:
      - "8123:80"
    environment:
      ARSNOVA_HOSTNAME: "localhost"
      CSP_FRAME_ANCESTORS: ""
    depends_on:
      - arsnova-backend-core
      - arsnova-auth-service
      - arsnova-ws-gateway
      - arsnova-http-gateway
      - arsnova-comment-service
      - arsnova-web
    networks:
      - njorddeploy_net
      - particify_internal

  arsnova-web:
    image: particify/arsnova-webclient:3.14.20261123
    container_name: njorddeploy-particify-web
    restart: unless-stopped
    networks:
      - particify_internal

  arsnova-backend-core:
    image: particify/arsnova-server-core:3.14.20261123
    container_name: njorddeploy-particify-core
    restart: unless-stopped
    depends_on:
      particify-couchdb:
        condition: service_healthy
      particify-rabbitmq:
        condition: service_healthy
    environment:
      SYSTEM_ROOTURL: "http://localhost:8123"
      SYSTEM_API_PROXYPATH: "/api"
      SYSTEM_SOCKETIO_BINDADDRESS: "0.0.0.0"
      SYSTEM_COUCHDB_HOST: "particify-couchdb"
      SYSTEM_COUCHDB_USERNAME: "arsnova"
      SYSTEM_COUCHDB_PASSWORD: "ChangeMeParticifyDatabasePassword2026!"
      SYSTEM_COUCHDB_CREATEDB: "true"
      SYSTEM_MESSAGE_BROKER_RABBITMQ_ENABLED: "true"
      SYSTEM_MESSAGE_BROKER_RABBITMQ_HOST: "particify-rabbitmq"
      SYSTEM_MESSAGE_BROKER_RABBITMQ_USERNAME: "guest"
      SYSTEM_MESSAGE_BROKER_RABBITMQ_PASSWORD: "guest"
      SYSTEM_MESSAGE_BROKER_RABBITMQ_VIRTUAL_HOST: "/"
      SYSTEM_MAIL_HOST: ""
      SYSTEM_MAIL_PORT: "25"
      SYSTEM_MAIL_IMPLICITTLS: "false"
      SYSTEM_MAIL_USERNAME: "particify"
      SYSTEM_MAIL_PASSWORD: "ChangeMeSecurePassword123!"
      SYSTEM_MAIL_SENDERNAME: "Particify"
      SYSTEM_MAIL_SENDERADDRESS: "particify@example.com"
      SYSTEM_FORMATTING_SERVICE_HOST_URL: "http://arsnova-formatting-service:3000"
      SECURITY_JWT_SECRET: "ChangeMeParticifyJwtSecretKey32CharsMin2026!"
      SECURITY_JWT_SERVER_ID: "arsnova.backend.v3:localhost"
      SECURITY_AUTHENTICATIONPROVIDERS_GUEST_ENABLED: "true"
      SECURITY_AUTHENTICATIONPROVIDERS_GUEST_ALLOWEDROLES: "participant"
      SECURITY_AUTHENTICATIONPROVIDERS_REGISTERED_TITLE: "Particify"
      SECURITY_AUTHENTICATIONPROVIDERS_REGISTERED_ALLOWEDEMAILDOMAINS: "*"
    networks:
      - particify_internal

  arsnova-http-gateway:
    image: particify/arsnova-server-gateway:3.14.20261123
    container_name: njorddeploy-particify-http-gateway
    restart: unless-stopped
    depends_on:
      particify-rabbitmq:
        condition: service_healthy
      arsnova-auth-service:
        condition: service_started
    environment:
      SERVER_PORT: "8080"
      ROUTING_ENDPOINTS_CORE: "http://arsnova-backend-core:8080"
      ROUTING_ENDPOINTS_WS_GATEWAY: "http://arsnova-ws-gateway:8080"
      ROUTING_ENDPOINTS_COMMENT_SERVICE: "http://arsnova-comment-service:8080"
      ROUTING_ENDPOINTS_ROOMACCESS_SERVICE: "http://arsnova-auth-service:8080"
      ROUTING_ENDPOINTS_FORMATTING_SERVICE: "http://arsnova-formatting-service:3000"
      HTTP_CLIENT_AUTH_SERVICE: "http://arsnova-auth-service:8080"
      HTTP_CLIENT_CORE: "http://arsnova-backend-core:8080"
      HTTP_CLIENT_WS_GATEWAY: "http://arsnova-ws-gateway:8080"
      HTTP_CLIENT_COMMENT_SERVICE: "http://arsnova-comment-service:8080"
      SECURITY_JWT_PUBLIC_SECRET: "ChangeMeParticifyJwtSecretKey32CharsMin2026!"
      SECURITY_JWT_INTERNAL_SECRET: "ChangeMeParticifyJwtSecretKey32CharsMin2026!"
      SECURITY_JWT_SERVER_ID: "arsnova.backend.v3:localhost"
    networks:
      - particify_internal

  arsnova-ws-gateway:
    image: particify/arsnova-server-websocket:3.14.20261123
    container_name: njorddeploy-particify-ws-gateway
    restart: unless-stopped
    depends_on:
      particify-rabbitmq:
        condition: service_healthy
      arsnova-auth-service:
        condition: service_started
    environment:
      SERVER_PORT: "8080"
      STOMP_RELAY_HOST: "particify-rabbitmq"
      STOMP_RELAY_USER: "guest"
      STOMP_RELAY_PASSWORD: "guest"
      HTTP_CLIENT_AUTH_SERVICE: "http://arsnova-auth-service:8080"
      SECURITY_JWT_SECRET: "ChangeMeParticifyJwtSecretKey32CharsMin2026!"
      RABBITMQ_HOST: "particify-rabbitmq"
      RABBITMQ_USERNAME: "guest"
      RABBITMQ_PASSWORD: "guest"
    networks:
      - particify_internal

  arsnova-auth-service:
    image: particify/arsnova-server-authz:3.14.20261123
    container_name: njorddeploy-particify-auth
    restart: unless-stopped
    depends_on:
      particify-postgres-auth:
        condition: service_healthy
      particify-rabbitmq:
        condition: service_healthy
    environment:
      SERVER_PORT: "8080"
      SPRING_DATASOURCE_URL: "jdbc:postgresql://particify-postgres-auth:5432/arsnovaauth"
      SPRING_DATASOURCE_USERNAME: "arsnovaauth"
      SPRING_DATASOURCE_PASSWORD: "ChangeMeParticifyDatabasePassword2026!"
      SPRING_JPA_HIBERNATE_DDL_AUTO: "validate"
      RABBITMQ_HOST: "particify-rabbitmq"
      RABBITMQ_USERNAME: "guest"
      RABBITMQ_PASSWORD: "guest"
      SECURITY_JWT_SECRET: "ChangeMeParticifyJwtSecretKey32CharsMin2026!"
      SECURITY_JWT_SERVER_ID: "arsnova.backend.v3:localhost"
    networks:
      - particify_internal

  arsnova-comment-service:
    image: particify/arsnova-server-comments:3.14.20261123
    container_name: njorddeploy-particify-comment
    restart: unless-stopped
    depends_on:
      particify-postgres-comment:
        condition: service_healthy
      particify-rabbitmq:
        condition: service_healthy
    environment:
      SERVER_PORT: "8080"
      SPRING_DATASOURCE_URL: "jdbc:postgresql://particify-postgres-comment:5432/arsnovacomment"
      SPRING_DATASOURCE_USERNAME: "arsnovacomment"
      SPRING_DATASOURCE_PASSWORD: "ChangeMeParticifyDatabasePassword2026!"
      SPRING_JPA_HIBERNATE_DDL_AUTO: "update"
      SPRING_RABBITMQ_HOST: "particify-rabbitmq"
      SPRING_RABBITMQ_USERNAME: "guest"
      SPRING_RABBITMQ_PASSWORD: "guest"
      SECURITY_JWT_SECRET: "ChangeMeParticifyJwtSecretKey32CharsMin2026!"
    networks:
      - particify_internal

  arsnova-formatting-service:
    image: particify/arsnova-server-formatting:3.14.20261123
    container_name: njorddeploy-particify-formatting
    restart: unless-stopped
    environment:
      SERVER_PORT: "3000"
    networks:
      - particify_internal

  particify-couchdb:
    image: particify/couchdb:3.5
    container_name: njorddeploy-particify-couchdb
    restart: unless-stopped
    environment:
      COUCHDB_USER: "arsnova"
      COUCHDB_PASSWORD: "ChangeMeParticifyDatabasePassword2026!"
    volumes:
      - "./data/particify/couchdb:/opt/couchdb/data"
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:5984/_up || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 10
    networks:
      - particify_internal

  particify-postgres-auth:
    image: postgres:17-alpine
    container_name: njorddeploy-particify-postgres-auth
    restart: unless-stopped
    environment:
      POSTGRES_DB: "arsnovaauth"
      POSTGRES_USER: "arsnovaauth"
      POSTGRES_PASSWORD: "ChangeMeParticifyDatabasePassword2026!"
    volumes:
      - "./data/particify/postgres-auth:/var/lib/postgresql/data"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U arsnovaauth -d arsnovaauth"]
      interval: 10s
      timeout: 5s
      retries: 10
    networks:
      - particify_internal

  particify-postgres-comment:
    image: postgres:17-alpine
    container_name: njorddeploy-particify-postgres-comment
    restart: unless-stopped
    environment:
      POSTGRES_DB: "arsnovacomment"
      POSTGRES_USER: "arsnovacomment"
      POSTGRES_PASSWORD: "ChangeMeParticifyDatabasePassword2026!"
    volumes:
      - "./data/particify/postgres-comment:/var/lib/postgresql/data"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U arsnovacomment -d arsnovacomment"]
      interval: 10s
      timeout: 5s
      retries: 10
    networks:
      - particify_internal

  particify-rabbitmq:
    image: particify/rabbitmq-stomp:4.4-alpine
    container_name: njorddeploy-particify-rabbitmq
    restart: unless-stopped
    environment:
      RABBITMQ_NODENAME: "rabbit@localhost"
    volumes:
      - "./data/particify/rabbitmq:/var/lib/rabbitmq"
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "-q", "ping"]
      interval: 10s
      timeout: 5s
      retries: 12
    networks:
      - particify_internal

networks:
  njorddeploy_net:
  particify_internal:
    name: particify_internal
```

Start the service:
```bash
docker compose up -d
```

---

## ⚙️ Configuration & Environment Variables

| Variable | Default Value | Description |
|---|---|---|
| `PARTICIFY_WEB_PORT` | `8123` | External host port for accessing the Particify audience response web interface. |
| `PARTICIFY_HOSTNAME` | `localhost` | Public hostname or domain for Particify (used for Nginx routing and JWT server ID, e.g. particify.example.com). |
| `PARTICIFY_ROOT_URL` | `http://localhost:8123` | Public base URL of Particify including scheme (e.g. https://particify.example.com), used for activation and invitation links. |
| `PARTICIFY_GUEST_ENABLED` | `true` | Enable anonymous guest access (true recommended with 'participant' role so audiences can vote without login). |
| `PARTICIFY_GUEST_ALLOWED_ROLES` | `participant` | Roles permitted for guest accounts: 'participant' (Menti.com style: audience votes without login, moderators must register) or 'moderator,participant'. |
| `PARTICIFY_AUTH_TITLE` | `Particify` | Display title for the built-in account login provider. |
| `PARTICIFY_ALLOWED_EMAIL_DOMAINS` | `*` | Comma-separated list of email domains allowed to register accounts (e.g. 'example.com' or '*' for all). |
| `PARTICIFY_JWT_SECRET` | `ChangeMeParticifyJwtSecretKey32CharsMin2026!` | Strong secret key (minimum 32 characters) used to sign authentication JWT tokens across Particify microservices. Change before production use. |
| `PARTICIFY_DB_PASSWORD` | `ChangeMeParticifyDatabasePassword2026!` | Password securing Particify internal CouchDB and PostgreSQL (auth & comments) databases. |
| `PARTICIFY_CSP_FRAME_ANCESTORS` | *None* | Optional Content-Security-Policy frame-ancestors origins allowed to embed Particify (leave empty to disallow framing). |
| `PARTICIFY_MAIL_HOST` | *None* | Optional SMTP server hostname for sending account registration and password reset emails. |
| `PARTICIFY_MAIL_PORT` | `25` | SMTP server port (e.g. 25, 465, or 587). |
| `PARTICIFY_MAIL_IMPLICITTLS` | `false` | Set to true for implicit TLS (port 465) or false for STARTTLS/plain. |
| `PARTICIFY_MAIL_USERNAME` | *None* | Optional SMTP authentication username. |
| `PARTICIFY_MAIL_PASSWORD` | *None* | Optional SMTP authentication password. |
| `PARTICIFY_MAIL_SENDERNAME` | `Particify` | Display name shown on outgoing Particify emails. |
| `PARTICIFY_MAIL_SENDERADDRESS` | `particify@example.com` | Sender email address for outgoing Particify emails. |

---

## 🔑 First-Run Onboarding Guide

Open the Particify web UI to create a room as a guest or register an account. Configure optional SMTP settings to enable email-based account verification.

- **Upstream Setup Guide:** [https://particify.de/en/manual/](https://particify.de/en/manual/)

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

Deploy **Particify** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
