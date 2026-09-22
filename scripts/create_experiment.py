"""Create one controlled delivery experiment on Meta.

Builds a paused Engagement campaign with two ad sets that target the same
trait-defined Custom Audience and differ only in the creative they carry.
The ad sets are left paused; scripts/run_scheduler.py brings them live
together at the scheduled hour so both variants enter the auction under
identical conditions.

Creatives are attached in Ads Manager after creation. The two creatives
of a design must be uploaded to the two ad sets respectively, one framed
for introverts and one for extraverts.

"""

import argparse
import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from . import campaigns  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="Campaign name identifying the condition.")
    parser.add_argument("--audience-id", required=True, help="Custom Audience to target.")
    parser.add_argument(
        "--start",
        required=True,
        help="Trial start time as YYYY-MM-DDTHH:MM:SS in the ad account time zone.",
    )
    args = parser.parse_args()

    start_time = datetime.datetime.strptime(args.start, campaigns.TIME_FORMAT)

    campaigns.init_api()
    campaign_id = campaigns.create_campaign(args.name)
    adsets = campaigns.create_competing_adsets(campaign_id, args.audience_id, start_time)

    end_time = start_time + datetime.timedelta(hours=campaigns.TRIAL_DURATION_HOURS)
    print(f"Campaign {campaign_id} created paused as {args.name!r}")
    for variant, adset_id in adsets.items():
        print(f"  ad set {variant:10} {adset_id}")
    print("\nAdd to your schedule CSV:")
    print("campaign_id,start_time,end_time")
    print(
        f"{campaign_id},"
        f"{start_time.strftime('%Y-%m-%d %H:%M:%S')},"
        f"{end_time.strftime('%Y-%m-%d %H:%M:%S')}"
    )


if __name__ == "__main__":
    main()
