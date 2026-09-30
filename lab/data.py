"""Hämtar BTCUSDT 5-minuters candles från Binance (publikt, ingen nyckel) och cachar lokalt.

Kör:  uv run python -m lab.data --days 180
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import httpx
import pandas as pd

# Binances rena marknadsdata-endpoint: samma candles som api.binance.com, men nåbar även
# från GitHub Actions (amerikanska IP-adresser blockeras av api.binance.com).
URL = "https://data-api.binance.vision/api/v3/klines"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
BAR_MS = 5 * 60 * 1000

COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore",
]


def cache_path(symbol: str, interval: str) -> Path:
    return DATA_DIR / f"{symbol}_{interval}.csv"


def fetch(symbol: str = "BTCUSDT", interval: str = "5m", days: int = 180) -> pd.DataFrame:
    """Hämtar `days` dagar bakåt från nu, 1000 candles per anrop."""
    end = int(time.time() * 1000)
    start = end - days * 24 * 60 * 60 * 1000
    rows: list[list] = []
    with httpx.Client(timeout=20) as client:
        cursor = start
        while cursor < end:
            r = client.get(URL, params={
                "symbol": symbol, "interval": interval,
                "startTime": cursor, "limit": 1000,
            })
            r.raise_for_status()
            batch = r.json()
            if not batch:
                break
            rows.extend(batch)
            cursor = batch[-1][0] + BAR_MS
            time.sleep(0.15)  # snällt mot Binance rate limit

    df = pd.DataFrame(rows, columns=COLUMNS).drop(columns=["ignore"])
    for c in ["open", "high", "low", "close", "volume", "quote_volume",
              "taker_buy_base", "taker_buy_quote"]:
        df[c] = df[c].astype(float)
    df = df.drop_duplicates("open_time").sort_values("open_time").reset_index(drop=True)
    # Sista candlen kan vara ofärdig — släng den.
    now_ms = int(time.time() * 1000)
    df = df[df["close_time"] < now_ms].reset_index(drop=True)
    df["time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    return df


def load(symbol: str = "BTCUSDT", interval: str = "5m") -> pd.DataFrame:
    path = cache_path(symbol, interval)
    if not path.exists():
        raise SystemExit(f"Ingen data i {path}. Kör först: uv run python -m lab.data")
    df = pd.read_csv(path)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=180)
    args = p.parse_args()
    DATA_DIR.mkdir(exist_ok=True)
    df = fetch(days=args.days)
    path = cache_path("BTCUSDT", "5m")
    df.to_csv(path, index=False)
    print(f"{len(df)} candles, {df['time'].iloc[0]} → {df['time'].iloc[-1]}")
    print(f"Sparat: {path}")


if __name__ == "__main__":
    main()
