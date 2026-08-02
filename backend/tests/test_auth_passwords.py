import pytest

from app.auth.passwords import (
    PasswordValidationError,
    hash_password,
    validate_password,
    verify_password,
)


def test_password_policy_accepts_long_passphrases_without_composition_rules() -> None:
    validate_password("correct horse battery staple")
    validate_password("abcdefghijkl")


@pytest.mark.parametrize("password", ["short", "a" * 129])
def test_password_policy_rejects_values_outside_12_to_128_characters(
    password: str,
) -> None:
    with pytest.raises(PasswordValidationError):
        validate_password(password)


def test_passwords_are_stored_as_argon2id_phc_strings() -> None:
    password_hash = hash_password("correct horse battery staple")

    assert password_hash.startswith("$argon2id$")
    verified, upgraded_hash = verify_password(
        "correct horse battery staple",
        password_hash,
    )
    assert verified is True
    assert upgraded_hash is None


def test_password_verification_rejects_wrong_or_invalid_hashes() -> None:
    password_hash = hash_password("correct horse battery staple")

    assert verify_password("wrong password value", password_hash) == (False, None)
    assert verify_password("correct horse battery staple", "not-a-phc-hash") == (
        False,
        None,
    )
