import numpy as np
import time
import importlib, pathlib, pandas as pd, vectorbt as vbt
from ib_insync import IB, Stock, util, MarketOrder, StopOrder
from ta.volatility import AverageTrueRange
from dotenv import load_dotenv
import argparse, os
from universe import load_universe
from predictors import mean_reversion, momentum  
import yaml, pathlib
from predictors import PREDICTORS

CONFIG = yaml.safe_load(pathlib.Path("config.yaml").read_text())


load_dotenv()



# ----------------------------------------------------------------------
# 1. Config loader  (YAML  +  CLI / ENV override)
# ----------------------------------------------------------------------
def load_config():
    cfg = yaml.safe_load(pathlib.Path("config.yaml").read_text())

    # ENV var override
    if "MODE" in os.environ:
        cfg["mode"] = os.environ["MODE"]

    # CLI override
    parser = argparse.ArgumentParser(description="Daily quant-bot")
    parser.add_argument("--mode", choices=["backtest", "live"],
                        help="Run in backtest or live mode")
    args, _ = parser.parse_known_args()
    if args.mode:
        cfg["mode"] = args.mode

    return cfg


CONFIG = load_config()          # global dict


# ----------------------------------------------------------------------
# 2. Helpers
# ----------------------------------------------------------------------

def get_data(tickers):
    """
    Download up to 8 years of daily closes from Interactive Brokers.

    Requires Gateway/TWS to be running with API enabled.

    Env vars (fallback defaults shown):
        IB_IB       127.0.0.1
        IB_PORT       4002
        IB_CLIENT_ID  99
    """
    host       = os.getenv("IB_IP",   "127.0.0.1")
    port       = int(os.getenv("IB_PORT", 7497))
    client_id  = int(os.getenv("IB_CLIENT_ID", 99))

    ib = IB()
    ib.connect(host, port, clientId=client_id)

    dfs = []
    for tkr in tickers:
        bars = ib.reqHistoricalData(
            Stock(tkr, "SMART", "USD"),
            endDateTime="",
            durationStr="8 Y",
            barSizeSetting="1 day",
            whatToShow="ADJUSTED_LAST",
            useRTH=False,
            formatDate=1,
            timeout=20
        )

        if not bars:                       # ← empty list, skip
            print(f"[WARN] no data for {tkr}")
            continue

        df = util.df(bars)
        # ── enforce datetime & set as index ──────────────────────────
        ser = pd.Series(
            data=df["close"].values,                 # numeric values
            index=pd.to_datetime(df["date"]),        # DatetimeIndex
            name=tkr
            ).sort_index()

        ser = ser[~ser.index.duplicated(keep="last")]
        dfs.append(ser)
        time.sleep(0.3)

    ib.disconnect()

    if not dfs:
        raise RuntimeError("All IBKR requests returned empty – check API perms.")

    price = pd.concat(dfs, axis=1).sort_index().ffill()
    
    price.index = pd.to_datetime(price.index)
    price = price.tz_localize(None)
#    print(price)
    if price.empty:
        raise RuntimeError("IBKR returned no bars – check symbols or connection.")
    return price

def run_predictors(price_df: pd.DataFrame) -> pd.Series:
    cfg_pred = CONFIG["predictors"]

    weighted_probs = []
    weights = []

    for name, settings in cfg_pred.items():
        if not settings.get("enabled", True):
            continue                        # skip disabled predictor
        if name not in PREDICTORS:
            print(f"[WARN] predictor '{name}' not found")
            continue

        # ---- call predictor with its params ------------------------
        params = settings.get("params", {})
        prob = PREDICTORS[name](price_df, **params)

        # ---- collect weighted --------------------------------------
        weighted_probs.append(prob * settings.get("weight", 1))
        weights.append(settings.get("weight", 1))

    if not weighted_probs:
        raise ValueError("No predictors enabled!")

    # weighted average  (sum(p_i * w_i) / sum(w))
  #  combined = pd.concat(weighted_probs, axis=1).sum(axis=1) / sum(weights)
    combined = pd.concat(weighted_probs, axis=0).groupby(level=0).sum() / sum(weights)
    return combined.clip(0, 1)        # safety

def decide(proba: pd.DataFrame):
    """Translate probability into entry/exit boolean masks."""
    buy  = proba > CONFIG["buy_threshold"]
    sell = proba < CONFIG["sell_threshold"]
    return buy, sell


def get_recent_ohlcv(ib, symbol):
    """Fetch recent 20-day OHLC data for one ticker."""
    contract = Stock(symbol, "SMART", "USD")
    bars = ib.reqHistoricalData(
        contract,
        endDateTime="",
        durationStr="30 D",
        barSizeSetting="1 day",
        whatToShow="TRADES",
        useRTH=False,
        formatDate=1,
        timeout=10
    )
    df = util.df(bars)
    df = df.set_index(pd.to_datetime(df["date"]))
    return df[["high", "low", "close"]].sort_index()

def execute_live(today_buy, today_sell, cfg):
    """Submit live orders based on today's entry/exit signals."""
    ib = IB()
    ib.connect(
        os.getenv("IB_IP", "127.0.0.1"),
        int(os.getenv("IB_PORT", 7497)),
        int(os.getenv("IB_CLIENT_ID", 7))
    )
    ib.reqMarketDataType(3) # Delayed data if live not available
    max_cash = float(cfg.get("max_cash_per_trade", 1000))
    atr_window = int(cfg.get("atr_window", 14))
    atr_mult = float(cfg.get("atr_multiplier", 1.5))
    # Fetch current positions
    positions = {pos.contract.symbol: pos.position for pos in ib.positions()}

    for tkr in today_buy.index:
        contract = Stock(tkr, "SMART", "USD")

        if today_buy[tkr] and positions.get(tkr, 0) == 0:
            print(f"🔼 Buying {tkr} with ATR stop-loss")
            ticker = ib.reqMktData(contract, '', False, False)
            ib.sleep(2)

            # Market price
            price = ticker.last if ticker.last else ticker.close
            
            if price is None or np.isnan(price) or price <= 0:
                print(f"[ERROR] Price for {tkr} is invalid: {price}")
                continue
            # Quantity
            qty = max(1,int(max_cash / price))

            # OHLCV for ATR
            ohlc = get_recent_ohlcv(ib, tkr)
            atr = AverageTrueRange(high=ohlc["high"], low=ohlc["low"], close=ohlc["close"], window=atr_window).average_true_range()
            stop_price = round(price - atr_mult * atr.iloc[-1], 2)
            
            # Place buy + stop
            order = MarketOrder("BUY", qty)
            ib.placeOrder(contract, order)

            stop_order = StopOrder("SELL", qty, stop_price)
            ib.placeOrder(contract, stop_order)

            print(f"✅ Order sent: BUY {qty} {tkr} @ {price:.2f}, stop-loss at {stop_price:.2f}")

        elif today_sell[tkr] and positions.get(tkr, 0) > 0:
            print(f"🔽 Selling all shares of {tkr}")
            order = MarketOrder("SELL", positions[tkr])
            ib.placeOrder(contract, order)

    ib.disconnect()


# ----------------------------------------------------------------------
# 3. Main orchestration
# ----------------------------------------------------------------------
def main():
#    print("MODE in memory -->", CONFIG["mode"])
    basket  = load_universe()
#    print("TICKERS:", basket)
    tickers = [d["ticker"] for d in basket]

    price     = get_data(tickers)
    proba     = run_predictors(price)
    entries, exits = decide(proba)

    if CONFIG["mode"] == "backtest":
        entries = entries[price.columns]
        exits = exits[price.columns]
        entries = entries.reindex(price.index)
        exits = exits.reindex(price.index)

        pf = vbt.Portfolio.from_signals(
            price,
            entries,
            exits,
            init_cash=CONFIG["cash"],
            freq="1D"        # enables Sharpe, Sortino, etc.
        )
        print(pf.stats())

        for column in price.columns:
            try:
                fig = pf[column].plot()
                fig.write_image(f"data/backtest_plot_{column}.png")
                print(f"✅ Plot saved to: data/backtest_plot_{column}.png")
            except Exception as e:
                print(f"[WARN] Could not plot {column}: {e}")


    else:
        # --- LIVE MODE -------------------------------------------------
        # `entries.iloc[-1]` and `exits.iloc[-1]` contain today's signals
                # LIVE MODE

        # Just today’s signals
        today_buy = entries.iloc[-1]
        today_sell = exits.iloc[-1]
        
        print("Today's probabilities:")
        print(proba.iloc[-1])
        print("Buy signals:")
        print(entries.iloc[-1])
        print("Sell signals:")
        print(exits.iloc[-1])



        # Print what will happen
        for tkr in tickers:
            action = None
            if today_buy[tkr]:
                action = "BUY"
            elif today_sell[tkr]:
                action = "SELL"
            if action:
                print(f"📍 Signal for {tkr}: {action}")

        if today_buy.any() or today_sell.any():
            execute_live(today_buy, today_sell, CONFIG)
        else:
            print("✅ No action today (no buy or sell signals)")



# bot.py  (bottom)
if __name__ == "__main__":
    main()

