"""Download historical public Kraken trades to CSV.

The script uses the public API only and never requires credentials.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_URL = "https://api.kraken.com/0/public/Trades"
REQUEST_TIMEOUT_SECONDS = 15


def fetch_trades(pair: str, since: int) -> tuple[list[list[object]], int]:
    """Fetch one public trade page and return trades plus the next cursor."""
    query = urlencode({"pair": pair, "since": str(since)})
    request = Request(
        f"{API_URL}?{query}",
        headers={"User-Agent": "KrakenTools historical trades downloader"},
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read())
    except (HTTPError, URLError) as error:
        raise RuntimeError(f"Kraken public API request failed: {error}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError("Kraken public API returned invalid JSON") from error

    if payload.get("error"):
        raise RuntimeError(f"Kraken public API error: {payload['error']}")
    result = payload.get("result")
    if not isinstance(result, dict):
        raise RuntimeError("Kraken public API returned an unexpected result")
    trade_key = next((key for key in result if key != "last"), None)
    trades = result.get(trade_key, []) if trade_key else []
    next_cursor = int(result.get("last", since))
    if not isinstance(trades, list):
        raise RuntimeError("Kraken public API returned an invalid trade list")
    return trades, next_cursor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", default="XXBTZEUR")
    parser.add_argument("--since", default="2014-06-11T00:00:00+00:00")
    parser.add_argument("--output", type=Path, default=Path("trades.csv"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        start = datetime.fromisoformat(args.since).astimezone(timezone.utc)
    except ValueError as error:
        raise ValueError("since must be an ISO-8601 timestamp") from error

    cursor = int(start.timestamp() * 1_000_000_000)
    rows_written = 0
    with args.output.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(["Timestamp", "Tid", "Price", "Volume"])
        while True:
            trades, next_cursor = fetch_trades(args.pair, cursor)
            if not trades or next_cursor <= cursor:
                break
            for trade in trades:
                if len(trade) < 3:
                    continue
                timestamp = float(trade[2])
                writer.writerow(
                    [
                        datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat(),
                        int(timestamp * 1_000_000_000),
                        trade[0],
                        trade[1],
                    ]
                )
                rows_written += 1
            output_file.flush()
            cursor = next_cursor
            print(f"{rows_written} trades processed; next cursor: {cursor}")
            time.sleep(1)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError) as error:
        raise SystemExit(f"Error: {error}") from error
