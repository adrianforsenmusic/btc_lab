# btc_lab — handoff till Claude Code

## Vem du jobbar med
Användaren är INTE utvecklare. Svenska genomgående.
Ett steg i taget, gör allt själv i terminalen, förklara kort och konkret.
(Parkeringsappen är ett separat projekt i ~/development/parking_app — blanda inte ihop.)

## Vad det här är
Ett forskningslabb för en BTC-"konsensus"-idé som Adrian hittade i ett socialt medie-inlägg:
flera oberoende vyer över BTC 5-min-candles → handla bara om ≥ 28/31 håller med →
kvarts-Kelly. Labbet ska ÄRLIGT mäta om det har någon fördel innan en krona riskeras.

## Hårda regler
- **Bara papper.** Ingen börs-API-nyckel, inga ordrar, ingen riktig handel från den här koden.
  Riktiga affärer är Adrians eget beslut och görs av honom själv. Ge ingen personlig
  investeringsrådgivning.
- Låtsas aldrig att något fungerar. Mät mot baslinjer ("stå utanför", slump med lika många
  affärer) EFTER avgifter.
- Trösklar sätts i förväg, optimeras inte på facit. Tröskelsvepet i backtestet är bara insyn.
- Lenses får aldrig titta framåt — `test_lenses_never_look_ahead` vaktar det.
- LLM-vyer (Claude/Jev) på historisk data före modellens träningsgräns är förorenade
  (modellen kan "minnas" utfallet). Utvärdera LLM-/Jev-vyer bara framåt i tiden.

## Stack
Python 3.12 via uv. `uv run ...` för allt.
- `lab/data.py` — Binance publika klines (ingen nyckel), cache i `data/BTCUSDT_5m.csv`.
- `lab/lenses.py` — 13 deterministiska vyer (momentum, mean reversion, RSI, breakout,
  fakeout, volym, volatilitet, orderflöde, trend-t, veke), röstar -1/0/+1.
- `lab/backtest.py` — beslut var 4:e h, 4 h hålltid, 0,2 % avgift tur och retur, jämför
  mot baslinjer, slump-percentil, korrelation mellan vyer, halvårsstabilitet.
- `lab/jev_news.py` — TypeSafe **Jev** bedömer krypto-rubriker (RSS: CoinDesk,
  Cointelegraph, Decrypt): Noul relevans, Choice bullish/bearish/neutral, Score impact.
  Sammanvägning i KOD (`news_vote`). Varje bedömning loggas i `logs/news_judgments.jsonl`.
  Jev är dålig på siffror (TypeSafes egna docs) → candles/indikatorer stannar i kod.
- `lab/paper.py` — ett papperbeslut nu → `logs/paper_log.csv`; `--settle` fyller i facit.
- `tests/test_lab.py` — `uv run pytest`.
- TypeSafe-skillen (plugin `typesafe@typesafe-ai`) är installerad; läs live-docs
  (https://docs.typesafe.ai/llms.txt) innan Jev-kod ändras.
- Nyckel: `.env` med `TYPESAFE_API_KEY=` (finns lokalt, aldrig i git). `.env`, `data/`, `logs/` är gitignorerade.

## Kommandon
```
uv run python -m lab.data --days 180   # hämta/uppdatera candles
uv run python -m lab.backtest          # ärligt backtest
uv run python -m lab.jev_news --dry-run
uv run python -m lab.paper             # ett papperbeslut
uv run python -m lab.paper --settle    # fyll i facit efter 4 h
```

## Status — 2026-09-29
**Första backtestet (178 dagar, 2026-04-03 → 2026-09-29, 1073 beslutspunkter):**
- Konsensus vid 90 % (28/31-regeln): **0 affärer**. Vyerna håller nästan aldrig med
  varandra — i snitt röstar bara 3,3 av 13 något annat än FLAT.
- Ingen enskild vy har fördel ens FÖRE avgift (alla runt 0 %, flera negativa per 4 h).
  Efter 0,2 % avgift förlorar alla. Kvarts-Kelly = 0 % för alla.
- Även med sänkt tröskel (50 %, 40 %, 30 %) är snittet negativt efter avgift.
- Slutsats hittills: den tekniska delen av metoden har ingen mätbar fördel på 4 h.
  Det betyder inte att nyhetsvyn saknar värde — den är obeprövad.

**Jev-nyhetsvyn — körd mot riktiga Jev 2026-09-29 (jev-1.13.0), fungerar tekniskt:**
- 26 rubriker ≈ 18 000 input-tokens ≈ $0,0008 per körning (uppmätt).
- Första körningen avslöjade två designfel (rättade INNAN något prisfacit fanns):
  (1) åsikter/prognoser ("BTC $600K by 2029") och efterhandsrapporter ("Bitcoin holds
  $83K") räknades som nyheter → nya Nouls `opinion` och `recap`, och bara rubriker med
  nyhetsvärde ≥ 0,3 räknas. (2) lutningen var en SUMMA → en pratig dag gav röst av
  ren volym; nu viktat snitt med krympning mot 0.
- Känd miss: "Democrats killed the Clarity Act" fick relevans 0,02 och åsikt 0,92 —
  fel, en stoppad amerikansk kryptolag är relevant. Kryptisk rubrik utan sammanfattning
  → Jev läser bokstavligt (dokumenterad svaghet). Inte åtgärdat; håll utkik efter fler.
- Sammanvägningen testad (7 tester gröna). Om nyhetsvyn FÖRUTSÄGER något är helt okänt.

**Papperstrading-boten igång sedan 2026-09-29 (verifierad med en körning via launchd, exit 0):**
- `scripts/paper_run.sh` körs av launchd kl 00:02, 04:02, 08:02, 12:02, 16:02, 20:02
  (lokal tid): först `--settle`, sen ett nytt beslut. Utskrift → `logs/paper_run.log`.
- Installerad som `~/Library/LaunchAgents/com.adrianforsen.btclab.paper.plist`
  (källa i `scripts/`). Stoppa: `launchctl bootout gui/$(id -u)/com.adrianforsen.btclab.paper`
- Kör bara när Macen är vaken; en missad körning tas igen när den vaknar (bara en).
- Med 14 vyer kräver 90 %-regeln 13 av 14 → den kommer nästan aldrig handla. Det är
  metodens regel, inte en bugg. `pris_efter_4h` fylls i för ALLA rader, så nyhetsvyn kan
  utvärderas mot prisrörelsen även utan affärer.
- Nästa steg: efter några veckor (flera hundra rader, inte 30) — utvärdera om
  nyhetsvyns UP/DOWN stämmer med `pris_efter_4h` oftare än slumpen.

**Online-versionen (GitHub Actions) — tillagd 2026-09-30:**
- `.github/workflows/paper-bot.yml` kör samma kod var 4:e h (cron i UTC), även när Macen sover.
- Loggar i `online/logs/` (committas av boten), dashboard i `docs/index.html` → GitHub Pages.
  Hålls isär från den lokala boten via `BTCLAB_LOG_DIR` / `BTCLAB_DASHBOARD` (se `lab/__init__.py`).
- Prisdata från `data-api.binance.vision` (api.binance.com blockerar GitHubs amerikanska IP).
- Enda hemligheten: repo-secret `TYPESAFE_API_KEY`. Kör manuellt: `gh workflow run paper-bot.yml`.
