# Data

Everything here was produced from the local MT5 installation on 2026-11-22.

## `EURUSD_H1.csv`

Hourly OHLCV for EURUSD, 2022-01-03 → 2026-11-20 (30,451 bars).

| Column | Meaning |
|---|---|
| `time` | Bar open time, UTC, ISO-8601 (`...Z`). |
| `open` / `high` / `low` / `close` | Prices for the hour. |
| `tick_volume` | Number of price updates (MT5 "tick volume"), not contracts. |
| `spread` | Average spread in points, as reported by MT5 (often 0 on historical bars). |

Source: MetaTrader 5 terminal, `EURUSD`, `TIMEFRAME_H1`, exported with
`mt5.copy_rates_range` and cleaned (deduplicated, sorted, positive prices only).
Regenerate with `tools/refresh_data.py`.

## `strategies_EURUSD_H1.csv`

Raw **deal history** of 12 strategies from the local MT5 backtester, batch **#192**
(`m1_ohlc`, 2022-01-01 → 2026-11-21, 100,000 USD deposit, EURUSD H1).

One row = one deal. `direction` is `in` (open) or `out` (close); `type` is `buy` or `sell`.
`profit`, `commission` and `swap` are as reported by MT5; `balance` is the account balance after
the deal. `strategy` is the anonymised label `S01…S12` used throughout the notebook.

The 12 were selected from 2,404 completed runs for **diversity**, not only for profit: a greedy
max-min correlation filter on realised daily P&L, keeping the pairwise daily correlation below
~0.47 on that measure. Note that mark-to-market correlation (what the notebook computes) is
higher — closed-trade P&L hides shared risk while positions are open.

## `strategies_meta.csv`

The MT5 summary row for each strategy (`net_profit`, `trades`, `max_drawdown_pct`, `win_rate`,
`profit_factor`, `sharpe`, `deposit`) plus `run_item_id` and the original `source_file`.
Used to verify that the notebook's mark-to-market reconstruction matches MT5 to the cent.

## Bias warning

These strategies are survivors of a 7,279-strategy search on one symbol. Their backtest
performance is upward-biased, and they are correlated by construction. They are here to
demonstrate the *method*, not to estimate a live return.
