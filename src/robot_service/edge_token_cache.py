import json
import os
import threading
import time
from typing import Optional, Dict

from cryptography.fernet import Fernet, InvalidToken


class EdgeTokenCache:
    """A small, secure token cache for Edge use.

    - In-memory dict for fast access
    - Encrypted file on disk for persistence
    - TTL handling and refresh hook support
    """

    def __init__(self, persist_path: str, encryption_key: Optional[bytes] = None):
        self._lock = threading.RLock()
        self._store: Dict[str, Dict] = {}
        self.persist_path = persist_path
        os.makedirs(os.path.dirname(persist_path), exist_ok=True)

        if encryption_key is None:
            # generate ephemeral key if not provided (not ideal for long-term persistence)
            encryption_key = Fernet.generate_key()
        self._fernet = Fernet(encryption_key)

        self._load_from_disk()

    def _load_from_disk(self):
        if not os.path.exists(self.persist_path):
            return
        try:
            with open(self.persist_path, 'rb') as f:
                data = f.read()
            if not data:
                return
            plaintext = self._fernet.decrypt(data)
            payload = json.loads(plaintext.decode())
            now = int(time.time())
            with self._lock:
                for k, v in payload.items():
                    if v.get('expires_at') is None or v['expires_at'] > now:
                        self._store[k] = v
        except (InvalidToken, ValueError):
            # cannot decrypt or parse — skip loading to avoid crashing
            return

    def _persist_to_disk(self):
        tmp = self.persist_path + '.tmp'
        with self._lock:
            payload = json.dumps(self._store).encode()
            ciphertext = self._fernet.encrypt(payload)
            with open(tmp, 'wb') as f:
                f.write(ciphertext)
            os.replace(tmp, self.persist_path)

    def set(self, key: str, token: str, expires_in: Optional[int] = None, metadata: Optional[dict] = None):
        with self._lock:
            now = int(time.time())
            expires_at = now + expires_in if expires_in is not None else None
            self._store[key] = {
                'token': token,
                'expires_at': expires_at,
                'metadata': metadata or {},
                'updated_at': now,
            }
        self._persist_to_disk()

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            now = int(time.time())
            if entry.get('expires_at') is not None and entry['expires_at'] <= now:
                # expired, remove and persist
                del self._store[key]
                self._persist_to_disk()
                return None
            return entry['token']

    def delete(self, key: str):
        with self._lock:
            if key in self._store:
                del self._store[key]
                self._persist_to_disk()

    def list_keys(self):
        with self._lock:
            return list(self._store.keys())


def generate_key_from_env(env_var: str = 'EDGE_TOKEN_KEY') -> bytes:
    val = os.environ.get(env_var)
    if val:
        # if user provided base64 urlsafe key directly
        try:
            return val.encode()
        except Exception:
            pass
    # fallback: generate ephemeral key
    return Fernet.generate_key()


__all__ = [
    'EdgeTokenCache',
    'generate_key_from_env',
]
