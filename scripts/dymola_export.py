#!/usr/bin/env python3
"""
Dymola Data Export Script
Converts Dymola .mat files to CSV format for Grafana visualization
"""

import os
import sys
import pandas as pd
import numpy as np
from scipy.io import loadmat
from pathlib import Path
import json
import logging
from datetime import datetime
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DymolaExporter:
    """Export Dymola .mat files to CSV format with metadata"""
    
    def __init__(self, output_dir="data/processed"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def extract_mat_data(self, mat_file_path):
        """Extract data from .mat file"""
        try:
            mat_data = loadmat(mat_file_path)
            
            # Extract variable names and data
            variables = {}
            time_vector = None
            
            # Common Dymola structure
            if 'data_2' in mat_data:
                data_matrix = mat_data['data_2']
                names = mat_data.get('name', [])
                descriptions = mat_data.get('description', [])
                
                # Decode names if they're byte strings
                if len(names) > 0 and isinstance(names[0], np.ndarray):
                    names = [name.item() if hasattr(name, 'item') else str(name) 
                            for name in names]
                
                # First column is typically time
                if data_matrix.shape[0] > 0:
                    time_vector = data_matrix[0, :]
                    
                # Extract other variables
                for i, name in enumerate(names[1:], 1):
                    if i < data_matrix.shape[0]:
                        variables[str(name)] = data_matrix[i, :]
                        
            return time_vector, variables
            
        except Exception as e:
            logger.error(f"Error extracting data from {mat_file_path}: {e}")
            return None, None
    
    def convert_to_csv(self, mat_file_path, simulation_name=None):
        """Convert .mat file to CSV format"""
        mat_path = Path(mat_file_path)
        
        if not mat_path.exists():
            logger.error(f"File not found: {mat_file_path}")
            return None
            
        simulation_name = simulation_name or mat_path.stem
        
        logger.info(f"Processing {mat_file_path}")
        
        time_vector, variables = self.extract_mat_data(mat_file_path)
        
        if time_vector is None or not variables:
            logger.error("No data extracted from .mat file")
            return None
            
        # Create DataFrame
        df_data = {'time': time_vector}
        df_data.update(variables)
        
        df = pd.DataFrame(df_data)
        
        # Save to CSV
        csv_path = self.output_dir / f"{simulation_name}.csv"
        df.to_csv(csv_path, index=False)
        
        # Generate metadata
        metadata = {
            'simulation_name': simulation_name,
            'source_file': str(mat_path),
            'export_timestamp': datetime.now().isoformat(),
            'variables': list(variables.keys()),
            'time_range': {
                'start': float(time_vector.min()),
                'end': float(time_vector.max()),
                'duration': float(time_vector.max() - time_vector.min())
            },
            'data_points': len(time_vector),
            'csv_file': str(csv_path)
        }
        
        # Save metadata
        metadata_path = self.output_dir / f"{simulation_name}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
            
        logger.info(f"Exported {len(variables)} variables to {csv_path}")
        logger.info(f"Metadata saved to {metadata_path}")
        
        return {
            'csv_path': csv_path,
            'metadata_path': metadata_path,
            'metadata': metadata
        }
    
    def batch_convert(self, input_dir, pattern="*.mat"):
        """Convert all .mat files in directory"""
        input_path = Path(input_dir)
        results = []
        
        mat_files = list(input_path.glob(pattern))
        
        if not mat_files:
            logger.warning(f"No .mat files found in {input_dir}")
            return results
            
        for mat_file in mat_files:
            result = self.convert_to_csv(mat_file)
            if result:
                results.append(result)
                
        logger.info(f"Processed {len(results)} files successfully")
        return results


def main():
    parser = argparse.ArgumentParser(description='Export Dymola .mat files to CSV')
    parser.add_argument('input', help='Input .mat file or directory')
    parser.add_argument('--output', '-o', default='data/processed', 
                       help='Output directory for CSV files')
    parser.add_argument('--name', '-n', help='Simulation name override')
    parser.add_argument('--batch', '-b', action='store_true', 
                       help='Batch process directory')
    
    args = parser.parse_args()
    
    exporter = DymolaExporter(args.output)
    
    if args.batch or Path(args.input).is_dir():
        results = exporter.batch_convert(args.input)
        print(f"Processed {len(results)} files")
    else:
        result = exporter.convert_to_csv(args.input, args.name)
        if result:
            print(f"Exported to: {result['csv_path']}")
        else:
            print("Export failed")


if __name__ == "__main__":
    main()