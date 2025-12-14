#!/usr/bin/env python3
"""
QUICK START SCRIPT
Interactive setup and launch
"""

import os
import sys
from pathlib import Path


def check_dependencies():
    """Check if required packages are installed"""
    print("Checking dependencies...")
    
    required = [
        'alpaca_trade_api',
        'pandas',
        'numpy',
        'dotenv'
    ]
    
    missing = []
    for package in required:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            missing.append(package)
            print(f"  ❌ {package} - MISSING")
    
    if missing:
        print("\n⚠️  Missing packages detected!")
        print("Install with: pip install -r requirements.txt")
        return False
    
    print("✅ All dependencies installed\n")
    return True


def check_env_file():
    """Check if .env file exists and has credentials"""
    print("Checking environment configuration...")
    
    if not os.path.exists('.env'):
        print("  ❌ .env file not found")
        print("\nCreating .env from template...")
        
        if os.path.exists('.env.example'):
            import shutil
            shutil.copy('.env.example', '.env')
            print("  ✅ Created .env file")
            print("\n⚠️  IMPORTANT: Edit .env and add your Alpaca API keys!")
            print("     Get keys from: https://app.alpaca.markets/paper/dashboard/overview")
            return False
        else:
            print("  ❌ .env.example not found")
            return False
    
    # Check if keys are set
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv('ALPACA_API_KEY')
    api_secret = os.getenv('ALPACA_SECRET_KEY')
    
    if not api_key or api_key == 'your_paper_api_key_here':
        print("  ❌ ALPACA_API_KEY not configured")
        print("\n⚠️  Edit .env and add your Alpaca API credentials")
        return False
    
    if not api_secret or api_secret == 'your_paper_secret_key_here':
        print("  ❌ ALPACA_SECRET_KEY not configured")
        print("\n⚠️  Edit .env and add your Alpaca API credentials")
        return False
    
    print("  ✅ API credentials configured")
    print(f"  ✅ API Key: {api_key[:8]}...")
    print("✅ Environment configured\n")
    return True


def validate_config():
    """Validate strategy configuration"""
    print("Validating strategy configuration...")
    
    try:
        from utils import validate_strategy_parameters
        is_valid = validate_strategy_parameters()
        print()
        return is_valid
    except Exception as e:
        print(f"  ⚠️  Could not validate: {e}\n")
        return True


def show_menu():
    """Show interactive menu"""
    print("="*80)
    print("VELOCITY + ACCELERATION TRADING BOT")
    print("="*80)
    print()
    print("1. Run Trading Bot (Paper Trading)")
    print("2. Run Trading Bot (Live Trading) ⚠️")
    print("3. Analyze Performance")
    print("4. Validate Configuration")
    print("5. Test Alpaca Connection")
    print("6. Exit")
    print()
    
    choice = input("Select option (1-6): ").strip()
    return choice


def test_connection():
    """Test Alpaca API connection"""
    print("\nTesting Alpaca connection...")
    
    try:
        import alpaca_trade_api as tradeapi
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv('ALPACA_API_KEY')
        api_secret = os.getenv('ALPACA_SECRET_KEY')
        base_url = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
        
        api = tradeapi.REST(api_key, api_secret, base_url, api_version='v2')
        
        # Get account
        account = api.get_account()
        
        print("✅ Connection successful!")
        print(f"   Account Status: {account.status}")
        print(f"   Equity: ${float(account.equity):,.2f}")
        print(f"   Cash: ${float(account.cash):,.2f}")
        print(f"   Buying Power: ${float(account.buying_power):,.2f}")
        
        # Check if market is open
        clock = api.get_clock()
        print(f"   Market Open: {clock.is_open}")
        if not clock.is_open:
            print(f"   Next Open: {clock.next_open}")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


def run_bot(paper_trading=True):
    """Run the trading bot"""
    print("\n" + "="*80)
    if paper_trading:
        print("🚀 STARTING BOT - PAPER TRADING MODE")
    else:
        print("⚠️  STARTING BOT - LIVE TRADING MODE")
        confirm = input("Are you sure? This will use real money! (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled.")
            return
    print("="*80)
    print()
    
    try:
        from trading_bot import VelocityAccelerationBot
        
        bot = VelocityAccelerationBot(paper_trading=paper_trading)
        bot.run(scan_interval_seconds=60)
        
    except KeyboardInterrupt:
        print("\n⚠️  Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")


def analyze_performance():
    """Analyze trading performance"""
    print("\n" + "="*80)
    print("📊 PERFORMANCE ANALYSIS")
    print("="*80)
    print()
    
    try:
        from utils import PerformanceAnalyzer
        
        analyzer = PerformanceAnalyzer()
        analyzer.print_summary()
        
        print("\n📈 Performance by Signal Score:")
        print(analyzer.analyze_by_signal_score())
        
        print("\n📈 Performance by Acceleration:")
        print(analyzer.analyze_by_acceleration())
        
    except FileNotFoundError:
        print("⚠️  No trade history found. Run the bot first to generate data.")
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Main entry point"""
    print("\n")
    print("="*80)
    print(" VELOCITY + ACCELERATION TRADING BOT - SETUP")
    print("="*80)
    print()
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Setup incomplete. Please install dependencies and try again.")
        sys.exit(1)
    
    # Check environment
    if not check_env_file():
        print("\n❌ Setup incomplete. Please configure .env file and try again.")
        sys.exit(1)
    
    # Validate configuration
    validate_config()
    
    print("✅ Setup complete! Ready to trade.\n")
    
    # Interactive menu
    while True:
        choice = show_menu()
        
        if choice == '1':
            run_bot(paper_trading=True)
        elif choice == '2':
            run_bot(paper_trading=False)
        elif choice == '3':
            analyze_performance()
        elif choice == '4':
            validate_config()
        elif choice == '5':
            test_connection()
        elif choice == '6':
            print("\n👋 Goodbye!")
            break
        else:
            print("Invalid choice. Please select 1-6.")
        
        print()
        input("Press Enter to continue...")
        print("\n")


if __name__ == "__main__":
    main()
