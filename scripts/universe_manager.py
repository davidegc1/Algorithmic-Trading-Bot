"""
Universe Manager
Browse, compare, and switch between multiple stock universes
"""

import os
import json
import pandas as pd
from datetime import datetime
from typing import List, Dict
import shutil


class UniverseManager:
    """Manage multiple stock universes"""
    
    def __init__(self, base_dir: str = 'universes'):
        self.base_dir = base_dir
        
    def list_universes(self) -> List[Dict]:
        """List all available universes"""
        
        if not os.path.exists(self.base_dir):
            print(f"No universes directory found at: {self.base_dir}")
            return []
        
        universes = []
        
        # Find all universe directories
        for item in os.listdir(self.base_dir):
            universe_path = os.path.join(self.base_dir, item)
            
            if os.path.isdir(universe_path) and item.startswith('universe_'):
                metadata_file = os.path.join(universe_path, 'metadata.json')
                
                if os.path.exists(metadata_file):
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    metadata['directory'] = universe_path
                    metadata['name'] = item
                    universes.append(metadata)
        
        # Sort by creation date (newest first)
        universes.sort(key=lambda x: x['created'], reverse=True)
        
        return universes
    
    def show_universes(self):
        """Display all universes in a formatted table"""
        
        universes = self.list_universes()
        
        if not universes:
            print("No universes found. Run universe_builder.py to create one.")
            return
        
        print(f"\n{'='*100}")
        print(f"AVAILABLE STOCK UNIVERSES ({len(universes)} total)")
        print(f"{'='*100}\n")
        
        print(f"{'#':<4} {'Created':<20} {'Stocks':<8} {'Avg Vol':<10} {'Top Stock':<10} {'Directory':<30}")
        print("-" * 100)
        
        for idx, universe in enumerate(universes, 1):
            created = universe['created']
            total = universe['total_stocks']
            avg_vol = f"{universe['avg_volatility']:.1f}%"
            top_stock = universe['top_10_tickers'][0] if universe['top_10_tickers'] else 'N/A'
            directory = universe['name']
            
            print(f"{idx:<4} {created:<20} {total:<8} {avg_vol:<10} {top_stock:<10} {directory:<30}")
        
        print("\n")
    
    def get_universe_details(self, universe_id: int = None, universe_name: str = None):
        """Get detailed information about a specific universe"""
        
        universes = self.list_universes()
        
        if not universes:
            print("No universes found.")
            return None
        
        # Get universe by ID or name
        if universe_id:
            if universe_id > len(universes) or universe_id < 1:
                print(f"Invalid universe ID: {universe_id}")
                return None
            universe = universes[universe_id - 1]
        elif universe_name:
            universe = next((u for u in universes if u['name'] == universe_name), None)
            if not universe:
                print(f"Universe not found: {universe_name}")
                return None
        else:
            print("Please provide universe_id or universe_name")
            return None
        
        print(f"\n{'='*80}")
        print(f"UNIVERSE DETAILS: {universe['name']}")
        print(f"{'='*80}\n")
        
        print(f"Created: {universe['created']}")
        print(f"Total Stocks: {universe['total_stocks']}")
        print(f"Average Volatility: {universe['avg_volatility']:.2f}%")
        print(f"Volatility Range: {universe['min_volatility']:.2f}% - {universe['max_volatility']:.2f}%")
        print(f"Average Volume: {universe['avg_volume']:,}")
        print(f"Average Market Cap: ${universe['avg_market_cap']/1e6:.1f}M")
        print(f"Price Range: ${universe['price_range']['min']:.2f} - ${universe['price_range']['max']:.2f}")
        
        print(f"\nTop 10 Stocks:")
        for i, ticker in enumerate(universe['top_10_tickers'], 1):
            print(f"  {i}. {ticker}")
        
        print(f"\nDirectory: {universe['directory']}")
        
        return universe
    
    def activate_universe(self, universe_id: int = None, universe_name: str = None):
        """
        Activate a universe by copying its universe.py to custom_universe.py
        This makes scanners use this universe
        """
        
        universes = self.list_universes()
        
        if not universes:
            print("No universes found.")
            return False
        
        # Get universe
        if universe_id:
            if universe_id > len(universes) or universe_id < 1:
                print(f"Invalid universe ID: {universe_id}")
                return False
            universe = universes[universe_id - 1]
        elif universe_name:
            universe = next((u for u in universes if u['name'] == universe_name), None)
            if not universe:
                print(f"Universe not found: {universe_name}")
                return False
        else:
            print("Please provide universe_id or universe_name")
            return False
        
        # Copy universe.py to custom_universe.py
        source = os.path.join(universe['directory'], 'universe.py')
        destination = 'custom_universe.py'
        
        if not os.path.exists(source):
            print(f"Error: universe.py not found in {universe['directory']}")
            return False
        
        # Backup current custom_universe.py if it exists
        if os.path.exists(destination):
            backup = f'custom_universe_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.py'
            shutil.copy2(destination, backup)
            print(f"✓ Backed up current universe to: {backup}")
        
        # Copy new universe
        shutil.copy2(source, destination)
        
        print(f"\n{'='*80}")
        print(f"✓ ACTIVATED UNIVERSE: {universe['name']}")
        print(f"{'='*80}")
        print(f"Total Stocks: {universe['total_stocks']}")
        print(f"Average Volatility: {universe['avg_volatility']:.2f}%")
        print(f"Created: {universe['created']}")
        print(f"\nYour scanners will now use this universe!")
        print(f"Run: python volatile_scanner_advanced.py")
        
        return True
    
    def compare_universes(self, id1: int, id2: int):
        """Compare two universes side by side"""
        
        universes = self.list_universes()
        
        if id1 > len(universes) or id2 > len(universes) or id1 < 1 or id2 < 1:
            print("Invalid universe IDs")
            return
        
        u1 = universes[id1 - 1]
        u2 = universes[id2 - 1]
        
        print(f"\n{'='*80}")
        print("UNIVERSE COMPARISON")
        print(f"{'='*80}\n")
        
        print(f"{'Metric':<25} {'Universe 1':<25} {'Universe 2':<25}")
        print("-" * 80)
        print(f"{'Name':<25} {u1['name']:<25} {u2['name']:<25}")
        print(f"{'Created':<25} {u1['created']:<25} {u2['created']:<25}")
        print(f"{'Total Stocks':<25} {u1['total_stocks']:<25} {u2['total_stocks']:<25}")
        print(f"{'Avg Volatility':<25} {u1['avg_volatility']:.2f}%{'':<22} {u2['avg_volatility']:.2f}%")
        print(f"{'Max Volatility':<25} {u1['max_volatility']:.2f}%{'':<22} {u2['max_volatility']:.2f}%")
        print(f"{'Avg Volume':<25} {u1['avg_volume']:,}{'':<15} {u2['avg_volume']:,}")
        
        # Find common stocks
        df1 = pd.read_csv(os.path.join(u1['directory'], 'universe_data.csv'))
        df2 = pd.read_csv(os.path.join(u2['directory'], 'universe_data.csv'))
        
        common = set(df1['ticker']).intersection(set(df2['ticker']))
        unique_u1 = set(df1['ticker']) - set(df2['ticker'])
        unique_u2 = set(df2['ticker']) - set(df1['ticker'])
        
        print(f"\n{'Common Stocks':<25} {len(common)}")
        print(f"{'Unique to Universe 1':<25} {len(unique_u1)}")
        print(f"{'Unique to Universe 2':<25} {len(unique_u2)}")
        
        if len(common) > 0:
            print(f"\nSample Common Stocks: {', '.join(list(common)[:10])}")
    
    def delete_universe(self, universe_id: int = None, universe_name: str = None):
        """Delete a universe (with confirmation)"""
        
        universes = self.list_universes()
        
        if not universes:
            print("No universes found.")
            return False
        
        # Get universe
        if universe_id:
            if universe_id > len(universes) or universe_id < 1:
                print(f"Invalid universe ID: {universe_id}")
                return False
            universe = universes[universe_id - 1]
        elif universe_name:
            universe = next((u for u in universes if u['name'] == universe_name), None)
            if not universe:
                print(f"Universe not found: {universe_name}")
                return False
        else:
            print("Please provide universe_id or universe_name")
            return False
        
        # Confirmation
        print(f"\n⚠️  WARNING: About to delete universe:")
        print(f"Name: {universe['name']}")
        print(f"Created: {universe['created']}")
        print(f"Stocks: {universe['total_stocks']}")
        print(f"Directory: {universe['directory']}")
        
        confirm = input("\nType 'DELETE' to confirm: ").strip()
        
        if confirm != 'DELETE':
            print("Cancelled.")
            return False
        
        # Delete directory
        import shutil
        shutil.rmtree(universe['directory'])
        
        print(f"✓ Deleted universe: {universe['name']}")
        return True
    
    def export_universe(self, universe_id: int, output_format: str = 'csv'):
        """Export universe to different format"""
        
        universes = self.list_universes()
        
        if universe_id > len(universes) or universe_id < 1:
            print("Invalid universe ID")
            return
        
        universe = universes[universe_id - 1]
        df = pd.read_csv(os.path.join(universe['directory'], 'universe_data.csv'))
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if output_format == 'csv':
            filename = f'universe_export_{timestamp}.csv'
            df.to_csv(filename, index=False)
        elif output_format == 'json':
            filename = f'universe_export_{timestamp}.json'
            df.to_json(filename, orient='records', indent=2)
        elif output_format == 'excel':
            filename = f'universe_export_{timestamp}.xlsx'
            df.to_excel(filename, index=False, engine='openpyxl')
        else:
            print(f"Unsupported format: {output_format}")
            return
        
        print(f"✓ Exported to: {filename}")


def main():
    """Interactive universe manager"""
    
    manager = UniverseManager()
    
    while True:
        print(f"\n{'='*80}")
        print("UNIVERSE MANAGER")
        print(f"{'='*80}")
        print("1. List all universes")
        print("2. View universe details")
        print("3. Activate a universe (use in scanners)")
        print("4. Compare two universes")
        print("5. Delete a universe")
        print("6. Exit")
        
        choice = input("\nEnter choice (1-6): ").strip()
        
        if choice == '1':
            manager.show_universes()
        
        elif choice == '2':
            manager.show_universes()
            universe_id = int(input("\nEnter universe # to view details: "))
            manager.get_universe_details(universe_id=universe_id)
        
        elif choice == '3':
            manager.show_universes()
            universe_id = int(input("\nEnter universe # to activate: "))
            manager.activate_universe(universe_id=universe_id)
        
        elif choice == '4':
            manager.show_universes()
            id1 = int(input("\nEnter first universe #: "))
            id2 = int(input("Enter second universe #: "))
            manager.compare_universes(id1, id2)
        
        elif choice == '5':
            manager.show_universes()
            universe_id = int(input("\nEnter universe # to DELETE: "))
            manager.delete_universe(universe_id=universe_id)
        
        elif choice == '6':
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice")


if __name__ == "__main__":
    main()