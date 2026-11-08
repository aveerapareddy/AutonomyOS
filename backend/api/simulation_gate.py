"""Single-process API gate for the shared PyBullet client. Run one API worker."""
from contextlib import contextmanager
from threading import Lock
from fastapi import HTTPException

lock = Lock()

@contextmanager
def simulation_slot():
    if not lock.acquire(blocking=False):
        raise HTTPException(409, 'A simulation is already running; retry after completion')
    try:
        yield
    finally:
        lock.release()
