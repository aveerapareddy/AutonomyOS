"""Run an isolated-worker queue consumer against a local shared volume."""
import argparse
from pathlib import Path
import signal
import threading
from backend.operations.jobs import JobStore

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--once',action='store_true');a=p.parse_args()
    store=JobStore(a.root);stop=threading.Event()
    signal.signal(signal.SIGTERM,lambda *_:stop.set());signal.signal(signal.SIGINT,lambda *_:stop.set())
    while not stop.is_set():
        worked=store.run_one()
        if a.once:break
        if not worked:stop.wait(.25)
