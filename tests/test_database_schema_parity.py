# tests/test_database_schema_parity.py

"""
Automated Database Schema Parity & Drift Prevention Test Suite.
---------------------------------------------------------------
Inspects SQLite database tables, column names, data types, nullability,
default values, foreign keys, and indexes against the canonical Model
Schema Contracts. Eliminates 'no such column' / UndefinedColumn errors
and DDL migration drift across production environments.
"""

import sqlite3
from pathlib import Path
from typing import Any, Dict, List

import pytest

from managers.customer_sandbox_manager import CustomerSandboxManager
from managers.database_manager import DatabaseManager

# ==============================================================================
# Canonical Model Schema Contracts (Single Source of Truth)
# ==============================================================================

CANONICAL_SAAS_SCHEMA: Dict[str, Dict[str, Any]] = {
    "users": {
        "columns": {
            "id": {"type": "INTEGER", "notnull": 0, "pk": 1},
            "username": {"type": "TEXT", "notnull": 1, "pk": 0},
            "email": {"type": "TEXT", "notnull": 0, "pk": 0},
            "password_hash": {"type": "TEXT", "notnull": 1, "pk": 0},
            "role": {"type": "TEXT", "notnull": 1, "pk": 0, "dflt_value": "'user'"},
            "plan": {"type": "TEXT", "notnull": 1, "pk": 0, "dflt_value": "'free'"},
            "stripe_customer_id": {"type": "TEXT", "notnull": 0, "pk": 0},
            "stripe_subscription_id": {"type": "TEXT", "notnull": 0, "pk": 0},
            "api_key": {"type": "TEXT", "notnull": 0, "pk": 0},
            "created_at": {
                "type": "TIMESTAMP",
                "notnull": 0,
                "pk": 0,
                "dflt_value": "CURRENT_TIMESTAMP",
            },
            "updated_at": {
                "type": "TIMESTAMP",
                "notnull": 0,
                "pk": 0,
                "dflt_value": "CURRENT_TIMESTAMP",
            },
        },
        "indexes": ["idx_users_username", "idx_users_api_key"],
        "foreign_keys": [],
    },
    "servers": {
        "columns": {
            "id": {"type": "INTEGER", "notnull": 0, "pk": 1},
            "user_id": {"type": "INTEGER", "notnull": 1, "pk": 0},
            "name": {"type": "TEXT", "notnull": 1, "pk": 0},
            "ip": {"type": "TEXT", "notnull": 0, "pk": 0},
            "ssh_user": {"type": "TEXT", "notnull": 0, "pk": 0},
            "connection_type": {
                "type": "TEXT",
                "notnull": 0,
                "pk": 0,
                "dflt_value": "'agent'",
            },
            "agent_token": {"type": "TEXT", "notnull": 0, "pk": 0},
            "status": {
                "type": "TEXT",
                "notnull": 0,
                "pk": 0,
                "dflt_value": "'pending'",
            },
            "os_info": {"type": "TEXT", "notnull": 0, "pk": 0},
            "last_seen": {"type": "TIMESTAMP", "notnull": 0, "pk": 0},
            "created_at": {
                "type": "TIMESTAMP",
                "notnull": 0,
                "pk": 0,
                "dflt_value": "CURRENT_TIMESTAMP",
            },
        },
        "indexes": ["idx_servers_user_id", "idx_servers_agent_token"],
        "foreign_keys": [
            {
                "from": "user_id",
                "table": "users",
                "to": "id",
                "on_delete": "CASCADE",
            }
        ],
    },
    "deployments": {
        "columns": {
            "id": {"type": "INTEGER", "notnull": 0, "pk": 1},
            "user_id": {"type": "INTEGER", "notnull": 1, "pk": 0},
            "server_id": {"type": "INTEGER", "notnull": 0, "pk": 0},
            "component_name": {"type": "TEXT", "notnull": 1, "pk": 0},
            "status": {
                "type": "TEXT",
                "notnull": 0,
                "pk": 0,
                "dflt_value": "'pending'",
            },
            "logs": {"type": "TEXT", "notnull": 0, "pk": 0},
            "created_at": {
                "type": "TIMESTAMP",
                "notnull": 0,
                "pk": 0,
                "dflt_value": "CURRENT_TIMESTAMP",
            },
        },
        "indexes": ["idx_deployments_user_id"],
        "foreign_keys": [
            {
                "from": "user_id",
                "table": "users",
                "to": "id",
                "on_delete": "CASCADE",
            },
            {
                "from": "server_id",
                "table": "servers",
                "to": "id",
                "on_delete": "SET NULL",
            },
        ],
    },
    "subscriptions": {
        "columns": {
            "id": {"type": "INTEGER", "notnull": 0, "pk": 1},
            "user_id": {"type": "INTEGER", "notnull": 1, "pk": 0},
            "stripe_customer_id": {"type": "TEXT", "notnull": 0, "pk": 0},
            "stripe_subscription_id": {"type": "TEXT", "notnull": 0, "pk": 0},
            "plan": {"type": "TEXT", "notnull": 1, "pk": 0},
            "status": {"type": "TEXT", "notnull": 1, "pk": 0},
            "current_period_end": {"type": "INTEGER", "notnull": 0, "pk": 0},
            "cancel_at_period_end": {
                "type": "INTEGER",
                "notnull": 0,
                "pk": 0,
                "dflt_value": "0",
            },
            "created_at": {
                "type": "TIMESTAMP",
                "notnull": 0,
                "pk": 0,
                "dflt_value": "CURRENT_TIMESTAMP",
            },
        },
        "indexes": [],
        "foreign_keys": [
            {
                "from": "user_id",
                "table": "users",
                "to": "id",
                "on_delete": "CASCADE",
            }
        ],
    },
}

CANONICAL_SANDBOX_SCHEMA: Dict[str, Dict[str, Any]] = {
    "sandboxes": {
        "columns": {
            "id": {"type": "INTEGER", "notnull": 0, "pk": 1},
            "client_id": {"type": "TEXT", "notnull": 1, "pk": 0},
            "component_id": {"type": "TEXT", "notnull": 1, "pk": 0},
            "version": {"type": "TEXT", "notnull": 1, "pk": 0},
            "vmid": {"type": "INTEGER", "notnull": 1, "pk": 0},
            "ip_address": {"type": "TEXT", "notnull": 0, "pk": 0},
            "access_url": {"type": "TEXT", "notnull": 0, "pk": 0},
            "status": {"type": "TEXT", "notnull": 1, "pk": 0},
            "created_at": {"type": "TIMESTAMP", "notnull": 1, "pk": 0},
            "expires_at": {"type": "TIMESTAMP", "notnull": 1, "pk": 0},
            "uat_signed_off": {
                "type": "INTEGER",
                "notnull": 0,
                "pk": 0,
                "dflt_value": "0",
            },
            "uat_signoff_date": {"type": "TIMESTAMP", "notnull": 0, "pk": 0},
            "uat_notes": {"type": "TEXT", "notnull": 0, "pk": 0},
        },
        "indexes": [],
        "foreign_keys": [],
    }
}


# ==============================================================================
# Schema Inspection Helper Functions (SQLite PRAGMA reflection)
# ==============================================================================


def inspect_table_columns(
    conn: sqlite3.Connection, table_name: str
) -> Dict[str, Dict[str, Any]]:
    """Inspects table columns using PRAGMA table_info."""
    cursor = conn.execute(f"PRAGMA table_info({table_name});")
    rows = cursor.fetchall()
    columns = {}
    for row in rows:
        col_name = row["name"]
        columns[col_name] = {
            "type": str(row["type"]).upper(),
            "notnull": row["notnull"],
            "pk": row["pk"],
            "dflt_value": row["dflt_value"],
        }
    return columns


def inspect_table_foreign_keys(
    conn: sqlite3.Connection, table_name: str
) -> List[Dict[str, Any]]:
    """Inspects table foreign key constraints using PRAGMA foreign_key_list."""
    cursor = conn.execute(f"PRAGMA foreign_key_list({table_name});")
    rows = cursor.fetchall()
    fks = []
    for row in rows:
        fks.append(
            {
                "from": row["from"],
                "table": row["table"],
                "to": row["to"],
                "on_delete": str(row["on_delete"]).upper(),
            }
        )
    return fks


def inspect_table_indexes(conn: sqlite3.Connection, table_name: str) -> List[str]:
    """Inspects explicit user indexes on a table using PRAGMA index_list."""
    cursor = conn.execute(f"PRAGMA index_list({table_name});")
    rows = cursor.fetchall()
    indexes = []
    for row in rows:
        name = row["name"]
        # Skip internal auto-indexes created for UNIQUE/PRIMARY KEY
        if not name.startswith("sqlite_autoindex_"):
            indexes.append(name)
    return indexes


def inspect_database_tables(conn: sqlite3.Connection) -> List[str]:
    """Retrieves all non-system table names in the SQLite database."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name;"
    )
    rows = cursor.fetchall()
    return [row["name"] for row in rows]


def verify_schema_parity(
    conn: sqlite3.Connection, canonical_schema: Dict[str, Dict[str, Any]]
) -> None:
    """
    Asserts complete 1-to-1 schema parity between a live database connection
    and a canonical Model Schema Contract.
    """
    actual_tables = inspect_database_tables(conn)
    expected_tables = sorted(canonical_schema.keys())

    assert sorted(actual_tables) == expected_tables, (
        f"Database table mismatch! Expected: {expected_tables}, "
        f"Found: {actual_tables}"
    )

    for table_name, expected_meta in canonical_schema.items():
        actual_cols = inspect_table_columns(conn, table_name)
        expected_cols = expected_meta["columns"]

        # 1. Exact Column Names
        assert set(actual_cols.keys()) == set(expected_cols.keys()), (
            f"Column parity failed on table '{table_name}'. "
            f"Missing columns: {set(expected_cols.keys()) - set(actual_cols.keys())}, "
            f"Extra columns: {set(actual_cols.keys()) - set(expected_cols.keys())}"
        )

        # 2. Column Types, Nullability, Primary Keys, and Default Values
        for col_name, exp_spec in expected_cols.items():
            act_spec = actual_cols[col_name]
            assert act_spec["type"] == exp_spec["type"], (
                f"Type mismatch on '{table_name}.{col_name}': "
                f"expected {exp_spec['type']}, got {act_spec['type']}"
            )
            assert act_spec["notnull"] == exp_spec["notnull"], (
                f"NOT NULL mismatch on '{table_name}.{col_name}': "
                f"expected {exp_spec['notnull']}, got {act_spec['notnull']}"
            )
            assert act_spec["pk"] == exp_spec["pk"], (
                f"PRIMARY KEY mismatch on '{table_name}.{col_name}': "
                f"expected {exp_spec['pk']}, got {act_spec['pk']}"
            )
            if "dflt_value" in exp_spec:
                assert act_spec["dflt_value"] == exp_spec["dflt_value"], (
                    f"Default value mismatch on '{table_name}.{col_name}': "
                    f"expected {exp_spec['dflt_value']}, got {act_spec['dflt_value']}"
                )

        # 3. Foreign Key Constraints
        expected_fks = expected_meta.get("foreign_keys", [])
        actual_fks = inspect_table_foreign_keys(conn, table_name)
        for exp_fk in expected_fks:
            matching = [
                fk
                for fk in actual_fks
                if fk["from"] == exp_fk["from"]
                and fk["table"] == exp_fk["table"]
                and fk["to"] == exp_fk["to"]
                and fk["on_delete"] == exp_fk["on_delete"]
            ]
            assert matching, (
                f"Missing or mismatched Foreign Key on '{table_name}': {exp_fk}. "
                f"Actual: {actual_fks}"
            )

        # 4. Explicit Index Parity
        expected_indexes = expected_meta.get("indexes", [])
        actual_indexes = inspect_table_indexes(conn, table_name)
        for exp_idx in expected_indexes:
            assert exp_idx in actual_indexes, (
                f"Missing expected index '{exp_idx}' on table '{table_name}'. "
                f"Actual indexes: {actual_indexes}"
            )


# ==============================================================================
# Unit Test Cases for Database Schema Parity
# ==============================================================================


def test_database_manager_schema_parity(tmp_path: Path):
    """
    Verifies that DatabaseManager initializes all tables, columns, types,
    constraints, and indexes in exact 1-to-1 parity with CANONICAL_SAAS_SCHEMA.
    """
    db_file = tmp_path / "saas_parity.db"
    db_manager = DatabaseManager(db_file)

    with db_manager.get_connection() as conn:
        verify_schema_parity(conn, CANONICAL_SAAS_SCHEMA)


def test_customer_sandbox_manager_schema_parity(tmp_path: Path):
    """
    Verifies that CustomerSandboxManager initializes all sandbox tables
    in exact 1-to-1 parity with CANONICAL_SANDBOX_SCHEMA.
    """
    db_file = tmp_path / "sandbox_parity.db"
    sandbox_mgr = CustomerSandboxManager(
        db_path=db_file, base_domain="test.njorddeploy.com"
    )

    with sandbox_mgr._get_connection() as conn:
        verify_schema_parity(conn, CANONICAL_SANDBOX_SCHEMA)


def test_schema_parity_detects_missing_column(tmp_path: Path):
    """
    Verifies that the parity validator catches a missing column (Drift Detection).
    """
    db_file = tmp_path / "drift_missing_col.db"
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    # Create table with a missing column (e.g. missing 'password_hash')
    conn.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL
        );
        """
    )

    drift_schema = {
        "users": {
            "columns": {
                "id": {"type": "INTEGER", "notnull": 0, "pk": 1},
                "username": {"type": "TEXT", "notnull": 1, "pk": 0},
                "password_hash": {"type": "TEXT", "notnull": 1, "pk": 0},
            },
            "indexes": [],
            "foreign_keys": [],
        }
    }

    with pytest.raises(AssertionError) as exc_info:
        verify_schema_parity(conn, drift_schema)
    assert "Missing columns: {'password_hash'}" in str(exc_info.value)
    conn.close()


def test_schema_parity_detects_type_mismatch(tmp_path: Path):
    """
    Verifies that the parity validator catches an unexpected column data type drift.
    """
    db_file = tmp_path / "drift_type.db"
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username INTEGER NOT NULL
        );
        """
    )

    drift_schema = {
        "users": {
            "columns": {
                "id": {"type": "INTEGER", "notnull": 0, "pk": 1},
                "username": {"type": "TEXT", "notnull": 1, "pk": 0},
            },
            "indexes": [],
            "foreign_keys": [],
        }
    }

    with pytest.raises(AssertionError) as exc_info:
        verify_schema_parity(conn, drift_schema)
    assert "Type mismatch on 'users.username'" in str(exc_info.value)
    conn.close()


def test_schema_parity_detects_foreign_key_drift(tmp_path: Path):
    """
    Verifies that missing or drifted foreign key actions (e.g. SET NULL vs CASCADE)
    are detected immediately.
    """
    db_file = tmp_path / "drift_fk.db"
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY);")
    # Foreign key has ON DELETE RESTRICT instead of CASCADE
    conn.execute(
        """
        CREATE TABLE servers (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE RESTRICT
        );
        """
    )

    drift_schema = {
        "users": {
            "columns": {"id": {"type": "INTEGER", "notnull": 0, "pk": 1}},
            "indexes": [],
            "foreign_keys": [],
        },
        "servers": {
            "columns": {
                "id": {"type": "INTEGER", "notnull": 0, "pk": 1},
                "user_id": {"type": "INTEGER", "notnull": 1, "pk": 0},
            },
            "indexes": [],
            "foreign_keys": [
                {
                    "from": "user_id",
                    "table": "users",
                    "to": "id",
                    "on_delete": "CASCADE",
                }
            ],
        },
    }

    with pytest.raises(AssertionError) as exc_info:
        verify_schema_parity(conn, drift_schema)
    assert "Missing or mismatched Foreign Key on 'servers'" in str(exc_info.value)
    conn.close()


def test_dal_query_integrity_against_schema(tmp_path: Path):
    """
    Verifies that all DatabaseManager CRUD operations execute cleanly without
    referencing non-existent columns (eliminating 'UndefinedColumn' errors).
    """
    db_file = tmp_path / "query_integrity.db"
    db = DatabaseManager(db_file)

    user = db.create_user("user_a", "hash_a", email="a@example.com")
    assert user["id"] is not None

    server = db.add_server(user["id"], "Test Server", ip="10.0.0.1")
    assert server["id"] is not None

    dep_id = db.create_deployment(user["id"], "traefik", server_id=server["id"])
    assert dep_id is not None

    assert db.update_deployment_status(dep_id, "running", logs="starting...")
    deps = db.list_deployments_for_user(user["id"])
    assert len(deps) == 1
    first_dep, *_ = deps
    assert first_dep["component_name"] == "traefik"
    assert first_dep["server_name"] == "Test Server"
