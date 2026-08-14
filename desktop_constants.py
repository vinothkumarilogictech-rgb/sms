"""Configuration for the Windows desktop client."""

import os

from dotenv import load_dotenv


load_dotenv(override=True)

DEFAULT_SERVER_URL = "https://sms.ilogicigroup.com/"
APP_TITLE = "Bike application"


def get_server_url() -> str:
    """Return the server URL the desktop EXE should open."""
    return (os.getenv("REMOTE_APP_URL") or DEFAULT_SERVER_URL).strip().rstrip("/") + "/"
