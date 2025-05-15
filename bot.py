import importlib, pathlib, pandas as pd, vectorbt as vbt
import argparse, os
from universe import load_universe
from predictors import mean_reversion  # first and only predictor today
import yaml, pathlib
CONFIG = yaml.safe_load(pathlib.Path("config.yaml").read_text())


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
    """Download daily close data."""
    return vbt.YFData.download(
        tickers,
        start=str(CONFIG["start"])
    ).get("Close")


def run_predictors(price_df: pd.DataFrame) -> pd.Series:
    """Aggregate probabilities from all predictors (mean today)."""
    preds = [
        mean_reversion.predict(
            price_df,
            CONFIG["lookback_ma"],
            CONFIG["z_entry"]
        )
        # add more predictors here
    ]
    return pd.concat(preds, axis=1).mean(axis=1)


def decide(proba: pd.Series):
    """Translate probability into entry/exit boolean masks."""
    buy  = proba > CONFIG["buy_threshold"]
    sell = proba < CONFIG["sell_threshold"]
    return buy, sell


# ----------------------------------------------------------------------
# 3. Main orchestration
# ----------------------------------------------------------------------
def main():
    basket  = load_universe()
    tickers = [d["ticker"] for d in basket]

    price     = get_data(tickers)
    proba     = run_predictors(price)
    entries, exits = decide(proba)

    if CONFIG["mode"] == "backtest":
        pf = vbt.Portfolio.from_signals(
            price,
            entries,
            exits,
            init_cash=CONFIG["cash"],
            freq="1D"        # enables Sharpe, Sortino, etc.
        )
        print(pf.stats())
    else:
        # --- LIVE MODE -------------------------------------------------
        # `entries.iloc[-1]` and `exits.iloc[-1]` contain today's signals
        from broker import execute_live     # lazy-import; avoids IB deps in back-test
        execute_live(entries.iloc[-1], exits.iloc[-1], CONFIG)


