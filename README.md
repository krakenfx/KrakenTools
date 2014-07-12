KrakenTools
===========

This is a basic Kraken Toolkit written in Python.

kraken_trades_dl.py
-------------------

Create a Kraken API key with permission to "Query Closed Orders & Trades". Edit lines 81-82 to use your API key and secret. **Do not commit or push your API key or secret to GitHub nor any other public location.**

**dt_end**: Set this to a unix timestamp in order to query trades only up to that time. By default, the script will retreive all trades up to and including your most recent trade.

historical_trades.py
--------------------

Retrieve public historical data for the specified pair.
