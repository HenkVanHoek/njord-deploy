# src/utils/auth_utils.py

from argon2 import PasswordHasher
from argon2.low_level import Type

# START OF INTEGRATOR FIX: Switch from problematic passlib to direct argon2-cffi.

# Initialize the PasswordHasher with standard, secure Argon2ID parameters.
# passlib's convention: memory_cost=65536, time_cost=4, parallelism=2
# argon2-cffi uses slightly different parameter names but same values.
PH = PasswordHasher(time_cost=4, memory_cost=65536, parallelism=2, type=Type.ID)


def generate_basic_auth_hash(username: str, password: str) -> str:
    """
    Generates a username:hashed_password string suitable for Traefik and
    other basic authentication systems using the Argon2ID algorithm.

    The password hash is generated using the direct argon2-cffi
    implementation to bypass passlib backend loading issues.

    Args:
        username: The user's plaintext username.
        password: The user's plaintext password.

    Returns:
        A string in the format "username:hash" where hash is an Argon2ID hash.
    """
    # 1. Generate the secure hash.
    # We use the pre-configured PasswordHasher instance PH.
    hashed_password = PH.hash(password)

    # 2. Return the result in the required Traefik/htpasswd format.
    return f"{username}:{hashed_password}"


# END OF INTEGRATOR FIX
