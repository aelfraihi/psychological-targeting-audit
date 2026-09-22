"""Read-only helpers for the Meta Marketing API.

Covers the three things the audit needs from the platform: locating the
campaigns and ad sets belonging to an experiment, reading the estimated
size of a Custom Audience, and pulling delivery metrics at the ad level.

Reach is the metric the analysis depends on. Impressions inflate with
repeat exposures to the same user and spend reflects advertiser cost, so
neither measures how the optimizer split unique users between the two
competing creatives.
"""

import json
from datetime import timedelta

import pandas as pd
import requests

from . import config


def _get(path, params):
    """Issue a GET against the Graph API and return the 'data' payload."""
    params = dict(params)
    params.setdefault("access_token", config.ACCESS_TOKEN)
    response = requests.get(f"{config.BASE_URL}/{path}", params=params, timeout=60)
    if response.status_code != 200:
        raise RuntimeError(f"Graph API error {response.status_code} on {path}: {response.text}")
    return response.json().get("data", [])


def _paginate(path, params):
    """Follow Graph API cursors and return every record across all pages."""
    params = dict(params)
    params.setdefault("access_token", config.ACCESS_TOKEN)
    url = f"{config.BASE_URL}/{path}"
    records = []
    while True:
        response = requests.get(url, params=params, timeout=60)
        if response.status_code != 200:
            raise RuntimeError(f"Graph API error {response.status_code} on {path}: {response.text}")
        payload = response.json()
        records.extend(payload.get("data", []))
        next_page = payload.get("paging", {}).get("next")
        if not next_page:
            return records
        url = next_page
        params = None


def get_campaigns_by_name(name_filter, account_id=None):
    """Return campaigns whose name contains name_filter as a DataFrame.

    Experiment campaigns are named by condition, so filtering on the name
    is how a run is recovered after the fact.
    """
    account_id = account_id or config.ACCOUNT_ID
    records = _paginate(
        f"{account_id}/campaigns",
        {
            "fields": "name,id,start_time",
            "filtering": json.dumps(
                [{"field": "name", "operator": "CONTAIN", "value": name_filter}]
            ),
        },
    )
    return pd.DataFrame(
        {
            "campaign_id": [r["id"] for r in records],
            "campaign_name": [r["name"] for r in records],
            "start_time": [r.get("start_time") for r in records],
        }
    )


def get_adsets_by_campaign_id(campaign_id):
    """Return the ad sets of a campaign as a list of dicts with id and name."""
    return _paginate(f"{campaign_id}/adsets", {"fields": "name,id"})


def get_custom_audience_size(audience_id):
    """Return Meta's lower and upper size estimate for a Custom Audience.

    Meta reports audience size as a bounded range rather than an exact
    count, which is why the paper reports behavioral audience sizes as
    intervals.
    """
    params = {
        "fields": "approximate_count_lower_bound,approximate_count_upper_bound",
        "access_token": config.ACCESS_TOKEN,
    }
    response = requests.get(f"{config.BASE_URL}/{audience_id}", params=params, timeout=60)
    if response.status_code != 200:
        raise RuntimeError(f"Graph API error {response.status_code}: {response.text}")
    return response.json()


def get_ad_level_data(ad_id):
    """Return lifetime delivery metrics for a single ad.

    One record per ad, carrying the reach figure that feeds the
    aligned versus misaligned comparison.
    """
    return _get(
        f"{ad_id}/insights",
        {
            "fields": "ad_id,ad_name,actions,impressions,spend,reach,cpm,cpc,ctr",
            "level": "ad",
            "date_preset": "maximum",
        },
    )


def get_daily_stat(object_id, start_date, end_date, stat="impressions"):
    """Return a daily time series of one metric over a date range."""
    return _get(
        f"{object_id}/insights",
        {
            "time_range": json.dumps({"since": start_date, "until": end_date}),
            "fields": stat,
            "time_increment": 1,
        },
    )


def get_total_stat(object_id, stat="reach"):
    """Return the lifetime total of one metric for a campaign, ad set or ad."""
    return _get(f"{object_id}/insights", {"fields": stat, "date_preset": "maximum"})


def get_hourly_stat(object_id, start_date, end_date, stat="impressions"):
    """Return an hourly series of one metric, one Graph API call per day.

    Trials run for 12 hours, so hourly resolution is what shows whether
    the two competing variants diverged early or late in the run.
    """
    records = []
    current = start_date
    while current <= end_date:
        day = current.strftime("%Y-%m-%d")
        records.extend(
            _get(
                f"{object_id}/insights",
                {
                    "fields": stat,
                    "time_range": json.dumps({"since": day, "until": day}),
                    "time_increment": 1,
                    "breakdowns": "hourly_stats_aggregated_by_advertiser_time_zone",
                },
            )
        )
        current += timedelta(days=1)
    return records


def get_stat_by_breakdown(ad_id, stat="reach", breakdown="gender,age"):
    """Return one metric for an ad split by a Meta demographic breakdown.

    Used to confirm that delivery differences between competing variants
    are not driven by the two ad sets landing on different age or gender
    distributions.
    """
    return _get(
        f"{ad_id}/insights",
        {
            "fields": stat,
            "breakdowns": breakdown,
            "time_increment": 1,
            "date_preset": "maximum",
        },
    )
