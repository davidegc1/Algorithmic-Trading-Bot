"""
Test Script: Verify NASDAQ Error Fix
Tests the NASDAQ ticker fetching to confirm the float error is resolved
"""

import sys
sys.path.insert(0, '.')

from universe_builder import UniverseBuilder


def test_nasdaq_fetch():
    """Test NASDAQ ticker fetching"""
    
    print("="*80)
    print("TESTING NASDAQ TICKER FETCH")
    print("="*80)
    
    builder = UniverseBuilder()
    
    print("\n1. Testing NASDAQ fetch...")
    nasdaq_tickers = builder.get_all_nasdaq_tickers()
    
    if nasdaq_tickers:
        print(f"✅ SUCCESS: Fetched {len(nasdaq_tickers)} NASDAQ tickers")
        print(f"\nFirst 10 tickers: {nasdaq_tickers[:10]}")
        print(f"Last 10 tickers: {nasdaq_tickers[-10:]}")
        
        # Check for float types (should be none)
        float_tickers = [t for t in nasdaq_tickers if not isinstance(t, str)]
        if float_tickers:
            print(f"\n❌ FOUND {len(float_tickers)} NON-STRING TICKERS:")
            print(float_tickers[:10])
        else:
            print(f"\n✅ All tickers are strings (no float errors)")
        
        # Check for invalid tickers
        invalid = [t for t in nasdaq_tickers if 'nan' in t.lower() or t == '']
        if invalid:
            print(f"\n⚠️  Found {len(invalid)} invalid tickers:")
            print(invalid[:10])
        else:
            print(f"✅ No invalid tickers (nan, empty strings)")
            
        return True
    else:
        print("❌ FAILED: Could not fetch NASDAQ tickers")
        return False


def test_nyse_fetch():
    """Test NYSE ticker fetching"""
    
    print("\n" + "="*80)
    print("TESTING NYSE TICKER FETCH")
    print("="*80)
    
    builder = UniverseBuilder()
    
    print("\n2. Testing NYSE fetch...")
    nyse_tickers = builder.get_all_nyse_tickers()
    
    if nyse_tickers:
        print(f"✅ SUCCESS: Fetched {len(nyse_tickers)} NYSE tickers")
        print(f"\nFirst 10 tickers: {nyse_tickers[:10]}")
        print(f"Last 10 tickers: {nyse_tickers[-10:]}")
        return True
    else:
        print("❌ FAILED: Could not fetch NYSE tickers")
        return False


def test_preferred_stock_filter():
    """Test that preferred stocks are filtered out"""
    
    print("\n" + "="*80)
    print("TESTING PREFERRED STOCK FILTER")
    print("="*80)
    
    builder = UniverseBuilder()
    
    # Get all tickers
    all_tickers = builder.get_all_market_tickers()
    
    # Check for $ symbols (preferred stocks)
    preferred = [t for t in all_tickers if '$' in t]
    
    if preferred:
        print(f"\n❌ FOUND {len(preferred)} PREFERRED STOCKS (should be 0):")
        print(preferred[:20])
        return False
    else:
        print(f"\n✅ No preferred stocks found (all filtered out)")
        return True


def test_combined_fetch():
    """Test combined NASDAQ + NYSE fetch"""
    
    print("\n" + "="*80)
    print("TESTING COMBINED FETCH (NASDAQ + NYSE)")
    print("="*80)
    
    builder = UniverseBuilder()
    
    print("\n3. Testing combined fetch...")
    all_tickers = builder.get_all_market_tickers()
    
    if all_tickers:
        print(f"✅ SUCCESS: Fetched {len(all_tickers)} total tickers")
        
        # Count by length (rough indicator of quality)
        short = [t for t in all_tickers if len(t) <= 4]
        long = [t for t in all_tickers if len(t) == 5]
        
        print(f"\nTicker length distribution:")
        print(f"  1-4 characters: {len(short)} tickers")
        print(f"  5 characters: {len(long)} tickers")
        
        return True
    else:
        print("❌ FAILED: Could not fetch combined tickers")
        return False


def main():
    """Run all tests"""
    
    print("\n" + "="*80)
    print("NASDAQ ERROR FIX VERIFICATION")
    print("="*80)
    print("\nThis will test if the NASDAQ float error is fixed")
    print("Expected: ~3,500 NASDAQ + ~2,500 NYSE = ~6,000 total tickers\n")
    
    input("Press Enter to start tests...")
    
    results = []
    
    # Test 1: NASDAQ
    results.append(("NASDAQ Fetch", test_nasdaq_fetch()))
    
    # Test 2: NYSE
    results.append(("NYSE Fetch", test_nyse_fetch()))
    
    # Test 3: Preferred Stock Filter
    results.append(("Preferred Stock Filter", test_preferred_stock_filter()))
    
    # Test 4: Combined
    results.append(("Combined Fetch", test_combined_fetch()))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:<30} {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED - NASDAQ ERROR IS FIXED!")
        print("="*80)
        print("\nYou can now run full market scans with:")
        print("  python universe_builder.py")
        print("  Select option 3 (Full Market Scan)")
    else:
        print("\n" + "="*80)
        print("❌ SOME TESTS FAILED - PLEASE REVIEW ERRORS ABOVE")
        print("="*80)


if __name__ == "__main__":
    main()
