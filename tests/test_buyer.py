"""
Unit tests for the OrderBuyer module v2.1
Tests price validation, signal expiry, and slippage protection
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import (
    SIGNAL_MAX_AGE_SECONDS,
    MAX_SLIPPAGE_PCT,
    MAX_SPREAD_PCT,
    USE_LIMIT_ORDERS,
    LIMIT_ORDER_BUFFER,
    HOT_SIGNAL_ENABLED,
    HOT_SIGNAL_MIN_SCORE,
)


class TestBuyerConfig:
    """Tests for buyer configuration parameters"""

    def test_signal_max_age(self):
        """Signal max age should be 60 seconds"""
        assert SIGNAL_MAX_AGE_SECONDS == 60

    def test_max_slippage(self):
        """Max slippage should be 2%"""
        assert MAX_SLIPPAGE_PCT == 0.02

    def test_max_spread(self):
        """Max spread should be 2%"""
        assert MAX_SPREAD_PCT == 0.02

    def test_limit_orders_enabled(self):
        """Limit orders should be enabled"""
        assert USE_LIMIT_ORDERS is True

    def test_limit_order_buffer(self):
        """Limit order buffer should be 0.5%"""
        assert LIMIT_ORDER_BUFFER == 0.005

    def test_hot_signal_enabled(self):
        """Hot signal should be enabled"""
        assert HOT_SIGNAL_ENABLED is True

    def test_hot_signal_min_score(self):
        """Hot signal min score should be 90"""
        assert HOT_SIGNAL_MIN_SCORE == 90


class TestSignalExpiry:
    """Tests for signal expiry logic"""

    def test_fresh_signal_valid(self):
        """Signal within 60 seconds should be valid"""
        signal_time = datetime.now()
        age = (datetime.now() - signal_time).total_seconds()
        assert age < SIGNAL_MAX_AGE_SECONDS

    def test_old_signal_expired(self):
        """Signal older than 60 seconds should be expired"""
        signal_time = datetime.now() - timedelta(seconds=61)
        age = (datetime.now() - signal_time).total_seconds()
        assert age > SIGNAL_MAX_AGE_SECONDS

    def test_signal_at_boundary(self):
        """Signal at exactly 60 seconds should be expired"""
        signal_time = datetime.now() - timedelta(seconds=60)
        age = (datetime.now() - signal_time).total_seconds()
        assert age >= SIGNAL_MAX_AGE_SECONDS


class TestSlippageCalculation:
    """Tests for slippage calculation"""

    def test_no_slippage(self):
        """Same price = 0% slippage"""
        signal_price = 10.0
        current_price = 10.0
        slippage = (current_price - signal_price) / signal_price
        assert slippage == 0.0

    def test_positive_slippage_acceptable(self):
        """1% slippage should be acceptable"""
        signal_price = 10.0
        current_price = 10.10  # 1% higher
        slippage = (current_price - signal_price) / signal_price
        assert slippage == pytest.approx(0.01, rel=0.01)
        assert slippage <= MAX_SLIPPAGE_PCT

    def test_excessive_slippage_rejected(self):
        """3% slippage should be rejected"""
        signal_price = 10.0
        current_price = 10.30  # 3% higher
        slippage = (current_price - signal_price) / signal_price
        assert slippage == pytest.approx(0.03, rel=0.01)
        assert slippage > MAX_SLIPPAGE_PCT

    def test_negative_slippage_acceptable(self):
        """Negative slippage (price dropped) should be acceptable"""
        signal_price = 10.0
        current_price = 9.90  # 1% lower
        slippage = (current_price - signal_price) / signal_price
        assert slippage == pytest.approx(-0.01, rel=0.01)
        assert abs(slippage) <= MAX_SLIPPAGE_PCT


class TestSpreadCalculation:
    """Tests for bid-ask spread calculation"""

    def test_tight_spread_acceptable(self):
        """0.5% spread should be acceptable"""
        bid = 10.00
        ask = 10.05
        mid = (bid + ask) / 2
        spread_pct = (ask - bid) / mid
        assert spread_pct == pytest.approx(0.005, rel=0.01)
        assert spread_pct <= MAX_SPREAD_PCT

    def test_wide_spread_rejected(self):
        """3% spread should be rejected"""
        bid = 10.00
        ask = 10.30
        mid = (bid + ask) / 2
        spread_pct = (ask - bid) / mid
        assert spread_pct > MAX_SPREAD_PCT

    def test_spread_at_limit(self):
        """2% spread should be at limit"""
        bid = 10.00
        ask = 10.20
        mid = (bid + ask) / 2
        spread_pct = (ask - bid) / mid
        assert spread_pct == pytest.approx(0.0198, rel=0.01)
        assert spread_pct <= MAX_SPREAD_PCT


class TestLimitOrderBuffer:
    """Tests for limit order price calculation"""

    def test_limit_price_with_buffer(self):
        """Limit order should add buffer to ask price"""
        ask_price = 10.00
        limit_price = ask_price * (1 + LIMIT_ORDER_BUFFER)
        assert limit_price == pytest.approx(10.05, rel=0.01)

    def test_buffer_percentage(self):
        """Buffer should be 0.5%"""
        base = 100.0
        buffered = base * (1 + LIMIT_ORDER_BUFFER)
        assert buffered == pytest.approx(100.5, rel=0.001)


class TestHotSignalCriteria:
    """Tests for hot signal detection"""

    def test_hot_signal_qualifies(self):
        """Score >= 90 should qualify as hot"""
        score = 90
        assert score >= HOT_SIGNAL_MIN_SCORE

    def test_below_hot_threshold(self):
        """Score < 90 should not be hot"""
        score = 85
        assert score < HOT_SIGNAL_MIN_SCORE

    def test_max_score_is_hot(self):
        """Max score (95) should be hot"""
        score = 95
        assert score >= HOT_SIGNAL_MIN_SCORE


class TestPositionSizing:
    """Tests for position sizing based on score"""

    def test_standard_tier(self):
        """Score 60-84 should use standard size (5%)"""
        from config.config import SCORE_TIER_STANDARD, POSITION_SIZE_STANDARD
        score = 65
        # SCORE_TIER_STANDARD is a tuple (min, max)
        assert SCORE_TIER_STANDARD[0] <= score <= SCORE_TIER_STANDARD[1]
        assert POSITION_SIZE_STANDARD == 0.05

    def test_strong_tier(self):
        """Score 85-94 should use strong size (7%)"""
        from config.config import SCORE_TIER_STRONG, POSITION_SIZE_STRONG
        score = 90
        # SCORE_TIER_STRONG is a tuple (min, max)
        assert SCORE_TIER_STRONG[0] <= score <= SCORE_TIER_STRONG[1]
        assert POSITION_SIZE_STRONG == 0.07

    def test_maximum_tier(self):
        """Score 95+ should use maximum size (10%)"""
        from config.config import SCORE_TIER_MAXIMUM, POSITION_SIZE_MAXIMUM
        score = 95
        # SCORE_TIER_MAXIMUM is a tuple (min, max)
        assert SCORE_TIER_MAXIMUM[0] <= score <= SCORE_TIER_MAXIMUM[1]
        assert POSITION_SIZE_MAXIMUM == 0.10


class TestSignalStructure:
    """Tests for expected signal structure"""

    def test_signal_has_required_fields(self):
        """Signal should have all required fields"""
        signal = {
            'symbol': 'TEST',
            'signal_type': 'BUY',
            'signal_price': 10.0,
            'score': 75,
            'timestamp': datetime.now().isoformat(),
            'metrics': {
                'vwap': 9.5,
                'rsi': 55,
                'breakout_pct': 0.02,
                'relative_volume': 3.0
            }
        }

        required_fields = ['symbol', 'signal_type', 'signal_price', 'score', 'timestamp']
        for field in required_fields:
            assert field in signal

    def test_metrics_structure(self):
        """Metrics should contain technical indicators"""
        metrics = {
            'vwap': 9.5,
            'rsi': 55,
            'breakout_pct': 0.02,
            'relative_volume': 3.0,
            'breakout_ref': 'premarket_high'
        }

        expected_keys = ['vwap', 'rsi', 'breakout_pct', 'relative_volume']
        for key in expected_keys:
            assert key in metrics


class TestModuleImport:
    """Tests for module import"""

    def test_import_buyer(self):
        """OrderBuyer should be importable"""
        from core.buyer import OrderBuyer
        assert OrderBuyer is not None

    def test_import_main_function(self):
        """main function should be importable"""
        from core.buyer import main
        assert main is not None


class TestPriceValidation:
    """Tests for price validation logic"""

    @pytest.fixture
    def mock_buyer(self):
        """Create a mock buyer for testing"""
        from core.buyer import OrderBuyer

        with patch.object(OrderBuyer, '__init__', lambda self: None):
            buyer = OrderBuyer()
            buyer.MAX_SLIPPAGE_PCT = MAX_SLIPPAGE_PCT
            buyer.MAX_SPREAD_PCT = MAX_SPREAD_PCT
            buyer.USE_LIMIT_ORDERS = USE_LIMIT_ORDERS
            buyer.LIMIT_ORDER_BUFFER = LIMIT_ORDER_BUFFER
            buyer.api = Mock()
            return buyer

    def test_validate_price_accepts_good_quote(self, mock_buyer):
        """Good quote with tight spread should pass"""
        # Mock quote with tight spread
        mock_quote = Mock()
        mock_quote.bid_price = 10.00
        mock_quote.ask_price = 10.05
        mock_buyer.api.get_latest_quote.return_value = mock_quote

        is_valid, price, reason = mock_buyer.validate_price('TEST', 10.02)

        assert is_valid is True
        assert price == pytest.approx(10.05, rel=0.01)  # Ask price

    def test_validate_price_rejects_wide_spread(self, mock_buyer):
        """Wide spread should fail validation"""
        mock_quote = Mock()
        mock_quote.bid_price = 10.00
        mock_quote.ask_price = 10.50  # 5% spread
        mock_buyer.api.get_latest_quote.return_value = mock_quote

        is_valid, price, reason = mock_buyer.validate_price('TEST', 10.00)

        assert is_valid is False
        assert 'spread' in reason.lower()

    def test_validate_price_rejects_slippage(self, mock_buyer):
        """Excessive slippage should fail validation"""
        mock_quote = Mock()
        mock_quote.bid_price = 10.50
        mock_quote.ask_price = 10.55  # Tight spread but price moved up
        mock_buyer.api.get_latest_quote.return_value = mock_quote

        # Signal price was 10.00, current ask is 10.55 (5.5% slippage)
        is_valid, price, reason = mock_buyer.validate_price('TEST', 10.00)

        assert is_valid is False
        assert 'slippage' in reason.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
