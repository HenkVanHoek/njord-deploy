# src/managers/database_manager.py

"""
NjordDeploy Multi-Tenant Database Manager
-----------------------------------------
Thread-safe SQLite database manager for Multi-Tenant users, servers/nodes,
deployments, and Stripe subscriptions.
"""

import contextlib
import logging
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.resource_utils import get_app_data_dir

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages SQLite database connections, schema migrations, and CRUD operations
    for NjordDeploy multi-tenancy and SaaS features.
    """

    _instance: Optional["DatabaseManager"] = None
    _lock = threading.Lock()

    def __init__(self, db_path: Optional[Path] = None):
        """Initializes the database manager with persistent storage."""
        if db_path is None:
            data_dir = get_app_data_dir()
            db_path = data_dir / "njord_saas.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()

    @classmethod
    def get_instance(cls, db_path: Optional[Path] = None) -> "DatabaseManager":
        """Singleton accessor for the global DatabaseManager instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(db_path)
            return cls._instance

    @contextlib.contextmanager
    def get_connection(self):
        """Provides a thread-local SQLite connection context with WAL enabled."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=30.0,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initializes tables and indexes if they do not exist."""
        with self.get_connection() as conn:
            # 1. Users Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    plan TEXT NOT NULL DEFAULT 'free',
                    stripe_customer_id TEXT,
                    stripe_subscription_id TEXT,
                    api_key TEXT UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            # 2. Servers Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS servers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    ip TEXT,
                    ssh_user TEXT,
                    connection_type TEXT DEFAULT 'agent',
                    agent_token TEXT UNIQUE,
                    status TEXT DEFAULT 'pending',
                    os_info TEXT,
                    last_seen TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                );
                """
            )

            # 3. Deployments Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS deployments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    server_id INTEGER,
                    component_name TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    logs TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    FOREIGN KEY (server_id) REFERENCES servers (id) ON DELETE SET NULL
                );
                """
            )

            # 4. Subscriptions History Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    stripe_customer_id TEXT,
                    stripe_subscription_id TEXT UNIQUE,
                    plan TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_period_end INTEGER,
                    cancel_at_period_end INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                );
                """
            )

            # Indexes
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_servers_user_id ON servers(user_id);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_servers_agent_token "
                "ON servers(agent_token);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_deployments_user_id "
                "ON deployments(user_id);"
            )

    # --------------------------------------------------------------------------
    # User Management
    # --------------------------------------------------------------------------

    def create_user(
        self,
        username: str,
        password_hash: str,
        email: Optional[str] = None,
        role: str = "user",
        plan: str = "free",
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Creates a new user and returns their profile dictionary."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (username, email, password_hash, role, plan, api_key)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    username.strip(),
                    email.strip() if email else None,
                    password_hash,
                    role,
                    plan,
                    api_key,
                ),
            )
            user_id = cursor.lastrowid
            row = conn.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            return dict(row)

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves a user dictionary by their integer ID."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Retrieves a user by their unique username."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ?", (username.strip(),)
            ).fetchone()
            return dict(row) if row else None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Retrieves a user by their unique email."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE email = ?", (email.strip(),)
            ).fetchone()
            return dict(row) if row else None

    def get_user_by_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Retrieves a user by their unique API key."""
        if not api_key:
            return None
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE api_key = ?", (api_key.strip(),)
            ).fetchone()
            return dict(row) if row else None

    def get_user_by_stripe_customer_id(
        self, customer_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieves a user by their Stripe customer ID."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE stripe_customer_id = ?", (customer_id,)
            ).fetchone()
            return dict(row) if row else None

    def update_user_plan(
        self,
        user_id: int,
        plan: str,
        stripe_customer_id: Optional[str] = None,
        stripe_subscription_id: Optional[str] = None,
    ) -> bool:
        """Updates a user's subscription plan and Stripe IDs."""
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE users
                SET plan = ?,
                    stripe_customer_id = COALESCE(?, stripe_customer_id),
                    stripe_subscription_id = COALESCE(?, stripe_subscription_id),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (plan, stripe_customer_id, stripe_subscription_id, user_id),
            )
            return True

    def update_user_api_key(self, user_id: int, new_api_key: str) -> bool:
        """Updates or regenerates a user's API token."""
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE users SET api_key = ?, updated_at = CURRENT_TIMESTAMP "
                "WHERE id = ?",
                (new_api_key, user_id),
            )
            return True

    def count_total_users(self) -> int:
        """Returns the total number of registered users."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM users;").fetchone()
            return row["count"] if row else 0

    # --------------------------------------------------------------------------
    # Server / Node Management
    # --------------------------------------------------------------------------

    def add_server(
        self,
        user_id: int,
        name: str,
        ip: Optional[str] = None,
        ssh_user: Optional[str] = None,
        connection_type: str = "agent",
        agent_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Registers a new server node for a user."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO servers
                (user_id, name, ip, ssh_user, connection_type, agent_token, status)
                VALUES (?, ?, ?, ?, ?, ?, 'pending')
                """,
                (user_id, name.strip(), ip, ssh_user, connection_type, agent_token),
            )
            server_id = cursor.lastrowid
            row = conn.execute(
                "SELECT * FROM servers WHERE id = ?", (server_id,)
            ).fetchone()
            return dict(row)

    def get_server_by_id(
        self, server_id: int, user_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Retrieves a server by ID, optionally scoped to a user."""
        with self.get_connection() as conn:
            if user_id is not None:
                row = conn.execute(
                    "SELECT * FROM servers WHERE id = ? AND user_id = ?",
                    (server_id, user_id),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM servers WHERE id = ?", (server_id,)
                ).fetchone()
            return dict(row) if row else None

    def get_server_by_agent_token(self, agent_token: str) -> Optional[Dict[str, Any]]:
        """Retrieves a server by its unique agent token."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM servers WHERE agent_token = ?", (agent_token,)
            ).fetchone()
            return dict(row) if row else None

    def list_servers_for_user(self, user_id: int) -> List[Dict[str, Any]]:
        """Lists all registered servers for a given user."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM servers WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def count_servers_for_user(self, user_id: int) -> int:
        """Returns the total number of servers owned by a user."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS count FROM servers WHERE user_id = ?", (user_id,)
            ).fetchone()
            return row["count"] if row else 0

    def update_server_heartbeat(
        self, agent_token: str, ip: Optional[str] = None, os_info: Optional[str] = None
    ) -> bool:
        """Updates last_seen timestamp and online status when agent checks in."""
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE servers
                SET status = 'online',
                    last_seen = CURRENT_TIMESTAMP,
                    ip = COALESCE(?, ip),
                    os_info = COALESCE(?, os_info)
                WHERE agent_token = ?
                """,
                (ip, os_info, agent_token),
            )
            return True

    def delete_server(self, server_id: int, user_id: int) -> bool:
        """Deletes a server belonging to a user."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM servers WHERE id = ? AND user_id = ?", (server_id, user_id)
            )
            return cursor.rowcount > 0

    # --------------------------------------------------------------------------
    # Deployment Logs & History
    # --------------------------------------------------------------------------

    def create_deployment(
        self, user_id: int, component_name: str, server_id: Optional[int] = None
    ) -> int:
        """Records a new deployment attempt."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO deployments (user_id, server_id, component_name, status)
                VALUES (?, ?, ?, 'running')
                """,
                (user_id, server_id, component_name),
            )
            return cursor.lastrowid

    def update_deployment_status(
        self, deployment_id: int, status: str, logs: Optional[str] = None
    ) -> bool:
        """Updates status and log outputs of a deployment."""
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE deployments SET status = ?, logs = COALESCE(?, logs) "
                "WHERE id = ?",
                (status, logs, deployment_id),
            )
            return True

    def list_deployments_for_user(
        self, user_id: int, limit: int = 25
    ) -> List[Dict[str, Any]]:
        """Lists recent deployments for a given user."""
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT d.*, s.name as server_name
                FROM deployments d
                LEFT JOIN servers s ON d.server_id = s.id
                WHERE d.user_id = ?
                ORDER BY d.created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]
