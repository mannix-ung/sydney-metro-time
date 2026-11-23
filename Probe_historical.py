"""
Find which dates in the Transport for NSW historical archive actually contain
trip update data.

For each mode and month listed below, it asks the API for the file list,
downloads ONE day's file (the first of that month), and counts the rows.
Nothing is saved except a small summary printed to the screen.

Setup: put TFNSW_API_KEY=your_key in a .env file in this folder.
Run:   python probe_historical.py
"""

import csv
import io
import os
import zipfile

import requests
from dotenv import load_dotenv

API_URL = "https://api.transport.nsw.gov.au/v1/gtfs/historical"

SERVICES = [
    ("MET", "Metro"),
    ("FER", "SydneyFerries"),
]

# First day of each month to check (year, month).
MONTHS = [(year, month) for year in (2020, 2021, 2022, 2023) for month in (1, 4, 7, 10)]


def first_file_url(api_key, mode, service, year, month):
    """Ask for one month's TripUpdate files and return the first file's URL."""
    body = {
        "transportMode": mode,
        "serviceName": service,
        "schemaType": "TripUpdate",
        "fromDate": f"{year}-{month:02d}-01",
        "toDate": f"{year}-{month:02d}-07",
    }
    response = requests.post(
        API_URL,
        json=body,
        headers={"Authorization": f"apikey {api_key}"},
        timeout=60,
    )
    response.raise_for_status()
    files = response.json().get("files", [])
    if not files:
        return None, None
    return files[0]["fileDate"], files[0]["fileURL"]


def count_rows(file_url):
    """Download a day's zip and count the data rows in the CSV inside it."""
    response = requests.get(file_url, timeout=300)
    response.raise_for_status()
    size_mb = len(response.content) / 1_000_000
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        name = z.namelist()[0]
        with z.open(name) as f:
            reader = csv.reader(io.TextIOWrapper(f, encoding="utf-8"))
            next(reader, None)  # skip the header row
            rows = sum(1 for _ in reader)
    return rows, size_mb


def main():
    load_dotenv()
    api_key = os.getenv("TFNSW_API_KEY")
    if not api_key:
        raise SystemExit("No API key found. Put TFNSW_API_KEY=your_key in a .env file.")

    print(f"{'service':<15}{'date':<12}{'rows':>12}{'zip MB':>10}")
    for mode, service in SERVICES:
        for year, month in MONTHS:
            try:
                file_date, url = first_file_url(api_key, mode, service, year, month)
                if url is None:
                    print(f"{service:<15}{year}-{month:02d}    no files")
                    continue
                rows, size_mb = count_rows(url)
                print(f"{service:<15}{file_date:<12}{rows:>12,}{size_mb:>10.1f}")
            except Exception as error:
                print(f"{service:<15}{year}-{month:02d}    error: {error}")


if __name__ == "__main__":
    main()