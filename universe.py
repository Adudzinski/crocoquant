import yaml, datetime, requests
import pandas as pd


MAX_PER_SECTOR = 4

import yfinance as yf

def fetch_mw_top_n(n=200):
    tickers = pd.read_csv("data/tickers.csv")["ticker"].tolist()
    rows = []
    for tkr in tickers[:n]:
        info = yf.Ticker(tkr).info
        rows.append(dict(
            ticker=tkr,
            sector=info["sector"],
            mcap=info["marketCap"]
        ))
    rows.sort(key=lambda r: r["mcap"], reverse=True)
    return rows



def build_universe(save_to="data/universe.yaml"):
    # --- fetch the latest MSCI World constituents table ---------------
    # (pseudo-code, replace with actual scrape or static CSV)
    rows = fetch_mw_top_n(200)

    # --- rank by m-cap, enforce ≤4 per sector -------------------------
    basket = []
    sector_count = {}
    for row in rows:
        if len(basket) == 12:
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
