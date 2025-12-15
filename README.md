# High Volatility Stock Scanner

Aggressive trading system for finding 100-500% gain opportunities in volatile stocks.

## 🎯 Features

- **Universe Builder**: Dynamically build stock universes from 8,000+ stocks
- **Multi-Timeframe Volatility**: Track volatility across daily, weekly, monthly, quarterly, and annual periods
- **Advanced Scanners**: Multiple scanning strategies for different trading styles
- **Real-Time Monitoring**: Live watchlist tracking with alerts
- **Universe Management**: Organize and switch between multiple universes

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up API keys
cp .env.example .env
# Edit .env and add your Alpaca API keys

# Build a universe
python scripts/universe_builder.py

# Run scanner
python scripts/volatile_scanner_advanced.py

# Monitor watchlist
python scripts/watchlist_monitor.py
```

## 📁 Project Structure

```
trading/
├── scripts/        # All executable scripts
├── docs/          # Documentation and guides
├── universes/     # Generated stock universes
├── data/          # Active universe and backups
├── results/       # Scan outputs
└── config/        # Configuration files
```

## 📖 Documentation

See [docs/](docs/) for comprehensive guides:
- [Volatility Guide](docs/VOLATILITY_GUIDE.md) - Understanding volatility metrics
- [Multi-Timeframe Trading](docs/MULTITIMEFRAME_TRADING_GUIDE.md) - Trading strategies
- [Universe Builder](docs/UNIVERSE_BUILDER_GUIDE.md) - Creating universes
- [Scanner Documentation](docs/README_SCANNERS.md) - Scanner features

## ⚙️ Requirements

- Python 3.8+
- yfinance, pandas, numpy, requests, python-dotenv
- Optional: Alpaca API account for trading integration

## 📊 Example Usage

```python
# Import and use programmatically
from scripts.universe_builder import UniverseBuilder

builder = UniverseBuilder()
builder.quick_scan(n_stocks=1000)
```

## 🤝 Contributing

Feel free to submit issues, fork the repository, and create pull requests.

## 📄 License

MIT License - See LICENSE file for details
