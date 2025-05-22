#crocoquant

##Quant-Bot 

A once-a-day trading bot that pulls daily prices, combines multiple predictors into buy probabilities, and either

    Back-tests the strategy with vectorbt, or

    Trades live via Interactive Brokers (paper or live account) using ib-insync.

Runs completely inside Docker and can be scheduled by a cron side-car container so you don’t need to keep your laptop on. 

Folder layout

quant-bot/
├── README.md     # you’re here
├── config.yaml    # strategy knobs (mode, thresholds…)
├── .env.example   # sample IB credentials
├── predictors/    # drop-in signal modules (mean_reversion.py, …)
├── universe.py    # builds 12-stock basket (≤ 4 per sector)
├── bot.py       # orchestrator (data → predictors → decisions)
├── backtest.py    # thin wrapper → bot.py in back-test mode
├── Dockerfile     # slim Python 3.12 image
├── docker-compose.yml # bot + scheduler services
└── data/        # universe.yaml, logs/ (git-ignored)

##Prerequisites

Before getting started, ensure you have the following installed:

a) Docker: Install Docker b) Interactive Brokers Account: You will need a live or paper trading account with Interactive Brokers. Install Trader Workstation (TWS) or IB Gateway to access the IBKR API.


##Quick start — back-test

    Clone the repo
    git clone https://github.com/<you>/quant-bot.git && cd quant-bot

    Install dependencies
    pip install -r requirements.txt

    Build the 12-stock universe
    python -c "import universe; universe.build_universe()"

    Run a back-test
    python bot.py --mode backtest 

##Live trading — paper

    1. Start IB Gateway or TWS, enable “API → ActiveX/Socket”.

    2. Copy .env.example → .env and fill IB_HOST, IB_PORT, IB_CLIENT_ID.

    3. In config.yaml set mode: live (or use --mode live).

    4. Launch the stack:

    docker compose up -d
    docker compose logs -f scheduler

    The cron side-car triggers the bot every weekday at **21 : 05 Europe/Berlin**.  
    Change this schedule inside `docker-compose.yml` → `scheduler` → `command` line, then:

    	docker compose up -d --build scheduler  
    	docker compose logs -f scheduler

##ATR-Based Stop-Loss (Live Trading)

    The live bot uses an ATR-based stop-loss:

    - The bot fetches 14 days of OHLC data from IBKR

    - Computes the Average True Range (ATR) per asset

    - Places a stop-loss order at: entry_price − 1.5 × ATR

    - Configurable via config.yaml:

	atr_window: 14
	atr_multiplier: 1.5

    This allows dynamic risk management that adjusts to asset volatility.




##Adding predictors

Create predictors/<name>.py with

def predict(price_df, **kwargs) -> pd.Series:
    # return 0-to-1 probabilities

The bot auto-discovers every predict() in predictors/ and averages them—no bot-code edits needed.

Declare them in `config.yaml`:

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
      clip: 0.15''' 

##Universe rules

universe.build_universe() ranks MSCI-World by market-cap, enforces ≤ 4 per GICS sector, and dumps the basket to data/universe.yaml. Regenerate whenever you want a fresh list.

Key configuration fields (config.yaml)
Key	Meaning
mode	backtest / live
start	Start date for back-test data
cash	Initial cash for back-test
lookback_ma, z_entry	Mean-reversion parameters
buy_threshold, sell_threshold	Probability cut-offs
log_path	Folder for live logs


## Data sources

The bot by default downloads historical prices from Yahoo Finance via vectorbt, but
you can switch to IBKR historical data by replacing get_data() in bot.py:

    IBKR requires Gateway/TWS running with API enabled.

    Fetches up to 8 years of daily bars.

    Requires proper IB market data subscriptions (US Equities bundle).

    Handles duplicate dates and missing bars gracefully.




##Updating Dependencies

If you add or update any Python dependencies, follow these steps to update your Docker container:

1. Install New Dependencies Locally Install the required dependencies with:

    pip install

2. Update requirements.txt After installing the new dependencies, update the requirements.txt by running:

    pipreqs . --force

(If pipreqs is not installed do: pip install pipreqs)

3.  Rebuild the Docker Image Rebuild the Docker image to include the new dependencies:

    docker build -t trading-bot .

4.  Restart the Docker Container After rebuilding the image, restart the container with the new dependencies:

    docker stop crocoquant-container docker rm crocoquant-container 
    docker run -d --name crocoquant-container crocoquant

#WSL & Interactive Brokers API: IP Address Issue

When running this bot inside WSL (Windows Subsystem for Linux), the localhost IP (127.0.0.1) will not work to connect to TWS (Trader Workstation). This is because WSL runs in a separate network environment from Windows.

Issue:

By default, trying to connect using: ib.connect("127.0.0.1", 7497, clientId=1)

may fail with:

 ConnectionRefusedError: [Errno 111] Connect call failed

This happens because WSL needs to connect using the Windows host machine’s IP, not 127.0.0.1.
Solution: Use Windows IP Instead

1. Find Your Windows IP

Run this in Windows PowerShell:

 ipconfig | findstr /C:"IPv4 Address"

Look for an IP like 192.168.x.x (this is your local network IP).

2. Store IP in .env File

Create a .env file in your project folder: IB_IP=192.168.x.x # Replace with your actual IP

3. Load IP in Your Python Script

Install python-dotenv if not already installed:

 pip install python-dotenv

##Final Notes

- Every time your Windows IP changes, update the .env file.
- This setup keeps your IP private while ensuring WSL can connect to TWS.
- If you're still having issues, check that TWS API settings allow incoming connections (Edit > Global Configuration > API > Settings).


