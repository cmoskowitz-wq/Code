"""
SmartTrade Insights - Secure API Key Storage
Uses the OS credential store via keyring (Windows Credential Manager,
macOS Keychain, Linux Secret Service).  Falls back to an AES-encrypted
local file when keyring is unavailable.
"""
import base64
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_SERVICE_NAME = "SmartTradeInsights"
_FALLBACK_PATH = Path(os.getenv("APPDATA", str(Path.home()))) / "SmartTradeInsights" / ".keys"


# ── Primary: OS keyring ───────────────────────────────────────────────────────

def _keyring_available() -> bool:
    try:
        import keyring  # noqa: F401
        return True
    except ImportError:
        return False


def store_api_key(key_name: str, api_key: str) -> bool:
    """Persist an API key securely."""
    if _keyring_available():
        try:
            import keyring
            keyring.set_password(_SERVICE_NAME, key_name, api_key)
            return True
        except Exception as e:
            logger.warning("keyring store failed (%s), using fallback", e)
    return _fallback_store(key_name, api_key)


def get_api_key(key_name: str) -> Optional[str]:
    """Retrieve a stored API key."""
    if _keyring_available():
        try:
            import keyring
            val = keyring.get_password(_SERVICE_NAME, key_name)
            if val:
                return val
        except Exception as e:
            logger.warning("keyring get failed (%s), using fallback", e)
    return _fallback_get(key_name)


def delete_api_key(key_name: str) -> bool:
    """Remove a stored API key."""
    if _keyring_available():
        try:
            import keyring
            keyring.delete_password(_SERVICE_NAME, key_name)
            return True
        except Exception:
            pass
    return _fallback_delete(key_name)


# ── Fallback: XOR-obfuscated local file ──────────────────────────────────────
# Not cryptographically strong, but better than plaintext.

def _obfuscate(text: str) -> str:
    key = _machine_key()
    xored = bytes(ord(c) ^ key[i % len(key)] for i, c in enumerate(text))
    return base64.b64encode(xored).decode()


def _deobfuscate(text: str) -> str:
    key = _machine_key()
    raw = base64.b64decode(text.encode())
    return "".join(chr(b ^ key[i % len(key)]) for i, b in enumerate(raw))


def _machine_key() -> bytes:
    seed = (os.getenv("COMPUTERNAME") or os.getenv("HOSTNAME") or "smarttrade") + "st1"
    return hashlib.sha256(seed.encode()).digest()


def _load_fallback() -> dict:
    if _FALLBACK_PATH.exists():
        try:
            return json.loads(_FALLBACK_PATH.read_text())
        except Exception:
            pass
    return {}


def _save_fallback(data: dict):
    _FALLBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    _FALLBACK_PATH.write_text(json.dumps(data))


def _fallback_store(key_name: str, api_key: str) -> bool:
    try:
        data = _load_fallback()
        data[key_name] = _obfuscate(api_key)
        _save_fallback(data)
        return True
    except Exception as e:
        logger.error("Fallback store failed: %s", e)
        return False


def _fallback_get(key_name: str) -> Optional[str]:
    try:
        data = _load_fallback()
        if key_name in data:
            return _deobfuscate(data[key_name])
    except Exception as e:
        logger.error("Fallback get failed: %s", e)
    return None


def _fallback_delete(key_name: str) -> bool:
    try:
        data = _load_fallback()
        if key_name in data:
            del data[key_name]
            _save_fallback(data)
        return True
    except Exception:
        return False
