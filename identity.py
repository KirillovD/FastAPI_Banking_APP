from pydantic import EmailStr, TypeAdapter


BCRYPT_MAX_PASSWORD_BYTES = 72
_EMAIL_ADAPTER = TypeAdapter(EmailStr)


def canonicalize_email(value: str) -> str:
    return str(_EMAIL_ADAPTER.validate_python(value))


def validate_password_bytes(password: str) -> str:
    if len(password.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError(
            "Password must be at most 72 UTF-8 bytes"
        )

    return password


def password_fits_bcrypt(password: str) -> bool:
    return (
        len(password.encode("utf-8"))
        <= BCRYPT_MAX_PASSWORD_BYTES
    )
