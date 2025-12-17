import json
import os
import threading
import time
from typing import Callable, Dict, Optional

from .edge_token_cache import generate_key_from_env
from cryptography.fernet import Fernet, InvalidToken


DEFAULT_RETRY_INTERVAL = 5


class EdgeTokenSync:
    """Background sync worker for Edge token persistence and cloud sync.

    Usage:
      sync = EdgeTokenSync(persist_path, sync_callback)
      sync.start()
      sync.enqueue({'key': 'user1', 'token': 'abc', 'metadata': {}})
      sync.stop()

    The `sync_callback` receives a dict with the queued item and should return True on success.
    """

    def __init__(self, persist_path: str, sync_callback: Callable[[Dict], bool], encryption_key: Optional[bytes] = None):
        self.persist_path = persist_path
        os.makedirs(os.path.dirname(persist_path), exist_ok=True)
        self._lock = threading.RLock()
        self._queue: Dict[str, Dict] = {}
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._sync_callback = sync_callback
        if encryption_key is None:
            encryption_key = generate_key_from_env()
        self._fernet = Fernet(encryption_key)
        self._load()

    def _load(self):
        if not os.path.exists(self.persist_path):
            return
        try:
            with open(self.persist_path, 'rb') as f:
                data = f.read()
            if not data:
                return
            plaintext = self._fernet.decrypt(data)
            payload = json.loads(plaintext.decode())
            with self._lock:
                self._queue = payload
        except (InvalidToken, ValueError):
            return

    def _persist(self):
        tmp = self.persist_path + '.tmp'
        with self._lock:
            payload = json.dumps(self._queue).encode()
            ciphertext = self._fernet.encrypt(payload)
            with open(tmp, 'wb') as f:
                f.write(ciphertext)
            os.replace(tmp, self.persist_path)

    def enqueue(self, item_id: str, item: Dict):
        with self._lock:
            self._queue[item_id] = {
                'item': item,
                'attempts': 0,
                'last_try': None,
            }
        self._persist()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self, wait: bool = True):
        self._stop_event.set()
        if wait and self._thread:
            self._thread.join(timeout=5)

    def _run(self):
        while not self._stop_event.is_set():
            to_remove = []
            with self._lock:
                items = list(self._queue.items())
            for item_id, data in items:
                now = int(time.time())
                last = data.get('last_try') or 0
                attempts = data.get('attempts', 0)
                backoff = DEFAULT_RETRY_INTERVAL * (2 ** attempts)
                if now - last < backoff:
                    continue
                success = False
                try:
                    success = bool(self._sync_callback(data['item']))
                except Exception:
                    success = False

                with self._lock:
                    if success:
                        to_remove.append(item_id)
                    else:
                        self._queue[item_id]['attempts'] = attempts + 1
                        self._queue[item_id]['last_try'] = now
                        # cap attempts to avoid infinite growth
                        if self._queue[item_id]['attempts'] > 10:
                            to_remove.append(item_id)
            if to_remove:
                with self._lock:
                    for k in to_remove:
                        if k in self._queue:
                            del self._queue[k]
                    self._persist()
            time.sleep(1)

    def pending_count(self) -> int:
        with self._lock:
            return len(self._queue)


__all__ = ['EdgeTokenSync']
