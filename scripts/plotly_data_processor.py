#!/usr/bin/env python3
"""
Plotly Data Processor for Advanced Visualizations
Processes Dymola data for complex Plotly visualizations
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class PlotlyDataProcessor:
    """Process Dymola data for advanced Plotly visualizations"""
    
    def __init__(self):
        self.color_scales = {
            'temperature': 'RdYlBu_r',
            'pressure': 'Viridis', 
            'velocity': 'Plasma',
            'flow_rate': 'Cividis'
        }
    
    def create_3d_trajectory(self, df: pd.DataFrame, 
                           x_col: str = 'time',
                           y_col: str = 'temperature', 
                           z_col: str = 'pressure',
                           color_col: str = 'velocity') -> Dict:
        """Create 3D trajectory plot configuration"""
        
        if not all(col in df.columns for col in [x_col, y_col, z_col]):
            raise ValueError(f"Missing required columns: {[x_col, y_col, z_col]}")
        
        # Create color array
        color_data = df[color_col].values if color_col in df.columns else None
        
        config = {
            "data": [{
                "x": df[x_col].tolist(),
                "y": df[y_col].tolist(), 
                "z": df[z_col].tolist(),
                "type": "scatter3d",
                "mode": "markers+lines",
                "marker": {
                    "size": 4,
                    "color": color_data.tolist() if color_data is not None else df[y_col].tolist(),
                    "colorscale": self.color_scales.get(color_col, "Viridis"),
                    "showscale": True,
                    "colorbar": {
                        "title": color_col.replace('_', ' ').title(),
                        "titleside": "right"
                    },
                    "opacity": 0.8
                },
                "line": {
                    "width": 3,
                    "color": "rgba(31, 119, 180, 0.6)"
                },
                "name": "Simulation Trajectory"
            }],
            "layout": {
                "title": {
                    "text": "3D Simulation Trajectory",
                    "font": {"size": 16}
                },
                "scene": {
                    "xaxis": {
                        "title": x_col.replace('_', ' ').title(),
                        "backgroundcolor": "rgba(0,0,0,0)",
                        "gridcolor": "rgba(255,255,255,0.2)"
                    },
                    "yaxis": {
                        "title": y_col.replace('_', ' ').title(),
                        "backgroundcolor": "rgba(0,0,0,0)",
                        "gridcolor": "rgba(255,255,255,0.2)"
                    },
                    "zaxis": {
                        "title": z_col.replace('_', ' ').title(),
                        "backgroundcolor": "rgba(0,0,0,0)",
                        "gridcolor": "rgba(255,255,255,0.2)"
                    },
                    "camera": {
                        "eye": {"x": 1.5, "y": 1.5, "z": 1.5}
                    },
                    "bgcolor": "rgba(0,0,0,0)"
                },
                "paper_bgcolor": "rgba(0,0,0,0)",
                "plot_bgcolor": "rgba(0,0,0,0)",
                "margin": {"l": 0, "r": 0, "b": 0, "t": 40}
            }
        }
        
        return config
    
    def create_surface_plot(self, df: pd.DataFrame,
                          x_col: str = 'time',
                          y_col: str = 'position', 
                          z_col: str = 'temperature',
                          grid_size: Tuple[int, int] = (50, 50)) -> Dict:
        """Create 3D surface plot configuration"""
        
        # Create meshgrid for surface plot
        x_unique = np.linspace(df[x_col].min(), df[x_col].max(), grid_size[0])
        y_unique = np.linspace(df[y_col].min(), df[y_col].max(), grid_size[1])
        X, Y = np.meshgrid(x_unique, y_unique)
        
        # Interpolate Z values
        from scipy.interpolate import griddata
        points = df[[x_col, y_col]].values
        values = df[z_col].values
        Z = griddata(points, values, (X, Y), method='cubic', fill_value=np.nan)
        
        config = {
            "data": [{
                "x": x_unique.tolist(),
                "y": y_unique.tolist(), 
                "z": Z.tolist(),
                "type": "surface",
                "colorscale": self.color_scales.get(z_col, "Hot"),
                "showscale": True,
                "colorbar": {
                    "title": z_col.replace('_', ' ').title(),
                    "titleside": "right"
                },
                "opacity": 0.9
            }],
            "layout": {
                "title": {
                    "text": f"{z_col.title()} Surface",
                    "font": {"size": 16}
                },
                "scene": {
                    "xaxis": {"title": x_col.replace('_', ' ').title()},
                    "yaxis": {"title": y_col.replace('_', ' ').title()},
                    "zaxis": {"title": z_col.replace('_', ' ').title()},
                    "camera": {"eye": {"x": 1.25, "y": 1.25, "z": 1.25}}
                },
                "margin": {"l": 0, "r": 0, "b": 0, "t": 40}
            }
        }
        
        return config
    
    def create_phase_space(self, df: pd.DataFrame,
                          x_col: str = 'temperature',
                          y_col: str = 'pressure',
                          color_col: str = 'time') -> Dict:
        """Create phase space scatter plot"""
        
        config = {
            "data": [{
                "x": df[x_col].tolist(),
                "y": df[y_col].tolist(),
                "mode": "markers",
                "type": "scatter",
                "marker": {
                    "size": 6,
                    "color": df[color_col].tolist(),
                    "colorscale": "Rainbow",
                    "showscale": True,
                    "colorbar": {
                        "title": color_col.replace('_', ' ').title(),
                        "titleside": "right"
                    },
                    "line": {
                        "width": 1,
                        "color": "rgba(0,0,0,0.3)"
                    },
                    "opacity": 0.7
                },
                "name": f"{x_col} vs {y_col}",
                "hovertemplate": f"{x_col}: %{{x}}<br>{y_col}: %{{y}}<br>{color_col}: %{{marker.color}}<extra></extra>"
            }],
            "layout": {
                "title": {
                    "text": f"{x_col.title()}-{y_col.title()} Phase Space",
                    "font": {"size": 16}
                },
                "xaxis": {
                    "title": x_col.replace('_', ' ').title(),
                    "gridcolor": "rgba(255,255,255,0.2)"
                },
                "yaxis": {
                    "title": y_col.replace('_', ' ').title(),
                    "gridcolor": "rgba(255,255,255,0.2)"
                },
                "paper_bgcolor": "rgba(0,0,0,0)",
                "plot_bgcolor": "rgba(0,0,0,0)",
                "margin": {"l": 50, "r": 50, "b": 50, "t": 60}
            }
        }
        
        return config
    
    def create_correlation_heatmap(self, df: pd.DataFrame,
                                 variables: List[str] = None) -> Dict:
        """Create correlation matrix heatmap"""
        
        if variables is None:
            # Use all numeric columns except time
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            variables = [col for col in numeric_cols if col != 'time']
        
        # Calculate correlation matrix
        corr_matrix = df[variables].corr()
        
        config = {
            "data": [{
                "z": corr_matrix.values.tolist(),
                "x": variables,
                "y": variables,
                "type": "heatmap",
                "colorscale": "RdBu",
                "zmid": 0,
                "showscale": True,
                "colorbar": {
                    "title": "Correlation",
                    "titleside": "right"
                },
                "hoverongaps": False,
                "hovertemplate": "X: %{x}<br>Y: %{y}<br>Correlation: %{z:.3f}<extra></extra>"
            }],
            "layout": {
                "title": {
                    "text": "Variable Correlation Matrix",
                    "font": {"size": 16}
                },
                "xaxis": {"title": "Variables"},
                "yaxis": {"title": "Variables"},
                "margin": {"l": 100, "r": 50, "b": 100, "t": 60}
            }
        }
        
        return config
    
    def create_animated_scatter(self, df: pd.DataFrame,
                              x_col: str = 'temperature',
                              y_col: str = 'pressure', 
                              time_col: str = 'time',
                              size_col: str = None) -> Dict:
        """Create animated scatter plot over time"""
        
        # Create time bins for animation
        time_values = np.linspace(df[time_col].min(), df[time_col].max(), 20)
        frames = []
        
        for t in time_values:
            # Get data at this time point (with some tolerance)
            tolerance = (df[time_col].max() - df[time_col].min()) / 40
            mask = np.abs(df[time_col] - t) <= tolerance
            frame_data = df[mask]
            
            if len(frame_data) > 0:
                marker_config = {
                    "color": frame_data[y_col].tolist(),
                    "colorscale": "Viridis",
                    "showscale": True,
                    "size": 10
                }
                
                if size_col and size_col in frame_data.columns:
                    marker_config["size"] = frame_data[size_col].tolist()
                    marker_config["sizemode"] = "diameter"
                    marker_config["sizeref"] = frame_data[size_col].max() / 20
                
                frame = {
                    "data": [{
                        "x": frame_data[x_col].tolist(),
                        "y": frame_data[y_col].tolist(),
                        "mode": "markers",
                        "type": "scatter", 
                        "marker": marker_config,
                        "name": f"t = {t:.2f}"
                    }],
                    "name": str(t)
                }
                frames.append(frame)
        
        config = {
            "data": frames[0]["data"] if frames else [],
            "layout": {
                "title": {
                    "text": f"Animated {x_col.title()} vs {y_col.title()}",
                    "font": {"size": 16}
                },
                "xaxis": {"title": x_col.replace('_', ' ').title()},
                "yaxis": {"title": y_col.replace('_', ' ').title()},
                "updatemenus": [{
                    "type": "buttons",
                    "showactive": False,
                    "buttons": [
                        {
                            "label": "Play",
                            "method": "animate", 
                            "args": [None, {"frame": {"duration": 500}, "transition": {"duration": 300}}]
                        },
                        {
                            "label": "Pause",
                            "method": "animate",
                            "args": [[None], {"frame": {"duration": 0}, "mode": "immediate"}]
                        }
                    ]
                }],
                "sliders": [{
                    "steps": [
                        {
                            "args": [[str(t)], {"frame": {"duration": 0}, "mode": "immediate"}],
                            "label": f"{t:.2f}",
                            "method": "animate"
                        }
                        for t in time_values
                    ],
                    "active": 0,
                    "currentvalue": {"prefix": "Time: "},
                    "len": 0.9,
                    "x": 0.1,
                    "y": 0,
                    "xanchor": "left",
                    "yanchor": "bottom"
                }],
                "margin": {"l": 50, "r": 50, "b": 100, "t": 60}
            },
            "frames": frames
        }
        
        return config
    
    def create_parallel_coordinates(self, df: pd.DataFrame,
                                  variables: List[str] = None,
                                  color_col: str = 'time') -> Dict:
        """Create parallel coordinates plot"""
        
        if variables is None:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            variables = [col for col in numeric_cols if col != 'time'][:6]  # Limit to 6 for readability
        
        # Normalize data for better visualization
        df_norm = df[variables].copy()
        for col in variables:
            df_norm[col] = (df[col] - df[col].min()) / (df[col].max() - df[col].min())
        
        dimensions = []
        for var in variables:
            dimensions.append({
                "range": [df[var].min(), df[var].max()],
                "label": var.replace('_', ' ').title(),
                "values": df[var].tolist()
            })
        
        config = {
            "data": [{
                "type": "parcoords",
                "line": {
                    "color": df[color_col].tolist(),
                    "colorscale": "Rainbow",
                    "showscale": True,
                    "colorbar": {
                        "title": color_col.replace('_', ' ').title()
                    }
                },
                "dimensions": dimensions
            }],
            "layout": {
                "title": {
                    "text": "Parallel Coordinates Plot",
                    "font": {"size": 16}
                },
                "margin": {"l": 100, "r": 100, "b": 50, "t": 60}
            }
        }
        
        return config


def main():
    """Example usage and testing"""
    
    # Create sample data
    np.random.seed(42)
    n_points = 1000
    
    time = np.linspace(0, 10, n_points)
    temperature = 20 + 10 * np.sin(time) + 2 * np.random.random(n_points)
    pressure = 100 + 5 * np.cos(time * 1.5) + np.random.random(n_points)
    velocity = 5 + 3 * np.sin(time * 2) + np.random.random(n_points)
    position = np.cumsum(velocity) / 100
    
    df = pd.DataFrame({
        'time': time,
        'temperature': temperature,
        'pressure': pressure,
        'velocity': velocity,
        'position': position
    })
    
    processor = PlotlyDataProcessor()
    
    # Generate various plot configurations
    plots = {
        '3d_trajectory': processor.create_3d_trajectory(df),
        'phase_space': processor.create_phase_space(df),
        'correlation_heatmap': processor.create_correlation_heatmap(df),
        'parallel_coordinates': processor.create_parallel_coordinates(df)
    }
    
    # Save configurations
    output_dir = Path("dashboards/plotly_configs")
    output_dir.mkdir(exist_ok=True)
    
    for name, config in plots.items():
        with open(output_dir / f"{name}.json", 'w') as f:
            json.dump(config, f, indent=2)
        print(f"Saved {name} configuration")


if __name__ == '__main__':
    main()