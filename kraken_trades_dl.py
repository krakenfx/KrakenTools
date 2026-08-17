"""Download private Kraken trade history to a tab-separated file.

Credentials are read from environment variables and the script performs
read-only API calls. It never retries a request after an uncertain response.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_BASE = "https://api.kraken.com"
API_VERSION = "0"
REQUEST_TIMEOUT_SECONDS = 15


def sign_private_request(secret: str, path: str, nonce: str, payload: bytes) -> str:
    """Return Kraken's base64-encoded HMAC-SHA512 request signature."""
    secret_bytes = base64.b64decode(secret, validate=True)
    message = path.encode("utf-8") + hashlib.sha256(
        nonce.encode("utf-8") + payload
    ).digest()
    return base64.b64encode(hmac.new(secret_bytes, message, hashlib.sha512).digest()).decode(
        "ascii"
    )


def request_private(
    api_key: str,
    api_secret: str,
    method: str,
    parameters: dict[str, str],
) -> dict[str, Any]:
    """Perform one authenticated read-only request."""
    nonce = str(time.time_ns() // 1_000)
    request_parameters = {"nonce": nonce, **parameters}
    encoded_payload = urlencode(request_parameters).encode("utf-8")
    path = f"/{API_VERSION}/private/{method}"
    request = Request(
        f"{API_BASE}{path}",
        data=encoded_payload,
        headers={
            "User-Agent": "KrakenTools trade history downloader",
            "Content-Type": "application/x-www-form-urlencoded",
            "API-Key": api_key,
            "API-Sign": sign_private_request(
                api_secret, path, nonce, encoded_payload
            ),
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read())
    except (HTTPError, URLError) as error:
        raise RuntimeError(f"Kraken request failed: {error}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError("Kraken returned invalid JSON") from error

    if not isinstance(payload, dict):
        raise RuntimeError("Kraken returned an unexpected response shape")
    if payload.get("error"):
        raise RuntimeError(f"Kraken API error: {payload['error']}")
    result = payload.get("result")
    if not isinstance(result, dict):
        raise RuntimeError("Kraken response did not contain a result object")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("trades.txt"))
    parser.add_argument("--page-size", type=int, default=50)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.page_size <= 0:
        raise ValueError("page-size must be positive")

    api_key = os.environ.get("KRAKEN_API_KEY")
    api_secret = os.environ.get("KRAKEN_API_SECRET")
    if not api_key or not api_secret:
        raise RuntimeError("KRAKEN_API_KEY and KRAKEN_API_SECRET are required")

    with args.output.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.writer(output_file, delimiter="\t", lineterminator="\n")
        writer.writerow(
            [
                "timestamp",
                "fee",
                "vol",
                "ordertype",
                "ordertxid",
                "pair",
                "cost",
                "type",
                "price",
            ]
        )
        end: str | None = None
        seen_trade_ids: set[str] = set()
        while True:
            parameters = {"ofs": "0"}
            if end is not None:
                parameters["end"] = end
            result = request_private(api_key, api_secret, "TradesHistory", parameters)
            trades = result.get("trades")
            if not isinstance(trades, dict) or not trades:
                break

            oldest_timestamp: float | None = None
            rows_written = 0
            for trade_id, trade in trades.items():
                if trade_id in seen_trade_ids or not isinstance(trade, dict):
                    continue
                timestamp = float(trade.get("time", 0))
                oldest_timestamp = (
                    timestamp
                    if oldest_timestamp is None
                    else min(oldest_timestamp, timestamp)
                )
                writer.writerow(
                    [
                        datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat(),
                        trade.get("fee", ""),
                        trade.get("vol", ""),
                        trade.get("ordertype", ""),
                        trade.get("ordertxid", ""),
                        trade.get("pair", ""),
                        trade.get("cost", ""),
                        trade.get("type", ""),
                        trade.get("price", ""),
                    ]
                )
                seen_trade_ids.add(trade_id)
                rows_written += 1
            output_file.flush()
            print(f"{rows_written} trades processed; total: {len(seen_trade_ids)}")

            if oldest_timestamp is None:
                break
            next_end = str(int(oldest_timestamp))
            if end is not None and next_end >= end:
                break
            end = next_end
            time.sleep(1)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError) as error:
        raise SystemExit(f"Error: {error}") from error
