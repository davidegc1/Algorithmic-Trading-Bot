"""
LOG VIEWER
Interactive tool to view and filter trading bot logs
"""

import os
import sys
from datetime import datetime, timedelta


class LogViewer:
    """View and filter bot logs"""
    
    def __init__(self, log_file: str = 'trading_bot.log'):
        self.log_file = log_file
        
        if not os.path.exists(log_file):
            print(f"⚠️  Log file not found: {log_file}")
            sys.exit(1)
    
    def show_menu(self):
        """Show viewer menu"""
        print("\n" + "="*80)
        print("LOG VIEWER")
        print("="*80)
        print("1. View All Logs (last 100 lines)")
        print("2. View Today's Logs")
        print("3. View Entries Only")
        print("4. View Exits Only")
        print("5. Search by Symbol")
        print("6. View Errors/Warnings")
        print("7. View Real-time (tail)")
        print("8. Export Filtered Logs")
        print("9. Back")
        print()
        
        choice = input("Select option (1-9): ").strip()
        return choice
    
    def read_log(self, lines: int = None) -> list:
        """Read log file"""
        with open(self.log_file, 'r') as f:
            if lines:
                return f.readlines()[-lines:]
            else:
                return f.readlines()
    
    def view_all(self, lines: int = 100):
        """View last N lines"""
        print("\n" + "="*80)
        print(f"LAST {lines} LOG LINES")
        print("="*80)
        
        log_lines = self.read_log(lines)
        for line in log_lines:
            print(line.rstrip())
    
    def view_today(self):
        """View today's logs only"""
        print("\n" + "="*80)
        print("TODAY'S LOGS")
        print("="*80)
        
        today = datetime.now().strftime('%Y-%m-%d')
        log_lines = self.read_log()
        
        count = 0
        for line in log_lines:
            if today in line:
                print(line.rstrip())
                count += 1
        
        print(f"\n{count} log entries today")
    
    def view_entries(self):
        """View entry signals only"""
        print("\n" + "="*80)
        print("ENTRY SIGNALS")
        print("="*80)
        
        log_lines = self.read_log()
        
        count = 0
        for line in log_lines:
            if "ENTERING" in line or "FILLED" in line:
                print(line.rstrip())
                count += 1
        
        print(f"\n{count} entry-related logs")
    
    def view_exits(self):
        """View exit signals only"""
        print("\n" + "="*80)
        print("EXIT SIGNALS")
        print("="*80)
        
        log_lines = self.read_log()
        
        count = 0
        for line in log_lines:
            if "EXITING" in line or "SOLD" in line:
                print(line.rstrip())
                count += 1
        
        print(f"\n{count} exit-related logs")
    
    def search_symbol(self):
        """Search logs for specific symbol"""
        symbol = input("\nEnter symbol to search: ").strip().upper()
        
        print("\n" + "="*80)
        print(f"LOGS FOR {symbol}")
        print("="*80)
        
        log_lines = self.read_log()
        
        count = 0
        for line in log_lines:
            if symbol in line:
                print(line.rstrip())
                count += 1
        
        print(f"\n{count} logs mentioning {symbol}")
    
    def view_errors(self):
        """View errors and warnings"""
        print("\n" + "="*80)
        print("ERRORS & WARNINGS")
        print("="*80)
        
        log_lines = self.read_log()
        
        count = 0
        for line in log_lines:
            if "ERROR" in line or "WARNING" in line or "⚠️" in line or "❌" in line:
                print(line.rstrip())
                count += 1
        
        print(f"\n{count} errors/warnings")
    
    def tail_logs(self):
        """Show real-time logs (simulated)"""
        print("\n" + "="*80)
        print("REAL-TIME LOGS (Press Ctrl+C to stop)")
        print("="*80)
        print()
        
        print("💡 Tip: Use this in a separate terminal:")
        print(f"   tail -f {self.log_file}")
        print()
        
        input("Press Enter to continue...")
    
    def export_filtered(self):
        """Export filtered logs to file"""
        filter_type = input("\nFilter type (symbol/entry/exit/error/today): ").strip().lower()
        output_file = input("Output filename: ").strip()
        
        log_lines = self.read_log()
        filtered = []
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        for line in log_lines:
            if filter_type == 'entry' and ("ENTERING" in line or "FILLED" in line):
                filtered.append(line)
            elif filter_type == 'exit' and ("EXITING" in line or "SOLD" in line):
                filtered.append(line)
            elif filter_type == 'error' and ("ERROR" in line or "WARNING" in line):
                filtered.append(line)
            elif filter_type == 'today' and today in line:
                filtered.append(line)
            elif filter_type == 'symbol':
                symbol = input("Which symbol? ").strip().upper()
                if symbol in line:
                    filtered.append(line)
        
        with open(output_file, 'w') as f:
            f.writelines(filtered)
        
        print(f"✅ Exported {len(filtered)} lines to {output_file}")
    
    def run(self):
        """Main viewer loop"""
        while True:
            choice = self.show_menu()
            
            if choice == '1':
                lines = input("How many lines? (default 100): ").strip()
                lines = int(lines) if lines else 100
                self.view_all(lines)
            elif choice == '2':
                self.view_today()
            elif choice == '3':
                self.view_entries()
            elif choice == '4':
                self.view_exits()
            elif choice == '5':
                self.search_symbol()
            elif choice == '6':
                self.view_errors()
            elif choice == '7':
                self.tail_logs()
            elif choice == '8':
                self.export_filtered()
            elif choice == '9':
                break
            else:
                print("Invalid choice")
            
            input("\nPress Enter to continue...")


def main():
    viewer = LogViewer('trading_bot.log')
    viewer.run()


if __name__ == "__main__":
    main()
