#!/usr/bin/env python3
"""
Data Server for Grafana Infinity Plugin
Serves Dymola simulation data via REST API for Grafana visualization
"""

import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for Grafana


class DymolaDataServer:
    """Server for providing Dymola data to Grafana Infinity plugin"""
    
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.processed_dir = self.data_dir / "processed"
        self.metadata_dir = self.data_dir / "metadata"
        self.catalog_path = self.metadata_dir / "catalog.json"
        
        self._load_catalog()
    
    def _load_catalog(self):
        """Load simulation catalog"""
        if self.catalog_path.exists():
            with open(self.catalog_path) as f:
                self.catalog = json.load(f)
        else:
            self.catalog = {'simulations': {}}
    
    def list_simulations(self, limit: int = 100) -> List[Dict]:
        """List available simulations"""
        simulations = []
        
        for sim_id, sim_data in list(self.catalog['simulations'].items())[:limit]:
            simulations.append({
                'id': sim_id,
                'name': sim_data.get('simulation_name', 'Unknown'),
                'created': sim_data.get('created'),
                'variables': sim_data.get('variables', []),
                'duration': sim_data.get('time_range', {}).get('duration', 0),
                'data_points': sim_data.get('data_points', 0)
            })
        
        return sorted(simulations, key=lambda x: x['created'] or '', reverse=True)
    
    def get_simulation_data(self, sim_id: str, 
                          variables: List[str] = None,
                          time_start: float = None,
                          time_end: float = None,
                          sample_rate: int = None) -> Optional[Dict]:
        """Get simulation data for specific variables and time range"""
        
        if sim_id not in self.catalog['simulations']:
            return None
            
        sim_info = self.catalog['simulations'][sim_id]
        
        # Find CSV file path
        csv_path = None
        organized_path = sim_info.get('organized_path')
        
        if organized_path and Path(organized_path).exists():
            # Check if it's already CSV
            if organized_path.endswith('.csv'):
                csv_path = Path(organized_path)
            else:
                # Look for corresponding CSV file
                csv_name = Path(organized_path).stem + '.csv'
                csv_path = self.processed_dir / csv_name
        
        if not csv_path or not csv_path.exists():
            # Try to find CSV file by name pattern
            csv_files = list(self.processed_dir.rglob(f"{sim_id}.csv"))
            if not csv_files:
                csv_files = list(self.processed_dir.rglob("*.csv"))
                csv_files = [f for f in csv_files if sim_id in f.name or 
                           sim_info.get('simulation_name', '') in f.name]
            
            if csv_files:
                csv_path = csv_files[0]
            else:
                return None
        
        try:
            # Load CSV data
            df = pd.read_csv(csv_path)
            
            # Filter by time range if specified
            if time_start is not None or time_end is not None:
                if 'time' in df.columns:
                    if time_start is not None:
                        df = df[df['time'] >= time_start]
                    if time_end is not None:
                        df = df[df['time'] <= time_end]
            
            # Filter by variables if specified
            available_vars = [col for col in df.columns if col != 'time']
            if variables:
                # Keep time column plus requested variables
                requested_vars = ['time'] + [v for v in variables if v in df.columns]
                df = df[requested_vars]
                available_vars = [v for v in requested_vars if v != 'time']
            
            # Sample data if requested
            if sample_rate and len(df) > sample_rate:
                step = len(df) // sample_rate
                df = df.iloc[::step]
            
            # Convert to JSON-friendly format
            data = df.to_dict('records')
            
            return {
                'simulation_id': sim_id,
                'simulation_name': sim_info.get('simulation_name', 'Unknown'),
                'variables': available_vars,
                'data_points': len(data),
                'time_range': {
                    'start': float(df['time'].min()) if 'time' in df.columns else None,
                    'end': float(df['time'].max()) if 'time' in df.columns else None
                },
                'data': data
            }
            
        except Exception as e:
            logger.error(f"Error loading data for {sim_id}: {e}")
            return None
    
    def get_variable_stats(self, sim_id: str, variable: str) -> Optional[Dict]:
        """Get statistics for a specific variable"""
        data = self.get_simulation_data(sim_id, [variable])
        
        if not data or not data['data']:
            return None
            
        # Extract variable values
        values = [row.get(variable) for row in data['data'] if row.get(variable) is not None]
        
        if not values:
            return None
            
        values = np.array(values, dtype=float)
        
        return {
            'variable': variable,
            'count': len(values),
            'mean': float(np.mean(values)),
            'std': float(np.std(values)),
            'min': float(np.min(values)),
            'max': float(np.max(values)),
            'percentiles': {
                '25': float(np.percentile(values, 25)),
                '50': float(np.percentile(values, 50)),
                '75': float(np.percentile(values, 75)),
                '95': float(np.percentile(values, 95))
            }
        }


# Global server instance
server = DymolaDataServer()


@app.route('/')
def home():
    """API documentation"""
    return jsonify({
        'name': 'Dymola Data Server',
        'version': '1.0',
        'description': 'REST API for Grafana Infinity plugin to access Dymola simulation data',
        'endpoints': {
            '/simulations': 'List available simulations',
            '/simulations/<id>': 'Get simulation data',
            '/simulations/<id>/variables/<variable>/stats': 'Get variable statistics',
            '/csv/<id>': 'Download raw CSV file',
            '/health': 'Health check'
        }
    })


@app.route('/simulations')
def list_simulations():
    """List all available simulations"""
    limit = request.args.get('limit', 100, type=int)
    simulations = server.list_simulations(limit)
    return jsonify(simulations)


@app.route('/simulations/<sim_id>')
def get_simulation_data(sim_id):
    """Get data for a specific simulation"""
    
    # Parse query parameters
    variables = request.args.get('variables')
    if variables:
        variables = [v.strip() for v in variables.split(',')]
    
    time_start = request.args.get('time_start', type=float)
    time_end = request.args.get('time_end', type=float)
    sample_rate = request.args.get('sample_rate', type=int)
    
    # Get data
    data = server.get_simulation_data(
        sim_id, variables, time_start, time_end, sample_rate
    )
    
    if data is None:
        return jsonify({'error': 'Simulation not found'}), 404
        
    return jsonify(data)


@app.route('/simulations/<sim_id>/variables/<variable>/stats')
def get_variable_stats(sim_id, variable):
    """Get statistics for a specific variable"""
    stats = server.get_variable_stats(sim_id, variable)
    
    if stats is None:
        return jsonify({'error': 'Variable not found'}), 404
        
    return jsonify(stats)


@app.route('/csv/<sim_id>')
def download_csv(sim_id):
    """Download raw CSV file"""
    if sim_id not in server.catalog['simulations']:
        return jsonify({'error': 'Simulation not found'}), 404
    
    sim_info = server.catalog['simulations'][sim_id]
    organized_path = sim_info.get('organized_path')
    
    if organized_path and Path(organized_path).exists():
        if organized_path.endswith('.csv'):
            return send_file(organized_path, as_attachment=True)
        else:
            # Look for corresponding CSV
            csv_name = Path(organized_path).stem + '.csv'
            csv_path = server.processed_dir / csv_name
            if csv_path.exists():
                return send_file(csv_path, as_attachment=True)
    
    return jsonify({'error': 'CSV file not found'}), 404


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'simulations_count': len(server.catalog.get('simulations', {})),
        'data_directory': str(server.data_dir)
    })


# Grafana-specific endpoints for easy querying
@app.route('/grafana/search')
def grafana_search():
    """Search endpoint for Grafana variable queries"""
    simulations = server.list_simulations()
    return jsonify([sim['id'] for sim in simulations])


@app.route('/grafana/variables/<sim_id>')
def grafana_variables(sim_id):
    """Get variables for a simulation (for Grafana variable queries)"""
    if sim_id not in server.catalog['simulations']:
        return jsonify([])
        
    variables = server.catalog['simulations'][sim_id].get('variables', [])
    return jsonify(variables)


@app.route('/grafana/timeseries/<sim_id>')
def grafana_timeseries(sim_id):
    """Get time series data formatted for Grafana"""
    variables = request.args.get('variables', 'all')
    if variables != 'all':
        variables = [v.strip() for v in variables.split(',')]
    else:
        variables = None
        
    data = server.get_simulation_data(sim_id, variables)
    
    if data is None:
        return jsonify([])
    
    # Format for Grafana time series
    series = []
    
    for variable in data['variables']:
        points = []
        for row in data['data']:
            if 'time' in row and variable in row:
                # Convert time to milliseconds timestamp
                timestamp = int(row['time'] * 1000)
                value = row[variable]
                points.append([value, timestamp])
        
        series.append({
            'target': f"{data['simulation_name']}.{variable}",
            'datapoints': points
        })
    
    return jsonify(series)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Dymola Data Server')
    parser.add_argument('--port', type=int, default=5000, help='Server port')
    parser.add_argument('--host', default='0.0.0.0', help='Server host')
    parser.add_argument('--data-dir', default='data', help='Data directory')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    # Update server data directory
    server.data_dir = Path(args.data_dir)
    server.processed_dir = server.data_dir / "processed"
    server.metadata_dir = server.data_dir / "metadata"
    server.catalog_path = server.metadata_dir / "catalog.json"
    server._load_catalog()
    
    logger.info(f"Starting Dymola Data Server on {args.host}:{args.port}")
    logger.info(f"Data directory: {server.data_dir}")
    logger.info(f"Available simulations: {len(server.catalog.get('simulations', {}))}")
    
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()