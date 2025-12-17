import time
from cryptography.fernet import Fernet

from src.robot_service.edge_token_sync import EdgeTokenSync


def test_enqueue_and_success(tmp_path):
    key = Fernet.generate_key()
    persist = tmp_path / 'sync.enc'

    # sync_callback that succeeds on first try
    def callback(item):
        assert 'token' in item
        return True

    sync = EdgeTokenSync(str(persist), sync_callback=callback, encryption_key=key)
    sync.enqueue('i1', {'token': 'abc'})
    sync.start()
    time.sleep(0.5)
    sync.stop()
    assert sync.pending_count() == 0


def test_retry_and_persist(tmp_path):
    key = Fernet.generate_key()
    persist = tmp_path / 'sync2.enc'

    # callback fails first 2 times then succeeds
    state = {'calls': 0}

    def callback(item):
        state['calls'] += 1
        return state['calls'] > 2

    sync = EdgeTokenSync(str(persist), sync_callback=callback, encryption_key=key)
    sync.enqueue('i2', {'token': 'xyz'})
    sync.start()
    # give time for retries
    time.sleep(6)
    sync.stop()
    assert state['calls'] >= 3
    assert sync.pending_count() == 0
