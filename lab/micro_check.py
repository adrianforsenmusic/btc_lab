"""Går mikrotrading ihop? Mäter hur stora BTC-rörelserna är på korta hålltider jämfört
med avgiften, och om någon vy har fördel FÖRE avgift på varje hålltid.

Kör:  uv run python -m lab.micro_check
"""

from __future__ import annotations

import numpy as np

from lab.backtest import FEE_ROUND_TRIP, WARMUP
from lab.data import load
from lab.lenses import compute_lenses

HORIZONS = {"5 min": 1, "15 min": 3, "1 h": 12, "4 h": 48}


def main() -> None:
    df = load()
    votes = compute_lenses(df)
    print(f"Avgift tur och retur: {FEE_ROUND_TRIP:.2%}\n")
    print(f"{'hålltid':>8} {'median rörelse':>15} {'rörelser > avgift':>18} "
          f"{'bästa vy före avgift':>22}  {'snitt alla vyer':>15}")
    for label, h in HORIZONS.items():
        fwd = (df["close"].shift(-h) / df["close"] - 1).to_numpy()
        idx = np.arange(WARMUP, len(df) - h, h)       # inga överlappande affärer
        f = fwd[idx]
        med = np.median(np.abs(f))
        share = (np.abs(f) > FEE_ROUND_TRIP).mean()
        edges = {}
        for name in votes.columns:
            d = votes[name].to_numpy()[idx]
            m = d != 0
            if m.sum() >= 30:
                edges[name] = (d[m] * f[m]).mean()
        best = max(edges, key=edges.get)
        print(f"{label:>8} {med:>14.3%} {share:>17.0%} "
              f"{edges[best]:>+13.3%} ({best[:14]}) {np.mean(list(edges.values())):>+13.3%}")


if __name__ == "__main__":
    main()
