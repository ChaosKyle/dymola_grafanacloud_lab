#!/usr/bin/env python3
"""
Data Manager for organizing and indexing Dymola simulation data
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class DataManager:
    """Manage data lake organization and metadata"""
    
    def __init__(self, base_dir="data"):
        self.base_dir = Path(base_dir)
        self.raw_dir = self.base_dir / "raw"
        self.processed_dir = self.base_dir / "processed"
        self.metadata_dir = self.base_dir / "metadata"
        self.archive_dir = self.base_dir / "archive"
        
        # Create directories
        for dir_path in [self.raw_dir, self.processed_dir, 
                        self.metadata_dir, self.archive_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
            
        self.catalog_path = self.metadata_dir / "catalog.json"
        self._load_catalog()
    
    def _load_catalog(self):
        """Load or create simulation catalog"""
        if self.catalog_path.exists():
            with open(self.catalog_path) as f:
                self.catalog = json.load(f)
        else:
            self.catalog = {
                'version': '1.0',
                'created': datetime.now().isoformat(),
                'simulations': {},
                'statistics': {
                    'total_simulations': 0,
                    'total_size_mb': 0,
                    'last_updated': None
                }
            }
            
    def _save_catalog(self):
        """Save catalog to disk"""
        self.catalog['statistics']['last_updated'] = datetime.now().isoformat()
        with open(self.catalog_path, 'w') as f:
            json.dump(self.catalog, f, indent=2)
    
    def organize_file(self, file_path: Path, simulation_name: str = None) -> Dict:
        """Organize file into data lake structure"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        # Generate simulation name if not provided
        if not simulation_name:
            simulation_name = file_path.stem
            
        # Create date-based directory structure
        today = datetime.now()
        date_dir = today.strftime("%Y-%m-%d")
        
        # Determine target directory based on file type
        if file_path.suffix.lower() == '.mat':
            target_dir = self.raw_dir / date_dir
        elif file_path.suffix.lower() == '.csv':
            target_dir = self.processed_dir / date_dir
        else:
            target_dir = self.raw_dir / date_dir
            
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate timestamped filename
        timestamp = today.strftime("%Y%m%d_%H%M%S")
        new_filename = f"{simulation_name}_{timestamp}{file_path.suffix}"
        target_path = target_dir / new_filename
        
        # Copy file to organized location
        shutil.copy2(file_path, target_path)
        
        # Update catalog
        simulation_id = f"{simulation_name}_{timestamp}"
        self.catalog['simulations'][simulation_id] = {
            'simulation_name': simulation_name,
            'original_file': str(file_path),
            'organized_path': str(target_path),
            'file_type': file_path.suffix.lower(),
            'size_bytes': target_path.stat().st_size,
            'created': today.isoformat(),
            'date_partition': date_dir
        }
        
        self.catalog['statistics']['total_simulations'] += 1
        self.catalog['statistics']['total_size_mb'] += target_path.stat().st_size / (1024 * 1024)
        
        self._save_catalog()
        
        logger.info(f"Organized {file_path} -> {target_path}")
        
        return {
            'simulation_id': simulation_id,
            'organized_path': target_path,
            'catalog_entry': self.catalog['simulations'][simulation_id]
        }
    
    def get_simulation_info(self, simulation_id: str) -> Optional[Dict]:
        """Get information about a simulation"""
        return self.catalog['simulations'].get(simulation_id)
    
    def list_simulations(self, 
                        date_from: str = None, 
                        date_to: str = None,
                        name_pattern: str = None) -> List[Dict]:
        """List simulations with optional filtering"""
        results = []
        
        for sim_id, sim_data in self.catalog['simulations'].items():
            # Date filtering
            if date_from or date_to:
                sim_date = datetime.fromisoformat(sim_data['created']).date()
                
                if date_from:
                    if sim_date < datetime.strptime(date_from, "%Y-%m-%d").date():
                        continue
                        
                if date_to:
                    if sim_date > datetime.strptime(date_to, "%Y-%m-%d").date():
                        continue
            
            # Name pattern filtering
            if name_pattern:
                if name_pattern.lower() not in sim_data['simulation_name'].lower():
                    continue
                    
            results.append({
                'id': sim_id,
                **sim_data
            })
            
        return sorted(results, key=lambda x: x['created'], reverse=True)
    
    def archive_old_data(self, days_old: int = 90):
        """Archive data older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        archived_count = 0
        
        for sim_id, sim_data in list(self.catalog['simulations'].items()):
            sim_date = datetime.fromisoformat(sim_data['created'])
            
            if sim_date < cutoff_date:
                # Create archive structure
                archive_year_dir = self.archive_dir / str(sim_date.year)
                archive_year_dir.mkdir(exist_ok=True)
                
                # Move file to archive
                source_path = Path(sim_data['organized_path'])
                if source_path.exists():
                    archive_path = archive_year_dir / source_path.name
                    shutil.move(str(source_path), str(archive_path))
                    
                    # Update catalog entry
                    self.catalog['simulations'][sim_id]['archived'] = True
                    self.catalog['simulations'][sim_id]['archive_path'] = str(archive_path)
                    
                    archived_count += 1
                    
        self._save_catalog()
        logger.info(f"Archived {archived_count} old simulations")
        
        return archived_count
    
    def get_data_summary(self) -> Dict:
        """Get summary statistics of data lake"""
        summary = {
            'total_simulations': len(self.catalog['simulations']),
            'total_size_mb': round(self.catalog['statistics']['total_size_mb'], 2),
            'date_range': None,
            'file_types': {},
            'recent_simulations': []
        }
        
        if self.catalog['simulations']:
            dates = [datetime.fromisoformat(sim['created']) 
                    for sim in self.catalog['simulations'].values()]
            summary['date_range'] = {
                'earliest': min(dates).isoformat(),
                'latest': max(dates).isoformat()
            }
            
            # File type breakdown
            for sim in self.catalog['simulations'].values():
                file_type = sim.get('file_type', 'unknown')
                summary['file_types'][file_type] = summary['file_types'].get(file_type, 0) + 1
            
            # Recent simulations
            recent_sims = sorted(self.catalog['simulations'].items(), 
                               key=lambda x: x[1]['created'], reverse=True)[:5]
            summary['recent_simulations'] = [
                {
                    'id': sim_id,
                    'name': sim_data['simulation_name'],
                    'created': sim_data['created'],
                    'size_mb': round(sim_data['size_bytes'] / (1024 * 1024), 2)
                }
                for sim_id, sim_data in recent_sims
            ]
            
        return summary


def main():
    """CLI interface for data manager"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage Dymola simulation data')
    parser.add_argument('action', choices=['organize', 'list', 'summary', 'archive'])
    parser.add_argument('--file', help='File to organize')
    parser.add_argument('--name', help='Simulation name')
    parser.add_argument('--days', type=int, default=90, help='Days for archive operation')
    parser.add_argument('--from-date', help='Filter from date (YYYY-MM-DD)')
    parser.add_argument('--to-date', help='Filter to date (YYYY-MM-DD)')
    parser.add_argument('--pattern', help='Name pattern to filter')
    
    args = parser.parse_args()
    
    manager = DataManager()
    
    if args.action == 'organize':
        if not args.file:
            print("--file required for organize action")
            return
        result = manager.organize_file(args.file, args.name)
        print(f"Organized as: {result['simulation_id']}")
        
    elif args.action == 'list':
        simulations = manager.list_simulations(args.from_date, args.to_date, args.pattern)
        for sim in simulations:
            print(f"{sim['id']}: {sim['simulation_name']} ({sim['created']})")
            
    elif args.action == 'summary':
        summary = manager.get_data_summary()
        print(json.dumps(summary, indent=2))
        
    elif args.action == 'archive':
        count = manager.archive_old_data(args.days)
        print(f"Archived {count} simulations older than {args.days} days")


if __name__ == "__main__":
    main()