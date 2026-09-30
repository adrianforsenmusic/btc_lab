"""Papperstrading-loggen: ETT beslut nu, sparat som en rad. Inga riktiga pengar, ingen
börsnyckel, inga ordrar — bara "vad hade systemet gjort, och vad hände sen?".

Kör:  uv run python -m lab.paper          → nytt beslut, ny rad i logs/paper_log.csv
      uv run python -m lab.paper --settle → fyller i facit för rader som är ≥ 4 h gamla
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import pandas as pd

from lab import LOG_DIR
from lab.backtest import CONSENSUS, FEE_ROUND_TRIP, HORIZON
from lab.data import fetch
from lab.jev_news import run_news_lens
from lab.lenses import compute_lenses

LOG = LOG_DIR / "paper_log.csv"
FIELDS = ["tid_utc", "pris", "up", "down", "flat", "nyhetsvy", "beslut",
          "planerad_stop", "planerat_mål", "pris_efter_4h", "resultat_efter_avgift", "anteckning"]
NAMES = {1: "UP", -1: "DOWN", 0: "FLAT"}


def snapshot() -> dict:
    df = fetch(days=2)  # 576 bars räcker för alla lenses (behöver 288)
    votes = compute_lenses(df).iloc[-1].to_dict()

    news = run_news_lens()
    if news is not None:
        votes["jev_news"] = news[0]

    n = len(votes)
    up = sum(1 for v in votes.values() if v == 1)
    dn = sum(1 for v in votes.values() if v == -1)
    decision = 1 if up / n >= CONSENSUS else -1 if dn / n >= CONSENSUS else 0

    price = float(df["close"].iloc[-1])
    # Stop/mål i kod: 1,5 resp. 3 × genomsnittlig 5-min-range senaste 4 h, skalat till 4 h.
    rng = float((df["high"] - df["low"]).tail(48).mean()) * (HORIZON ** 0.5)
    stop = price - decision * 1.5 * rng if decision else None
    target = price + decision * 3 * rng if decision else None

    row = {
        "tid_utc": df["time"].iloc[-1].isoformat(),
        "pris": round(price, 2), "up": up, "down": dn, "flat": n - up - dn,
        "nyhetsvy": NAMES[news[0]] if news else "–",
        "beslut": ("HANDLA " + NAMES[decision]) if decision else "INGEN AFFÄR",
        "planerad_stop": round(stop, 2) if stop else "", "planerat_mål": round(target, 2) if target else "",
        "pris_efter_4h": "", "resultat_efter_avgift": "", "anteckning": "",
    }
    print("\nRöster:", ", ".join(f"{k}={NAMES[int(v)]}" for k, v in votes.items()))
    print(f"UP {up} / DOWN {dn} / FLAT {n - up - dn} av {n}  →  {row['beslut']}  (pris {price:,.0f})")
    # Senaste röst per vy, för dashboarden.
    LOG.parent.mkdir(exist_ok=True)
    (LOG.parent / "latest_votes.json").write_text(json.dumps(
        {"tid_utc": row["tid_utc"], "votes": {k: int(v) for k, v in votes.items()}}))
    return row


def append(row: dict) -> None:
    LOG.parent.mkdir(exist_ok=True)
    new = not LOG.exists()
    with open(LOG, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)
    print(f"Loggat i {LOG}")


def settle() -> None:
    if not LOG.exists():
        print("Ingen logg än.")
        return
    log = pd.read_csv(LOG, dtype=str).fillna("")
    df = fetch(days=7)  # tål att Macen sovit några dagar
    filled = 0
    for i, r in log.iterrows():
        if r["pris_efter_4h"]:
            continue
        t0 = pd.Timestamp(r["tid_utc"])
        # Facit finns först när candlen 4 h senare är stängd (fetch släpper ofärdiga).
        after = df[df["time"] == t0 + pd.Timedelta(minutes=5 * HORIZON)]
        if after.empty:
            continue
        p1 = float(after["close"].iloc[0])
        log.at[i, "pris_efter_4h"] = f"{p1:.2f}"
        if r["beslut"].startswith("HANDLA"):
            d = 1 if r["beslut"].endswith("UP") else -1
            log.at[i, "resultat_efter_avgift"] = f"{d * (p1 / float(r['pris']) - 1) - FEE_ROUND_TRIP:+.4%}"
        filled += 1
    log.to_csv(LOG, index=False)
    print(f"Fyllde i facit för {filled} rader. Totalt {len(log)} rader i loggen.")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--settle", action="store_true")
    args = p.parse_args()
    if args.settle:
        settle()
    else:
        append(snapshot())


if __name__ == "__main__":
    main()
