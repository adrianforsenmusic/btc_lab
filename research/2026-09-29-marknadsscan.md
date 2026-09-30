# Marknadsscan 2026-09-29 — underlag för egen paper-bot

Research, inte råd. Inget här är en rekommendation att köpa eller sälja något.
Allt ska in i labbet som *hypoteser* och mätas ärligt (efter avgift, mot baslinjer).

## 1. Volatila coins just nu (CoinPaprika, topp 250, volym ≥ $5M/24h, stablecoins borttagna)

Sorterat på |24h| + |7d| rörelse. Data hämtad 2026-09-29.

| Rank | Symbol | Namn | 24h % | 7d % | Volym 24h ($M) | Mcap ($M) | Första data |
|---:|---|---|---:|---:|---:|---:|---|
| 41 | QNT | Quant | +16,1 | **+263,6** | 891 | 3 245 | 2018-08 |
| 119 | GRASS | GRASS | +27,7 | +75,4 | 68 | 525 | 2024-12 |
| 135 | TIBBIR | Ribbita by Virtuals | +33,9 | +51,1 | 8 | 394 | 2025-04 |
| 43 | BTW | Bitway | +26,5 | +51,3 | 29 | 3 014 | 2026-03 |
| 117 | NIGHT | Midnight | +15,0 | +35,0 | 33 | 539 | 2025-12 |
| 45 | PUMP | Pump.fun | +19,7 | +28,5 | 268 | 2 704 | 2024-02 |
| 100 | AKE | Akedo | −2,2 | −40,8 | 8 | 696 | 2025-08 |
| 195 | ZBCN | Zebec Network | +19,9 | +21,3 | 11 | 191 | 2025-02 |
| 181 | USELESS | Useless Coin | +1,2 | −31,8 | 36 | 239 | 2025-05 |
| 47 | AAVE | Aave | +13,2 | +14,1 | 620 | 2 567 | 2020-10 |

⚠️ QNT +264 % på 7 dagar för en coin i topp 50 är ovanligt — kontrollera mot en andra
källa innan det används. Låg volym (TIBBIR, AKE, ZBCN ≈ $8–11M) betyder att spread och
slippage äter stora delar av rörelsen — backtest utan det är för optimistiskt.

## 2. Nyast listade i topp 250 (första data efter 2025-09)

| Rank | Symbol | Namn | Första data | 7d % | Volym ($M) | Mcap ($M) |
|---:|---|---|---|---:|---:|---:|
| 233 | DGAI | DGrid AI | 2026-08-25 | −7,9 | 27 | 144 |
| 201 | CASHCAT | Cash Cat | 2026-07-08 | +0,8 | 17 | 178 |
| 199 | EDGE | edgeX | 2026-03-31 | −14,2 | 2 | 183 |
| 43 | BTW | Bitway | 2026-03-02 | +51,3 | 29 | 3 014 |
| 228 | SENT | Sentient | 2026-01-24 | −4,0 | 3 | 148 |
| 20 | RAIN | Rain Protocol | 2026-01-20 | −3,0 | 5 | 9 009 |
| 81 | LIT | Lighter | 2026-01-05 | −9,1 | 60 | 1 120 |
| 117 | NIGHT | Midnight | 2025-12-09 | +35,0 | 33 | 539 |
| 156 | MON | Monad | 2025-11-24 | +0,5 | 17 | 292 |
| 30 | CC | Canton Network | 2025-11-10 | +9,8 | 17 | 4 950 |
| 76 | ASTER | Aster | 2025-09-19 | −0,9 | 83 | 1 199 |

Riktigt nystartade projekt (dagar gamla, DEX/pump.fun) finns inte i topp 250 och har
knappt någon historik att backtesta mot. Där är risken för rug pulls och manipulation
störst — om de ska med behövs en egen "är det här ett bedrägeri?"-grind (se `jev_screen`
/ Noul-frågor nedan) och *mycket* små paper-positioner.

## 3. "Populära traders" — vad som faktiskt går att mäta

Mänskliga influencers och copy-trading-topplistor är dåliga källor: överlevnadsbias
(förlorarna försvinner), betald promotion och inga verifierbara resultat. Jag har därför
inte samlat profiler på personer, utan de mest följda *strategierna* och de enda publika
topplistorna med verifierbara, lika villkor — AI-bottar mot varandra:

**Strategier som nämns mest 2026** ([Trnd Tools][s1], [Trendrider][s2], [Bravos][s3]):
- Trendföljning med glidande medel + momentum (håll vinnare, klipp förlorare).
- Breakout med volymfilter: volym > 1,5 × snittet av de 20 senaste candlarna.
- Altcoin-rotation efter berättelse/sektor (AI-agenter, DeFi-lån, token burns).
- Köp styrka *tidigt* i fortsättningen, inte efter tre stora candlar i rad.

→ Trend, breakout och volym finns redan som lenses i `lab/lenses.py` och hade ingen
fördel på BTC 4 h efter avgift. Rotation/berättelser är *ny* — och är något Jev kan bedöma.

**AI-bottar i livetävlingar:**
- [TradeRank][s4] (paper, $10k, identiska regler): säsongen från 13 sep — **1 av 18
  modeller slår att bara hålla BTC**. Historiskt: 56 modeller, 9 säsonger, bara 46 %
  av modell-säsongerna slutade med vinst. "No model wins consistently."
- Alpha Arena (nof1, [via TradeRank][s7]): riktiga $10k per modell på krypto-perps sedan okt 2025.
- [Agent Market Arena][s5] (forskning, livehandel): *ramverket* runt modellen (risk-stil,
  minne) förklarade mer av utfallet än vilken modell som satt i botten.
- [Studie, 6 mån produktion][s6]: ingen riktningsfördel efter avgift; 49 % av positioner
  som var +3 % inom 24 h stängdes ändå med förlust; en enkel bracket (fast take-profit/
  stop-loss) gav +39 bps per position. **Mekanik (storlek, risk, exit) betydde mer än
  vilken modell som användes.**

## 4. Andras paper-/Jev-bottar på GitHub

| Repo | ★ | Licens | Vad det är | Värt att låna |
|---|---:|---|---|---|
| [buberlo/jev-trader][g1] | 34 | MIT | Market making, 6 Jev-bedömningar per block, hårda risk-veton, kalibreringslogg | Arkitekturen: *kod räknar, Jev tolkar, kod bestämmer, veto kan aldrig delegeras*. Brier/ECE-kalibrering av Jevs sannolikheter. |
| [TauricResearch/TradingAgents][g2] | – | – | Multi-agent-trading; `post_screen.py` sållar sociala inlägg med Jev | Två frågor per inlägg: Noul "handlar det om X?" + Choice bullish/bearish/neutral. Direkt tillämpbart på `jev_news.py` för X/Reddit. |
| [tdg88gmdzs-svg/crypto-paperbot][g3] | 0 | – | Ärlig paper-bot BTC/ETH | Samma slutsats som btc_lab: trend −54 %, mean reversion −94 % vs hålla −10 % efter 0,26 % avgift. |
| [CharlieChenyuZhang/jev-trading][g4] | 1 | ingen | Jev Choice/Score/Noul-batteri per marknad | Frågedesign med rörelsezoner i bps som Choice-alternativ. |
| [AshrithSathu/aitrade-paper][g5] | 0 | MIT | Jev-styrd paper-trading på Polymarket | Prediction markets som alternativ arena. |
| [virattt/ai-hedge-fund][g6] | – | – | Stor LLM-hedgefond-demo med TypeSafe-klient | Hur Jev kopplas in som en av flera LLM-leverantörer. |
| [tradermonty/claude-trading-agent][g7] | 11 | ingen | Claude Managed Agents + 10 analys-skills | Idéer för analysverktyg, inte för beslut. |

Repon utan licens får läsas men inte kopieras rakt in.

## 5. Förslag på nästa experiment i btc_lab (alla bara papper)

1. **Bracket-exit** (take-profit/stop-loss) i `paper.py` och backtest — billigaste
   förbättringen enligt studien ovan. Sätt nivåerna i förväg.
2. **Kalibreringslogg à la jev-trader:** logga (state, Jev-svar, utfall) och räkna Brier
   score, så vi ser om Jevs 0,7 faktiskt betyder 70 %.
3. **Social-sållning à la TradingAgents** som ny källa till nyhetsvyn.
4. **Altcoin-universum:** kör samma ärliga backtest på 3–5 likvida volatila coins från
   tabell 1 (volym > $50M). Volatilare = större rörelser i förhållande till avgiften, men
   också större risk. Mät, anta inget.
5. **Scam-/pump-grind med Jev** innan en ny coin ens får komma in i universumet.

[s1]: https://trndtools.com/blog/top-crypto-trading-strategies-for-2026
[s2]: https://trendrider.net/blog/crypto-momentum-trading-strategies-2026
[s3]: https://bravosresearch.com/blog/cryptocurrency/profitable-crypto-trading-strategies/
[s4]: https://www.traderank.ai/llm-trading-benchmark
[s5]: https://www.alphaxiv.org/overview/2510.11695v1
[s6]: https://arxiv.org/abs/2609.05663
[s7]: https://www.traderank.ai/best-llm-for-trading
[g1]: https://github.com/buberlo/jev-trader
[g2]: https://github.com/TauricResearch/TradingAgents
[g3]: https://github.com/tdg88gmdzs-svg/crypto-paperbot
[g4]: https://github.com/CharlieChenyuZhang/jev-trading
[g5]: https://github.com/AshrithSathu/aitrade-paper
[g6]: https://github.com/virattt/ai-hedge-fund
[g7]: https://github.com/tradermonty/claude-trading-agent
