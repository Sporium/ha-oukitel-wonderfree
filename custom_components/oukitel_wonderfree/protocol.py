"""Wonderfree (Quectel) cloud protocol.

Reconstructed from the Wonderfree app (`com.quectel.commonappeu`). The login
handshake is unusual enough to be worth stating plainly:

    random    = 16 random alphanumeric characters
    key       = md5_hex(random)[8:24]          -> 16 chars, AES-128
    iv        = key[8:16] + key[0:8]
    pwd       = base64(AES-128-CBC/PKCS5(password, key, iv))
    signature = sha256_hex(email + pwd + random + DOMAIN_SECRET)

`pwd` keeps the trailing newline that Android's `Base64.encodeToString(..., 0)`
appends, because the app feeds that exact string into the signature. Dropping
it produces a signature the server rejects.

Authenticated calls carry a plain `Authorization: <token>` header; there is no
per-request signing. A response `code` of 5032 means the token expired and
should be refreshed, 5106 means the session is gone entirely.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import string
from typing import Final

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# Region constants, from the app's region table.
REGIONS: Final[dict[str, dict[str, str]]] = {
    "eu": {
        "api": "https://iot-api.quecteleu.com",
        "ws": "wss://iot-ws.quecteleu.com/ws/v1",
        "user_domain": "E.SP.4294967410",
        "domain_secret": "3aRNUwWahjyANa7WfBK2wCCkxCexB6nXxKJwXxfePvzf",
    },
    "us": {
        "api": "https://iot-api.quectelus.com",
        "ws": "wss://ws.quectelus.com/ws/v1",
        "user_domain": "U.SP.8589934603",
        "domain_secret": "pUTp5goB1bLinprRQMmK3EPiiuPiGrJtKUNptWRXVmP",
    },
    "cn": {
        "api": "https://iot-gateway.quectel.com",
        "ws": "wss://iot-ws.quectel.com/ws/v1",
        "user_domain": "C.DM.5903.1",
        "domain_secret": "EufftRJSuWuVY7c6txzGifV9bJcfXHAFa7hXY5doXSn7",
    },
}

DEFAULT_REGION: Final = "eu"

# Service prefixes, then the endpoint under each.
PATH_LOGIN: Final = "/v2/enduser/enduserapi/emailPwdLogin"
PATH_REFRESH: Final = "/v2/enduser/enduserapi/refreshToken"
PATH_DEVICE_LIST: Final = "/v2/binding/enduserapi/userDeviceList"
PATH_DEVICE_INFO: Final = "/v2/binding/enduserapi/deviceInfo"
PATH_PROPERTY_DATA: Final = "/v2/quecdatastorage/enduserapi/getPropertyDataList"
PATH_PROPERTY_CHART: Final = "/v2/quecdatastorage/enduserapi/getPropertyChartList"
PATH_CONTROL: Final = "/v2/binding/enduserapi/batchControlDevice"

CODE_TOKEN_EXPIRED: Final = 5032
CODE_SESSION_GONE: Final = 5106

_ALPHABET: Final = string.ascii_letters + string.digits


def make_random(length: int = 16) -> str:
    """The app's 16-character alphanumeric nonce."""
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


def derive_key_iv(random: str) -> tuple[bytes, bytes]:
    """Derive the AES key and IV the way the app does."""
    key = hashlib.md5(random.encode()).hexdigest().upper()[8:24]
    iv = key[8:16] + key[0:8]
    return key.encode(), iv.encode()


# NOTE — password encoding is confirmed to the byte level except one detail.
# Against the live EU endpoint: form-encoded body is correct (the server
# accepts `email` and reaches password handling), and a malformed password
# returns code 5353 "Password decryption failed". The trailing-newline vs
# no-newline choice below is the app's literal behaviour; if a real login ever
# returns 5353, flip `_APPEND_NEWLINE` — that is the only remaining unknown.
_APPEND_NEWLINE: bool = True


def encrypt_password(password: str, random: str) -> str:
    """Encrypt the password exactly as the app does, newline included."""
    key, iv = derive_key_iv(random)
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    body = padder.update(password.encode()) + padder.finalize()
    encryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    ciphertext = encryptor.update(body) + encryptor.finalize()
    encoded = base64.b64encode(ciphertext).decode()
    # Android's Base64.DEFAULT appends a newline; the signature includes it.
    return encoded + "\n" if _APPEND_NEWLINE else encoded


def sign_login(email: str, pwd: str, random: str, domain_secret: str) -> str:
    """Signature over the concatenated login fields."""
    return hashlib.sha256(f"{email}{pwd}{random}{domain_secret}".encode()).hexdigest()


def build_login_payload(email: str, password: str, region: str = DEFAULT_REGION) -> dict[str, str]:
    """Assemble the body for emailPwdLogin."""
    conf = REGIONS[region]
    random = make_random()
    pwd = encrypt_password(password, random)
    return {
        "pwd": pwd,
        "email": email,
        "random": random,
        "userDomain": conf["user_domain"],
        "signature": sign_login(email, pwd, random, conf["domain_secret"]),
    }
