from cryptography.fernet import Fernet

with open("secret.key", "rb") as f:
    key = f.read()

cipher = Fernet(key)

def encrypt_field(value: str) -> str:
    """Шифрует строку перед сохранением в БД"""
    if value is None:
        return None
    return cipher.encrypt(value.encode("utf-8")).decode("utf-8")

def decrypt_field(value: str) -> str:
    if value is None:
        return None
    try:
        return cipher.decrypt(value.encode("utf-8")).decode("utf-8")
    except Exception:
        return value
