import os
import time
import tempfile

from cryptography.fernet import Fernet

from src.robot_service.edge_token_cache import EdgeTokenCache


def test_set_get_and_expiry(tmp_path):
    key = Fernet.generate_key()
    persist = tmp_path / 'tokens.enc'
    cache = EdgeTokenCache(str(persist), encryption_key=key)

    cache.set('user1', 'tok-abc', expires_in=1)
    assert cache.get('user1') == 'tok-abc'
    time.sleep(1.1)
    assert cache.get('user1') is None


def test_persistence_across_instances(tmp_path):
    key = Fernet.generate_key()
    persist = tmp_path / 'tokens2.enc'
    cache = EdgeTokenCache(str(persist), encryption_key=key)
    cache.set('u', 'tkn', expires_in=60, metadata={'a': 1})

    # new instance should load from disk
    cache2 = EdgeTokenCache(str(persist), encryption_key=key)
    assert cache2.get('u') == 'tkn'
