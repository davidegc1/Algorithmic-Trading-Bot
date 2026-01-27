"""
ORDER EXECUTION UTILITIES
Robust order execution with proper polling, timeout, and error handling.
"""

import os
import time
import logging
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi

load_dotenv()

from core.shared_state import get_logs_dir

# Configure logging
logs_dir = get_logs_dir()
logger = logging.getLogger(__name__)


class OrderExecutor:
    """
    Handles order submission and monitoring with proper polling.

    Instead of just sleeping 2 seconds and hoping, this class:
    - Polls order status every 500ms
    - Handles timeouts gracefully
    - Manages partial fills
    - Provides detailed execution info
    """

    def __init__(
        self,
        api: tradeapi.REST,
        poll_interval_ms: int = 500,
        max_wait_seconds: int = 30
    ):
        """
        Initialize the order executor.

        Args:
            api: Alpaca REST API instance
            poll_interval_ms: Milliseconds between status checks (default 500)
            max_wait_seconds: Maximum time to wait for fill (default 30)
        """
        self.api = api
        self.poll_interval_ms = poll_interval_ms
        self.max_wait_seconds = max_wait_seconds

    def submit_and_wait(
        self,
        symbol: str,
        qty: int,
        side: str,
        order_type: str = 'market',
        time_in_force: str = 'day',
        limit_price: float = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Submit order and poll until filled or timeout.

        Args:
            symbol: Stock symbol
            qty: Number of shares
            side: 'buy' or 'sell'
            order_type: 'market' or 'limit' (default 'market')
            time_in_force: 'day', 'gtc', 'ioc' (default 'day')
            limit_price: Required for limit orders

        Returns:
            Tuple of (success: bool, result: dict)
            On success: {'filled_price': float, 'filled_qty': int, 'order_id': str}
            On failure: {'status': str, 'order_id': str, 'reason': str}
        """
        try:
            # Build order parameters
            order_params = {
                'symbol': symbol,
                'qty': qty,
                'side': side,
                'type': order_type,
                'time_in_force': time_in_force
            }

            if order_type == 'limit' and limit_price:
                order_params['limit_price'] = limit_price

            # Submit order
            logger.info(f"Submitting {side} order: {qty} {symbol} @ {order_type}")
            order = self.api.submit_order(**order_params)
            order_id = order.id

            # Poll for fill
            start_time = time.time()
            poll_count = 0

            while time.time() - start_time < self.max_wait_seconds:
                poll_count += 1
                order = self.api.get_order(order_id)

                if order.status == 'filled':
                    filled_price = float(order.filled_avg_price)
                    filled_qty = int(order.filled_qty)
                    elapsed = time.time() - start_time

                    logger.info(
                        f"Order FILLED: {symbol} {filled_qty} @ ${filled_price:.2f} "
                        f"(polls: {poll_count}, time: {elapsed:.1f}s)"
                    )

                    return True, {
                        'filled_price': filled_price,
                        'filled_qty': filled_qty,
                        'order_id': order_id,
                        'elapsed_seconds': elapsed,
                        'poll_count': poll_count
                    }

                if order.status in ['canceled', 'expired', 'rejected']:
                    logger.warning(f"Order {order.status}: {symbol} - {order_id}")
                    return False, {
                        'status': order.status,
                        'order_id': order_id,
                        'reason': f"Order was {order.status}"
                    }

                if order.status == 'partially_filled':
                    filled_qty = int(order.filled_qty) if order.filled_qty else 0
                    logger.info(f"Partial fill: {filled_qty}/{qty} for {symbol}")

                # Wait before next poll
                time.sleep(self.poll_interval_ms / 1000)

            # Timeout - cancel order
            logger.warning(f"Order TIMEOUT after {self.max_wait_seconds}s: {symbol}")

            try:
                self.api.cancel_order(order_id)
                logger.info(f"Cancelled timed-out order: {order_id}")
            except Exception as e:
                logger.error(f"Failed to cancel order: {e}")

            # Check if we got a partial fill
            order = self.api.get_order(order_id)
            if order.filled_qty and int(order.filled_qty) > 0:
                filled_price = float(order.filled_avg_price)
                filled_qty = int(order.filled_qty)
                return True, {
                    'filled_price': filled_price,
                    'filled_qty': filled_qty,
                    'order_id': order_id,
                    'partial': True,
                    'requested_qty': qty
                }

            return False, {
                'status': 'timeout',
                'order_id': order_id,
                'reason': f"Order did not fill within {self.max_wait_seconds}s"
            }

        except Exception as e:
            logger.error(f"Order execution error for {symbol}: {e}")
            return False, {
                'status': 'error',
                'order_id': None,
                'reason': str(e)
            }

    def submit_bracket_order(
        self,
        symbol: str,
        qty: int,
        side: str,
        stop_loss_price: float,
        take_profit_price: float = None,
        limit_price: float = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Submit a bracket order with stop loss (and optional take profit).

        Args:
            symbol: Stock symbol
            qty: Number of shares
            side: 'buy' or 'sell'
            stop_loss_price: Stop loss trigger price
            take_profit_price: Optional take profit price
            limit_price: Optional limit price for entry

        Returns:
            Tuple of (success, result_dict)
        """
        try:
            order_class = 'bracket' if take_profit_price else 'oto'

            order_params = {
                'symbol': symbol,
                'qty': qty,
                'side': side,
                'type': 'limit' if limit_price else 'market',
                'time_in_force': 'day',
                'order_class': order_class,
                'stop_loss': {'stop_price': stop_loss_price}
            }

            if limit_price:
                order_params['limit_price'] = limit_price

            if take_profit_price:
                order_params['take_profit'] = {'limit_price': take_profit_price}

            order = self.api.submit_order(**order_params)

            logger.info(
                f"Bracket order submitted: {symbol} {side} {qty} "
                f"SL=${stop_loss_price:.2f}"
            )

            return True, {
                'order_id': order.id,
                'status': order.status,
                'order_class': order_class
            }

        except Exception as e:
            logger.error(f"Bracket order error for {symbol}: {e}")
            return False, {
                'status': 'error',
                'reason': str(e)
            }

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get current status of an order."""
        try:
            order = self.api.get_order(order_id)
            return {
                'order_id': order.id,
                'symbol': order.symbol,
                'status': order.status,
                'side': order.side,
                'qty': int(order.qty),
                'filled_qty': int(order.filled_qty) if order.filled_qty else 0,
                'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None,
                'created_at': order.created_at,
                'filled_at': order.filled_at
            }
        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            return {'status': 'error', 'reason': str(e)}

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        try:
            self.api.cancel_order(order_id)
            logger.info(f"Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False

    def cancel_all_orders(self) -> int:
        """Cancel all open orders. Returns count of cancelled orders."""
        try:
            self.api.cancel_all_orders()
            logger.info("All orders cancelled")
            return -1  # Unknown count
        except Exception as e:
            logger.error(f"Error cancelling all orders: {e}")
            return 0


def calculate_position_size(
    portfolio_value: float,
    size_pct: float,
    price: float,
    slippage_buffer: float = 0.01
) -> int:
    """
    Calculate position size with slippage buffer.

    Args:
        portfolio_value: Total portfolio value
        size_pct: Position size as percentage (e.g., 0.05 for 5%)
        price: Current stock price
        slippage_buffer: Buffer for slippage (default 1%)

    Returns:
        Number of shares to buy
    """
    # Reduce size by slippage buffer to account for market orders
    effective_size = size_pct * (1 - slippage_buffer)
    position_value = portfolio_value * effective_size

    # Round down to whole shares
    shares = int(position_value / price)

    return max(1, shares)  # At least 1 share
