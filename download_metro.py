"""
Download Sydney Metro trip updates from the Transport for NSW historical
archive and shrink each day to one row per trip per stop.

Each raw day is ~100 MB zipped and ~2.6 million rows, because the feed saves a
fresh prediction for every upcoming stop every few seconds. We only keep the
LAST prediction for each trip at each stop (the closest thing to what actually
happened), which brings a day down to ~4,500 rows. The raw zip is deleted after
processing.

Also downloads the Metro timetables published in (and just before) the period,
so each day can be matched to the timetable that was in force.

Setup: TFNSW_API_KEY=your_key in a .env file in this folder.
Run:   python download_metro.py
       (safe to stop and re-run: days already processed are skipped)
"""

import os
import tempfile
import zipfile
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

# ---- settings you might change -------------------------------------------
START = date(2022, 4, 1)
END = date(2022, 6, 30)
# ---------------------------------------------------------------------------

API_URL = "https://api.transport.nsw.gov.au/v1/gtfs/historical"
BASE = Path(__file__).parent / "data"
DAILY_DIR = BASE / "daily"          # one small CSV per day
TIMETABLE_DIR = BASE / "timetables"  # raw GTFS timetable zips

RAW_COLUMNS = [
    "trip_id", "start_date", "start_time", "direction_id",
    "current_stop_sequence", "stop_id",
    "arrival_delay", "departure_delay", "arrival_time", "departure_time",
    "header_TimeStamp", "vehicle_label",
]


def list_files(api_key, schema, start, end):
    """Ask the API for the files between two dates (max 90 days per call)."""
    files = []
    chunk_start = start
    while chunk_start <= end:
        chunk_end = min(chunk_start + timedelta(days=89), end)
        body = {
            "transportMode": "MET",
            "serviceName": "Metro",
            "schemaType": schema,
            "fromDate": chunk_start.isoformat(),
            "toDate": chunk_end.isoformat(),
        }
        response = requests.post(
            API_URL, json=body,
            headers={"Authorization": f"apikey {api_key}"}, timeout=60,
        )
        response.raise_for_status()
        files += response.json().get("files", [])
        chunk_start = chunk_end + timedelta(days=1)
    return files


def download(url, path):
    """Stream a file to disk so a 100 MB download doesn't sit in memory."""
    with requests.get(url, stream=True, timeout=600) as response:
        response.raise_for_status()
        with open(path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1 << 20):
                f.write(chunk)


def reduce_day(zip_path):
    """Keep the last prediction for each (service date, trip, stop)."""
    with zipfile.ZipFile(zip_path) as z:
        with z.open(z.namelist()[0]) as f:
            df = pd.read_csv(f, usecols=RAW_COLUMNS)
    if df.empty:
        return df

    df = df.rename(columns={
        "start_date": "service_date",
        "current_stop_sequence": "stop_sequence",
        "header_TimeStamp": "last_seen",
    })
    keys = ["service_date", "trip_id", "stop_sequence"]

    snapshots = df.groupby(keys).size().rename("snapshots")
    df = df.sort_values("last_seen")
    last = df.groupby(keys, as_index=False).last()
    last = last.merge(snapshots, on=keys)

    # 0 means "no time given" in this feed
    for col in ["arrival_time", "departure_time"]:
        last[col] = last[col].where(last[col] > 0)

    return last.sort_values(["service_date", "trip_id", "stop_sequence"])


def main():
    load_dotenv()
    api_key = os.getenv("TFNSW_API_KEY")
    if not api_key:
        raise SystemExit("No API key found. Put TFNSW_API_KEY=your_key in a .env file.")
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    TIMETABLE_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Timetables: include 60 days before START to catch the one in force.
    print("Timetables:")
    for item in list_files(api_key, "Timetable", START - timedelta(days=60), END):
        path = TIMETABLE_DIR / f"timetable_{item['fileDate']}.zip"
        if path.exists():
            continue
        download(item["fileURL"], path)
        print(f"  saved {path.name}")

    # 2. Trip updates, one day at a time.
    print("Trip updates:")
    files = list_files(api_key, "TripUpdate", START, END)
    for item in files:
        out = DAILY_DIR / f"metro_{item['fileDate']}.csv"
        if out.exists():
            print(f"  {item['fileDate']}  already done")
            continue
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw.zip"
            try:
                download(item["fileURL"], raw)
                day = reduce_day(raw)
            except Exception as error:
                print(f"  {item['fileDate']}  failed: {error}")
                continue
        day.to_csv(out, index=False)
        print(f"  {item['fileDate']}  {len(day):,} rows")

    print("Done. Re-run any time to fill in days that failed.")


if __name__ == "__main__":
    main()