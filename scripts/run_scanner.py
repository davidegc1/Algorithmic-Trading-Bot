"""
Quick runner for volatile stock scanner
Choose between basic or advanced scan
"""

import sys
import os

def main():
    print("\n" + "="*80)
    print("VOLATILE STOCK SCANNER")
    print("="*80)
    print("\nSelect scanner mode:")
    print("1. Basic Scanner (faster, ~2-3 minutes)")
    print("2. Advanced Scanner (comprehensive, ~3-5 minutes)")
    print("3. Quick Scan (custom ticker list)")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        print("\nRunning basic scanner...\n")
        from volatile_stock_scanner import main as basic_scan
        basic_scan()
        
    elif choice == "2":
        print("\nRunning advanced scanner...\n")
        from volatile_scanner_advanced import run_comprehensive_scan
        run_comprehensive_scan()
        
    elif choice == "3":
        tickers_input = input("\nEnter tickers (comma-separated, e.g., MARA,RIOT,IONQ): ").strip()
        tickers = [t.strip().upper() for t in tickers_input.split(',')]
        
        print(f"\nScanning {len(tickers)} tickers...\n")
        from volatile_scanner_advanced import AdvancedVolatilityScanner
        import pandas as pd
        
        scanner = AdvancedVolatilityScanner()
        df = scanner.scan_market(custom_tickers=tickers)
        
        if not df.empty:
            print("\n" + "="*80)
            print("RESULTS")
            print("="*80)
            display_cols = ['ticker', 'price', 'day_change_%', 'hist_vol_%', 
                          'atr_%', 'vol_ratio', 'market_cap_$M']
            print(df[display_cols].to_string(index=False))
            
            # Save with correct Mac path
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_dir = '/Users/student/Desktop/trading/outputs'
            os.makedirs(output_dir, exist_ok=True)
            output_path = f'{output_dir}/custom_scan_{timestamp}.csv'
            df.to_csv(output_path, index=False)
            print(f"\nResults saved to: {output_path}")
        else:
            print("No data retrieved")
    
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()