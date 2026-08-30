#!/usr/bin/env bash
# ==============================================================================
# NjordDeploy Systemd Service Manager & Installer
# ==============================================================================
# Easily install, start, stop, monitor, and uninstall NjordDeploy as a
# persistent 24/7 native Linux systemd service.
# ==============================================================================

set -euo pipefail

# Text formatting
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

SERVICE_NAME="njorddeploy.service"
SERVICE_DEST="/etc/systemd/system/${SERVICE_NAME}"
ENV_FILE="/etc/default/njorddeploy"
DATA_DIR="/var/lib/njorddeploy"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Detect Python interpreter (prefer project venv, fallback to system)
if [[ -f "${PROJECT_ROOT}/.venv/bin/python" ]]; then
    PYTHON_BIN="${PROJECT_ROOT}/.venv/bin/python"
elif [[ -f "${PROJECT_ROOT}/env/bin/python" ]]; then
    PYTHON_BIN="${PROJECT_ROOT}/env/bin/python"
else
    PYTHON_BIN="$(which python3 || echo '/usr/bin/python3')"
fi

# Detect Run User / Group
RUN_USER="${SUDO_USER:-$(id -un)}"
RUN_GROUP="$(id -gn "${RUN_USER}")"

print_header() {
    echo -e "${BLUE}${BOLD}======================================================${NC}"
    echo -e "${BLUE}${BOLD}   NjordDeploy 24/7 Systemd Service Manager           ${NC}"
    echo -e "${BLUE}${BOLD}======================================================${NC}"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo -e "${RED}[ERROR] This command requires root privileges. Please run with sudo.${NC}"
        exit 1
    fi
}

install_service() {
    check_root
    echo -e "${GREEN}[+] Installing NjordDeploy as a persistent systemd service...${NC}"

    # 1. Create persistent data directory
    echo -e "${BLUE}[*] Setting up persistent storage at ${DATA_DIR}...${NC}"
    mkdir -p "${DATA_DIR}"
    chown -R "${RUN_USER}:${RUN_GROUP}" "${DATA_DIR}"
    chmod 750 "${DATA_DIR}"

    # 2. Setup default environment file if missing
    if [[ ! -f "${ENV_FILE}" ]]; then
        echo -e "${BLUE}[*] Creating default environment file at ${ENV_FILE}...${NC}"
        cat <<ENV_EOF > "${ENV_FILE}"
# /etc/default/njorddeploy
NJORD_SERVER_MODE=true
NJORD_HOST=0.0.0.0
NJORD_PORT=5001
NJORD_DATA_DIR=${DATA_DIR}
NJORD_SSH_KEY_PATH=${DATA_DIR}/id_ed25519_njorddeploy
NJORD_SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || echo "njord-secret-key-$(date +%s)")
ENV_EOF
        chmod 600 "${ENV_FILE}"
        chown "${RUN_USER}:${RUN_GROUP}" "${ENV_FILE}"
    fi

    # 3. Generate systemd unit file
    echo -e "${BLUE}[*] Writing systemd unit file to ${SERVICE_DEST}...${NC}"
    cat <<UNIT_EOF > "${SERVICE_DEST}"
[Unit]
Description=NjordDeploy 24/7 Persistent Self-Hosted Service Daemon
Documentation=https://github.com/HenkVanHoek/njord-deploy
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${RUN_USER}
Group=${RUN_GROUP}
WorkingDirectory=${PROJECT_ROOT}
EnvironmentFile=-${ENV_FILE}
EnvironmentFile=-${PROJECT_ROOT}/.env
Environment=NJORD_SERVER_MODE=true
Environment=NJORD_HOST=0.0.0.0
Environment=NJORD_PORT=5001
Environment=NJORD_DATA_DIR=${DATA_DIR}
Environment=NJORD_SSH_KEY_PATH=${DATA_DIR}/id_ed25519_njorddeploy
ExecStart=${PYTHON_BIN} ${PROJECT_ROOT}/run_service.py
Restart=always
RestartSec=5s
TimeoutStopSec=15
LimitNOFILE=65535
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target
UNIT_EOF

    chmod 644 "${SERVICE_DEST}"

    # 4. Reload systemd daemon & enable service
    echo -e "${BLUE}[*] Reloading systemd daemon and enabling ${SERVICE_NAME}...${NC}"
    systemctl daemon-reload
    systemctl enable "${SERVICE_NAME}"
    systemctl restart "${SERVICE_NAME}"

    echo -e "${GREEN}[✓] NjordDeploy service installed and started successfully!${NC}"
    echo -e "${BLUE}[*] Verifying healthcheck endpoint...${NC}"
    sleep 2
    if curl -s -f "http://127.0.0.1:5001/api/health" > /dev/null 2>&1; then
        echo -e "${GREEN}[✓] Healthcheck OK! Service is live on http://127.0.0.1:5001${NC}"
    else
        echo -e "${YELLOW}[!] Service started. Check logs using: $0 logs${NC}"
    fi
}

uninstall_service() {
    check_root
    echo -e "${YELLOW}[!] Uninstalling NjordDeploy service...${NC}"
    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        echo -e "${BLUE}[*] Stopping active service...${NC}"
        systemctl stop "${SERVICE_NAME}" || true
    fi
    if systemctl is-enabled --quiet "${SERVICE_NAME}" 2>/dev/null; then
        echo -e "${BLUE}[*] Disabling service auto-start...${NC}"
        systemctl disable "${SERVICE_NAME}" || true
    fi
    if [[ -f "${SERVICE_DEST}" ]]; then
        echo -e "${BLUE}[*] Removing ${SERVICE_DEST}...${NC}"
        rm -f "${SERVICE_DEST}"
    fi
    systemctl daemon-reload
    echo -e "${GREEN}[✓] Service uninstalled successfully. (Data in ${DATA_DIR} preserved).${NC}"
}

service_status() {
    echo -e "${BLUE}[*] Service Status:${NC}"
    systemctl status "${SERVICE_NAME}" --no-pager || true
    echo ""
    echo -e "${BLUE}[*] Live API Healthcheck Probe:${NC}"
    if command -v curl &>/dev/null; then
        curl -s "http://127.0.0.1:5001/api/health" || echo -e "${RED}Service endpoint unreachable.${NC}"
        echo ""
    fi
}

service_logs() {
    journalctl -u "${SERVICE_NAME}" -f -n 50
}

usage() {
    print_header
    echo -e "Usage: $0 {install|uninstall|start|stop|restart|status|logs}"
    echo ""
    echo "Commands:"
    echo "  install    - Provision data directory, generate unit file, enable & start service"
    echo "  uninstall  - Stop and remove systemd service unit"
    echo "  start      - Start the NjordDeploy service"
    echo "  stop       - Stop the NjordDeploy service"
    echo "  restart    - Restart the NjordDeploy service"
    echo "  status     - Show systemctl status and API health report"
    echo "  logs       - Follow real-time systemd journal logs"
    echo ""
}

ACTION="${1:-help}"

case "${ACTION}" in
    install)
        install_service
        ;;
    uninstall)
        uninstall_service
        ;;
    start)
        check_root
        systemctl start "${SERVICE_NAME}"
        echo -e "${GREEN}[✓] Service started.${NC}"
        ;;
    stop)
        check_root
        systemctl stop "${SERVICE_NAME}"
        echo -e "${YELLOW}[✓] Service stopped.${NC}"
        ;;
    restart)
        check_root
        systemctl restart "${SERVICE_NAME}"
        echo -e "${GREEN}[✓] Service restarted.${NC}"
        ;;
    status)
        service_status
        ;;
    logs)
        service_logs
        ;;
    *)
        usage
        exit 1
        ;;
esac
