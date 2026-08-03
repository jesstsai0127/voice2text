import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from joblock import JobAlreadyRunningError, exclusive_job_lock


def test_lock_can_be_acquired_and_released(tmp_path):
    lock_path = str(tmp_path / "job.lock")

    with exclusive_job_lock(lock_path):
        pass

    # released cleanly, so it can be acquired again right after
    with exclusive_job_lock(lock_path):
        pass


def test_second_acquire_while_held_raises(tmp_path):
    lock_path = str(tmp_path / "job.lock")

    with exclusive_job_lock(lock_path):
        with pytest.raises(JobAlreadyRunningError):
            with exclusive_job_lock(lock_path):
                pass
