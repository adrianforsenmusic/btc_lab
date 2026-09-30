"""Deterministiska "vyer" (lenses) över candles — samma idé som de 31 vyerna i
konsensus-prompten, men uträknade i kod så att de kan backtestas på tusentals punkter
gratis och utan att modellen "minns" vad som hände.

Varje lens tittar BARA på candles fram till och med index i (aldrig framåt) och röstar
+1 (UP), -1 (DOWN) eller 0 (FLAT). Trösklarna är satta i förväg, inte optimerade på
datan — annars blir backtestet för bra.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

UP, DOWN, FLAT = 1, -1, 0


def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def _sign_band(x: pd.Series, band: float) -> pd.Series:
    """+1 om x > band, -1 om x < -band, annars 0. NaN → 0."""
    out = np.where(x > band, UP, np.where(x < -band, DOWN, FLAT))
    return pd.Series(out, index=x.index).where(x.notna(), FLAT).astype(int)


def compute_lenses(df: pd.DataFrame) -> pd.DataFrame:
    """Returnerar en DataFrame med en kolumn per lens, värden -1/0/+1."""
    c, h, l, o, v = df["close"], df["high"], df["low"], df["open"], df["volume"]
    ret_12 = c / c.shift(12) - 1   # senaste timmen
    ret_48 = c / c.shift(48) - 1   # senaste 4 h
    out: dict[str, pd.Series] = {}

    # 1 Momentum 1 h
    out["momentum_1h"] = _sign_band(ret_12, 0.003)
    # 2 Momentum 4 h
    out["momentum_4h"] = _sign_band(ret_48, 0.008)
    # 3 EMA-kors (1 h mot 4 h)
    out["ema_cross"] = _sign_band(_ema(c, 12) / _ema(c, 48) - 1, 0.001)
    # 4 Högre tidsram: pris mot 24 h-EMA
    out["htf_trend_24h"] = _sign_band(c / _ema(c, 288) - 1, 0.005)

    # 5 Mean reversion: z-score mot 4 h-snitt (hög z → förvänta nedgång)
    mean48, std48 = c.rolling(48).mean(), c.rolling(48).std()
    out["mean_reversion_z"] = -_sign_band((c - mean48) / std48, 2.0)

    # 6 RSI 14 (överköpt → ner, översåld → upp)
    delta = c.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rsi = 100 - 100 / (1 + gain / loss)
    out["rsi_extreme"] = pd.Series(
        np.where(rsi > 70, DOWN, np.where(rsi < 30, UP, FLAT)), index=c.index
    ).astype(int)

    # 7 Breakout ur 4 h-range
    prev_high = h.shift(1).rolling(48).max()
    prev_low = l.shift(1).rolling(48).min()
    out["range_breakout"] = pd.Series(
        np.where(c > prev_high, UP, np.where(c < prev_low, DOWN, FLAT)), index=c.index
    ).astype(int)

    # 8 Fakeout: bröt range senaste 6 barerna men är tillbaka innanför → motsatt håll
    broke_up = (h.rolling(6).max() > prev_high.shift(6)) & (c < prev_high.shift(6))
    broke_dn = (l.rolling(6).min() < prev_low.shift(6)) & (c > prev_low.shift(6))
    out["fakeout"] = pd.Series(
        np.where(broke_up & ~broke_dn, DOWN, np.where(broke_dn & ~broke_up, UP, FLAT)),
        index=c.index,
    ).astype(int)

    # 9 Volymbekräftelse: timmens riktning, bara om volymen är klart över dygnssnittet
    vol_ratio = v.rolling(12).mean() / v.rolling(288).mean()
    out["volume_confirmation"] = _sign_band(ret_12, 0.001).where(vol_ratio > 1.5, FLAT)

    # 10 Volatilitetsexpansion: timmens riktning när ATR 1 h > 1,5× ATR 24 h
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr_ratio = tr.rolling(12).mean() / tr.rolling(288).mean()
    out["volatility_expansion"] = _sign_band(ret_12, 0.001).where(atr_ratio > 1.5, FLAT)

    # 11 Orderflöde: andel köparinitierad volym senaste timmen
    taker_ratio = df["taker_buy_base"].rolling(12).sum() / v.rolling(12).sum()
    out["taker_flow"] = _sign_band(taker_ratio - 0.5, 0.05)

    # 12 Trendstyrka: t-värde för lutningen över 2 h
    x = np.arange(24) - 11.5
    slope = c.rolling(24).apply(lambda y: np.dot(x, y) / np.dot(x, x), raw=True)
    resid_std = c.rolling(24).std()
    out["trend_tstat"] = _sign_band(slope * 24 / resid_std, 2.0)

    # 13 Likviditetssvep: sista barens lång veke (avvisning) → motsatt håll
    body = (c - o).abs()
    lower_wick = np.minimum(o, c) - l
    upper_wick = h - np.maximum(o, c)
    big = 0.003 * c
    out["wick_rejection"] = pd.Series(
        np.where((lower_wick > 2 * body) & (lower_wick > big), UP,
                 np.where((upper_wick > 2 * body) & (upper_wick > big), DOWN, FLAT)),
        index=c.index,
    ).astype(int)

    return pd.DataFrame(out)
