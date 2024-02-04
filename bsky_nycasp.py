import argparse
import datetime
import os

import requests
from atproto import Client


def download_data(date: datetime.date) -> str:
    headers = {
        "User-Agent": "bsky-nycasp/0.1",
        "Ocp-Apim-Subscription-Key": os.environ["API_KEY_311"],
    }

    date_fmt = date.strftime("%Y-%m-%d")
    r = requests.get(
        "https://api.nyc.gov/public/api/GetCalendar",
        params={"fromdate": date_fmt, "todate": date_fmt},
        headers=headers,
    )
    r.raise_for_status()
    data = r.json()
    print(data)

    for item in data["days"][0]["items"]:
        if item["type"] == "Alternate Side Parking":
            return item["details"]

    raise ValueError("Could not find ASP data")


def get_asp_status(date: datetime.date | None = None) -> str:
    # Format the target date
    today = date is None
    if today:
        date = datetime.date.today()
    assert date is not None

    msg = download_data(date)
    if today:
        date_human = date.strftime("%B %-d")
        msg = msg.replace("suspended", f"suspended today, {date_human}")
        msg = msg.replace("in effect", f"in effect today, {date_human}")
    else:
        date_human = date.strftime("%A, %B %-d")
        update = f"will be suspended tomorrow, {date_human}"
        msg = msg.replace("is suspended", update)
        msg = msg.replace("are suspended", update)
        msg = msg.replace("are in effect", f"will be in effect tomorrow, {date_human}")

    return msg


def post_to_bsky(msg: str) -> None:
    username = os.environ.get("BSKY_USERNAME", "")
    password = os.environ.get("BSKY_PASSWORD", "")
    if username == "" or password == "":
        raise ValueError(
            "The environment variables BSKY_USERNAME and BSKY_PASSWORD must be set"
        )

    client = Client()
    client.login(username, password)
    client.send_post(text=msg)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Post NYCASP status to BSKY")
    parser.add_argument("--tomorrow", action="store_true", help="Post tomorrow's status")
    args = parser.parse_args()

    if args.tomorrow:
        msg = get_asp_status(datetime.date.today() + datetime.timedelta(days=1))
    else:
        msg = get_asp_status()

    print(f"Message: {msg}")
    post_to_bsky(msg)
