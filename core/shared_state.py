"""
Shared State Management Utilities

Provides centralized state management for cooldowns and other shared state
across trading bot services.
"""

import os
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, ContextManager
import sys

# Platform-specific file locking
if sys.platform == 'win32':
    import msvcrt
else:
    import fcntl

logger = logging.getLogger(__name__)


def get_state_dir() -> str:
    """Get the state directory path"""
    # Get the project root (parent of core/)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    state_dir = os.path.join(project_root, 'state')
    os.makedirs(state_dir, exist_ok=True)
    return state_dir


def get_logs_dir() -> str:
    """Get the logs directory path"""
    # Get the project root (parent of core/)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logs_dir = os.path.join(project_root, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir


class SafeJSONFile(ContextManager):
    """
    Thread-safe JSON file access with file locking
    
    Prevents race conditions when multiple processes access the same JSON file.
    Supports both read and write operations with automatic locking.
    
    Usage:
        # Read
        with SafeJSONFile('file.json', 'r') as data:
            value = data.get('key')
        
        # Write
        with SafeJSONFile('file.json', 'w') as data:
            data['key'] = 'value'
    """
    
    def __init__(self, filepath: str, mode: str = 'r', timeout: float = 5.0):
        """
        Initialize safe JSON file handler
        
        Args:
            filepath: Path to JSON file
            mode: File mode ('r' for read, 'w' for write)
            timeout: Maximum time to wait for lock (seconds)
        """
        self.filepath = filepath
        self.mode = mode
        self.timeout = timeout
        self.file = None
        self.locked = False
        self.data = None
        self.is_write = mode == 'w'
    
    def _lock_file(self):
        """Acquire file lock (platform-specific)"""
        if sys.platform == 'win32':
            # Windows locking
            start_time = time.time()
            while time.time() - start_time < self.timeout:
                try:
                    msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
                    self.locked = True
                    return True
                except IOError:
                    time.sleep(0.1)
            raise TimeoutError(f"Could not acquire lock on {self.filepath} within {self.timeout}s")
        else:
            # Unix/macOS locking
            start_time = time.time()
            while time.time() - start_time < self.timeout:
                try:
                    fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    self.locked = True
                    return True
                except (IOError, OSError):
                    time.sleep(0.1)
            raise TimeoutError(f"Could not acquire lock on {self.filepath} within {self.timeout}s")
    
    def _unlock_file(self):
        """Release file lock (platform-specific)"""
        if self.locked and self.file:
            try:
                if sys.platform == 'win32':
                    msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(self.file.fileno(), fcntl.LOCK_UN)
            except (IOError, OSError):
                pass  # Ignore errors during unlock
            finally:
                self.locked = False
    
    def __enter__(self):
        """Enter context manager"""
        # Create file if it doesn't exist (for write mode)
        if self.is_write and not os.path.exists(self.filepath):
            os.makedirs(os.path.dirname(self.filepath) or '.', exist_ok=True)
            with open(self.filepath, 'w') as f:
                json.dump({}, f)
        
        # Open file
        if self.is_write:
            self.file = open(self.filepath, 'r+')  # Open for read+write
        else:
            if not os.path.exists(self.filepath):
                self.data = {}
                return self
            self.file = open(self.filepath, 'r')
        
        # Acquire lock
        self._lock_file()
        
        # Load data
        if self.file:
            try:
                self.file.seek(0)
                content = self.file.read()
                if content.strip():
                    parsed = json.loads(content)
                    # Support both dict and list JSON files
                    if isinstance(parsed, list):
                        self.data = parsed
                    elif isinstance(parsed, dict):
                        self.data = parsed
                    else:
                        self.data = {}
                else:
                    self.data = {} if not self.is_write else {}
            except (json.JSONDecodeError, ValueError):
                logger.warning(f"⚠️  Invalid JSON in {self.filepath}, using empty dict")
                self.data = {}
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager"""
        try:
            # Write data back if in write mode
            if self.is_write and self.file and self.data is not None:
                self.file.seek(0)
                self.file.truncate(0)
                # Support both dict and list
                json.dump(self.data, self.file, indent=2)
                self.file.flush()
                os.fsync(self.file.fileno())  # Force write to disk
        except Exception as e:
            logger.error(f"❌ Error writing to {self.filepath}: {e}")
        finally:
            # Unlock and close
            self._unlock_file()
            if self.file:
                self.file.close()
                self.file = None
    
    def __getitem__(self, key):
        """Get item from data dict"""
        if self.data is None:
            self.data = {}
        return self.data[key]
    
    def __setitem__(self, key, value):
        """Set item in data dict"""
        if self.data is None:
            self.data = {}
        self.data[key] = value
    
    def __delitem__(self, key):
        """Delete item from data dict"""
        if self.data is None:
            self.data = {}
        del self.data[key]
    
    def get(self, key, default=None):
        """Get item with default"""
        if self.data is None:
            self.data = {}
        return self.data.get(key, default)
    
    def keys(self):
        """Get keys"""
        if self.data is None:
            self.data = {}
        return self.data.keys()
    
    def items(self):
        """Get items"""
        if self.data is None:
            self.data = {}
        return self.data.items()
    
    def values(self):
        """Get values"""
        if self.data is None:
            self.data = {}
        return self.data.values()
    
    def __contains__(self, key):
        """Check if key exists"""
        if self.data is None:
            self.data = {}
        return key in self.data
    
    def __len__(self):
        """Get length"""
        if self.data is None:
            self.data = {}
        return len(self.data)
    
    def update(self, other):
        """Update with another dict"""
        if self.data is None:
            self.data = {}
        self.data.update(other)
    
    def copy(self):
        """Return a copy of the data"""
        if self.data is None:
            self.data = {}
        return self.data.copy()


class CooldownManager:
    """Manages cooldown state shared between buyer and seller services"""
    
    def __init__(self, cooldowns_file: str = None, cooldown_minutes: int = 15):
        """
        Initialize cooldown manager
        
        Args:
            cooldowns_file: Path to cooldowns JSON file (defaults to state/cooldowns.json)
            cooldown_minutes: Default cooldown duration in minutes
        """
        if cooldowns_file is None:
            cooldowns_file = os.path.join(get_state_dir(), 'cooldowns.json')
        self.cooldowns_file = cooldowns_file
        self.cooldown_minutes = cooldown_minutes
        self.cooldowns: Dict[str, datetime] = {}
        
        # Load existing cooldowns on startup
        self.load_cooldowns()
        
        logger.info(f"✅ CooldownManager initialized (file: {cooldowns_file})")
    
    def load_cooldowns(self):
        """Load cooldowns from file"""
        try:
            with SafeJSONFile(self.cooldowns_file, 'r') as data:
                # Convert ISO format strings back to datetime objects
                self.cooldowns = {}
                now = datetime.now()
                
                for symbol, cooldown_until_str in data.items():
                    try:
                        cooldown_until = datetime.fromisoformat(cooldown_until_str)
                        # Only keep cooldowns that haven't expired
                        if cooldown_until > now:
                            self.cooldowns[symbol] = cooldown_until
                    except (ValueError, TypeError) as e:
                        logger.warning(f"⚠️  Invalid cooldown entry for {symbol}: {e}")
                        continue
                
                # Clean up expired cooldowns by saving
                if len(self.cooldowns) != len(data):
                    self.save_cooldowns()
                
                logger.info(f"📥 Loaded {len(self.cooldowns)} active cooldowns")
                
        except FileNotFoundError:
            logger.debug(f"No cooldowns file found at {self.cooldowns_file}")
            self.cooldowns = {}
        except Exception as e:
            logger.error(f"❌ Error loading cooldowns: {e}")
            self.cooldowns = {}
    
    def save_cooldowns(self):
        """Save cooldowns to file"""
        try:
            # Clean up expired cooldowns before saving
            now = datetime.now()
            expired = [symbol for symbol, cooldown_until in self.cooldowns.items() 
                      if cooldown_until <= now]
            
            for symbol in expired:
                del self.cooldowns[symbol]
            
            # Convert datetime objects to ISO format strings
            data = {
                symbol: cooldown_until.isoformat()
                for symbol, cooldown_until in self.cooldowns.items()
            }
            
            # Save to file with locking
            with SafeJSONFile(self.cooldowns_file, 'w') as file_data:
                file_data.update(data)
            
            if expired:
                logger.debug(f"🧹 Cleaned up {len(expired)} expired cooldowns")
            
        except Exception as e:
            logger.error(f"❌ Error saving cooldowns: {e}")
    
    def is_in_cooldown(self, symbol: str) -> bool:
        """
        Check if symbol is currently in cooldown

        IMPORTANT: Reloads cooldowns from file to ensure we have the latest
        state from other processes (e.g., seller adding cooldowns).

        Args:
            symbol: Stock symbol to check

        Returns:
            True if in cooldown, False otherwise
        """
        # Reload cooldowns from file to get latest state from other processes
        self.load_cooldowns()

        if symbol not in self.cooldowns:
            return False

        cooldown_until = self.cooldowns[symbol]
        now = datetime.now()

        if now >= cooldown_until:
            # Cooldown expired, remove it
            del self.cooldowns[symbol]
            self.save_cooldowns()
            return False

        return True
    
    def get_cooldown_until(self, symbol: str) -> Optional[datetime]:
        """
        Get the cooldown expiration time for a symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            datetime if in cooldown, None otherwise
        """
        if symbol not in self.cooldowns:
            return None
        
        cooldown_until = self.cooldowns[symbol]
        now = datetime.now()
        
        if now >= cooldown_until:
            # Cooldown expired, remove it
            del self.cooldowns[symbol]
            self.save_cooldowns()
            return None
        
        return cooldown_until
    
    def add_cooldown(self, symbol: str, cooldown_minutes: Optional[int] = None):
        """
        Add symbol to cooldown
        
        Args:
            symbol: Stock symbol to add to cooldown
            cooldown_minutes: Cooldown duration (uses default if not provided)
        """
        if cooldown_minutes is None:
            cooldown_minutes = self.cooldown_minutes
        
        cooldown_until = datetime.now() + timedelta(minutes=cooldown_minutes)
        self.cooldowns[symbol] = cooldown_until
        
        # Save immediately
        self.save_cooldowns()
        
        logger.debug(f"⏸️  {symbol} in cooldown until {cooldown_until}")
    
    def remove_cooldown(self, symbol: str):
        """
        Remove symbol from cooldown (if present)
        
        Args:
            symbol: Stock symbol to remove from cooldown
        """
        if symbol in self.cooldowns:
            del self.cooldowns[symbol]
            self.save_cooldowns()
            logger.debug(f"✅ Removed cooldown for {symbol}")


class PositionManager:
    """Manages position state shared between buyer and monitor services"""
    
    def __init__(self, positions_file: str = None):
        """
        Initialize position manager
        
        Args:
            positions_file: Path to positions JSON file (defaults to state/positions.json)
        """
        if positions_file is None:
            positions_file = os.path.join(get_state_dir(), 'positions.json')
        self.positions_file = positions_file
        self.positions: Dict[str, Dict[str, Any]] = {}
        
        # Load existing positions on startup
        self.load_positions()
        
        logger.info(f"✅ PositionManager initialized (file: {positions_file})")
    
    def load_positions(self) -> Dict[str, Dict[str, Any]]:
        """
        Load positions from file
        
        Returns:
            Dictionary of positions
        """
        try:
            with SafeJSONFile(self.positions_file, 'r') as data:
                self.positions = data.copy() if data else {}
                
                logger.info(f"📥 Loaded {len(self.positions)} positions from file")
            
            return self.positions
            
        except FileNotFoundError:
            logger.debug(f"No positions file found at {self.positions_file}")
            self.positions = {}
            return {}
        except Exception as e:
            logger.error(f"❌ Error loading positions: {e}")
            self.positions = {}
            return {}
    
    def save_positions(self):
        """Save positions to file"""
        try:
            with SafeJSONFile(self.positions_file, 'w') as file_data:
                file_data.update(self.positions)
            
            logger.debug(f"💾 Saved {len(self.positions)} positions")
            
        except Exception as e:
            logger.error(f"❌ Error saving positions: {e}")
    
    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get current positions
        
        Returns:
            Dictionary of positions
        """
        return self.positions.copy()
    
    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get position for a specific symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Position dict if found, None otherwise
        """
        return self.positions.get(symbol)
    
    def add_position(self, symbol: str, position_info: Dict[str, Any]):
        """
        Add or update a position
        
        Args:
            symbol: Stock symbol
            position_info: Position information dict
        """
        self.positions[symbol] = position_info
        self.save_positions()
        logger.debug(f"💾 Added/updated position for {symbol}")
    
    def remove_position(self, symbol: str):
        """
        Remove a position
        
        Args:
            symbol: Stock symbol
        """
        if symbol in self.positions:
            del self.positions[symbol]
            self.save_positions()
            logger.debug(f"🗑️  Removed position for {symbol}")
    
    def reconcile_with_alpaca(self, alpaca_positions: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Reconcile positions.json with Alpaca API positions
        
        This ensures positions.json matches what's actually in Alpaca:
        - Adds positions that exist in Alpaca but not in positions.json
        - Removes positions that don't exist in Alpaca anymore
        - Updates position info for existing positions
        
        Args:
            alpaca_positions: Dict of {symbol: position_info} from Alpaca API
            
        Returns:
            Reconciled positions dict
        """
        try:
            alpaca_symbols = set(alpaca_positions.keys())
            file_symbols = set(self.positions.keys())
            
            # Find missing positions (in Alpaca but not in file)
            missing = alpaca_symbols - file_symbols
            if missing:
                logger.info(f"📥 Found {len(missing)} positions in Alpaca not in file: {missing}")
                for symbol in missing:
                    # Create default position info from Alpaca data
                    alpaca_pos = alpaca_positions[symbol]
                    self.positions[symbol] = {
                        'entry_price': alpaca_pos.get('entry_price', alpaca_pos.get('avg_entry_price', 0)),
                        'quantity': alpaca_pos.get('qty', 0),
                        'entry_time': datetime.now().isoformat(),
                        'stop_loss': alpaca_pos.get('entry_price', alpaca_pos.get('avg_entry_price', 0)) * 0.975,
                        'signal_score': 100,  # Default
                        'acceleration': 0.0   # Default
                    }
            
            # Find stale positions (in file but not in Alpaca)
            stale = file_symbols - alpaca_symbols
            if stale:
                logger.info(f"🗑️  Found {len(stale)} positions in file not in Alpaca: {stale}")
                for symbol in stale:
                    del self.positions[symbol]
            
            # Update existing positions with current Alpaca data
            for symbol in alpaca_symbols & file_symbols:
                alpaca_pos = alpaca_positions[symbol]
                # Update quantity and current price, but preserve entry info
                if 'entry_price' not in self.positions[symbol]:
                    self.positions[symbol]['entry_price'] = alpaca_pos.get('entry_price', alpaca_pos.get('avg_entry_price', 0))
                if 'quantity' in alpaca_pos:
                    self.positions[symbol]['quantity'] = alpaca_pos['qty']
            
            # Save reconciled positions
            if missing or stale:
                self.save_positions()
                logger.info(f"✅ Reconciled positions: +{len(missing)} added, -{len(stale)} removed")
            
            return self.positions.copy()

        except Exception as e:
            logger.error(f"Error reconciling positions: {e}")
            return self.positions.copy()


class SignalNotifier:
    """
    Fast-path signal notification for high-priority signals.

    Allows scanner to notify buyer immediately for top-tier signals,
    bypassing the normal polling interval.
    """

    def __init__(self, hot_signal_file: str = None):
        state_dir = get_state_dir()
        self.hot_signal_file = hot_signal_file or os.path.join(state_dir, 'hot_signal.json')
        self.min_score_for_hot = 90  # Only signals >= 90 get fast-path

    def notify_hot_signal(self, signal: dict) -> bool:
        """
        Write a high-score signal for immediate processing.

        Args:
            signal: Signal dict from scanner

        Returns:
            True if signal was written as hot signal
        """
        try:
            score = signal.get('score', 0)
            if score < self.min_score_for_hot:
                return False

            with SafeJSONFile(self.hot_signal_file, 'w') as f:
                f['signal'] = signal
                f['timestamp'] = datetime.now().isoformat()
                f['processed'] = False

            logger.info(f"HOT SIGNAL: {signal['symbol']} score={score} written for fast-path")
            return True

        except Exception as e:
            logger.error(f"Error writing hot signal: {e}")
            return False

    def check_hot_signal(self) -> Optional[dict]:
        """
        Check for unprocessed hot signal.

        Returns:
            Signal dict if available and unprocessed, None otherwise
        """
        try:
            with SafeJSONFile(self.hot_signal_file, 'r') as data:
                if data.get('processed', True):
                    return None

                signal = data.get('signal')
                if not signal:
                    return None

                # Check if signal is fresh (< 60 seconds old)
                timestamp_str = data.get('timestamp')
                if timestamp_str:
                    signal_time = datetime.fromisoformat(timestamp_str)
                    if (datetime.now() - signal_time).total_seconds() > 60:
                        return None  # Too old

                return signal

        except FileNotFoundError:
            return None
        except Exception as e:
            logger.debug(f"Error checking hot signal: {e}")
            return None

    def mark_processed(self) -> None:
        """Mark the current hot signal as processed."""
        try:
            with SafeJSONFile(self.hot_signal_file, 'w') as f:
                f['processed'] = True
                f['signal'] = None
        except Exception as e:
            logger.error(f"Error marking hot signal processed: {e}")
