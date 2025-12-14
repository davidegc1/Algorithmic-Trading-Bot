"""
Universe Integration Script
Automatically updates scanners with dynamically discovered universe
"""

import sys
import os
from datetime import datetime


def integrate_universe_with_scanners(universe_file: str = 'custom_universe.py'):
    """
    Update scanner files to use custom universe instead of hardcoded lists
    """
    
    if not os.path.exists(universe_file):
        print(f"❌ Universe file '{universe_file}' not found")
        print("Run universe_builder.py first to generate the universe")
        return False
    
    # Import the custom universe
    import importlib.util
    spec = importlib.util.spec_from_file_location("custom_universe", universe_file)
    universe_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(universe_module)
    
    universe_tickers = universe_module.CUSTOM_UNIVERSE
    stats = universe_module.UNIVERSE_STATS
    
    print(f"\n{'='*80}")
    print("INTEGRATING CUSTOM UNIVERSE WITH SCANNERS")
    print(f"{'='*80}\n")
    print(f"Universe: {len(universe_tickers)} stocks")
    print(f"Average Volatility: {stats['avg_volatility']}%")
    print(f"Generated: {stats['generated']}\n")
    
    # Update volatile_scanner_advanced.py
    update_advanced_scanner(universe_tickers, stats)
    
    # Update volatile_stock_scanner.py
    update_basic_scanner(universe_tickers, stats)
    
    print(f"\n{'='*80}")
    print("✓ INTEGRATION COMPLETE")
    print(f"{'='*80}")
    print("\nYour scanners now use the dynamically discovered universe!")
    print("Run them as usual:")
    print("  python volatile_scanner_advanced.py")
    print("  python volatile_stock_scanner.py")


def update_advanced_scanner(tickers: list, stats: dict):
    """Update the advanced scanner with custom universe"""
    
    scanner_file = 'volatile_scanner_advanced.py'
    
    if not os.path.exists(scanner_file):
        print(f"❌ {scanner_file} not found")
        return
    
    with open(scanner_file, 'r') as f:
        content = f.read()
    
    # Create new get_expanded_universe method
    new_method = f'''    def get_expanded_universe(self) -> List[str]:
        """
        Dynamically discovered universe of volatile stocks
        Auto-generated on {stats['generated']}
        Total stocks: {len(tickers)}
        Avg volatility: {stats['avg_volatility']}%
        """
        
        # Load from custom universe file
        try:
            from custom_universe import CUSTOM_UNIVERSE
            return CUSTOM_UNIVERSE
        except ImportError:
            # Fallback to built-in list if custom universe not found
            print("⚠️  Custom universe not found, using fallback list")
            return {tickers[:50]}  # Fallback sample
'''
    
    # Find and replace the get_expanded_universe method
    import re
    pattern = r'def get_expanded_universe\(self\).*?return all_tickers'
    
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, new_method.strip() + '\n        \n        return all_tickers', content, flags=re.DOTALL)
        
        with open(scanner_file, 'w') as f:
            f.write(content)
        
        print(f"✓ Updated {scanner_file}")
    else:
        print(f"⚠️  Could not update {scanner_file} - manual update required")


def update_basic_scanner(tickers: list, stats: dict):
    """Update the basic scanner with custom universe"""
    
    scanner_file = 'volatile_stock_scanner.py'
    
    if not os.path.exists(scanner_file):
        print(f"❌ {scanner_file} not found")
        return
    
    with open(scanner_file, 'r') as f:
        content = f.read()
    
    # Create new get_stock_universe method
    new_method = f'''    def get_stock_universe(self) -> List[str]:
        """
        Dynamically discovered universe of volatile stocks
        Auto-generated on {stats['generated']}
        Total stocks: {len(tickers)}
        Avg volatility: {stats['avg_volatility']}%
        """
        
        # Load from custom universe file
        try:
            from custom_universe import CUSTOM_UNIVERSE
            return CUSTOM_UNIVERSE
        except ImportError:
            # Fallback to built-in list if custom universe not found
            print("⚠️  Custom universe not found, using fallback list")
            return {tickers[:50]}  # Fallback sample
'''
    
    # Find and replace the get_stock_universe method
    import re
    pattern = r'def get_stock_universe\(self\).*?return volatile_universe'
    
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, new_method.strip() + '\n        \n        return volatile_universe', content, flags=re.DOTALL)
        
        with open(scanner_file, 'w') as f:
            f.write(content)
        
        print(f"✓ Updated {scanner_file}")
    else:
        print(f"⚠️  Could not update {scanner_file} - manual update required")


def show_universe_stats(universe_file: str = 'custom_universe.py'):
    """Display statistics about the current universe"""
    
    if not os.path.exists(universe_file):
        print(f"❌ Universe file '{universe_file}' not found")
        return
    
    import importlib.util
    spec = importlib.util.spec_from_file_location("custom_universe", universe_file)
    universe_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(universe_module)
    
    universe = universe_module.CUSTOM_UNIVERSE
    stats = universe_module.UNIVERSE_STATS
    
    print(f"\n{'='*80}")
    print("CURRENT UNIVERSE STATISTICS")
    print(f"{'='*80}\n")
    print(f"Total Stocks: {stats['total_stocks']}")
    print(f"Average Volatility: {stats['avg_volatility']}%")
    print(f"Average Volume: {stats['avg_volume']:,}")
    print(f"Price Range: ${stats['price_range'][0]} - ${stats['price_range'][1]}")
    print(f"Generated: {stats['generated']}")
    print(f"\nSample Tickers: {', '.join(universe[:10])}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'integrate':
            integrate_universe_with_scanners()
        elif command == 'stats':
            show_universe_stats()
        else:
            print("Usage: python universe_integration.py [integrate|stats]")
    else:
        # Interactive mode
        print("\n" + "="*80)
        print("UNIVERSE INTEGRATION")
        print("="*80)
        print("\n1. Integrate custom universe with scanners")
        print("2. Show universe statistics")
        
        choice = input("\nEnter choice (1-2): ").strip()
        
        if choice == '1':
            integrate_universe_with_scanners()
        elif choice == '2':
            show_universe_stats()
        else:
            print("Invalid choice")
