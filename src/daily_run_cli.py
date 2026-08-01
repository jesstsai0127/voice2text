import os
import sys

from daily_run import run_daily

if __name__ == "__main__":
    output_dir = os.environ.get(
        "VOICE2TEXT_OUTPUT_DIR", os.path.expanduser("~/voice2text-runs")
    )
    results = run_daily(output_dir)
    for result in results:
        status = "skipped (duplicate)" if result["skipped"] else "processed"
        print(f"{result['episode']['title']}: {status}", file=sys.stderr)
