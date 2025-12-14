# High Volatility Stock Scanner Suite

Three powerful tools for finding aggressive trading opportunities on NYSE/NASDAQ.

## Tools Overview

### 1. Basic Scanner (`volatile_stock_scanner.py`)
**Best for:** Quick scans, daily screening
**Runtime:** 2-3 minutes
**Features:**
- Scans 100+ high-volatility stocks
- Calculates historical volatility, ATR, volume metrics
- Filters for $1-10 price range, high volume
- Identifies top movers and volume surges

**Usage:**
```bash
python volatile_stock_scanner.py
```

### 2. Advanced Scanner (`volatile_scanner_advanced.py`)
**Best for:** Comprehensive analysis, strategy identification
**Runtime:** 3-5 minutes
**Features:**
- Expanded universe (200+ stocks)
- Multiple trading strategies:
  - High Risk/High Reward (70%+ volatility)
  - Breakout Candidates (5%+ moves with volume)
  - Momentum Plays (10%+ weekly gains)
- Real-time metrics including intraday volatility
- Moving average analysis
- 52-week high/low distances

**Usage:**
```bash
python volatile_scanner_advanced.py
```

### 3. Watchlist Monitor (`watchlist_monitor.py`)
**Best for:** Real-time tracking, day trading
**Runtime:** Continuous (user-defined duration)
**Features:**
- Real-time minute-by-minute updates
- Price movement alerts (customizable threshold)
- Pre-configured watchlists (Crypto, Biotech, Tech, Meme)
- Custom watchlist support
- Tracks 5-minute momentum

**Usage:**
```bash
python watchlist_monitor.py
```

## Quick Start

### 1. Setup Environment

Create a `.env` file in the same directory as the scripts:

```bash
# Copy the example file
cp .env.example .env

# Edit with your API keys
nano .env  # or use your preferred editor
```

Your `.env` file should contain:
```bash
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

**Note:** The scanners currently use Yahoo Finance (no API key needed). The Alpaca credentials are loaded for future integration with your trading infrastructure.

### 2. Install Dependencies

```bash
pip install yfinance pandas numpy requests python-dotenv
```

### 3. Run Scanner

### Interactive Runner
```bash
python run_scanner.py
```
Choose from:
1. Basic Scanner
2. Advanced Scanner  
3. Custom ticker scan

## Scanner Criteria

### Default Filters (Customizable)
- **Price Range:** $1 - $10
- **Min Volume:** 1M shares/day
- **Min Volatility:** 50% annualized
- **Min ATR:** 3% daily
- **Max Market Cap:** $2B

### Volatility Scoring
Stocks are ranked by composite score:
- Historical Volatility (40%)
- Recent Volatility (30%)
- ATR Percentage (30%)

## Output Files

All scans automatically save CSV files:
- `volatile_stocks_full_YYYYMMDD_HHMMSS.csv` - Complete results
- `volatile_stocks_filtered_YYYYMMDD_HHMMSS.csv` - Filtered candidates
- `high_risk_plays_YYYYMMDD_HHMMSS.csv` - Most aggressive opportunities

## Key Metrics Explained

- **Historical Volatility:** Annualized standard deviation (252 trading days)
- **ATR (Average True Range):** 14-day average daily range
- **Volume Ratio:** Current volume / 20-day average
- **Beta:** Stock's correlation with market (>2.0 is 2x market volatility)
- **Volatility Trend:** Whether volatility is increasing or decreasing

## Sector Focus

Scanner covers high-volatility sectors:
- 🪙 Crypto-related stocks (MARA, RIOT, COIN)
- 🧬 Biotech/Pharma (SAVA, TBPH, IRWD)
- 🚗 EV/Battery (LCID, RIVN, PLUG)
- 💻 Small-cap tech (IONQ, SOFI, HOOD)
- 🌿 Cannabis (TLRY, CGC, SNDL)
- 🎮 Meme/High Beta (GME, AMC)

## Trading Strategy Integration

### For Your Aggressive Strategy
1. **Run Advanced Scanner** to identify candidates
2. **Filter for:** 
   - 100%+ volatility
   - $1-$5 price range
   - Volume >2M/day
3. **Use Watchlist Monitor** to track intraday moves
4. **Target:** Stocks with increasing volatility + volume surge

### Example Workflow
```bash
# Morning: Identify candidates
python volatile_scanner_advanced.py

# Day: Monitor top picks
python watchlist_monitor.py
# Select watchlist #5 (custom)
# Enter: MARA,RIOT,IONQ,SOFI,SAVA
# Alert: 3%
# Refresh: 30 seconds
```

## Customization

Edit scanner parameters in the code:
```python
filtered = scanner.filter_high_volatility(
    df,
    min_price=1.0,          # Adjust price range
    max_price=10.0,
    min_volume=1_000_000,   # Volume requirement
    min_volatility=100.0,   # Higher for more aggressive
    min_atr_percent=5.0,    # Higher = bigger daily moves
    max_market_cap_m=1000.0 # Smaller = more volatile
)
```

## Notes

- **Data Source:** Yahoo Finance (yfinance)
- **Rate Limiting:** Built-in delays to respect API limits
- **Market Hours:** Best results during market hours (9:30 AM - 4 PM ET)
- **Risk Warning:** High volatility = high risk. These are speculative plays.

## Dependencies

```bash
pip install yfinance pandas numpy requests python-dotenv
```

### Required Packages:
- **yfinance**: Yahoo Finance data access
- **pandas**: Data manipulation and analysis
- **numpy**: Numerical computations
- **requests**: HTTP requests
- **python-dotenv**: Environment variable management

### API Keys Setup:
1. Create a `.env` file (see `.env.example`)
2. Add your Alpaca API credentials
3. The scanners will automatically load them on startup

## Next Steps

Consider integrating with:
- Your Alpaca trading infrastructure
- Real-time alert system (Telegram/Discord bot)
- Backtesting framework to validate strategies
- Risk management system for position sizing
