#!/usr/bin/env python3
"""
Daily Trading Bot
=================
This script can run in **backtest** mode (default) or **live** trading mode.

Strategy
--------
- Mean‑reversion z‑score on a rolling moving average.
- Optional soft momentum filter (5‑day return > −1 %).
- Optional daily‑volatility cap (20‑day SD < 5 %).

Parameters live in `StrategyConfig` and can be overridden via CLI flags.

Examples
~~~~~~~~
Back‑test NVDA and plot equity‑curve:
    python daily_trading_bot.py --plot

Back‑test with stricter entry threshold:
    python daily_trading_bot.py --z_entry 2.0

Run live (paper):
    python daily_trading_bot.py --mode live
"""
import argparse
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, time as dtime
import os

import numpy as np
import pandas as pd
import vectorbt as vbt
import yfinance as yf

from ib_insync import IB, Stock, util

# ---------------------------------------------------------------------
# Configuration dataclasses
# ---------------------------------------------------------------------

@dataclass
class StrategyConfig:
    """Tunable strategy hyper‑parameters."""
    lookback_ma: int = 20           # rolling window for MA / σ
    z_entry: float = 1.5            # go long if z < −z_entry
    z_exit: float = 1.5             # exit if z >  z_exit
    momentum_window: int = 5        # lookback for momentum filter
    mom_thresh: float = -0.01       # require 5‑day return > −1 %
    vol_window: int = 20            # lookback for volatility cap
    vol_thresh: float = 0.05        # require daily SD < 5 %

@dataclass
class BotConfig:
    """Live‑trading settings."""
    symbols: tuple = ("NVDA",)      # tickers to trade
    cash: float = 10_000            # initial back‑test equity
    ib_host: str = os.getenv("IB_IP", "127.0.0.1")
    ib_port: int = 7497
    ib_client_id: int = 42
    order_size: int = 100           # shares per order
    run_at: dtime = dtime(21, 5)    # Europe/Berlin ~ 21:05 CET/CEST

# ---------------------------------------------------------------------
# Signal construction
# ---------------------------------------------------------------------

def compute_signals(close: pd.DataFrame, cfg: StrategyConfig):
    """Return boolean DataFrames of entry and exit signals."""
    ma = close.rolling(cfg.lookback_ma).mean()
    sd = close.rolling(cfg.lookback_ma).std()
    z = (close - ma) / sd

    mom = close.pct_change(cfg.momentum_window)
    mom_ok = mom > cfg.mom_thresh

    vol = close.pct_change().rolling(cfg.vol_window).std()
    vol_ok = vol < cfg.vol_thresh

    entries = (z < -cfg.z_entry) & mom_ok & vol_ok
    exits = z > cfg.z_exit

    return entries.fillna(False), exits.fillna(False)

# ---------------------------------------------------------------------
# Back‑testing with vectorbt
# ---------------------------------------------------------------------

def backtest(symbols, cfg: StrategyConfig, cash: float, plot=False):
    price = yf.download(list(symbols), start="2018-01-01", progress=False)["Close"].dropna()
    entries, exits = compute_signals(price, cfg)
    pf = vbt.Portfolio.from_signals(price, entries, exits, init_cash=cash, freq="1D")
    print(pf.stats())
    if plot:
        pf.plot().show()
    return pf

# ---------------------------------------------------------------------
# Live trading helpers
# ---------------------------------------------------------------------

async def execute_trade(ib: IB, symbol: str, action: str, qty: int):
    contract = Stock(symbol, "SMART", "USD")
    order = util.marketOrder(action, qty)
    trade = ib.placeOrder(contract, order)
    while not trade.isDone():
        await asyncio.sleep(0.5)
    print(f"{datetime.now():%Y-%m-%d %H:%M:%S}: {action} {qty} {symbol}")

async def daily_run(bot_cfg: BotConfig, strat_cfg: StrategyConfig):
    ib = IB()
    ib.connect(bot_cfg.ib_host, bot_cfg.ib_port, clientId=bot_cfg.ib_client_id)
    while True:
        now = datetime.now()
        target_dt = datetime.combine(now.date(), bot_cfg.run_at)
        if now.time() > bot_cfg.run_at:
            target_dt += timedelta(days=1)
        await asyncio.sleep(max(0, (target_dt - now).total_seconds()))

        # Fetch last 130 days (enough for rolling windows)
        price = yf.download(list(bot_cfg.symbols), period="130d", progress=False)["Close"].dropna()
        entries, exits = compute_signals(price, strat_cfg)
        last_entry = entries.iloc[-1]
        last_exit = exits.iloc[-1]

        for sym in bot_cfg.symbols:
            if last_entry[sym]:
                await execute_trade(ib, sym, "BUY", bot_cfg.order_size)
            elif last_exit[sym]:
                await execute_trade(ib, sym, "SELL", bot_cfg.order_size)

# ---------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Daily mean‑reversion trading bot")
    parser.add_argument("--mode", choices=["backtest", "live", "both"], default="backtest")
    parser.add_argument("--plot", action="store_true", help="Show plot after back‑test")
    parser.add_argument("--z_entry", type=float, help="Override z‑score entry threshold")
    parser.add_argument("--symbols", nargs="+", help="Ticker symbols (space‑separated)")
    args = parser.parse_args()

    strat_cfg = StrategyConfig()
    if args.z_entry is not None:
        strat_cfg.z_entry = args.z_entry

    bot_cfg = BotConfig()
    if args.symbols:
        bot_cfg.symbols = tuple(args.symbols)

    if args.mode in ("backtest", "both"):
        backtest(bot_cfg.symbols, strat_cfg, bot_cfg.cash, plot=args.plot)

    if args.mode in ("live", "both"):
        asyncio.run(daily_run(bot_cfg, strat_cfg))

if __name__ == "__main__":
    main()

