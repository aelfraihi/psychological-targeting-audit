"""Start and stop scheduled trials.

Run once an hour from cron so every trial gets the same 12 hour window:

    0 * * * * cd /path/to/repo && python scripts/run_scheduler.py schedule.csv

The schedule is a CSV with campaign_id, start_time and end_time columns,
times formatted as YYYY-MM-DD HH:MM:SS. scripts/create_experiment.py
prints the row to append for each experiment it creates.
"""

import argparse
import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from . import campaigns 


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("schedule", type=Path, help="Path to the schedule CSV.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without calling the API.",
    )
    args = parser.parse_args()

    now = datetime.datetime.now()
    print(f"Checking schedule at {now:%Y-%m-%d %H:%M:%S}")

    if args.dry_run:
        import pandas as pd

        schedule = pd.read_csv(args.schedule)
        print(f"{len(schedule)} campaigns in schedule, no changes applied")
        return

    campaigns.init_api()
    actions = campaigns.run_schedule(args.schedule, now=now)

    if not actions:
        print("No campaign reached a start or end boundary this hour")
    for campaign_id, action in actions:
        print(f"Campaign {campaign_id} {action}")


if __name__ == "__main__":
    main()
