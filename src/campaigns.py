"""Creation and scheduling of the controlled delivery experiments.

Each experiment is one campaign holding two ad sets that target the same
trait-defined Custom Audience. The ad sets are identical in bidding
strategy, budget, start time and duration, and differ only in the
creative they carry: one framing aligned with the audience trait and one
misaligned. Because both compete for the same users under the same
advertiser-specified parameters, any difference in delivery is produced
by the platform's optimization rather than by targeting.
"""

import datetime

import pandas as pd
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.campaign import Campaign
from facebook_business.api import FacebookAdsApi

from . import config

TRIAL_DURATION_HOURS = 12
DAILY_BUDGET_CENTS = 2000
BID_CAP_CENTS = 5
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"


def init_api():
    """Authenticate the Business SDK against the configured ad account."""
    config.require_credentials()
    FacebookAdsApi.init(config.APP_ID, config.APP_SECRET, access_token=config.ACCESS_TOKEN)


def create_campaign(name, account_id=None):
    """Create a paused Engagement campaign.

    The Engagement objective makes the optimizer rank placements by
    predicted interaction, which is the behavior the audit probes.
    Campaigns are created paused so that both ad sets go live together
    at a controlled time.
    """
    account_id = account_id or config.ACCOUNT_ID
    campaign = AdAccount(account_id).create_campaign(
        params={
            "name": name,
            "objective": "OUTCOME_ENGAGEMENT",
            "status": "PAUSED",
            "special_ad_categories": "NONE",
        }
    )
    return campaign.get_id()


def create_competing_adsets(campaign_id, audience_id, start_time, account_id=None):
    """Create the aligned and misaligned ad sets for one experiment.

    Both ad sets point at the same Custom Audience and carry identical
    parameters. A bid cap rather than lowest cost keeps the bid fixed
    across the pair, so the optimizer cannot advantage one variant by
    bidding differently on its behalf.
    """
    account_id = account_id or config.ACCOUNT_ID
    end_time = start_time + datetime.timedelta(hours=TRIAL_DURATION_HOURS)

    created = {}
    for variant in ("introvert", "extravert"):
        params = {
            "name": variant,
            "campaign_id": campaign_id,
            "daily_budget": DAILY_BUDGET_CENTS,
            "billing_event": "IMPRESSIONS",
            "optimization_goal": "POST_ENGAGEMENT",
            "bid_strategy": "LOWEST_COST_WITH_BID_CAP",
            "bid_amount": BID_CAP_CENTS,
            "start_time": start_time.strftime(TIME_FORMAT),
            "end_time": end_time.strftime(TIME_FORMAT),
            "targeting": {"custom_audiences": [{"id": audience_id}]},
            "status": "PAUSED",
        }
        adset = AdSet().api_create(params=params, parent_id=account_id)
        created[variant] = adset["id"]
    return created


def start_campaign(campaign_id):
    """Set a campaign live."""
    Campaign(campaign_id).api_update(params={"status": Campaign.Status.active})


def stop_campaign(campaign_id):
    """Pause a campaign."""
    Campaign(campaign_id).api_update(params={"status": Campaign.Status.paused})


def get_campaign_status(campaign_id):
    """Return the current delivery status of a campaign."""
    return Campaign(campaign_id)["status"]


def run_schedule(schedule_path, now=None, time_format="%Y-%m-%d %H:%M:%S"):
    """Start and stop campaigns according to a schedule file.

    Intended to run once an hour from cron. The schedule is a CSV with
    campaign_id, start_time and end_time. A campaign whose start hour has
    arrived is set live and one whose end hour has arrived is paused, so
    every trial gets the same 12 hour window without manual intervention.

    Trials are sequential rather than concurrent, which keeps separate
    experiments from competing against each other in the same auction.
    """
    now = now or datetime.datetime.now()
    schedule = pd.read_csv(schedule_path)
    one_hour = datetime.timedelta(hours=1)
    zero = datetime.timedelta(0)
    actions = []

    for row in schedule.to_dict(orient="records"):
        campaign_id = row["campaign_id"]
        start_time = datetime.datetime.strptime(row["start_time"], time_format)
        end_time = datetime.datetime.strptime(row["end_time"], time_format)

        if zero <= now - start_time < one_hour:
            start_campaign(campaign_id)
            actions.append((campaign_id, "started"))
        elif zero <= end_time - now < one_hour:
            stop_campaign(campaign_id)
            actions.append((campaign_id, "stopped"))

    return actions
