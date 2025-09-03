#!/usr/bin/env python3
"""
CSV Metrics Exporter for OpenTelemetry Alloy
Analyzes Dymola CSV files and exposes metrics in Prometheus format
"""

import os
import time
import pandas as pd
import numpy as np
from pathlib import Path
from flask import Flask, Response
from threading import Thread
import logging
from datetime import datetime
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


class CSVMetricsCollector:
    """Collect metrics from Dymola CSV files"""
    
    def __init__(self, data_dir="data/processed"):
        self.data_dir = Path(data_dir)
        self.metrics = {}
        self.last_scan = None
        
    def scan_csv_files(self):
        """Scan all CSV files and extract metrics"""
        if not self.data_dir.exists():
            logger.warning(f"Data directory {self.data_dir} does not exist")
            return
            
        csv_files = list(self.data_dir.rglob("*.csv"))
        
        total_files = len(csv_files)
        total_size = sum(f.stat().st_size for f in csv_files if f.exists())
        
        # Initialize base metrics
        self.metrics = {
            'dymola_csv_files_total': total_files,
            'dymola_csv_total_size_bytes': total_size,
            'dymola_csv_scan_timestamp': time.time()
        }
        
        # Per-file analysis
        simulation_metrics = {}
        variable_stats = {}
        
        for csv_file in csv_files[:10]:  # Limit to first 10 for performance
            try:
                df = pd.read_csv(csv_file)
                
                # Basic file metrics
                simulation_name = csv_file.stem
                row_count = len(df)
                col_count = len(df.columns)
                
                # Time series analysis if 'time' column exists
                if 'time' in df.columns:
                    time_col = df['time']
                    duration = float(time_col.max() - time_col.min()) if len(time_col) > 1 else 0
                    sample_rate = len(time_col) / duration if duration > 0 else 0
                    
                    self.metrics[f'dymola_simulation_duration_seconds{{simulation="{simulation_name}"}}'] = duration
                    self.metrics[f'dymola_simulation_sample_rate{{simulation="{simulation_name}"}}'] = sample_rate
                
                # Variable analysis
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                for col in numeric_cols:
                    if col != 'time':  # Skip time column
                        series = df[col].dropna()
                        if len(series) > 0:
                            var_mean = float(series.mean())
                            var_std = float(series.std())
                            var_min = float(series.min())
                            var_max = float(series.max())
                            
                            # Store variable statistics
                            base_name = f'dymola_variable'
                            labels = f'simulation="{simulation_name}",variable="{col}"'
                            
                            self.metrics[f'{base_name}_mean{{{labels}}}'] = var_mean
                            self.metrics[f'{base_name}_std{{{labels}}}'] = var_std
                            self.metrics[f'{base_name}_min{{{labels}}}'] = var_min
                            self.metrics[f'{base_name}_max{{{labels}}}'] = var_max
                
                # File-level metrics
                self.metrics[f'dymola_file_rows{{simulation="{simulation_name}"}}'] = row_count
                self.metrics[f'dymola_file_columns{{simulation="{simulation_name}"}}'] = col_count
                self.metrics[f'dymola_file_size_bytes{{simulation="{simulation_name}"}}'] = csv_file.stat().st_size
                
            except Exception as e:
                logger.error(f"Error processing {csv_file}: {e}")
                continue
        
        self.last_scan = datetime.now()
        logger.info(f"Scanned {total_files} CSV files, extracted {len(self.metrics)} metrics")
    
    def get_prometheus_metrics(self):
        """Format metrics in Prometheus exposition format"""
        if not self.metrics:
            self.scan_csv_files()
            
        lines = []
        
        # Add help and type information for key metrics
        lines.extend([
            "# HELP dymola_csv_files_total Total number of CSV files",
            "# TYPE dymola_csv_files_total gauge",
            f"dymola_csv_files_total {self.metrics.get('dymola_csv_files_total', 0)}",
            "",
            "# HELP dymola_csv_total_size_bytes Total size of all CSV files in bytes", 
            "# TYPE dymola_csv_total_size_bytes gauge",
            f"dymola_csv_total_size_bytes {self.metrics.get('dymola_csv_total_size_bytes', 0)}",
            "",
            "# HELP dymola_simulation_duration_seconds Duration of simulation in seconds",
            "# TYPE dymola_simulation_duration_seconds gauge",
            ""
        ])
        
        # Add all metrics
        for metric_name, value in self.metrics.items():
            if not metric_name.startswith('dymola_csv_'):
                lines.append(f"{metric_name} {value}")
        
        return "\n".join(lines)


# Global collector instance
collector = CSVMetricsCollector()


@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint"""
    return Response(collector.get_prometheus_metrics(), mimetype='text/plain')


@app.route('/csv-metrics')  
def csv_metrics():
    """Specialized CSV metrics endpoint"""
    collector.scan_csv_files()  # Refresh on each request
    return Response(collector.get_prometheus_metrics(), mimetype='text/plain')


@app.route('/health')
def health():
    """Health check endpoint"""
    status = {
        'status': 'healthy',
        'last_scan': collector.last_scan.isoformat() if collector.last_scan else None,
        'metrics_count': len(collector.metrics),
        'data_directory': str(collector.data_dir)
    }
    return json.dumps(status), 200, {'Content-Type': 'application/json'}


def background_scanner():
    """Background thread to periodically scan files"""
    while True:
        try:
            collector.scan_csv_files()
            time.sleep(60)  # Scan every minute
        except Exception as e:
            logger.error(f"Background scan error: {e}")
            time.sleep(30)  # Retry in 30 seconds


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='CSV Metrics Exporter')
    parser.add_argument('--port', type=int, default=5001, help='Server port')
    parser.add_argument('--data-dir', default='data/processed', help='Data directory')
    parser.add_argument('--no-background', action='store_true', help='Disable background scanning')
    
    args = parser.parse_args()
    
    # Update collector data directory
    collector.data_dir = Path(args.data_dir)
    
    # Start background scanner
    if not args.no_background:
        scanner_thread = Thread(target=background_scanner, daemon=True)
        scanner_thread.start()
    
    # Initial scan
    collector.scan_csv_files()
    
    logger.info(f"Starting CSV Metrics Exporter on port {args.port}")
    logger.info(f"Data directory: {collector.data_dir}")
    
    app.run(host='0.0.0.0', port=args.port, debug=False)


if __name__ == '__main__':
    main()