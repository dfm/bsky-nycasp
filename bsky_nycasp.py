import argparse
import datetime
import os

import requests
from atproto import Client


def get_asp_status(date: datetime.date | None = None) -> str:
    # Format the target date
    today = date is None
    if today:
        date = datetime.date.today()
    assert date is not None
    date_fmt = date.strftime("%m/%d/%Y")

    # Download the data from 311
    r = requests.get("https://portal.311.nyc.gov/home-cal/", params={"today": date_fmt})
    r.raise_for_status()
    data = r.json()

    # Work out which row has the ASP data (it should be the first one)
    current = None
    for row in data.get("results", []):
        if row.get("CalendarName", "") == "Alternate Side Parking":
            current = row
            break
    if current is None:
        raise ValueError("Could not find ASP data")

    # Format the message text
    msg = current.get("CalendarDetailMessage", "")
    if msg == "":
        if today:
            date_human = date.strftime("%B %-d")
            msg = f"NYCASP is in effect today, {date_human}."
        else:
            date_human = date.strftime("%A, %B %-d")
            msg = f"NYCASP will be in effect tomorrow, {date_human}."

    else:
        msg = msg.replace("Alternate side parking", "NYCASP rules")
        if today:
            date_human = date.strftime("%B %-d")
            msg = msg.replace("suspended", f"suspended today, {date_human}")
        else:
            date_human = date.strftime("%A, %B %-d")
            update = f"will be suspended tomorrow, {date_human}"
            msg = msg.replace("is suspended", update)
            msg = msg.replace("are suspended", update)
            msg = msg.replace("are in", "will be")

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
    parser.add_argument(
        "--tomorrow", action="store_true", help="Post tomorrow's status"
    )
    args = parser.parse_args()

    if args.tomorrow:
        msg = get_asp_status(datetime.date.today() + datetime.timedelta(days=1))
    else:
        msg = get_asp_status()

    print(f"Message: {msg}")
    post_to_bsky(msg)
