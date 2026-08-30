# src/managers/agent_manager.py

"""
NjordDeploy Remote Node Agent Manager
-------------------------------------
Generates zero-friction installation scripts and handles heartbeats,
system telemetry, and orchestration commands for remote servers & Raspberry Pis.
"""

import json
import logging
import secrets
from typing import Any, Dict, Optional, Tuple

from managers.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class AgentManager:
    """
    Manages node agent tokens, dynamic bash installation scripts,
    and inbound heartbeat telemetry from remote Raspberry Pis and servers.
    """

    def __init__(self, db: Optional[DatabaseManager] = None):
        """Initializes the AgentManager with database instance."""
        self.db = db or DatabaseManager.get_instance()

    def generate_agent_token(self) -> str:
        """Generates a secure, cryptographically random Agent authentication token."""
        return f"njord_agt_{secrets.token_hex(20)}"

    def register_node(
        self,
        user_id: int,
        server_name: str,
        connection_type: str = "agent",
        ip: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Registers a server and issues an Agent connection token."""
        token = self.generate_agent_token()
        server = self.db.add_server(
            user_id=user_id,
            name=server_name,
            ip=ip,
            connection_type=connection_type,
            agent_token=token,
        )
        return server

    def generate_install_command(self, agent_token: str, hub_url: str) -> str:
        """Generates the one-liner curl command to install the agent."""
        clean_url = hub_url.rstrip("/")
        return (
            f"curl -sSL {clean_url}/install-agent | "
            f"sudo bash -s -- --token {agent_token} --hub {clean_url}"
        )

    def generate_install_script(
        self, hub_url: str, agent_token: Optional[str] = None
    ) -> str:
        """
        Generates the self-contained bash agent installation script.
        Installs lightweight cron/systemd heartbeat and telemetry probe.
        """
        clean_hub = hub_url.rstrip("/")
        default_token = agent_token or ""

        script = f"""#!/usr/bin/env bash
# ==============================================================================
# NjordDeploy Node Agent Installer
# ==============================================================================
set -e

HUB_URL="{clean_hub}"
AGENT_TOKEN="{default_token}"

# Parse optional arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --hub) HUB_URL="$2"; shift ;;
        --token) AGENT_TOKEN="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

if [ -z "$AGENT_TOKEN" ]; then
    echo "❌ Error: Missing required --token parameter."
    exit 1
fi

echo "🚀 Installing NjordDeploy Node Agent connecting to $HUB_URL..."

# Create agent working directory
AGENT_DIR="/opt/njorddeploy-agent"
mkdir -p "$AGENT_DIR"
cat << 'EOF' > "$AGENT_DIR/agent.sh"
#!/usr/bin/env bash
# NjordDeploy Heartbeat Probe
HUB_URL="__HUB_ENDPOINT__"
AUTH_KEY="__AUTH_KEY_VAL__"

# Gather system telemetry
HOSTNAME=$(hostname)
OS_INFO=$(grep -E '^(PRETTY_NAME)=' /etc/os-release | cut -d= -f2 | tr -d '"')
MEM_USAGE=$(free -m | awk '/Mem:/ {{printf "%.1f/%.1f GB", $3/1024, $2/1024}}')
CONTAINERS=$(docker ps -q 2>/dev/null | wc -l || echo "0")

JSON_PAYLOAD=$(cat << JSON
{{
  "hostname": "$HOSTNAME",
  "os_info": "$OS_INFO",
  "memory": "$MEM_USAGE",
  "active_containers": $CONTAINERS,
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}}
JSON
)

# Send heartbeat to Control Hub
curl -s -X POST "$HUB_URL/api/agent/heartbeat" \\
     -H "Content-Type: application/json" \\
     -H "X-Njord-Agent-Token: $AUTH_KEY" \\
     -d "$JSON_PAYLOAD" > /dev/null 2>&1 || true
EOF

sed -i "s|__HUB_ENDPOINT__|$HUB_URL|g" "$AGENT_DIR/agent.sh"
sed -i "s|__AUTH_KEY_VAL__|$AGENT_TOKEN|g" "$AGENT_DIR/agent.sh"
chmod +x "$AGENT_DIR/agent.sh"

# Create systemd service & timer for periodic 30-second heartbeats
cat << EOF > /etc/systemd/system/njord-agent.service
[Unit]
Description=NjordDeploy Remote Node Agent
After=network.target

[Service]
Type=oneshot
ExecStart=$AGENT_DIR/agent.sh
EOF

cat << EOF > /etc/systemd/system/njord-agent.timer
[Unit]
Description=NjordDeploy Remote Node Heartbeat Timer

[Timer]
OnBootSec=10sec
OnUnitActiveSec=30sec
AccuracySec=1sec

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now njord-agent.timer
systemctl start njord-agent.service

echo "✅ NjordDeploy Agent installed and connected successfully!"
echo "📡 Node status is now live in your NjordDeploy dashboard."
"""
        return script

    def process_heartbeat(
        self, agent_token: str, telemetry: Dict[str, Any], client_ip: str
    ) -> Tuple[bool, str]:
        """Processes an incoming heartbeat from a node."""
        server = self.db.get_server_by_agent_token(agent_token)
        if not server:
            return False, "Invalid or unrecognized Agent token."

        os_info = telemetry.get("os_info") or telemetry.get("hostname")
        self.db.update_server_heartbeat(
            agent_token=agent_token,
            ip=client_ip,
            os_info=(
                json.dumps(telemetry) if isinstance(telemetry, dict) else str(os_info)
            ),
        )
        return True, "Heartbeat acknowledged."
