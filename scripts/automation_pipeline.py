#!/usr/bin/env python3
"""
Automation Pipeline for Real-time Dymola Data Processing
Monitors directories, processes new files, and updates dashboards
"""

import os
import time
import json
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess
import logging
from threading import Thread, Lock
import requests
from typing import Dict, List, Optional

from dymola_export import DymolaExporter
from data_manager import DataManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/automation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DymolaFileHandler(FileSystemEventHandler):
    """Handle new Dymola files and process them automatically"""
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
        self.processing_lock = Lock()
        self.processed_files = set()
    
    def on_created(self, event):
        """Handle new file creation"""
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        
        # Only process .mat files
        if file_path.suffix.lower() != '.mat':
            return
            
        # Avoid duplicate processing
        if str(file_path) in self.processed_files:
            return
            
        logger.info(f"New file detected: {file_path}")
        
        # Wait a bit to ensure file is fully written
        time.sleep(2)
        
        with self.processing_lock:
            self.processed_files.add(str(file_path))
            self.pipeline.process_new_file(file_path)
    
    def on_modified(self, event):
        """Handle file modifications"""
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        
        # Check if it's a relevant file and not already processed recently
        if (file_path.suffix.lower() == '.mat' and 
            str(file_path) not in self.processed_files):
            
            # Wait to ensure file is stable
            time.sleep(3)
            
            with self.processing_lock:
                self.processed_files.add(str(file_path))
                self.pipeline.process_new_file(file_path)


class AutomationPipeline:
    """Main automation pipeline for Dymola data processing"""
    
    def __init__(self, config_file="config/automation_config.json"):
        self.config = self._load_config(config_file)
        
        # Initialize components
        self.exporter = DymolaExporter(self.config.get('processed_dir', 'data/processed'))
        self.data_manager = DataManager(self.config.get('data_dir', 'data'))
        
        # Set up directories
        self.watch_dirs = self.config.get('watch_directories', ['data/raw'])
        self.processed_dir = Path(self.config.get('processed_dir', 'data/processed'))
        
        # Processing state
        self.processing_queue = []
        self.processing_thread = None
        self.observer = None
        
        # Statistics
        self.stats = {
            'files_processed': 0,
            'processing_errors': 0,
            'last_processed': None,
            'start_time': datetime.now()
        }
    
    def _load_config(self, config_file: str) -> Dict:
        """Load automation configuration"""
        default_config = {
            'watch_directories': ['data/raw'],
            'processed_dir': 'data/processed', 
            'data_dir': 'data',
            'processing_interval': 5,
            'cleanup_interval': 3600,
            'archive_after_days': 30,
            'grafana_webhook_url': None,
            'notification_settings': {
                'enable_slack': False,
                'slack_webhook': None,
                'enable_email': False
            }
        }
        
        config_path = Path(config_file)
        if config_path.exists():
            with open(config_path) as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    def start_monitoring(self):
        """Start file system monitoring"""
        logger.info("Starting automation pipeline...")
        
        # Create watch directories if they don't exist
        for watch_dir in self.watch_dirs:
            Path(watch_dir).mkdir(parents=True, exist_ok=True)
        
        # Set up file watcher
        self.observer = Observer()
        handler = DymolaFileHandler(self)
        
        for watch_dir in self.watch_dirs:
            self.observer.schedule(handler, watch_dir, recursive=True)
            logger.info(f"Watching directory: {watch_dir}")
        
        self.observer.start()
        
        # Start background processing thread
        self.processing_thread = Thread(target=self._background_processor, daemon=True)
        self.processing_thread.start()
        
        # Start periodic cleanup thread
        cleanup_thread = Thread(target=self._periodic_cleanup, daemon=True)
        cleanup_thread.start()
        
        logger.info("Automation pipeline started successfully")
    
    def stop_monitoring(self):
        """Stop monitoring and clean up"""
        logger.info("Stopping automation pipeline...")
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
        
        logger.info("Automation pipeline stopped")
    
    def process_new_file(self, file_path: Path):
        """Process a newly detected file"""
        try:
            logger.info(f"Processing file: {file_path}")
            
            # Validate file
            if not file_path.exists():
                logger.warning(f"File no longer exists: {file_path}")
                return
                
            if file_path.stat().st_size == 0:
                logger.warning(f"Empty file detected: {file_path}")
                return
            
            # Generate simulation name from filename
            simulation_name = file_path.stem
            
            # Export .mat to CSV
            export_result = self.exporter.convert_to_csv(file_path, simulation_name)
            
            if not export_result:
                logger.error(f"Failed to export {file_path}")
                self.stats['processing_errors'] += 1
                return
            
            # Organize file in data lake
            organize_result = self.data_manager.organize_file(file_path, simulation_name)
            
            # Update statistics
            self.stats['files_processed'] += 1
            self.stats['last_processed'] = datetime.now().isoformat()
            
            logger.info(f"Successfully processed {file_path}")
            logger.info(f"CSV output: {export_result['csv_path']}")
            logger.info(f"Organized as: {organize_result['simulation_id']}")
            
            # Send notifications if configured
            self._send_notification(f"Processed new simulation: {simulation_name}")
            
            # Trigger Grafana dashboard refresh if configured
            self._refresh_grafana_dashboard()
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            self.stats['processing_errors'] += 1
    
    def _background_processor(self):
        """Background thread for periodic tasks"""
        while True:
            try:
                # Process any queued items
                if self.processing_queue:
                    file_path = self.processing_queue.pop(0)
                    self.process_new_file(file_path)
                
                # Update health metrics
                self._update_health_metrics()
                
                time.sleep(self.config.get('processing_interval', 5))
                
            except Exception as e:
                logger.error(f"Background processor error: {e}")
                time.sleep(10)
    
    def _periodic_cleanup(self):
        """Periodic cleanup tasks"""
        while True:
            try:
                interval = self.config.get('cleanup_interval', 3600)
                time.sleep(interval)
                
                logger.info("Running periodic cleanup...")
                
                # Archive old data
                archive_days = self.config.get('archive_after_days', 30)
                archived_count = self.data_manager.archive_old_data(archive_days)
                
                if archived_count > 0:
                    logger.info(f"Archived {archived_count} old simulations")
                
                # Clean up temporary files
                self._cleanup_temp_files()
                
                # Rotate logs if needed
                self._rotate_logs()
                
                logger.info("Periodic cleanup completed")
                
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
    
    def _cleanup_temp_files(self):
        """Clean up temporary and stale files"""
        temp_patterns = ['*.tmp', '*.temp', '.DS_Store']
        
        for watch_dir in self.watch_dirs:
            watch_path = Path(watch_dir)
            
            for pattern in temp_patterns:
                for temp_file in watch_path.rglob(pattern):
                    try:
                        temp_file.unlink()
                        logger.debug(f"Removed temp file: {temp_file}")
                    except Exception as e:
                        logger.warning(f"Could not remove {temp_file}: {e}")
    
    def _rotate_logs(self):
        """Rotate log files if they get too large"""
        log_file = Path("logs/automation.log")
        
        if log_file.exists() and log_file.stat().st_size > 10 * 1024 * 1024:  # 10MB
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"automation_{timestamp}.log"
            shutil.move(log_file, log_file.parent / backup_name)
            logger.info(f"Rotated log file to {backup_name}")
    
    def _send_notification(self, message: str):
        """Send notification about processing events"""
        notification_config = self.config.get('notification_settings', {})
        
        # Slack notification
        if notification_config.get('enable_slack') and notification_config.get('slack_webhook'):
            try:
                payload = {
                    'text': f"Dymola Pipeline: {message}",
                    'channel': '#dymola-automation',
                    'username': 'Dymola Bot'
                }
                requests.post(notification_config['slack_webhook'], json=payload, timeout=5)
            except Exception as e:
                logger.warning(f"Failed to send Slack notification: {e}")
    
    def _refresh_grafana_dashboard(self):
        """Trigger Grafana dashboard refresh"""
        webhook_url = self.config.get('grafana_webhook_url')
        
        if webhook_url:
            try:
                response = requests.post(webhook_url, timeout=5)
                logger.debug(f"Grafana refresh response: {response.status_code}")
            except Exception as e:
                logger.warning(f"Failed to refresh Grafana dashboard: {e}")
    
    def _update_health_metrics(self):
        """Update health metrics for monitoring"""
        health_data = {
            'timestamp': datetime.now().isoformat(),
            'stats': self.stats,
            'config': {
                'watch_directories': self.watch_dirs,
                'processing_interval': self.config.get('processing_interval')
            }
        }
        
        # Write health data to file for monitoring
        health_file = Path("logs/health.json")
        with open(health_file, 'w') as f:
            json.dump(health_data, f, indent=2)
    
    def get_status(self) -> Dict:
        """Get current pipeline status"""
        return {
            'running': self.observer is not None and self.observer.is_alive(),
            'stats': self.stats.copy(),
            'config': self.config.copy(),
            'watched_directories': self.watch_dirs
        }


def main():
    """Command-line interface for automation pipeline"""
    import argparse
    import signal
    import sys
    
    parser = argparse.ArgumentParser(description='Dymola Automation Pipeline')
    parser.add_argument('--config', default='config/automation_config.json',
                       help='Configuration file path')
    parser.add_argument('--daemon', action='store_true',
                       help='Run as daemon process')
    parser.add_argument('--status', action='store_true',
                       help='Show current status')
    
    args = parser.parse_args()
    
    # Create pipeline
    pipeline = AutomationPipeline(args.config)
    
    if args.status:
        status = pipeline.get_status()
        print(json.dumps(status, indent=2))
        return
    
    def signal_handler(signum, frame):
        logger.info("Received interrupt signal, stopping...")
        pipeline.stop_monitoring()
        sys.exit(0)
    
    # Set up signal handling
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start monitoring
        pipeline.start_monitoring()
        
        if args.daemon:
            # Run as daemon
            while True:
                time.sleep(60)
                logger.debug("Pipeline running...")
        else:
            # Interactive mode
            print("Automation pipeline started. Press Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
                
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        return 1
    finally:
        pipeline.stop_monitoring()


if __name__ == '__main__':
    main()