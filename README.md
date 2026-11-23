# Market Regime Detection System
### EURUSD H1 · K-means + Gaussian HMM · 12 real MT5 strategies · walk-forward allocation

A self-contained Jupyter notebook that builds a market-regime research pipeline from scratch and
then tries to break its own conclusions. It is written to be read, re-run, and modified — every
number is computed, and every modelling choice is exposed as a parameter.

**Start here:** open [`market_regime_detection.ipynb`](market_regime_detection.ipynb) and run it
top to bottom. It takes ~1–3 minutes on an idle machine and needs only the two CSV files in
`data/`.

---

## What you will learn

| Part | Concept | Output |
|---|---|---|
| 1 | OHLCV hygiene, log returns, stylized facts | data audit, ACF/QQ plots |
| 2 | Volatility, ATR, ADX, trend R², efficiency ratio | feature matrix, scaling |
| 3 | K-means clustering, k-selection, stability (ARI) | regime timeline, transition matrix |
| 4 | Gaussian HMM: forward–backward, Baum–Welch, Viterbi, filtering | **implemented from scratch** |
| 5 | Regime characterisation and significance testing | conditional stats, durations |
| 6 | Reconstructing MT5 equity from raw deals | mark-to-market curves, correlation |
| 7 | Strategy × regime performance, rank stability | heatmaps, block-bootstrap CIs |
| 8 | Walk-forward allocation with costs and inference | scoreboard, bootstrap, cost sensitivity |
| 9 | A reusable experiment harness | K/model/feature/cost sweeps |
| 10 | Pitfalls, checklist, glossary, next steps | — |

The HMM is implemented from scratch (no `hmmlearn`) because the notebook is meant to teach the
algorithm, and because `hmmlearn` has no wheel for Python 3.14 at the time of writing.

---

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Then open the notebook in VS Code (select the `.venv` interpreter) or run:

```bash
jupyter lab market_regime_detection.ipynb
```

`jupyterlab` is not in `requirements.txt` because VS Code's built-in notebook support is enough;
install it if you want the browser UI.

---

## What is in this folder

| Path | What it is |
|---|---|
| `market_regime_detection.ipynb` | The project. 100 cells, 42 code, executed with outputs. |
| `data/EURUSD_H1.csv` | 30,451 hourly bars, 2022-01-03 → 2026-11-20, UTC. |
| `data/strategies_EURUSD_H1.csv` | 7,198 raw deals from 12 MT5 strategies. |
| `data/strategies_meta.csv` | MT5 summary rows for those strategies. |
| `data/README.md` | Column definitions, provenance, bias warning. |
| `figures/` | 21 PNGs produced by the notebook. |
| `outputs/` | 7 CSVs: regime profiles, strategy×regime tables, scoreboard, sweeps. |
| `tools/refresh_data.py` | Regenerate `data/` from your MT5 terminal and backtester DB. |
| `requirements.txt` | Core stack. |

The data ships with the notebook, so it runs offline. `tools/refresh_data.py` documents exactly
how it was produced and lets you change symbol, timeframe, dates, or strategy IDs.

---

## Results snapshot

These are the numbers from the default run. Treat them as a worked example, not a live forecast.

**Regimes (3-state HMM on 18,644 in-sample hourly bars).**

| State | Share | Ann. vol | Avg. ADX | Trend R² | Duration |
|---|---|---|---|---|---|
| Low-vol chop | 46% | 6.2% | 19 | 0.31 | ~40 bars (1.7 d) |
| Mid-vol trend | 30% | 6.6% | 36 | 0.64 | ~26 bars (1.1 d) |
| High-vol chop | 23% | 12.1% | 28 | 0.41 | ~46 bars (1.9 d) |

Persistence is 96–98% per hour; filtered and Viterbi paths agree 93% of the time. Volatility
differs sharply across states; **average returns do not** (all p > 0.25, none significant after
Bonferroni correction). That is the central empirical finding of the project.

**Out-of-sample allocation (2025-01 → 2026-11, 489 trading days, 1 bp per unit turnover).**

| Method | Sharpe | Max DD | Turnover / day |
|---|---|---|---|
| Equal weight | **0.46** | -3.3% | 0.00 |
| Regime risk-off | 0.47 | -3.1% | 0.06 |
| Inverse vol | 0.43 | -3.2% | 0.01 |
| Static max-Sharpe (in-sample fit) | 0.05 | -4.2% | 0.00 |
| Regime blend (50% EW) | -0.09 | -4.4% | 0.36 |
| Regime inverse vol | -0.61 | -6.5% | 0.72 |
| Regime equal weight | -0.62 | -6.6% | 0.72 |
| Regime max-Sharpe | -0.75 | -6.9% | 0.65 |

**The regime methods lose.** The blend halves turnover and recovers most of the loss, but is still
below equal weight; the paired block bootstrap puts `P(beats EW)` at 0.008–0.016 for the
full-strength variants. The in-sample max-Sharpe portfolio collapsing out of sample is the
textbook overfitting signature.

Three lessons the notebook makes explicit:

1. **Regimes are real as volatility states, not as direction predictors.** Use them for risk, not
   for return timing.
2. **Equal weight is a brutal baseline.** Any regime method must beat it after costs, out of
   sample, with a pre-declared metric.
3. **Regime switching churns.** 0.7× daily turnover costs ~1.8%/yr on a 2.5%-vol portfolio — more
   than the entire edge being chased.

**Caveats.** The 12 strategies are survivors of a 7,279-strategy search on one symbol; their
backtest Sharpe is upward-biased. The OOS window is 1.9 years. Costs are a flat 1 bp — no spread,
slippage, or market impact. Read the result as a lesson about method, not as an expected return.

---

## How to test your own hypothesis

1. Write the prediction **before** running: direction, minimum size, metric, period.
2. Change **one** thing in [`market_regime_detection.ipynb`](market_regime_detection.ipynb):
   `CONFIG["n_regimes"]`, `FEATURES`, `LOOKBACK`, `COST_BPS`, or a `run_experiment(...)` call.
3. Record the whole table, including failures. Count your attempts — 20 variants and the best one
   is not a discovery, it is a selection (see the deflated-Sharpe note in Part 9).

The harness in Part 9 can sweep the number of states, the model (K-means vs HMM), the feature set,
and costs, with results cached by specification.

---

## Design decisions and limits

* **Hourly data, daily allocation.** Regimes are detected at H1; weights are rebalanced daily at
  the close, applied to the next day. No intraday execution assumptions.
* **Frozen HMM.** Parameters are fitted before 2025 and applied online with `filter_proba`. No
  refitting, no smoothing, no Viterbi in the trading path. A quarterly refit is listed as an
  extension.
* **Mark-to-market, not balance.** Strategy equity is reconstructed from deals with floating P&L;
  it reproduces MT5's final balance to the cent. Closed-trade P&L understates shared risk, which
  is why the correlation matrix looks worse than the selection metrics suggested.
* **No leverage, no shorting.** Weights are long-only and sum to ≤ 1; cash earns zero.
* **Costs are a flat bps on turnover.** Realistic for liquid FX at small size, optimistic for
  larger size.

---

## Requirements

Tested on Python 3.14 with pandas 3.0, numpy 2.4, scikit-learn 1.9, matplotlib 3.11. The code
also works on pandas 2.2+ / matplotlib 3.9+. `MetaTrader5` is optional and only needed to refresh
prices from your terminal.

```bash
pip install -r requirements.txt
```

---

## Credit and provenance

* Price data: your MetaTrader 5 terminal, EURUSD H1, exported 2026-11-22.
* Strategy deals: your MT5 backtester, batch #192 (`m1_ohlc`, 2022-01-01 → 2026-11-21, 100k USD).
* Methods: Wilder (ATR/ADX), Kaufman (efficiency ratio), Rabiner (HMM tutorial), Hamilton (1989,
  regime switching), Bailey & López de Prado (deflated Sharpe).

Educational use only. Nothing here is investment advice.
