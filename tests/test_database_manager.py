# tests/test_database_manager.py

import tempfile
from pathlib import Path

import pytest

from managers.database_manager import DatabaseManager


@pytest.fixture
def temp_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = Path(tmpdir) / "test_saas.db"
        db = DatabaseManager(db_file)
        yield db


def test_user_lifecycle(temp_db):
    user = temp_db.create_user(
        username="alice",
        password_hash="pbkdf2:sha256:1000$mockhash",
        email="alice@example.com",
        role="user",
        plan="free",
        api_key="njord_sec_test_alice",
    )
    assert user["id"] is not None
    assert user["username"] == "alice"
    assert user["plan"] == "free"
    assert user["api_key"] == "njord_sec_test_alice"

    # Fetch by username
    by_name = temp_db.get_user_by_username("alice")
    assert by_name["id"] == user["id"]

    # Fetch by email
    by_email = temp_db.get_user_by_email("alice@example.com")
    assert by_email["id"] == user["id"]

    # Fetch by API key
    by_key = temp_db.get_user_by_api_key("njord_sec_test_alice")
    assert by_key["id"] == user["id"]

    # Update plan
    temp_db.update_user_plan(
        user["id"],
        plan="pro",
        stripe_customer_id="cus_123",
        stripe_subscription_id="sub_123",
    )
    updated = temp_db.get_user_by_id(user["id"])
    assert updated["plan"] == "pro"
    assert updated["stripe_customer_id"] == "cus_123"


def test_server_management(temp_db):
    user = temp_db.create_user("bob", "mockhash", email="bob@example.com")
    server1 = temp_db.add_server(
        user["id"],
        name="Home Raspberry Pi 5",
        ip="192.168.1.10",
        agent_token="njord_agt_bob_pi",
    )
    assert server1["name"] == "Home Raspberry Pi 5"
    assert server1["status"] == "pending"

    # Count servers
    count = temp_db.count_servers_for_user(user["id"])
    assert count == 1

    # Heartbeat
    temp_db.update_server_heartbeat(
        "njord_agt_bob_pi", ip="1.2.3.4", os_info="Debian 12"
    )
    server_updated = temp_db.get_server_by_agent_token("njord_agt_bob_pi")
    assert server_updated["status"] == "online"
    assert server_updated["ip"] == "1.2.3.4"

    # Delete
    deleted = temp_db.delete_server(server1["id"], user["id"])
    assert deleted is True
    assert temp_db.count_servers_for_user(user["id"]) == 0


def test_user_api_key_and_counts(temp_db):
    assert temp_db.get_user_by_api_key("") is None
    assert temp_db.get_user_by_api_key(None) is None
    assert temp_db.count_total_users() == 0

    user = temp_db.create_user("charlie", "hash123", email="charlie@test.com")
    assert temp_db.count_total_users() == 1

    temp_db.update_user_api_key(user["id"], "new_api_key_456")
    updated_user = temp_db.get_user_by_api_key("new_api_key_456")
    assert updated_user is not None
    assert updated_user["id"] == user["id"]

    temp_db.update_user_plan(user["id"], "pro", stripe_customer_id="cus_charlie")
    user_by_stripe = temp_db.get_user_by_stripe_customer_id("cus_charlie")
    assert user_by_stripe is not None
    assert user_by_stripe["id"] == user["id"]


def test_server_scoping_and_list(temp_db):
    alice = temp_db.create_user("alice_scope", "hash1")
    bob = temp_db.create_user("bob_scope", "hash2")

    server_alice = temp_db.add_server(alice["id"], "Alice Server")
    server_bob = temp_db.add_server(bob["id"], "Bob Server")

    # Scoped retrieval: Alice cannot see Bob's server
    assert temp_db.get_server_by_id(server_bob["id"], user_id=alice["id"]) is None
    assert temp_db.get_server_by_id(server_alice["id"], user_id=alice["id"]) is not None

    # Global retrieval without user_id
    server_fetch = temp_db.get_server_by_id(server_alice["id"])
    assert server_fetch is not None
    assert server_fetch["name"] == "Alice Server"

    # List servers for user
    alice_servers = temp_db.list_servers_for_user(alice["id"])
    assert len(alice_servers) == 1
    first_srv, *_ = alice_servers
    assert first_srv["id"] == server_alice["id"]


def test_deployment_lifecycle(temp_db):
    user = temp_db.create_user("deploy_user", "hash")
    server = temp_db.add_server(user["id"], "Target Host")

    dep_id = temp_db.create_deployment(
        user["id"], "adguard-home", server_id=server["id"]
    )
    assert dep_id is not None

    temp_db.update_deployment_status(dep_id, "success", logs="Deployment succeeded")

    deployments = temp_db.list_deployments_for_user(user["id"])
    assert len(deployments) == 1
    dep, *_ = deployments
    assert dep["id"] == dep_id
    assert dep["status"] == "success"
    assert dep["logs"] == "Deployment succeeded"
    assert dep["server_name"] == "Target Host"


def test_transaction_rollback_on_error(temp_db):
    with pytest.raises(RuntimeError):
        with temp_db.get_connection() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                ("rollback_user", "hash"),
            )
            raise RuntimeError("Forced transaction failure")

    assert temp_db.get_user_by_username("rollback_user") is None


def test_database_manager_singleton(tmp_path):
    db_file = tmp_path / "singleton_test.db"
    instance1 = DatabaseManager.get_instance(db_file)
    instance2 = DatabaseManager.get_instance()
    assert instance1 is instance2


def test_database_manager_default_path(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "managers.database_manager.get_app_data_dir", lambda: tmp_path / "default_dir"
    )
    db = DatabaseManager()
    assert db.db_path == tmp_path / "default_dir" / "njord_saas.db"
    assert db.db_path.exists()
