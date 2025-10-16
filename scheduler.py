#!/usr/bin/env python3
"""
Git-Backup-Enc: Scheduler Script
Cross-platform automatic backup scheduler
"""

import os
import sys
import time
import yaml
import signal
import argparse
from datetime import datetime
from pathlib import Path
import subprocess


class BackupScheduler:
    """Cross-platform backup scheduler"""
    
    def __init__(self, config_path: str = "config.yaml", interval_hours: float = 24.0):
        """
        Initialize scheduler
        
        Args:
            config_path: Path to configuration file
            interval_hours: Hours between backups (can be fractional, e.g., 0.5 for 30 minutes)
        """
        self.config_path = config_path
        self.interval_hours = interval_hours
        self.interval_seconds = interval_hours * 3600
        self.running = True
        self.backup_script = Path(__file__).parent / "backup.py"
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print("\n\nReceived shutdown signal. Stopping scheduler...")
        self.running = False
    
    def _load_config(self) -> dict:
        """Load configuration file"""
        if not os.path.exists(self.config_path):
            print(f"Error: Configuration file not found: {self.config_path}")
            sys.exit(1)
        
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        return config
    
    def _run_backup(self) -> bool:
        """
        Run a backup
        
        Returns:
            True if backup succeeded, False otherwise
        """
        try:
            print(f"\n{'=' * 60}")
            print(f"Running scheduled backup at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'=' * 60}\n")
            
            # Run backup script
            result = subprocess.run(
                [sys.executable, str(self.backup_script), '-c', self.config_path],
                capture_output=False,
                text=True
            )
            
            if result.returncode == 0:
                print(f"\n{'=' * 60}")
                print(f"Scheduled backup completed successfully!")
                print(f"{'=' * 60}\n")
                return True
            else:
                print(f"\n{'=' * 60}")
                print(f"Scheduled backup failed with exit code {result.returncode}")
                print(f"{'=' * 60}\n")
                return False
        
        except Exception as e:
            print(f"\nError running backup: {e}\n")
            return False
    
    def run(self):
        """Run the scheduler loop"""
        print(f"{'=' * 60}")
        print("Git-Backup-Enc: Automatic Backup Scheduler")
        print(f"{'=' * 60}")
        print(f"Configuration: {self.config_path}")
        print(f"Backup interval: {self.interval_hours} hours")
        print(f"Next backup: immediately")
        print(f"Press Ctrl+C to stop\n")
        
        # Load config to verify it exists
        config = self._load_config()
        
        # Run first backup immediately
        self._run_backup()
        
        # Schedule loop
        while self.running:
            try:
                next_backup_time = datetime.now().timestamp() + self.interval_seconds
                next_backup_dt = datetime.fromtimestamp(next_backup_time)
                
                print(f"Next backup scheduled at: {next_backup_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"(in {self.interval_hours} hours)")
                print("Press Ctrl+C to stop scheduler\n")
                
                # Sleep in small increments to allow for graceful shutdown
                sleep_interval = min(60, self.interval_seconds)  # Check every minute or less
                elapsed = 0
                
                while elapsed < self.interval_seconds and self.running:
                    time_to_sleep = min(sleep_interval, self.interval_seconds - elapsed)
                    time.sleep(time_to_sleep)
                    elapsed += time_to_sleep
                
                if self.running:
                    self._run_backup()
            
            except KeyboardInterrupt:
                print("\n\nScheduler stopped by user.")
                break
            except Exception as e:
                print(f"\nError in scheduler loop: {e}")
                print("Waiting 60 seconds before retry...\n")
                time.sleep(60)
        
        print("\nScheduler stopped.")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Git-Backup-Enc: Automatic Backup Scheduler',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default settings (24 hour interval)
  python scheduler.py
  
  # Run with custom interval (every 12 hours)
  python scheduler.py --interval 12
  
  # Run with custom config
  python scheduler.py -c /path/to/config.yaml --interval 6
  
  # Run every 30 minutes (0.5 hours)
  python scheduler.py --interval 0.5
"""
    )
    
    parser.add_argument(
        '-c', '--config',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    
    parser.add_argument(
        '--interval',
        type=float,
        default=24.0,
        help='Hours between backups (default: 24.0, can be fractional like 0.5 for 30 minutes)'
    )
    
    args = parser.parse_args()
    
    # Validate interval
    if args.interval <= 0:
        print("Error: Interval must be greater than 0")
        sys.exit(1)
    
    # Create and run scheduler
    scheduler = BackupScheduler(args.config, args.interval)
    scheduler.run()


if __name__ == "__main__":
    main()
