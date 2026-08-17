"""Safely demonstrate placing a Kraken spot limit order.

The script is a dry run by default. Set ``--execute`` and provide API
credentials through environment variables only when a real order is intended.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import time
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
    """Send one authenticated request without retrying an uncertain order."""
    nonce = str(time.time_ns() // 1_000)
    request_parameters = {"nonce": nonce, **parameters}
    encoded_payload = urlencode(request_parameters).encode("utf-8")
    path = f"/{API_VERSION}/private/{method}"
    request = Request(
        f"{API_BASE}{path}",
        data=encoded_payload,
        headers={
            "User-Agent": "KrakenTools safe order example",
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
            response_body = response.read()
    except (HTTPError, URLError) as error:
        raise RuntimeError(f"Kraken request failed: {error}") from error

    try:
        decoded = json.loads(response_body)
    except json.JSONDecodeError as error:
        raise RuntimeError("Kraken returned invalid JSON") from error

    if not isinstance(decoded, dict):
        raise RuntimeError("Kraken returned an unexpected response shape")
    if decoded.get("error"):
        raise RuntimeError(f"Kraken API error: {decoded['error']}")
    result = decoded.get("result")
    if not isinstance(result, dict):
        raise RuntimeError("Kraken response did not contain a result object")
    return result


def build_order_parameters(
    pair: str, side: str, price: str, volume: str, flags: str
) -> dict[str, str]:
    """Build and validate the order parameters before any network call."""
    if side not in {"buy", "sell"}:
        raise ValueError("side must be buy or sell")
    if not pair or any(character.isspace() for character in pair):
        raise ValueError("pair must be a non-empty symbol without whitespace")
    if float(price) <= 0 or float(volume) <= 0:
        raise ValueError("price and volume must be positive")
    return {
        "pair": pair,
        "type": side,
        "ordertype": "limit",
        "price": price,
        "volume": volume,
        "oflags": flags,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", default="XXBTZEUR")
    parser.add_argument("--price", default="400")
    parser.add_argument("--volume", default="10")
    parser.add_argument("--side", choices=("buy", "sell"), default="buy")
    parser.add_argument("--flags", default="viqc")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Submit the order; without this flag the script only prints the request.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    parameters = build_order_parameters(
        args.pair, args.side, args.price, args.volume, args.flags
    )

    if not args.execute:
        print(json.dumps({"dry_run": True, "method": "AddOrder", "parameters": parameters}))
        return 0

    api_key = os.environ.get("KRAKEN_API_KEY")
    api_secret = os.environ.get("KRAKEN_API_SECRET")
    if not api_key or not api_secret:
        raise RuntimeError(
            "KRAKEN_API_KEY and KRAKEN_API_SECRET are required with --execute"
        )

    result = request_private(api_key, api_secret, "AddOrder", parameters)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError) as error:
        raise SystemExit(f"Error: {error}") from error
