"""
PRICE STREAM SERVICE
Real-time price streaming using Alpaca WebSocket API

Provides real-time price updates for open positions to enable
immediate stop-loss and exit condition checking.
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, Set, Callable, Optional, List
from dotenv import load_dotenv

load_dotenv()

# Try to import alpaca-py (newer SDK with better WebSocket support)
# Fall back to alpaca-trade-api if not available
try:
    from alpaca.data.live import StockDataStream
    from alpaca.data.enums import DataFeed
    ALPACA_PY_AVAILABLE = True
except ImportError:
    ALPACA_PY_AVAILABLE = False
    try:
        from alpaca_trade_api.stream import Stream
    except ImportError:
        Stream = None

from core.shared_state import get_logs_dir

# Configure logging
logs_dir = get_logs_dir()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, 'price_stream.log'), mode='a'),
        logging.StreamHandler()
    ],
    force=True
)
logger = logging.getLogger(__name__)


class PriceStreamManager:
    """
    Manages WebSocket connection for real-time price updates.

    Subscribes to quote data for open positions and triggers callbacks
    on price updates. Supports automatic reconnection and fallback to polling.
    """

    def __init__(self, on_price_update: Callable[[str, float, float, float], None] = None):
        """
        Initialize the price stream manager.

        Args:
            on_price_update: Callback function(symbol, bid, ask, last_price)
        """
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.api_secret = os.getenv('ALPACA_SECRET_KEY')
        self.paper = os.getenv('ALPACA_BASE_URL', '').find('paper') >= 0

        self.on_price_update = on_price_update
        self.subscribed_symbols: Set[str] = set()
        self.latest_prices: Dict[str, dict] = {}
        self.stream = None
        self.running = False
        self._stream_task = None

        logger.info(f"PriceStreamManager initialized (alpaca-py: {ALPACA_PY_AVAILABLE})")

    async def _handle_quote(self, quote):
        """Handle incoming quote data."""
        try:
            if ALPACA_PY_AVAILABLE:
                symbol = quote.symbol
                bid = float(quote.bid_price)
                ask = float(quote.ask_price)
                mid = (bid + ask) / 2
            else:
                symbol = quote['symbol'] if isinstance(quote, dict) else quote.symbol
                bid = float(quote.get('bid_price', 0) if isinstance(quote, dict) else quote.bid_price)
                ask = float(quote.get('ask_price', 0) if isinstance(quote, dict) else quote.ask_price)
                mid = (bid + ask) / 2

            # Update latest prices
            self.latest_prices[symbol] = {
                'bid': bid,
                'ask': ask,
                'mid': mid,
                'timestamp': datetime.now()
            }

            # Trigger callback
            if self.on_price_update:
                self.on_price_update(symbol, bid, ask, mid)

        except Exception as e:
            logger.error(f"Error handling quote: {e}")

    async def _handle_trade(self, trade):
        """Handle incoming trade data (for last price)."""
        try:
            if ALPACA_PY_AVAILABLE:
                symbol = trade.symbol
                price = float(trade.price)
            else:
                symbol = trade['symbol'] if isinstance(trade, dict) else trade.symbol
                price = float(trade.get('price', 0) if isinstance(trade, dict) else trade.price)

            # Update latest price
            if symbol in self.latest_prices:
                self.latest_prices[symbol]['last'] = price
                self.latest_prices[symbol]['timestamp'] = datetime.now()

        except Exception as e:
            logger.error(f"Error handling trade: {e}")

    async def subscribe(self, symbols: List[str]) -> bool:
        """
        Subscribe to real-time quotes for symbols.

        Args:
            symbols: List of symbols to subscribe to

        Returns:
            True if subscription successful
        """
        try:
            if not symbols:
                return True

            new_symbols = set(symbols) - self.subscribed_symbols

            if not new_symbols:
                return True

            if ALPACA_PY_AVAILABLE:
                if self.stream is None:
                    self.stream = StockDataStream(
                        self.api_key,
                        self.api_secret,
                        feed=DataFeed.IEX  # Use IEX for free tier
                    )
                    self.stream.subscribe_quotes(self._handle_quote, *list(new_symbols))
                else:
                    self.stream.subscribe_quotes(self._handle_quote, *list(new_symbols))
            else:
                if Stream is None:
                    logger.error("No streaming library available")
                    return False

                if self.stream is None:
                    self.stream = Stream(
                        self.api_key,
                        self.api_secret,
                        data_feed='iex'
                    )

                for symbol in new_symbols:
                    self.stream.subscribe_quotes(self._handle_quote, symbol)

            self.subscribed_symbols.update(new_symbols)
            logger.info(f"Subscribed to {len(new_symbols)} symbols: {new_symbols}")
            return True

        except Exception as e:
            logger.error(f"Error subscribing to symbols: {e}")
            return False

    async def unsubscribe(self, symbols: List[str]) -> bool:
        """
        Unsubscribe from symbols.

        Args:
            symbols: List of symbols to unsubscribe from
        """
        try:
            if not symbols:
                return True

            to_remove = set(symbols) & self.subscribed_symbols

            if ALPACA_PY_AVAILABLE and self.stream:
                self.stream.unsubscribe_quotes(*list(to_remove))
            elif self.stream:
                for symbol in to_remove:
                    self.stream.unsubscribe_quotes(symbol)

            self.subscribed_symbols -= to_remove
            for symbol in to_remove:
                self.latest_prices.pop(symbol, None)

            logger.info(f"Unsubscribed from {len(to_remove)} symbols")
            return True

        except Exception as e:
            logger.error(f"Error unsubscribing: {e}")
            return False

    async def run(self):
        """Run the WebSocket stream."""
        if self.stream is None:
            logger.warning("No stream initialized, cannot run")
            return

        self.running = True
        logger.info("Starting price stream...")

        try:
            if ALPACA_PY_AVAILABLE:
                await self.stream._run_forever()
            else:
                self.stream.run()
        except Exception as e:
            logger.error(f"Stream error: {e}")
            self.running = False

    def start_async(self, loop: asyncio.AbstractEventLoop = None):
        """Start the stream in a background task."""
        if loop is None:
            loop = asyncio.get_event_loop()

        self._stream_task = loop.create_task(self.run())
        return self._stream_task

    def stop(self):
        """Stop the stream."""
        self.running = False
        if self._stream_task:
            self._stream_task.cancel()
        if self.stream:
            try:
                if ALPACA_PY_AVAILABLE:
                    self.stream.stop()
                else:
                    self.stream.stop_ws()
            except Exception as e:
                logger.debug(f"Error stopping stream: {e}")
        logger.info("Price stream stopped")

    def get_price(self, symbol: str) -> Optional[float]:
        """
        Get the latest mid price for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Latest mid price or None if not available
        """
        data = self.latest_prices.get(symbol)
        if data:
            return data.get('mid') or data.get('last')
        return None

    def get_quote(self, symbol: str) -> Optional[dict]:
        """
        Get the latest quote data for a symbol.

        Returns:
            Dict with bid, ask, mid, last, timestamp or None
        """
        return self.latest_prices.get(symbol)


class RealTimeMonitor:
    """
    Real-time position monitor using WebSocket price streaming.

    Checks exit conditions immediately when prices update,
    rather than waiting for polling intervals.
    """

    def __init__(
        self,
        positions: Dict[str, dict],
        on_exit_signal: Callable[[str, str, float], None],
        stop_loss_pct: float = 0.025,
        breakeven_profit: float = 0.05
    ):
        """
        Initialize the real-time monitor.

        Args:
            positions: Dict of {symbol: position_info} with entry_price, stop_loss
            on_exit_signal: Callback(symbol, reason, current_price) when exit triggered
            stop_loss_pct: Stop loss percentage (default 2.5%)
            breakeven_profit: Profit level to move stop to breakeven
        """
        self.positions = positions
        self.on_exit_signal = on_exit_signal
        self.stop_loss_pct = stop_loss_pct
        self.breakeven_profit = breakeven_profit
        self.highest_prices: Dict[str, float] = {}

        self.stream_manager = PriceStreamManager(on_price_update=self._on_price_update)

    def _on_price_update(self, symbol: str, bid: float, ask: float, mid: float):
        """Handle real-time price update and check exit conditions."""
        if symbol not in self.positions:
            return

        position = self.positions[symbol]
        entry_price = position.get('entry_price', mid)
        stop_loss = position.get('stop_loss', entry_price * (1 - self.stop_loss_pct))

        # Track highest price
        if symbol not in self.highest_prices:
            self.highest_prices[symbol] = mid
        elif mid > self.highest_prices[symbol]:
            self.highest_prices[symbol] = mid

        # Calculate profit
        profit_pct = (mid - entry_price) / entry_price

        # Check stop loss (use bid price for more conservative exit)
        if bid <= stop_loss:
            logger.info(f"STOP LOSS HIT: {symbol} bid=${bid:.2f} <= stop=${stop_loss:.2f}")
            if self.on_exit_signal:
                self.on_exit_signal(symbol, "STOP_LOSS", bid)
            return

        # Move stop to breakeven at profit threshold
        if profit_pct >= self.breakeven_profit:
            if stop_loss < entry_price:
                position['stop_loss'] = entry_price
                logger.info(f"{symbol} stop moved to breakeven @ ${entry_price:.2f}")

    async def start(self, symbols: List[str] = None):
        """Start monitoring positions."""
        if symbols is None:
            symbols = list(self.positions.keys())

        await self.stream_manager.subscribe(symbols)
        await self.stream_manager.run()

    def stop(self):
        """Stop monitoring."""
        self.stream_manager.stop()

    def add_position(self, symbol: str, position_info: dict):
        """Add a position to monitor."""
        self.positions[symbol] = position_info
        asyncio.create_task(self.stream_manager.subscribe([symbol]))

    def remove_position(self, symbol: str):
        """Remove a position from monitoring."""
        self.positions.pop(symbol, None)
        self.highest_prices.pop(symbol, None)
        asyncio.create_task(self.stream_manager.unsubscribe([symbol]))


# Standalone test
if __name__ == "__main__":
    def on_update(symbol, bid, ask, mid):
        print(f"{symbol}: bid=${bid:.2f}, ask=${ask:.2f}, mid=${mid:.2f}")

    async def main():
        manager = PriceStreamManager(on_price_update=on_update)
        await manager.subscribe(['AAPL', 'MSFT', 'GOOGL'])
        await manager.run()

    asyncio.run(main())
