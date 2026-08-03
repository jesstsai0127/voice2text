import os
import sys

from daily_run import run_daily, run_personal_uploads, run_podcast_backfill

_JOBS = {
    "daily": run_daily,
    "backfill": run_podcast_backfill,
    "personal-uploads": run_personal_uploads,
}

if __name__ == "__main__":
    job_name = sys.argv[1] if len(sys.argv) > 1 else "daily"
    job = _JOBS.get(job_name)
    if job is None:
        print(f"unknown job {job_name!r}, expected one of {list(_JOBS)}", file=sys.stderr)
        sys.exit(1)

    output_dir = os.environ.get(
        "VOICE2TEXT_OUTPUT_DIR", os.path.expanduser("~/voice2text-runs")
    )
    results = job(output_dir)
    for result in results:
        status = "skipped (duplicate)" if result["skipped"] else "processed"
        label = result["episode"]["title"] if "episode" in result else result["pending_upload"]["filename"]
        print(f"{label}: {status}", file=sys.stderr)
