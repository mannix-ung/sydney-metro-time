# Sydney Metro Punctuality

How punctual is Sydney Metro, and when and where do delays happen?

This project analyses three months of real-time Sydney Metro North West Line data
(April–June 2022, Tallawong to Chatswood) published by Transport for NSW.

> **Status: in progress.** Data collection is done; exploration and modelling are next.

## Data

- **Source:** [Transport for NSW Open Data Hub](https://opendata.transport.nsw.gov.au/),
  *Historical GTFS and GTFS Realtime* dataset (Creative Commons Attribution licence).
- **Period:** 1 April – 30 June 2022. No data was available for 9–10 April and 26 June.
- **Size:** each raw day is about 2.6 million rows (~100 MB zipped), because the feed
  records a fresh prediction for every upcoming stop every few seconds. The download
  script keeps only the **last prediction for each trip at each stop**, which shrinks a
  day to about 4,500 rows (~360,000 rows for the whole period).

## Early findings

- Trains usually arrive about **25 seconds early** and wait at the platform.
- The number of trips changes by day type: about 346 on weekdays, 375 on Fridays,
  fewer on weekends, and public holidays run a Sunday timetable.

*(More to come as the analysis progresses.)*

## How to run it

1. Install the requirements: `pip install -r requirements.txt`
2. Get a free API key from the [Transport for NSW Open Data Hub](https://opendata.transport.nsw.gov.au/)
   and put it in a file called `.env`:
   ```
   TFNSW_API_KEY=your_key_here
   ```
3. Download and reduce the data: `python download_metro.py`
   (takes a while; it's safe to stop and re-run)
4. Open `explore.ipynb` to see the analysis.

## Files

| File | What it does |
|---|---|
| `probe_historical.py` | Checks which dates in the archive actually contain data |
| `download_metro.py` | Downloads April–June 2022 and shrinks each day to one row per trip per stop |
| `explore.ipynb` | Exploration and charts |
