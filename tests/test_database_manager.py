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
