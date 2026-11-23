"""Refresh ``data/`` from the local MetaTrader 5 terminal and backtester database.

This is the exact recipe used to build the CSVs shipped with the notebook. You only need it
when you want to change the symbol, timeframe, date range, or strategy set.

Examples
--------
    python tools/refresh_data.py --symbol EURUSD --timeframe H1 --from 2022-01-01
    python tools/refresh_data.py --only-deals
    python tools/refresh_data.py --only-rates --symbol XAUUSD --timeframe H1

Requires MetaTrader5 (Windows) for the rates half; the deals half only needs sqlite3.
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

# The local MT5 backtester database (adjust if your project lives elsewhere).
DEFAULT_DB = Path(r"C:\Users\DAT\Desktop\VSCode\MT5_Backtester\data\website.sqlite3")

# run_item_id values from batch #192, in the S01..S12 order used by the notebook.
DEFAULT_IDS = [60399, 59558, 60379, 60372, 59601, 60334,
               59621, 59731, 60387, 60397, 60385, 59565]

TIMEFRAMES = {
    "M1": 1, "M5": 5, "M15": 15, "M30": 30,
    "H1": 16385, "H4": 16388, "D1": 16408,
}


def export_rates(symbol: str, timeframe: str, start: str, end: str, out: Path) -> None:
    import MetaTrader5 as mt5

    if not mt5.initialize():
        raise SystemExit(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        rates = mt5.copy_rates_range(
            symbol,
            TIMEFRAMES[timeframe],
            pd.Timestamp(start, tz="UTC").to_pydatetime(),
            pd.Timestamp(end, tz="UTC").to_pydatetime(),
        )
    finally:
        mt5.shutdown()

    if rates is None or len(rates) == 0:
        raise SystemExit(f"no rates returned for {symbol} {timeframe}")

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.set_index("time").sort_index()
    df = df[~df.index.duplicated(keep="first")]
    df = df[["open", "high", "low", "close", "tick_volume", "spread"]]
    df.index = df.index.strftime("%Y-%m-%dT%H:%M:%SZ")
    df.index.name = "time"
    df.to_csv(out)
    print(f"wrote {len(df):,} bars -> {out}")


def export_deals(db: Path, ids: list[int], out: Path, meta_out: Path) -> None:
    con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    try:
        id_list = ",".join(str(int(i)) for i in ids)
        meta = pd.read_sql_query(
            f"""select i.id, i.strategy_file, i.net_profit, i.trades, i.max_drawdown_pct,
                       i.win_rate, i.profit_factor, i.sharpe, i.deposit
                from run_items i where i.id in ({id_list})""",
            con,
        )
        meta = meta.set_index("id").loc[ids].reset_index()
        meta.insert(0, "strategy", [f"S{i:02d}" for i in range(1, len(meta) + 1)])

        deals = pd.read_sql_query(
            f"""select run_item_id, seq, deal_time, symbol, type, direction, volume, price,
                       commission, swap, profit, balance, comment
                from trades where run_item_id in ({id_list})""",
            con,
        )
    finally:
        con.close()

    mapping = dict(zip(meta["id"], meta["strategy"]))
    deals["strategy"] = deals["run_item_id"].map(mapping)
    deals = deals.sort_values(["strategy", "deal_time", "seq"]).reset_index(drop=True)
    deals["deal_time"] = pd.to_datetime(deals["deal_time"], format="%Y.%m.%d %H:%M:%S")
    deals = deals[["strategy", "run_item_id", "seq", "deal_time", "symbol", "type",
                   "direction", "volume", "price", "commission", "swap", "profit",
                   "balance", "comment"]]
    deals.to_csv(out, index=False)

    meta = meta.rename(columns={"id": "run_item_id", "strategy_file": "source_file"})
    meta.to_csv(meta_out, index=False)
    print(f"wrote {len(deals):,} deals for {len(meta)} strategies -> {out}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="EURUSD")
    ap.add_argument("--timeframe", default="H1", choices=sorted(TIMEFRAMES))
    ap.add_argument("--from", dest="start", default="2022-01-01")
    ap.add_argument("--to", dest="end", default="2026-11-22")
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--ids", type=int, nargs="*", default=DEFAULT_IDS)
    ap.add_argument("--only-rates", action="store_true")
    ap.add_argument("--only-deals", action="store_true")
    args = ap.parse_args()

    if not args.only_deals:
        export_rates(args.symbol, args.timeframe, args.start, args.end,
                     DATA / f"{args.symbol}_{args.timeframe}.csv")
    if not args.only_rates:
        export_deals(args.db, args.ids,
                     DATA / "strategies_EURUSD_H1.csv",
                     DATA / "strategies_meta.csv")


if __name__ == "__main__":
    main()
