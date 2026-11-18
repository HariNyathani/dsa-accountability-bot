"""DatabaseManager must not race while initializing its shared connection pool."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

from db import database


class _DummyConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class _DummyPool:
    def getconn(self):
        return _DummyConnection()

    def putconn(self, connection):
        pass


def test_concurrent_first_checkout_creates_only_one_pool(monkeypatch):
    pool_creations = []
    creations_lock = threading.Lock()
    start = threading.Barrier(8)

    def make_pool(min_connections, max_connections, dsn):
        time.sleep(0.05)  # widen the unsynchronized first-use window
        pool = _DummyPool()
        with creations_lock:
            pool_creations.append(pool)
        return pool

    monkeypatch.setattr(database, "SimpleConnectionPool", make_pool, raising=False)
    monkeypatch.setattr(database, "ThreadedConnectionPool", make_pool, raising=False)
    manager = database.DatabaseManager("isolated-test-placeholder")

    def checkout_once(_):
        start.wait()
        with manager.get_connection():
            pass

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(checkout_once, range(8)))

    assert len(pool_creations) == 1
