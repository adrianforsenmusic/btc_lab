"""Bygger dashboard.html från loggarna — öppna den i webbläsaren för att följa boten.
Byggs om automatiskt efter varje körning (scripts/paper_run.sh) och laddar om sig själv.

Kör:  uv run python -m lab.dashboard && open dashboard.html
"""

from __future__ import annotations

import html
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from lab import LOG_DIR as LOGS, ROOT

OUT = ROOT / os.environ.get("BTCLAB_DASHBOARD", "dashboard.html")
TZ = ZoneInfo("Europe/Stockholm")
# Körschemat: lokalt launchd i svensk tid; online GitHub Actions-cron i UTC.
RUN_TZ = ZoneInfo(os.environ.get("BTCLAB_RUN_TZ", "Europe/Stockholm"))
RUN_HOURS = [int(h) for h in os.environ.get("BTCLAB_RUN_HOURS", "0,4,8,12,16,20").split(",")]

LENS_NAMES = {
    "momentum_1h": "Momentum 1 h", "momentum_4h": "Momentum 4 h", "ema_cross": "EMA-kors",
    "htf_trend_24h": "Trend 24 h", "mean_reversion_z": "Mean reversion", "rsi_extreme": "RSI",
    "range_breakout": "Breakout", "fakeout": "Fakeout", "volume_confirmation": "Volym",
    "volatility_expansion": "Volatilitet", "taker_flow": "Orderflöde", "trend_tstat": "Trendstyrka",
    "wick_rejection": "Veke", "jev_news": "Jev: nyheter",
}
VOTE = {1: ("UP", "up"), -1: ("DOWN", "down"), 0: ("FLAT", "flat")}


def _local(ts: str) -> datetime:
    return pd.Timestamp(ts).tz_convert(TZ).to_pydatetime()


def _sv(t: datetime) -> str:
    days = ["mån", "tis", "ons", "tor", "fre", "lör", "sön"]
    months = ["jan", "feb", "mar", "apr", "maj", "jun", "jul", "aug", "sep", "okt", "nov", "dec"]
    return f"{days[t.weekday()]} {t.day} {months[t.month - 1]} {t:%H:%M}"


def _next_run(now: datetime) -> datetime:
    run_now = now.astimezone(RUN_TZ)
    for d in range(2):
        for h in sorted(RUN_HOURS):
            t = (run_now + timedelta(days=d)).replace(hour=h, minute=2, second=0, microsecond=0)
            if t > run_now:
                return t.astimezone(TZ)
    return now


def _news_scoreboard(log: pd.DataFrame) -> tuple[int, int]:
    """(träffar, antal) för nyhetsvyn när den röstade UP/DOWN och facit finns."""
    hits = n = 0
    for _, r in log.iterrows():
        if r["nyhetsvy"] in ("UP", "DOWN") and r["pris_efter_4h"]:
            n += 1
            up = float(r["pris_efter_4h"]) > float(r["pris"])
            hits += (r["nyhetsvy"] == "UP") == up
    return hits, n


def build() -> Path:
    e = html.escape
    now = datetime.now(TZ)
    log_path = LOGS / "paper_log.csv"
    log = pd.read_csv(log_path, dtype=str).fillna("") if log_path.exists() else pd.DataFrame()

    latest = json.loads((LOGS / "latest_votes.json").read_text()) \
        if (LOGS / "latest_votes.json").exists() else None
    news = None
    news_path = LOGS / "news_judgments.jsonl"
    if news_path.exists():
        lines = news_path.read_text().strip().splitlines()
        news = json.loads(lines[-1]) if lines else None

    # --- Senaste beslut ---
    if len(log):
        last = log.iloc[-1]
        up, dn, fl = int(last["up"]), int(last["down"]), int(last["flat"])
        total = up + dn + fl
        trade = last["beslut"].startswith("HANDLA")
        hero = f"""
        <section class="card hero">
          <div class="eyebrow">Senaste beslut · {_sv(_local(last['tid_utc']))}</div>
          <div class="decision {'trade' if trade else ''}">{e(last['beslut'])}</div>
          <div class="price">BTC {float(last['pris']):,.0f} USDT</div>
          <div class="bar" role="img" aria-label="UP {up}, DOWN {dn}, FLAT {fl} av {total}">
            <span class="up" style="flex:{up}"></span><span class="flat" style="flex:{fl}"></span><span class="down" style="flex:{dn}"></span>
          </div>
          <div class="barlegend"><span>UP {up}</span><span>FLAT {fl}</span><span>DOWN {dn}</span></div>
          <p class="muted">Affär kräver att minst 90 % av vyerna säger samma sak ({-(-total * 9 // 10)} av {total}).</p>
        </section>"""
    else:
        hero = '<section class="card hero"><div class="decision">Inga beslut än</div></section>'

    # --- Vyernas röster ---
    chips = ""
    if latest:
        for k, v in latest["votes"].items():
            label, cls = VOTE[v]
            chips += f'<li class="chip {cls}"><span>{e(LENS_NAMES.get(k, k))}</span><b>{label}</b></li>'
    votes_card = f'<section class="card"><h2>Vyernas röster</h2><ul class="chips">{chips}</ul></section>'

    # --- Jev nyheter ---
    news_rows = ""
    if news:
        js = sorted(news["judgments"],
                    key=lambda j: -j["relevant"] * (1 - j.get("opinion", 0)) * (1 - j.get("recap", 0)))
        for j in js[:6]:
            lean = j["p_bullish"] - j["p_bearish"]
            cls = "up" if lean > 0.2 else "down" if lean < -0.2 else "flat"
            news_rows += (f'<li><span class="lean {cls}">{lean:+.2f}</span>'
                          f'<span class="headline">{e(j["title"])}</span></li>')
        tilt_label, tilt_cls = VOTE[news["vote"]]
        news_head = (f'<div class="eyebrow">Nyhetsvy: <b class="{tilt_cls}">{tilt_label}</b> · '
                     f'lutning {news["tilt"]:+.2f} · {len(news["judgments"])} rubriker</div>')
    else:
        news_head = '<div class="eyebrow">Ingen Jev-körning än</div>'
    news_card = (f'<section class="card"><h2>Jev läser nyheterna</h2>{news_head}'
                 f'<ul class="news">{news_rows}</ul>'
                 f'<p class="muted">De rubriker som väger tyngst. + = positivt för BTC, − = negativt.</p></section>')

    # --- Facit ---
    settled = int((log["pris_efter_4h"] != "").sum()) if len(log) else 0
    trades = log[log["resultat_efter_avgift"] != ""] if len(log) else pd.DataFrame()
    pnl = sum(float(x.rstrip("%")) for x in trades["resultat_efter_avgift"]) if len(trades) else 0.0
    hits, n_news = _news_scoreboard(log) if len(log) else (0, 0)
    news_rate = f"{hits}/{n_news} ({hits / n_news:.0%})" if n_news else "–"
    score_card = f"""
    <section class="card">
      <h2>Facit hittills</h2>
      <dl class="stats">
        <div><dt>Beslut</dt><dd>{len(log)}</dd></div>
        <div><dt>Med facit</dt><dd>{settled}</dd></div>
        <div><dt>Affärer</dt><dd>{len(trades)}</dd></div>
        <div><dt>Resultat</dt><dd>{pnl:+.2f} %</dd></div>
        <div><dt>Jev rätt håll</dt><dd>{news_rate}</dd></div>
      </dl>
      <p class="muted">Jev-träffsäkerheten säger inget förrän den har minst ett par hundra röster. Slumpen ger 50 %.</p>
    </section>"""

    # --- Tabell ---
    trs = ""
    for _, r in log.iloc[::-1].iterrows():
        after = f'{float(r["pris_efter_4h"]):,.0f}' if r["pris_efter_4h"] else "väntar"
        move = ""
        if r["pris_efter_4h"]:
            m = float(r["pris_efter_4h"]) / float(r["pris"]) - 1
            move = f'<span class="{"up" if m > 0 else "down"}">{m:+.2%}</span>'
        trs += (f'<tr><td>{_local(r["tid_utc"]):%d/%m %H:%M}</td><td>{float(r["pris"]):,.0f}</td>'
                f'<td>{r["up"]}/{r["down"]}/{r["flat"]}</td><td>{e(r["nyhetsvy"])}</td>'
                f'<td>{e(r["beslut"])}</td><td>{after}</td><td>{move}</td></tr>')
    table = f"""
    <section class="card wide">
      <h2>Alla beslut</h2>
      <div class="scroll"><table>
        <thead><tr><th>Tid</th><th>Pris</th><th>U/D/F</th><th>Jev</th><th>Beslut</th><th>Efter 4 h</th><th>Rörelse</th></tr></thead>
        <tbody>{trs}</tbody>
      </table></div>
    </section>"""

    page = f"""<!doctype html>
<html lang="sv"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="300">
<title>BTC-labbet</title>
<style>
:root {{ --bg:#f6f7f9; --card:#fff; --text:#15181d; --muted:#667085; --line:#e4e7ec;
  --up:#0f8a4b; --down:#c4321f; --flat:#98a2b3; --accent:#1455c0; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#0e1116; --card:#171b22; --text:#e8eaee;
  --muted:#8b95a7; --line:#262c36; --up:#3ccf82; --down:#ff6b57; --flat:#5b6475; --accent:#6ea0ff; }} }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--text);
  font:15px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
header {{ max-width:1000px; margin:0 auto; padding:24px 16px 8px; display:flex;
  justify-content:space-between; align-items:baseline; flex-wrap:wrap; gap:8px; }}
h1 {{ font-size:20px; margin:0; }} h2 {{ font-size:15px; margin:0 0 12px; }}
main {{ max-width:1000px; margin:0 auto; padding:8px 16px 32px; display:grid;
  grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)); gap:16px; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:18px; min-width:0; }}
.wide {{ grid-column:1 / -1; }}
.eyebrow, .muted {{ color:var(--muted); font-size:13px; }}
.muted {{ margin:12px 0 0; }}
.decision {{ font-size:32px; font-weight:700; margin:6px 0 2px; }}
.decision.trade {{ color:var(--accent); }}
.price {{ font-size:18px; margin-bottom:14px; font-variant-numeric:tabular-nums; }}
.bar {{ display:flex; height:12px; border-radius:6px; overflow:hidden; gap:2px; }}
.bar .up {{ background:var(--up); }} .bar .down {{ background:var(--down); }} .bar .flat {{ background:var(--flat); }}
.barlegend {{ display:flex; justify-content:space-between; font-size:13px; color:var(--muted); margin-top:6px; }}
.chips {{ list-style:none; padding:0; margin:0; display:grid; grid-template-columns:1fr 1fr; gap:6px; }}
.chip {{ display:flex; justify-content:space-between; padding:6px 10px; border-radius:8px;
  border:1px solid var(--line); font-size:13px; }}
.chip b {{ font-size:12px; }}
.up {{ color:var(--up); }} .down {{ color:var(--down); }} .flat {{ color:var(--muted); }}
.news {{ list-style:none; padding:0; margin:10px 0 0; }}
.news li {{ display:flex; gap:10px; padding:7px 0; border-top:1px solid var(--line); font-size:13px; }}
.lean {{ font-variant-numeric:tabular-nums; font-weight:600; min-width:42px; }}
.stats {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(90px, 1fr)); gap:10px; margin:0; }}
.stats dt {{ color:var(--muted); font-size:12px; }} .stats dd {{ margin:0; font-size:20px; font-weight:600; }}
.scroll {{ overflow-x:auto; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; font-variant-numeric:tabular-nums; }}
th, td {{ text-align:left; padding:7px 8px; border-top:1px solid var(--line); white-space:nowrap; }}
th {{ color:var(--muted); font-weight:500; border-top:0; }}
footer {{ text-align:center; color:var(--muted); font-size:12px; padding:0 16px 24px; }}
</style></head>
<body>
<header><h1>BTC-labbet · papperstrading</h1>
<span class="eyebrow">Uppdaterad {now:%H:%M} · nästa körning {_next_run(now):%H:%M} · laddar om var 5:e min</span></header>
<main>{hero}{votes_card}{news_card}{score_card}{table}</main>
<footer>Bara papper — inga riktiga pengar, inga ordrar.</footer>
</body></html>"""
    OUT.write_text(page)
    return OUT


if __name__ == "__main__":
    print(build())
