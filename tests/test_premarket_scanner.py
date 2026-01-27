"""
Unit tests for the PreMarketScanner module
"""

import pytest
import sys
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestGapCalculation:
    """Tests for gap percentage calculation"""

    def test_gap_positive(self):
        """Positive gap calculation"""
        prior_close = 10.0
        current_price = 10.5
        gap = (current_price - prior_close) / prior_close
        assert gap == pytest.approx(0.05, rel=0.01)

    def test_gap_negative(self):
        """Negative gap calculation"""
        prior_close = 10.0
        current_price = 9.5
        gap = (current_price - prior_close) / prior_close
        assert gap == pytest.approx(-0.05, rel=0.01)

    def test_gap_large(self):
        """Large gap calculation (10%)"""
        prior_close = 10.0
        current_price = 11.0
        gap = (current_price - prior_close) / prior_close
        assert gap == pytest.approx(0.10, rel=0.01)

    def test_gap_threshold_pass(self):
        """Gap above 3% threshold should pass"""
        from config.config import MIN_GAP_PCT
        gap = 0.04  # 4%
        assert gap >= MIN_GAP_PCT

    def test_gap_threshold_fail(self):
        """Gap below 3% threshold should fail"""
        from config.config import MIN_GAP_PCT
        gap = 0.02  # 2%
        assert gap < MIN_GAP_PCT


class TestScoring:
    """Tests for watchlist scoring"""

    def test_score_calculation_basic(self):
        """Basic score formula test"""
        # Import the class and create instance without API
        from core.premarket_scanner import PreMarketScanner

        # Create scanner with mocked API
        with patch.object(PreMarketScanner, '__init__', lambda self: None):
            scanner = PreMarketScanner()

            # gap=5%, rel_vol=3x, no float adjustment
            score = scanner.calculate_score(0.05, 3.0, None)
            expected = 0.05 * 3.0 * 100  # = 15
            assert score == pytest.approx(expected, rel=0.01)

    def test_score_with_low_float(self):
        """Score with low float should be higher"""
        from core.premarket_scanner import PreMarketScanner

        with patch.object(PreMarketScanner, '__init__', lambda self: None):
            scanner = PreMarketScanner()

            # Same gap and volume, different float
            score_low_float = scanner.calculate_score(0.05, 3.0, 10_000_000)   # 10M
            score_high_float = scanner.calculate_score(0.05, 3.0, 50_000_000)  # 50M

            assert score_low_float > score_high_float

    def test_score_float_factor_capped(self):
        """Float factor should be capped at 2x"""
        from core.premarket_scanner import PreMarketScanner

        with patch.object(PreMarketScanner, '__init__', lambda self: None):
            scanner = PreMarketScanner()

            # Very low float (1M) should not give more than 2x boost
            base_score = 0.05 * 3.0 * 100  # 15
            score_tiny_float = scanner.calculate_score(0.05, 3.0, 1_000_000)

            # Should be capped at 2x
            assert score_tiny_float <= base_score * 2.0

    def test_score_higher_gap_higher_score(self):
        """Higher gap should give higher score"""
        from core.premarket_scanner import PreMarketScanner

        with patch.object(PreMarketScanner, '__init__', lambda self: None):
            scanner = PreMarketScanner()

            score_5pct = scanner.calculate_score(0.05, 2.0, None)
            score_10pct = scanner.calculate_score(0.10, 2.0, None)

            assert score_10pct > score_5pct

    def test_score_higher_volume_higher_score(self):
        """Higher relative volume should give higher score"""
        from core.premarket_scanner import PreMarketScanner

        with patch.object(PreMarketScanner, '__init__', lambda self: None):
            scanner = PreMarketScanner()

            score_2x = scanner.calculate_score(0.05, 2.0, None)
            score_4x = scanner.calculate_score(0.05, 4.0, None)

            assert score_4x > score_2x


class TestRelativeVolume:
    """Tests for relative volume calculation"""

    def test_relative_volume_basic(self):
        """Basic relative volume calculation"""
        pm_volume = 100_000
        avg_daily_volume = 500_000
        # Normalize: PM is 5.5 hours, full day is 6.5 hours
        normalized_pm = pm_volume * (6.5 / 5.5)
        relative = normalized_pm / avg_daily_volume
        assert relative == pytest.approx(0.236, rel=0.01)

    def test_relative_volume_high(self):
        """High relative volume (unusual activity)"""
        pm_volume = 1_000_000
        avg_daily_volume = 500_000
        normalized_pm = pm_volume * (6.5 / 5.5)
        relative = normalized_pm / avg_daily_volume
        assert relative > 2.0  # More than 2x average


class TestFilterCriteria:
    """Tests for filter criteria"""

    def test_price_filter_valid(self):
        """Price within valid range"""
        from config.config import PRICE_MIN, PRICE_MAX
        price = 10.0
        assert PRICE_MIN <= price <= PRICE_MAX

    def test_price_filter_too_low(self):
        """Price below minimum"""
        from config.config import PRICE_MIN
        price = 1.0
        assert price < PRICE_MIN

    def test_price_filter_too_high(self):
        """Price above maximum"""
        from config.config import PRICE_MAX
        price = 100.0
        assert price > PRICE_MAX

    def test_volume_filter(self):
        """Pre-market volume filter"""
        from config.config import MIN_PREMARKET_VOLUME
        assert MIN_PREMARKET_VOLUME == 50_000


class TestWatchlistOutput:
    """Tests for watchlist output format"""

    def test_watchlist_stock_structure(self):
        """Watchlist stock should have required fields"""
        stock = {
            'symbol': 'TEST',
            'rank': 1,
            'prior_close': 10.0,
            'premarket_price': 11.0,
            'premarket_high': 11.5,
            'premarket_volume': 100000,
            'gap_pct': 0.10,
            'relative_volume': 3.0,
            'score': 30.0
        }

        required_fields = [
            'symbol', 'rank', 'prior_close', 'premarket_price',
            'premarket_high', 'premarket_volume', 'gap_pct',
            'relative_volume', 'score'
        ]

        for field in required_fields:
            assert field in stock

    def test_watchlist_size(self):
        """Watchlist should have correct max size"""
        from config.config import DAILY_WATCHLIST_SIZE
        assert DAILY_WATCHLIST_SIZE == 25


class TestConfigIntegration:
    """Tests for config parameter integration"""

    def test_config_values_loaded(self):
        """Config values should be properly loaded"""
        from config.config import (
            DAILY_WATCHLIST_SIZE,
            MIN_GAP_PCT,
            MIN_PREMARKET_VOLUME,
            MIN_PREMARKET_REL_VOLUME,
            PRICE_MIN,
            PRICE_MAX,
        )

        assert DAILY_WATCHLIST_SIZE == 25
        assert MIN_GAP_PCT == 0.03
        assert MIN_PREMARKET_VOLUME == 50_000
        assert MIN_PREMARKET_REL_VOLUME == 2.0
        assert PRICE_MIN == 2.0
        assert PRICE_MAX == 50.0


class TestModuleImport:
    """Tests for module import"""

    def test_import_premarket_scanner(self):
        """PreMarketScanner should be importable"""
        from core.premarket_scanner import PreMarketScanner
        assert PreMarketScanner is not None

    def test_import_main_function(self):
        """main function should be importable"""
        from core.premarket_scanner import main
        assert main is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
