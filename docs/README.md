# Documentation

## 📚 Available Guides

### Core Documentation
- [**Volatility Guide**](VOLATILITY_GUIDE.md) - How volatility is measured and used
- [**Multi-Timeframe Trading Guide**](MULTITIMEFRAME_TRADING_GUIDE.md) - Trading with multiple volatility timeframes
- [**Scanner Documentation**](README_SCANNERS.md) - Overview of all scanner tools

### Universe Management
- [**Universe Builder Guide**](UNIVERSE_BUILDER_GUIDE.md) - Creating stock universes
- [**Universe Directory Guide**](UNIVERSE_DIRECTORY_GUIDE.md) - Organizing multiple universes

### Reference
- [**Changelog**](CHANGELOG_CLEANED_TICKERS.md) - Removed tickers and updates
- [**Repo Structure**](REPO_STRUCTURE_GUIDE.md) - Project organization

## 🎯 Getting Started

1. Start with [Scanner Documentation](README_SCANNERS.md) for overview
2. Read [Universe Builder Guide](UNIVERSE_BUILDER_GUIDE.md) to create your first universe
3. Study [Volatility Guide](VOLATILITY_GUIDE.md) to understand the metrics
4. Use [Multi-Timeframe Trading Guide](MULTITIMEFRAME_TRADING_GUIDE.md) for trading strategies

## 📖 Quick Reference

### Key Concepts

**Volatility**: Standard deviation of returns, annualized
- 70-100%: Moderate-high volatility
- 100-150%: High-aggressive volatility
- 150%+: Ultra-aggressive volatility

**Universe**: Curated list of stocks meeting your criteria

**Volatility Regime**: Direction of volatility trend
- Accelerating: Volatility increasing (best for trading)
- Decelerating: Volatility decreasing (time to exit)
- Mixed: Uncertain direction

### Common Tasks

**Create Universe:**
```bash
python scripts/universe_builder.py
```

**Run Scanner:**
```bash
python scripts/volatile_scanner_advanced.py
```

**Manage Universes:**
```bash
python scripts/universe_manager.py
```

**Monitor Watchlist:**
```bash
python scripts/watchlist_monitor.py
```
