"""Ärligt backtest av konsensus-metoden: handla bara när nästan alla vyer håller med.

Frågan vi svarar på: slår konsensusregeln "stå utanför" och "slumpmässiga affärer"
EFTER avgifter? Om inte — ingen poäng att riskera riktiga pengar.

Kör:  uv run python -m lab.backtest
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from lab.data import load
from lab.lenses import compute_lenses

HORIZON = 48            # 48 × 5 min = 4 h hålltid
FEE_ROUND_TRIP = 0.002  # 0,1 % in + 0,1 % ut (Binance spot, taker, utan rabatt)
WARMUP = 300            # lenses behöver 24 h historik
CONSENSUS = 28 / 31     # samma tröskel som i ursprungsmetoden (≈ 90 %)


def decide(votes: pd.DataFrame, threshold: float) -> pd.Series:
    """+1/-1 om andelen UP/DOWN av ALLA vyer ≥ threshold, annars 0 (FLAT)."""
    n = votes.shape[1]
    up = (votes == 1).sum(axis=1) / n
    dn = (votes == -1).sum(axis=1) / n
    return pd.Series(np.where(up >= threshold, 1, np.where(dn >= threshold, -1, 0)),
                     index=votes.index)


def stats(pnl: np.ndarray) -> dict:
    """Nyckeltal för en lista med avslutade affärer (avkastning per affär, efter avgift)."""
    if len(pnl) == 0:
        return {"affärer": 0, "träffsäkerhet": np.nan, "före avgift": np.nan,
                "snitt/affär": np.nan, "total": 0.0, "kvarts_kelly": 0.0}
    wins, losses = pnl[pnl > 0], pnl[pnl <= 0]
    p = len(wins) / len(pnl)
    kelly = 0.0
    if len(wins) and len(losses):
        b = wins.mean() / -losses.mean()          # vinst/förlust-kvot
        kelly = max(0.0, (p * b - (1 - p)) / b) / 4
    return {
        "affärer": len(pnl),
        "träffsäkerhet": p,
        "före avgift": pnl.mean() + FEE_ROUND_TRIP,
        "snitt/affär": pnl.mean(),
        "total": float(np.prod(1 + pnl) - 1),
        "kvarts_kelly": kelly,
    }


def run(step: int, threshold: float, seed: int = 7) -> None:
    df = load()
    votes = compute_lenses(df)
    fwd = df["close"].shift(-HORIZON) / df["close"] - 1   # FRAMTIDEN — bara för facit

    # Beslutspunkter var `step`:e bar, utan överlapp när step ≥ HORIZON.
    idx = np.arange(WARMUP, len(df) - HORIZON, step)
    v, f = votes.iloc[idx], fwd.iloc[idx].to_numpy()
    decision = decide(v, threshold).to_numpy()

    def pnl_for(dirs: np.ndarray) -> np.ndarray:
        m = dirs != 0
        return dirs[m] * f[m] - FEE_ROUND_TRIP

    days = (df["time"].iloc[idx[-1]] - df["time"].iloc[idx[0]]).days
    print(f"\nPeriod: {df['time'].iloc[idx[0]]:%Y-%m-%d} → {df['time'].iloc[idx[-1]]:%Y-%m-%d} "
          f"({days} dagar), {len(idx)} beslutspunkter, var {step * 5} min, "
          f"hålltid {HORIZON * 5 // 60} h, avgift {FEE_ROUND_TRIP:.1%} tur och retur")
    print(f"Antal vyer: {votes.shape[1]}. Konsensuströskel: {threshold:.0%}\n")

    rows = {}
    rows["KONSENSUS"] = stats(pnl_for(decision))
    rows["Stå utanför"] = stats(np.array([]))
    rows["Alltid köp (long)"] = stats(pnl_for(np.ones_like(decision)))

    # Slump med samma antal affärer som konsensus: vilken percentil hamnar konsensus på?
    n_trades = int((decision != 0).sum())
    rng = np.random.default_rng(seed)
    rand_means = []
    if n_trades:
        for _ in range(2000):
            dirs = np.zeros_like(decision)
            pick = rng.choice(len(decision), n_trades, replace=False)
            dirs[pick] = rng.choice([-1, 1], n_trades)
            rand_means.append(pnl_for(dirs).mean())
        rows[f"Slump ({n_trades} affärer, median av 2000)"] = {
            **stats(np.array([np.median(rand_means)])),
            "affärer": n_trades, "träffsäkerhet": np.nan, "före avgift": np.nan,
            "total": np.nan, "kvarts_kelly": np.nan,
        }

    # Varje enskild vy som egen strategi.
    for name in votes.columns:
        rows[f"  vy: {name}"] = stats(pnl_for(v[name].to_numpy()))

    table = pd.DataFrame(rows).T
    fmt = {"träffsäkerhet": "{:.1%}", "före avgift": "{:+.3%}", "snitt/affär": "{:+.3%}", "total": "{:+.1%}",
           "kvarts_kelly": "{:.1%}", "affärer": "{:.0f}"}
    for col, f_ in fmt.items():
        table[col] = table[col].map(lambda x, f_=f_: "–" if pd.isna(x) else f_.format(x))
    print(table.to_string())

    if n_trades and rand_means:
        pct = (np.array(rand_means) < rows["KONSENSUS"]["snitt/affär"]).mean()
        print(f"\nKonsensus slår {pct:.0%} av slumpmässiga strategier med lika många affärer.")
        print("(Under ~95 % går det inte att skilja från tur.)")

    # Hur "oberoende" är vyerna egentligen?
    active = v.replace(0, np.nan)
    corr = active.corr(min_periods=20).abs().to_numpy(copy=True)
    np.fill_diagonal(corr, np.nan)
    print(f"\nSnittkorrelation mellan vyernas röster (när båda röstar): "
          f"{np.nanmean(corr):.2f}  (0 = oberoende, 1 = alltid samma eller alltid motsatt)")
    agree = (v != 0).sum(axis=1)
    print(f"Vyer som inte röstar FLAT, i snitt per beslutspunkt: {agree.mean():.1f} av {v.shape[1]}")

    # Vad händer om man sänker kravet? (Bara för insyn — välj inte tröskel härifrån,
    # då har man anpassat regeln efter facit.)
    print("\nTröskel  affärer  träffsäkerhet  snitt/affär")
    for thr in [0.9, 0.7, 0.5, 0.4, 0.3, 0.2]:
        s = stats(pnl_for(decide(v, thr).to_numpy()))
        if s["affärer"]:
            print(f"  {thr:>4.0%}  {s['affärer']:>7}  {s['träffsäkerhet']:>12.1%}  "
                  f"{s['snitt/affär']:>+10.3%}")
        else:
            print(f"  {thr:>4.0%}  {0:>7}")

    # Stabilitet: samma sak på första och andra halvan.
    half = len(idx) // 2
    for label, sl in [("första halvan", slice(0, half)), ("andra halvan", slice(half, None))]:
        d, ff = decision[sl], f[sl]
        m = d != 0
        s = stats(d[m] * ff[m] - FEE_ROUND_TRIP)
        mean = s["snitt/affär"]
        mean_txt = "–" if pd.isna(mean) else f"{mean:+.3%}"
        print(f"Konsensus {label}: {s['affärer']} affärer, snitt/affär {mean_txt}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--step", type=int, default=HORIZON,
                   help="bars mellan beslut (48 = var 4:e timme, inga överlappande affärer)")
    p.add_argument("--threshold", type=float, default=CONSENSUS)
    args = p.parse_args()
    run(args.step, args.threshold)


if __name__ == "__main__":
    main()
