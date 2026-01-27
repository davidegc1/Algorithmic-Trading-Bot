#!/usr/bin/env python3
"""
ORCHESTRATOR
Runs all 4 trading services in coordinated manner

ONE COMMAND TO RULE THEM ALL:
    python -m core.orchestrator start
    python -m core.orchestrator stop
    python -m core.orchestrator status
    python -m core.orchestrator restart
"""

import os
import sys
import time
import signal
import subprocess
import logging
from datetime import datetime
from typing import Dict, List
import json
from core.shared_state import get_state_dir, get_logs_dir, SafeJSONFile

# Configure logging
logs_dir = get_logs_dir()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, 'orchestrator.log'), mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TradingBotOrchestrator:
    """Orchestrates all 4 trading bot services"""
    
    def __init__(self):
        # Get project root (parent of core/)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        state_dir = get_state_dir()
        
        self.services = {
            'scanner': {
                'module': 'core.scanner',
                'description': 'Scans 360 stocks every 2 minutes',
                'priority': 3,
                'process': None
            },
            'buyer': {
                'module': 'core.buyer',
                'description': 'Executes buy orders every 30 seconds',
                'priority': 2,
                'process': None
            },
            'monitor': {
                'module': 'core.monitor',
                'description': 'Tracks positions every 60 seconds',
                'priority': 2,
                'process': None
            },
            'seller': {
                'module': 'core.seller',
                'description': 'Executes sell orders every 15 seconds',
                'priority': 1,  # Highest priority
                'process': None
            }
        }
        
        self.project_root = project_root
        
        self.pid_file = os.path.join(state_dir, 'orchestrator.pid')
        self.status_file = os.path.join(state_dir, 'orchestrator_status.json')
    
    def start_service(self, name: str) -> bool:
        """Start a single service"""
        try:
            service = self.services[name]
            module = service['module']
            
            # Start process using module format
            logger.info(f"🚀 Starting {name}...")
            process = subprocess.Popen(
                ['python3', '-m', module],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid,  # Create new process group
                cwd=self.project_root  # Set working directory to project root
            )
            
            service['process'] = process
            
            # Wait a moment to check if it started
            time.sleep(2)
            
            if process.poll() is None:
                logger.info(f"✅ {name} started (PID: {process.pid})")
                return True
            else:
                logger.error(f"❌ {name} failed to start")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error starting {name}: {e}")
            return False
    
    def stop_service(self, name: str) -> bool:
        """Stop a single service"""
        try:
            service = self.services[name]
            process = service['process']
            
            if process is None:
                logger.info(f"⚠️  {name} not running")
                return True
            
            logger.info(f"🛑 Stopping {name}...")
            
            # Send SIGTERM to process group
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            except:
                process.terminate()
            
            # Wait for graceful shutdown
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning(f"⚠️  {name} didn't stop gracefully, forcing...")
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except:
                    process.kill()
            
            service['process'] = None
            logger.info(f"✅ {name} stopped")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error stopping {name}: {e}")
            return False
    
    def start_all(self):
        """Start all services in priority order"""
        logger.info("="*80)
        logger.info("🚀 STARTING ALL TRADING BOT SERVICES")
        logger.info("="*80)
        
        # Sort by priority (1 = highest)
        sorted_services = sorted(
            self.services.items(),
            key=lambda x: x[1]['priority']
        )
        
        success_count = 0
        
        for name, service in sorted_services:
            logger.info(f"\n{service['description']}")
            if self.start_service(name):
                success_count += 1
            time.sleep(1)
        
        if success_count == len(self.services):
            logger.info("\n" + "="*80)
            logger.info("✅ ALL SERVICES STARTED SUCCESSFULLY")
            logger.info("="*80)
            self.save_status()
            self.save_pid()
            return True
        else:
            logger.error("\n" + "="*80)
            logger.error(f"⚠️  ONLY {success_count}/{len(self.services)} SERVICES STARTED")
            logger.error("="*80)
            return False
    
    def stop_all(self):
        """Stop all services"""
        logger.info("="*80)
        logger.info("🛑 STOPPING ALL TRADING BOT SERVICES")
        logger.info("="*80)
        
        for name in self.services.keys():
            self.stop_service(name)
            time.sleep(0.5)
        
        logger.info("\n" + "="*80)
        logger.info("✅ ALL SERVICES STOPPED")
        logger.info("="*80)
        
        self.remove_pid()
    
    def status(self):
        """Show status of all services"""
        logger.info("="*80)
        logger.info("📊 TRADING BOT STATUS")
        logger.info("="*80)
        
        all_running = True
        
        for name, service in self.services.items():
            process = service['process']
            
            if process and process.poll() is None:
                status = f"✅ RUNNING (PID: {process.pid})"
            else:
                status = "❌ STOPPED"
                all_running = False
            
            logger.info(f"\n{name.upper()}: {status}")
            logger.info(f"   {service['description']}")
        
        logger.info("\n" + "="*80)
        
        if all_running:
            logger.info("✅ All services operational")
        else:
            logger.info("⚠️  Some services are down")
        
        logger.info("="*80)
        
        return all_running
    
    def restart_all(self):
        """Restart all services"""
        logger.info("🔄 RESTARTING ALL SERVICES")
        self.stop_all()
        time.sleep(2)
        self.start_all()
    
    def save_pid(self):
        """Save orchestrator PID"""
        try:
            with open(self.pid_file, 'w') as f:
                f.write(str(os.getpid()))
        except Exception as e:
            logger.error(f"❌ Error saving PID: {e}")
    
    def remove_pid(self):
        """Remove PID file"""
        try:
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)
        except Exception as e:
            logger.error(f"❌ Error removing PID: {e}")
    
    def save_status(self):
        """Save service status"""
        try:
            status = {
                'timestamp': datetime.now().isoformat(),
                'services': {}
            }
            
            for name, service in self.services.items():
                process = service['process']
                status['services'][name] = {
                    'running': process is not None and process.poll() is None,
                    'pid': process.pid if process else None,
                    'description': service['description']
                }
            
            with SafeJSONFile(self.status_file, 'w') as file_data:
                file_data.update(status)
                
        except Exception as e:
            logger.error(f"❌ Error saving status: {e}")
    
    def monitor_services(self):
        """Monitor services and restart if crashed"""
        logger.info("="*80)
        logger.info("👀 MONITORING SERVICES (Ctrl+C to stop)")
        logger.info("="*80)
        
        try:
            while True:
                crashed = []
                
                for name, service in self.services.items():
                    process = service['process']
                    
                    if process and process.poll() is not None:
                        logger.error(f"❌ {name} crashed! Restarting...")
                        crashed.append(name)
                
                # Restart crashed services
                for name in crashed:
                    self.stop_service(name)
                    time.sleep(1)
                    self.start_service(name)
                
                # Update status
                self.save_status()
                
                # Wait before next check
                time.sleep(30)
                
        except KeyboardInterrupt:
            logger.info("\n⚠️  Monitoring stopped")


def main():
    """Entry point"""
    
    if len(sys.argv) < 2:
        print("\n" + "="*80)
        print("TRADING BOT ORCHESTRATOR")
        print("="*80)
        print("\nUsage:")
        print("  python -m core.orchestrator start       # Start all services")
        print("  python -m core.orchestrator stop        # Stop all services")
        print("  python -m core.orchestrator status      # Check status")
        print("  python -m core.orchestrator restart     # Restart all")
        print("  python -m core.orchestrator monitor     # Monitor and auto-restart")
        print("\nServices:")
        print("  1. Scanner  - Scans 360 stocks every 2 minutes")
        print("  2. Buyer    - Executes buy orders every 30 seconds")
        print("  3. Monitor  - Tracks positions every 60 seconds")
        print("  4. Seller   - Executes sell orders every 15 seconds")
        print("\n" + "="*80)
        sys.exit(1)
    
    command = sys.argv[1].lower()
    orchestrator = TradingBotOrchestrator()
    
    if command == 'start':
        orchestrator.start_all()
        print("\n💡 TIP: Run 'python -m core.orchestrator monitor' to auto-restart crashed services")
        print("💡 TIP: Press Ctrl+C to stop gracefully\n")
        
        # Keep running
        try:
            while True:
                time.sleep(60)
                orchestrator.save_status()
        except KeyboardInterrupt:
            logger.info("\n\n⚠️  Stopping all services...")
            orchestrator.stop_all()
    
    elif command == 'stop':
        orchestrator.stop_all()
    
    elif command == 'status':
        orchestrator.status()
    
    elif command == 'restart':
        orchestrator.restart_all()
    
    elif command == 'monitor':
        orchestrator.start_all()
        orchestrator.monitor_services()
    
    else:
        print(f"❌ Unknown command: {command}")
        print("Valid commands: start, stop, status, restart, monitor")
        sys.exit(1)


if __name__ == "__main__":
    main()
