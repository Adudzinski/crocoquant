import yaml, datetime, requests
import pandas as pd
import time

CONFIG = yaml.safe_load(open("config.yaml"))

MAX_PER_SECTOR = CONFIG.get("max_per_sector",4)
TOTAL_COMPANIES_TO_TRADE = CONFIG.get("total_companies_to_trade",12)

import yfinance as yf

def fetch_mw_top_n():
    tickers = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "UNH", "V", "JNJ",
        "JPM", "XOM", "WMT", "PG", "MA", "HD", "CVX", "LLY", "MRK", "ABBV", "KO",
        "PEP", "NVO", "BHP", "ASML", "ORCL", "SAP", "TM", "T", "SHEL", "UL", "NESN"
    ]
    rows = []
    for tkr in tickers:
        try:
            info = yf.Ticker(tkr).info
            rows.append(dict(
                ticker=tkr,
                sector=info.get("sector", "Unkown"),
                mcap=info.get("marketCap",0)
            ))
            time.sleep(1.5)
        except Exception as e:
            print(f"[WARN] Failed to fetch {tkr}: {e}")
    rows = [r for r in rows if r["mcap"] > 0 and r["sector"] != "Unknown"]
    rows.sort(key=lambda r: r["mcap"], reverse=True)
    return rows



def build_universe(save_to="data/universe.yaml"):
    # --- fetch the latest MSCI World constituents table ---------------
    # (pseudo-code, replace with actual scrape or static CSV)
    rows = fetch_mw_top_n()

    # --- rank by m-cap, enforce ≤4 per sector -------------------------
    basket = []
    sector_count = {}
    for row in rows:
        if len(basket) == TOTAL_COMPANIES_TO_TRADE:
            break
        sector = row["sector"]
        if sector_count.get(sector, 0) >= MAX_PER_SECTOR:
            continue
        basket.append({"ticker": row["ticker"], "sector": sector})
        sector_count[sector] = sector_count.get(sector, 0) + 1

    # --- dump to YAML -------------------------------------------------
    out = {"as_of": datetime.date.today().isoformat(), "basket": basket}
    yaml.safe_dump(out, open(save_to, "w"))
    return basket

def load_universe(path="data/universe.yaml"):
    return yaml.safe_load(open(path))["basket"]

if __name__ == "__main__":
    build_universe()


