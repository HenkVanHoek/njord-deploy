# tests/test_auth_utils.py

# noinspection PyUnresolvedReferences
from passlib.hash import argon2

from src.utils.auth_utils import generate_basic_auth_hash


def test_generate_basic_auth_hash_creates_valid_argon2_output():
    """Test that the function generates a securely hashed string in the

    'username:hash' format using the Argon2ID algorithm.
    """
    username = "testuser"
    password = "SecurePassword123"

    # Call the function under test
    result_string = generate_basic_auth_hash(username, password)

    # 1. Assert the format: should be 'username:hash'
    assert result_string.startswith(f"{username}:")
    assert ":" in result_string

    # Unpack the result: (username, hash_string)
    # The new directive requires unpacking
    # The split result is a list [username, hash_string]
    parts = result_string.split(":", 1)
    unpacked_username, hash_string = parts  # Unpacking-First Mandate

    # 2. Assert the hash itself is a valid Argon2 hash
    # (i.e., starts with the standard Argon2ID prefix)
    assert hash_string.startswith("$argon2id$")

    # 3. Assert the hash is verifiable (the core security test)
    # Use the argon2 verification method from passlib
    assert argon2.verify(password, hash_string)


def test_generate_basic_auth_hash_is_unique_on_each_call():
    """Test that calling the function twice with the same input yields two

    DIFFERENT hashes, verifying that a unique salt is generated.
    """
    username = "testuser"
    password = "SecurePassword123"

    hash_one = generate_basic_auth_hash(username, password)
    hash_two = generate_basic_auth_hash(username, password)

    # The result strings must be different because Argon2 uses a random salt
    assert hash_one != hash_two

    # But both must still verify against the original password
    parts_one = hash_one.split(":", 1)
    parts_two = hash_two.split(":", 1)

    # Unpacking-First Mandate for the core assertion
    _, hash_one_string = parts_one
    _, hash_two_string = parts_two

    # Verify both hashes
    assert argon2.verify(password, hash_one_string)
    assert argon2.verify(password, hash_two_string)
