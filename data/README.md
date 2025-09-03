# Data Storage Structure

This directory contains the organized data lake for Dymola simulation results.

## Directory Structure

```
data/
├── raw/                    # Original .mat files from Dymola
│   ├── YYYY-MM-DD/        # Date-based organization
│   └── simulation_name/    # Project-based organization
├── processed/             # Converted CSV files
│   ├── YYYY-MM-DD/       # Date-based CSV files
│   └── metadata/         # JSON metadata files
├── metadata/             # Simulation metadata and catalogs
│   ├── catalog.json      # Master catalog of all simulations
│   └── schemas/          # Data schemas and variable definitions
└── archive/              # Long-term storage and backups
    └── YYYY/            # Annual archives
```

## File Naming Conventions

- **Raw files**: `simulation_name_YYYYMMDD_HHMMSS.mat`
- **Processed files**: `simulation_name_YYYYMMDD_HHMMSS.csv`
- **Metadata files**: `simulation_name_YYYYMMDD_HHMMSS_metadata.json`

## Data Organization Strategy

1. **Time-based partitioning** for efficient querying
2. **Project-based grouping** for related simulations
3. **Metadata indexing** for fast discovery
4. **Automated archiving** for storage management

## Access Patterns

- Grafana Infinity queries via REST API
- OpenTelemetry Alloy file monitoring
- Direct CSV access for analysis tools