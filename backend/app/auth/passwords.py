"""Password policy and Argon2id hashing for the single installation owner."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from argon2.low_level import Type

MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128

_password_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=64 * 1024,
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)


class PasswordValidationError(ValueError):
    """Raised when a new owner password does not meet the local policy."""


def validate_password(password: str) -> None:
    """Validate length while allowing passphrases without composition rules."""
    length = len(password)
    if length < MIN_PASSWORD_LENGTH:
        raise PasswordValidationError(
            f"Password must contain at least {MIN_PASSWORD_LENGTH} characters."
        )
    if length > MAX_PASSWORD_LENGTH:
        raise PasswordValidationError(
            f"Password must contain at most {MAX_PASSWORD_LENGTH} characters."
        )


def hash_password(password: str) -> str:
    """Validate and hash a password as an Argon2id PHC string."""
    validate_password(password)
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> tuple[bool, str | None]:
    """Verify a password and return an upgraded hash when parameters changed."""
    try:
        _password_hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False, None

    upgraded_hash = None
    if _password_hasher.check_needs_rehash(password_hash):
        upgraded_hash = _password_hasher.hash(password)
    return True, upgraded_hash
