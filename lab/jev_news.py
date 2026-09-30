"""Nyhetsvyn: Jev (TypeSafe) bedömer färska krypto-rubriker.

Varför Jev här och inte på candles: Jev är bra på språklig bedömning men dålig på
siffror (enligt TypeSafes egen dokumentation). All matte — indikatorer, trösklar,
sammanvägning — ligger därför i kod. Jev får bara det som faktiskt är en tolkning:
"vad betyder den här rubriken för Bitcoin?".

Det finns inget gratis nyhetsarkiv att backtesta mot. Därför loggas varje bedömning
(logs/news_judgments.jsonl) så att nyhetsvyn kan utvärderas i efterhand mot vad
priset faktiskt gjorde.

Kör:  uv run python -m lab.jev_news          (kräver TYPESAFE_API_KEY i .env)
      uv run python -m lab.jev_news --dry-run (visar bara rubrikerna och frågorna)
"""

from __future__ import annotations

import argparse
import json
import os
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import httpx

from lab import LOG_DIR, ROOT

FEEDS = {
    "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "cointelegraph": "https://cointelegraph.com/rss",
    "decrypt": "https://decrypt.co/feed",
}

# Nyhetsvyn röstar bara om sammanvägd lutning är tydlig. Satt i förväg, inte optimerad
# mot prisutfall (justerad 2026-09-29 efter manuell granskning, innan något facit fanns).
VOTE_BAND = 0.3
# Bara rubriker som tydligt är en ny, relevant händelse räknas alls (se Judgment.newsworthy).
NEWSWORTHY_MIN = 0.3


@dataclass
class Headline:
    source: str
    title: str
    summary: str
    published: datetime


@dataclass
class Judgment:
    title: str
    source: str
    published: str
    relevant: float          # Noul: P(rubriken kan röra BTC-priset inom timmar)
    p_bullish: float
    p_bearish: float
    p_neutral: float
    direction_confidence: float
    impact: float            # Score 0–2 (rutin / märkbar / stor)
    opinion: float           # Noul: åsikt/prognos snarare än ny händelse
    recap: float             # Noul: beskriver prisrörelse som redan hänt
    model: str
    input_tokens: int = 0

    @property
    def newsworthy(self) -> float:
        """Relevant OCH en ny händelse — inte en åsikt, inte en efterhandsrapport."""
        return self.relevant * (1 - self.opinion) * (1 - self.recap)


def load_env() -> None:
    """Minimal .env-läsare så att nyckeln aldrig behöver stå i koden."""
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


def _strip_html(text: str) -> str:
    import re
    return re.sub(r"<[^>]+>", " ", text or "").replace("&nbsp;", " ").strip()[:400]


def fetch_headlines(hours: int = 12) -> list[Headline]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    out: list[Headline] = []
    seen: set[str] = set()
    with httpx.Client(timeout=15, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0 btc_lab"}) as client:
        for source, url in FEEDS.items():
            try:
                root = ET.fromstring(client.get(url).content)
            except Exception as e:  # ett trasigt flöde ska inte stoppa resten
                print(f"  [varning] {source}: {e}")
                continue
            for item in root.iter("item"):
                title = (item.findtext("title") or "").strip()
                pub = item.findtext("pubDate")
                if not title or not pub or title.lower() in seen:
                    continue
                published = parsedate_to_datetime(pub).astimezone(timezone.utc)
                if published < cutoff:
                    continue
                seen.add(title.lower())
                out.append(Headline(source, title,
                                    _strip_html(item.findtext("description") or ""), published))
    return sorted(out, key=lambda h: h.published, reverse=True)


def questions():
    from typesafe_sdk import Choice, Noul, Score
    return {
        "relevant": Noul(
            instructions=(
                "Does `headline` report news that could plausibly move the price of "
                "Bitcoin within the next few hours? Opinion pieces, price recaps of moves "
                "that already happened, sponsored content and news about unrelated small "
                "tokens count as no."
            ),
        ),
        "direction": Choice(
            instructions=(
                "If traders react to `headline` in the next few hours, which way would it "
                "push the price of Bitcoin?"
            ),
            criteria={
                "bullish": "More demand for Bitcoin: e.g. inflows, adoption, easing "
                           "regulation, rate cuts, a large buyer.",
                "bearish": "Less demand or forced selling: e.g. outflows, hacks, bans, "
                           "enforcement, liquidations, a large seller.",
                "neutral": "No clear push either way, mixed, or not about Bitcoin.",
            },
        ),
        "impact": Score(
            instructions="How large a market event does `headline` describe for Bitcoin?",
            criteria=[
                "Routine: everyday commentary, small partnerships, analyst opinions.",
                "Notable: a meaningful but ordinary event, e.g. a mid-sized fund flow or "
                "a regulator statement.",
                "Major: an event that historically moves the whole crypto market, e.g. "
                "ETF approval or rejection, a top exchange hack or collapse, a national ban.",
            ],
        ),
        "opinion": Noul(
            instructions=(
                "Is `headline` mainly someone's opinion, forecast or price prediction, "
                "rather than a report that a new event has happened?"
            ),
        ),
        "recap": Noul(
            instructions=(
                "Is `headline` mainly describing price moves or market conditions that have "
                "already happened, rather than reporting a new event that could cause a move?"
            ),
        ),
    }


def judge(headlines: list[Headline]) -> list[Judgment]:
    from typesafe_sdk import TypeSafeClient

    qs = questions()
    out: list[Judgment] = []
    # En request per rubrik: liten state = bättre träffsäkerhet (Jev tappar av brus).
    with TypeSafeClient() as client:
        for h in headlines:
            r = client.system_one(
                state={"headline": {"title": h.title, "summary": h.summary,
                                    "source": h.source}},
                questions=qs,
            )
            d = r.choices["direction"]
            out.append(Judgment(
                title=h.title, source=h.source, published=h.published.isoformat(),
                relevant=r.nouls["relevant"].noul,
                p_bullish=d.probabilities.get("bullish", 0.0),
                p_bearish=d.probabilities.get("bearish", 0.0),
                p_neutral=d.probabilities.get("neutral", 0.0),
                direction_confidence=d.confidence,
                impact=r.scores["impact"].score,
                opinion=r.nouls["opinion"].noul,
                recap=r.nouls["recap"].noul,
                model=r.model,
                input_tokens=r.usage.input_tokens,
            ))
    return out


def news_vote(judgments: list[Judgment]) -> tuple[int, float]:
    """Sammanväger bedömningarna i KOD. Returnerar (röst -1/0/+1, lutning).

    Rubriker under NEWSWORTHY_MIN (åsikter, efterhandsrapporter, irrelevant) räknas inte.
    Lutningen är ett viktat SNITT av (P(bullish) − P(bearish)), där vikten är
    nyhetsvärde × impact (rutin 0,5 → stor 2,0). Snitt, inte summa: annars röstar vyn
    bara för att det är en pratig dag. "+1" i nämnaren drar mot 0 när det finns få
    riktiga nyheter. Tydlig lutning krävs för att rösta.
    """
    num = den = 0.0
    for j in judgments:
        if j.newsworthy < NEWSWORTHY_MIN:
            continue
        w = j.newsworthy * (0.5 + 0.75 * j.impact)
        num += w * (j.p_bullish - j.p_bearish)
        den += w
    tilt = num / (den + 1.0)
    vote = 1 if tilt > VOTE_BAND else -1 if tilt < -VOTE_BAND else 0
    return vote, tilt


def log_judgments(judgments: list[Judgment], vote: int, tilt: float) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    with open(LOG_DIR / "news_judgments.jsonl", "a") as f:
        f.write(json.dumps({"at": now, "vote": vote, "tilt": tilt,
                            "judgments": [asdict(j) for j in judgments]},
                           ensure_ascii=False) + "\n")


def run_news_lens(hours: int = 12, verbose: bool = True) -> tuple[int, float] | None:
    """Returnerar (röst, lutning), eller None om ingen nyckel finns."""
    load_env()
    if not os.environ.get("TYPESAFE_API_KEY"):
        if verbose:
            print("Jev: ingen TYPESAFE_API_KEY i .env — nyhetsvyn hoppas över.")
        return None
    headlines = fetch_headlines(hours)
    judgments = judge(headlines)
    vote, tilt = news_vote(judgments)
    log_judgments(judgments, vote, tilt)
    if verbose:
        print("  nyhet  rel   åsikt recap  lutning impact  rubrik")
        for j in sorted(judgments, key=lambda j: -j.newsworthy):
            lean = j.p_bullish - j.p_bearish
            print(f"  {j.newsworthy:.2f}  {j.relevant:.2f}  {j.opinion:.2f}  {j.recap:.2f}  "
                  f"{lean:+.2f}   {j.impact:.1f}    {j.title[:70]}")
        tokens = sum(j.input_tokens for j in judgments)
        print(f"Nyhetsvy: {({1: 'UP', -1: 'DOWN', 0: 'FLAT'})[vote]} "
              f"(lutning {tilt:+.2f}, {len(judgments)} rubriker, "
              f"modell {judgments[0].model if judgments else '–'}, "
              f"{tokens} tokens ≈ ${tokens * 0.042 / 1e6:.5f})")
    return vote, tilt


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--hours", type=int, default=12)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    if args.dry_run:
        hs = fetch_headlines(args.hours)
        print(f"{len(hs)} rubriker senaste {args.hours} h:")
        for h in hs:
            print(f"  {h.published:%H:%M} {h.source:13} {h.title[:90]}")
        print("\nFrågor som skickas till Jev per rubrik:")
        for k, q in questions().items():
            print(f"  {k}: {q.type}")
        return
    run_news_lens(args.hours)


if __name__ == "__main__":
    main()
