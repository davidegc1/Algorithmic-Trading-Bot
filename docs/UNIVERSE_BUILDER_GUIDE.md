# Dynamic Universe Building System

## 🎯 Overview

Instead of manually picking stocks, this system **automatically discovers** high-volatility stocks by screening the entire market (2,000 - 10,000 stocks) based on your criteria.

---

## 🚀 Quick Start

### Option 1: Quick Scan (Recommended for First Run)
```bash
python universe_builder.py
# Select option 1: Quick Scan (1000 stocks, ~20 minutes)
```

### Option 2: Targeted Scan (Best Balance)
```bash
python universe_builder.py
# Select option 2: Targeted Scan (specific sectors, ~15 minutes)
```

### Option 3: Full Market Scan (Most Comprehensive)
```bash
python universe_builder.py
# Select option 3: Full Market Scan (8000+ stocks, 2-3 hours)
```

---

## 📊 How It Works

### Step 1: Data Collection
The system fetches **all tradeable stocks** from:
- **NASDAQ** (~3,500 stocks)
- **NYSE** (~2,500 stocks)  
- **Total:** ~8,000-10,000 stocks

Source: Public NASDAQ FTP servers (free, official data)

### Step 2: Pre-Filtering
Quick filters applied **before** detailed analysis:
- ✅ Price: $0.50 - $50
- ✅ Volume: >500K shares/day
- ✅ Market Cap: <$5B
- ✅ Active trading (not delisted)

This reduces the universe to ~2,000-3,000 candidates.

### Step 3: Volatility Screening
For each remaining stock:
1. Download 1 month of price data
2. Calculate annualized volatility
3. Keep only stocks with **50%+ volatility**

### Step 4: Ranking & Selection
Final filters:
- Minimum 70% volatility
- Minimum 1M volume
- Maximum $2B market cap
- Select top 150-200 stocks

### Step 5: Output Generation
Creates three files:
1. **custom_universe.csv** - Full data with metrics
2. **custom_universe_tickers.txt** - Just ticker symbols
3. **custom_universe.py** - Python list for direct import

---

## 📁 Output Files

### custom_universe.csv
```csv
ticker,price,volume,market_cap,volatility,exchange
SAVA,3.45,2500000,450000000,145.32,NASDAQ
IONQ,12.34,3200000,1200000000,132.45,NYSE
...
```

### custom_universe.py
```python
CUSTOM_UNIVERSE = ['SAVA', 'IONQ', 'MARA', ...]

UNIVERSE_STATS = {
    'total_stocks': 200,
    'avg_volatility': 98.5,
    'avg_volume': 2500000,
    ...
}
```

---

## 🔄 Integration with Existing Scanners

### Automatic Integration
```bash
# After building universe, integrate it:
python universe_integration.py integrate
```

This automatically updates:
- `volatile_scanner_advanced.py`
- `volatile_stock_scanner.py`

Both will now use your dynamically discovered universe!

### Manual Integration
If you prefer manual control:

```python
# In your scanner file, replace get_expanded_universe() with:
def get_expanded_universe(self):
    from custom_universe import CUSTOM_UNIVERSE
    return CUSTOM_UNIVERSE
```

---

## ⏱️ Scan Modes Compared

| Mode | Stocks Scanned | Time | Best For |
|------|---------------|------|----------|
| **Quick** | 1,000 random | 15-20 min | Testing, daily updates |
| **Targeted** | 2,000 filtered | 15-25 min | Specific sectors, balanced approach |
| **Full** | 8,000+ all stocks | 2-3 hours | Weekly comprehensive scan |

---

## 🎯 Customization

### Adjust Screening Criteria

Edit `universe_builder.py`:

```python
# In quick_screen_ticker() method:
if price < 0.50 or price > 50:  # Change price range
if volume < 500_000:  # Change min volume
if volatility < 50:  # Change min volatility
```

### Adjust Final Filters

```python
# In rank_and_filter_universe():
final_universe = builder.rank_and_filter_universe(
    results_df,
    min_volatility=100,      # Raise for more aggressive
    min_volume=2_000_000,    # Raise for more liquid
    top_n=150                # Number of stocks in universe
)
```

---

## 📈 Workflow Examples

### Weekly Full Scan
```bash
# Sunday evening - build fresh universe
python universe_builder.py  # Select option 3 (Full)

# Takes 2-3 hours, run while sleeping
# Next morning:
python universe_integration.py integrate

# Use updated universe all week
python volatile_scanner_advanced.py
```

### Daily Quick Updates
```bash
# Each morning before market open (takes 20 min)
python universe_builder.py  # Select option 1 (Quick)
python universe_integration.py integrate
python volatile_scanner_advanced.py
```

### Sector-Focused Discovery
```bash
# Target specific sectors you're watching
python universe_builder.py  # Select option 2 (Targeted)

# Customizes for:
# - Biotech (BIO, GENE, THER, PHARM)
# - Tech (TECH, SOFT, AI, CYBER)
# - Crypto (CRYPTO, COIN, BLOCK)
# - Clean Energy (SOLAR, WIND, EV, BATTERY)
```

---

## 🔍 Advanced Features

### Multi-Exchange Coverage
```python
all_tickers = builder.get_all_market_tickers(
    include_nasdaq=True,   # ~3,500 stocks
    include_nyse=True,     # ~2,500 stocks
    include_sp500=False    # Optional: add S&P 500
)
```

### Batch Processing
- Processes 50 tickers at a time
- Automatic rate limiting (respects Yahoo Finance)
- Progress tracking with ETA
- Can pause/resume (saves results incrementally)

### Pattern-Based Filtering
```python
# In targeted scan mode, focuses on:
biotech_patterns = ['BIO', 'GENE', 'THER', 'PHARM']
tech_patterns = ['AI', 'CYBER', 'CLOUD', 'DATA']
crypto_patterns = ['CRYPTO', 'COIN', 'BLOCK']
```

---

## 💡 Pro Tips

### 1. Start with Quick Scan
Test the system with 1,000 stocks first. If results are good, run full scan.

### 2. Schedule Weekly Full Scans
Use cron/Task Scheduler to run full market scan weekly:
```bash
# Sunday 10 PM
0 22 * * 0 python /path/to/universe_builder.py
```

### 3. Compare Universes
Keep historical universes to track which stocks stay consistently volatile:
```bash
# Outputs are timestamped
custom_universe_20241212.csv
custom_universe_20241219.csv
```

### 4. Combine with Manual Picks
```python
# In scanner, combine discovered + manual:
discovered = get_discovered_universe()
manual = ['NVDA', 'TSLA', 'COIN']  # Your favorites
return discovered + manual
```

### 5. Filter by Exchange
```python
# Only NASDAQ stocks:
filtered = df[df['exchange'] == 'NASDAQ']

# Only NYSE stocks:
filtered = df[df['exchange'] == 'NYSE']
```

---

## 🚨 Important Notes

### Rate Limiting
- Yahoo Finance allows ~1-2 requests/second
- System auto-paces to stay under limits
- Full scan = ~8,000 requests over 2-3 hours

### Data Quality
- Some tickers may have incomplete data
- System automatically skips invalid tickers
- ~80-90% success rate typical

### Market Hours
- Can run anytime (uses historical data)
- Best to run outside market hours
- Data is typically 15-20 min delayed

### Storage
- Each universe ~50KB (CSV)
- Keep last 4-8 weeks for comparison
- Older ones can be archived/deleted

---

## 📊 Example Output

After running Quick Scan:

```
================================================================================
SCREENING 1000 TICKERS
This will take approximately 16 minutes
================================================================================

[1000/1000] ✓ ZYME - 142.3% vol

✓ Screening complete in 18.2 minutes
✓ Found 156 high-volatility candidates

================================================================================
APPLYING FINAL FILTERS
================================================================================

After filters: 143 stocks
Top 100 selected for universe

================================================================================
TOP 20 HIGH-VOLATILITY STOCKS DISCOVERED
================================================================================

ticker  price  volume  market_cap  volatility  exchange
  SAVA   3.45 2500000   450000000      145.32   NASDAQ
  IONQ  12.34 3200000  1200000000      132.45      NYSE
  MARA  18.92 5600000  2000000000      128.73   NASDAQ
   ...
```

---

## 🔄 Maintenance

### Weekly
- Run full market scan
- Review top discoveries
- Update scanners with new universe

### Daily  
- Run quick scan for fresh opportunities
- Check for new IPOs or delistings
- Monitor universe performance

### Monthly
- Compare current vs previous month universes
- Identify consistently volatile stocks
- Adjust screening criteria if needed

---

## 🎓 Next Steps

1. **Run your first scan:** `python universe_builder.py`
2. **Integrate results:** `python universe_integration.py integrate`
3. **Use in scanners:** `python volatile_scanner_advanced.py`
4. **Refine criteria** based on results
5. **Automate** weekly/daily runs

Your scanners will now dynamically discover the most volatile stocks in the entire market! 🚀
