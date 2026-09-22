"""Configuration loaded from the environment.

Copy .env.example to .env and fill in your own Meta Marketing API
credentials. No credentials are distributed with this repository.
"""

import os

from dotenv import load_dotenv

load_dotenv()

API_VERSION = os.getenv("META_API_VERSION", "v21.0")
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCOUNT_ID = os.getenv("ACCOUNT_ID")
APP_ID = os.getenv("APP_ID")
APP_SECRET = os.getenv("APP_SECRET")

PAGE_ID = os.getenv("MAIN_PAGE_ID")
INTROVERT_PAGE_ID = os.getenv("INTROVERT_PAGE_ID")
EXTRAVERT_PAGE_ID = os.getenv("EXTRAVERT_PAGE_ID")

INTROVERT_AUDIENCE_ID = os.getenv("INTROVERT_AUDIENCE_ID")
EXTRAVERT_AUDIENCE_ID = os.getenv("EXTRAVERT_AUDIENCE_ID")

REQUIRED = ("ACCESS_TOKEN", "ACCOUNT_ID", "APP_ID", "APP_SECRET")


def require_credentials():
    """Raise if the variables needed to talk to the Marketing API are unset."""
    missing = [name for name in REQUIRED if not globals().get(name)]
    if missing:
        raise RuntimeError(
            "Missing environment variables: "
            + ", ".join(missing)
            + ". Copy .env.example to .env and fill it in."
        )
