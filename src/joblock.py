import fcntl
import os
from contextlib import contextmanager

DEFAULT_LOCK_PATH = os.path.expanduser("~/.cache/voice2text/job.lock")


class JobAlreadyRunningError(Exception):
    pass


@contextmanager
def exclusive_job_lock(lock_path: str = None):
    path = lock_path or os.environ.get("VOICE2TEXT_LOCK_PATH", DEFAULT_LOCK_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    fd = open(path, "w")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fd.close()
        raise JobAlreadyRunningError(f"another job already holds the lock at {path}")

    try:
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        fd.close()
