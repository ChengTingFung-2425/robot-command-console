import os
import logging
from typing import Optional

from src.common.token_manager import get_edge_token_manager
from .edge_token_cache import EdgeTokenCache, generate_key_from_env
from .edge_token_sync import EdgeTokenSync


logger = logging.getLogger(__name__)


class TokenIntegration:
    """Wire TokenManager rotation events into Edge cache + sync worker."""

    def __init__(self, persist_dir: Optional[str] = None, encryption_env_var: str = 'EDGE_TOKEN_KEY'):
        self.persist_dir = persist_dir or os.path.join(os.path.expanduser('~'), '.robot-console')
        os.makedirs(self.persist_dir, exist_ok=True)
        cache_path = os.path.join(self.persist_dir, 'edge_tokens.enc')
        sync_path = os.path.join(self.persist_dir, 'edge_sync.enc')

        key = generate_key_from_env(encryption_env_var)

        self.cache = EdgeTokenCache(cache_path, encryption_key=key)

        # placeholder sync callback: in production implement cloud refresh API
        def sync_callback(item: dict) -> bool:
            # item example: {'key': 'app', 'token': '...', 'metadata': {...}}
            # Attempt to call cloud refresh/notify endpoint here.
            logger.info('Sync callback invoked for item', extra={'item_key': item.get('key')})
            # return False to trigger retry/backoff for now
            return False

        self.sync = EdgeTokenSync(sync_path, sync_callback, encryption_key=key)

        # subscribe to token rotations
        manager = get_edge_token_manager()
        manager.on_token_rotated(self._on_rotated)

    def start(self):
        self.sync.start()

    def stop(self):
        self.sync.stop()

    def _on_rotated(self, new_token: str, info) -> None:
        # persist token in cache and enqueue sync
        try:
            self.cache.set('app', new_token, expires_in=None,
                           metadata={'rotation_count': getattr(info, 'rotation_count', None)})
            self.sync.enqueue('app', {'key': 'app', 'token': new_token,
                                      'metadata': {'rotation_count': getattr(info, 'rotation_count', None)}})
        except Exception:
            logger.exception('Failed to persist/enqueue rotated token')


__all__ = ['TokenIntegration']
