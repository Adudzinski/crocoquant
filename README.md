# crocoquant

## Quant-Bot

A once-a-day trading bot that pulls daily prices, combines multiple predictors into buy probabilities, and either:

- Back-tests the strategy with vectorbt, or  
- Trades live via Interactive Brokers (paper or live account) using ib-insync.

Runs completely inside Docker and can be scheduled by a cron side-car container so you don’t need to keep your laptop on.

---

## Folder Layout

```
quant-bot/
├── README.md              # you’re here
├── config.yaml            # strategy knobs (mode, thresholds…)
├── .env.example           # sample IB credentials
├── predictors/            # drop-in signal modules (mean_reversion.py, …)
├── universe.py            # builds 12-stock basket (≤ 4 per sector)
├── bot.py                 # orchestrator (data → predictors → decisions)
├── backtest.py            # thin wrapper → bot.py in back-test mode
├── Dockerfile             # slim Python 3.12 image
├── docker-compose.yml     # bot + scheduler services
└── data/                  # universe.yaml, logs/ (git-ignored)
```

---

## Prerequisites

Ensure you have the following installed:

- **Docker**  
- **Interactive Brokers Account**: (Live or paper)  
  Install Trader Workstation (TWS) or IB Gateway to access the IBKR API.

---

## Quick Start — Back-Test

```bash
# Clone the repo
git clone https://github.com/<you>/quant-bot.git && cd quant-bot

# Install dependencies
pip install -r requirements.txt

# Build the 12-stock universe
python -c "import universe; universe.build_universe()"

# Run a back-test
python bot.py --mode backtest 
```

---

## Live Trading — Paper

1. Start IB Gateway or TWS, enable:  
   **API → ActiveX/Socket**

2. Copy `.env.example` → `.env` and set:  
   `IB_HOST`, `IB_PORT`, `IB_CLIENT_ID`

3. In `config.yaml`, set `mode: live` (or use `--mode live`).

4. Launch the stack:

```bash
docker compose up -d
docker compose logs -f scheduler
```

> ⏰ The cron side-car triggers the bot every weekday at **21:05 Europe/Berlin**.  
To change this, edit `docker-compose.yml` → `scheduler` → `command`, then:

```bash
docker compose up -d --build scheduler  
docker compose logs -f scheduler
```

---

## ATR-Based Stop-Loss (Live Trading)

The live bot uses an ATR-based stop-loss:

- Fetches 14 days of OHLC data from IBKR
- Computes the Average True Range (ATR)
- Places a stop-loss at:  
  `entry_price − 1.5 × ATR`
- Configurable in `config.yaml`:

```yaml
atr_window: 14
atr_multiplier: 1.5
```

This enables dynamic risk management based on volatility.

---

## Adding Predictors

Create `predictors/<name>.py`:

```python
def predict(price_df, **kwargs) -> pd.Series:
    # return 0-to-1 probabilities
```

The bot auto-discovers each `predict()` in `predictors/` and averages them.

Declare in `config.yaml`:

```yaml
predictors:
  mean_reversion:
    enabled: true
    weight: 0.5
    params:
      lookback: 30
      z_entry: 1.5

  momentum:
    enabled: true
    weight: 0.5
    params:
      lookback: 10
      clip: 0.15
```

---

## Universe Rules

`universe.build_universe()`:

- Ranks MSCI-World by market-cap  
- Enforces ≤ 4 per GICS sector  
- Saves to `data/universe.yaml`

Key fields in `config.yaml`:

| Key              | Meaning                        |
|------------------|--------------------------------|
| `mode`           | backtest / live                |
| `start`          | Start date for back-test       |
| `cash`           | Initial back-test cash         |
| `lookback_ma`    | Mean-reversion lookback window |
| `z_entry`        | Z-score entry threshold        |
| `buy_threshold`  | Buy probability cutoff         |
| `sell_threshold` | Sell probability cutoff        |
| `log_path`       | Path for logs                  |

---

## Data Sources

By default, historical prices are downloaded from **Yahoo Finance** via `vectorbt`.

To use **IBKR data** instead, modify `get_data()` in `bot.py`.

Notes:

- Requires IB Gateway/TWS running with API enabled
- Fetches up to 8 years of daily bars
- Needs IB market data subscriptions (US Equities bundle)
- Handles duplicates and missing bars

---

## Updating Dependencies

If you add or update Python dependencies:

1. Install them:

```bash
pip install <package>
```

2. Update `requirements.txt`:

```bash
pipreqs . --force
```

3. Rebuild the Docker image:

```bash
docker build -t trading-bot .
```

4. Restart the container:

```bash
docker stop crocoquant-container
docker rm crocoquant-container
docker run -d --name crocoquant-container crocoquant
```

---

## WSL & Interactive Brokers API — IP Address Issue

When using WSL (Windows Subsystem for Linux), `127.0.0.1` won't connect to TWS. Use your Windows host's IP.

### Solution:

1. Find Windows IP (PowerShell):

```powershell
ipconfig | findstr /C:"IPv4 Address"
```

2. Add to `.env`:

```dotenv
IB_IP=192.168.x.x
```

3. Load in Python:

```bash
pip install python-dotenv
```

---

## Final Notes

- Update your `.env` if your IP changes
- Ensure TWS allows incoming connections:  
  `Edit > Global Configuration > API > Settings`
