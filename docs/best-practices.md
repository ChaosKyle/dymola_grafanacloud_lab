# Best Practices and Troubleshooting Guide

This document provides best practices for implementing and maintaining the Dymola-Grafana Cloud visualization pipeline, along with common troubleshooting scenarios.

## Table of Contents

1. [Performance Optimization](#performance-optimization)
2. [Data Management Best Practices](#data-management-best-practices)
3. [Security Guidelines](#security-guidelines)
4. [Monitoring and Alerting](#monitoring-and-alerting)
5. [Troubleshooting Common Issues](#troubleshooting-common-issues)
6. [Scaling Considerations](#scaling-considerations)
7. [Maintenance and Operations](#maintenance-and-operations)

## Performance Optimization

### Data Processing

**Large .mat Files**
- Use sampling when converting large files: `sample_rate=1000` in API calls
- Consider parallel processing for batch conversions
- Implement data compression for long-term storage

```python
# Example: Efficient batch processing
exporter = DymolaExporter()
results = exporter.batch_convert('data/raw', pattern="*.mat")

# Use sampling for large datasets
data = server.get_simulation_data(sim_id, variables=['temp'], sample_rate=1000)
```

**Memory Management**
- Process files in chunks for very large datasets
- Use generators instead of loading entire datasets into memory
- Implement cleanup of temporary files

```python
# Memory-efficient data processing
def process_large_csv(file_path, chunk_size=10000):
    for chunk in pd.read_csv(file_path, chunksize=chunk_size):
        yield process_chunk(chunk)
```

### Grafana Dashboard Optimization

**Query Performance**
- Use time range filters to limit data scope
- Implement proper indexing in data sources
- Cache frequently accessed data

**Dashboard Design**
- Limit the number of panels per dashboard (recommended: < 20)
- Use dashboard variables for dynamic filtering
- Implement lazy loading for complex visualizations

```json
// Efficient Infinity query with filtering
{
  "url": "http://localhost:5000/simulations/${simulation_id}?variables=${variables}&time_start=${__from:date:seconds}&time_end=${__to:date:seconds}",
  "format": "table"
}
```

## Data Management Best Practices

### File Organization

**Directory Structure**
```
data/
├── raw/           # Original .mat files from Dymola
│   └── YYYY-MM-DD/
├── processed/     # Converted CSV files
│   └── YYYY-MM-DD/
├── metadata/      # Simulation catalogs and schemas
└── archive/       # Long-term storage
    └── YYYY/
```

**Naming Conventions**
- Use consistent naming: `simulation_name_YYYYMMDD_HHMMSS.mat`
- Include metadata in filenames: `model_experiment_condition_timestamp`
- Avoid spaces and special characters in filenames

### Data Retention Policies

**Automated Archiving**
```python
# Configure automatic archiving
manager = DataManager()
archived_count = manager.archive_old_data(days_old=90)
```

**Storage Optimization**
- Compress archived files using gzip or similar
- Implement tiered storage (hot/warm/cold)
- Regular cleanup of temporary files

### Data Quality Checks

**Validation Rules**
```python
# Example validation in automation pipeline
quality_checks = {
    "min_file_size_bytes": 1024,
    "max_file_age_hours": 24,
    "verify_mat_format": True,
    "check_variable_count": True
}
```

## Security Guidelines

### API Security

**Authentication**
```python
# Implement API key authentication
from flask import request, abort

@app.before_request
def check_auth():
    api_key = request.headers.get('X-API-Key')
    if not api_key or api_key != os.getenv('API_KEY'):
        abort(401)
```

**Network Security**
- Use HTTPS for all external communications
- Implement firewall rules to restrict access
- Use VPN for remote access to data servers

### Data Protection

**Sensitive Data Handling**
- Anonymize data before visualization
- Implement access controls based on user roles
- Encrypt data at rest and in transit

**Grafana Cloud Security**
- Use strong API keys and rotate regularly
- Implement proper RBAC in Grafana
- Monitor access logs for suspicious activity

## Monitoring and Alerting

### Health Monitoring

**Service Health Checks**
```python
# Comprehensive health check
def health_check():
    services = {
        'data_server': check_url('http://localhost:5000/health'),
        'csv_exporter': check_url('http://localhost:5001/health'),
        'alloy': check_process('alloy'),
        'automation': check_process('automation_pipeline.py')
    }
    return services
```

**Performance Metrics**
- Monitor CPU and memory usage
- Track processing times and queue lengths
- Alert on service failures or performance degradation

### Alerting Rules

**Grafana Alerts**
```yaml
# Example alert rule
- alert: HighProcessingLatency
  expr: processing_duration_seconds > 300
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Dymola processing taking too long"
```

## Troubleshooting Common Issues

### Connection Issues

**Problem**: Grafana cannot connect to data server
```bash
# Check if service is running
curl http://localhost:5000/health

# Check firewall settings
sudo ufw status

# Check logs
tail -f logs/data_server.log
```

**Solution**: Verify service status, check network connectivity, review firewall rules

### Data Processing Issues

**Problem**: .mat file conversion fails
```python
# Debug mat file structure
import scipy.io
mat_data = scipy.io.loadmat('problem_file.mat')
print(mat_data.keys())
```

**Solutions**:
- Verify .mat file format and structure
- Check for corrupted files
- Ensure sufficient disk space and memory

### Grafana Infinity Plugin Issues

**Common Problems and Solutions**:

1. **CORS Errors**
   ```python
   # Ensure CORS is enabled in data server
   from flask_cors import CORS
   CORS(app)
   ```

2. **Query Timeout**
   ```json
   // Increase timeout in datasource settings
   {
     "timeout": 60,
     "queryTimeout": "60s"
   }
   ```

3. **Empty Results**
   - Check simulation ID and variable names
   - Verify URL endpoint is accessible
   - Review server logs for errors

### OpenTelemetry Alloy Issues

**Configuration Validation**
```bash
# Validate Alloy configuration
alloy validate config/alloy-config.alloy

# Check Alloy logs
tail -f logs/alloy.log
```

**Common Fixes**:
- Verify Grafana Cloud credentials
- Check network connectivity to Grafana Cloud
- Ensure proper file permissions

## Scaling Considerations

### Horizontal Scaling

**Load Balancing**
```yaml
# Docker Compose example for scaling data servers
version: '3.8'
services:
  data-server:
    image: dymola-data-server
    replicas: 3
    ports:
      - "5000-5002:5000"
```

**Database Backend**
```python
# Replace file-based storage with database
class DatabaseDataManager:
    def __init__(self, db_connection):
        self.db = db_connection
        
    def store_simulation_data(self, data):
        # Store in PostgreSQL/InfluxDB
        pass
```

### Vertical Scaling

**Resource Optimization**
```python
# Configure processing limits
processing_config = {
    "max_concurrent_processing": 3,
    "memory_limit_mb": 2048,
    "processing_timeout_seconds": 600
}
```

## Maintenance and Operations

### Regular Maintenance Tasks

**Weekly Tasks**
- Review processing logs for errors
- Check disk space usage
- Update security patches
- Backup configuration files

**Monthly Tasks**
- Archive old data
- Review and optimize dashboard performance
- Update documentation
- Security audit

### Backup and Recovery

**Configuration Backup**
```bash
# Backup script
#!/bin/bash
tar -czf backup_$(date +%Y%m%d).tar.gz \
    config/ \
    dashboards/ \
    data/metadata/
```

**Disaster Recovery Plan**
1. Document all service dependencies
2. Maintain configuration backups
3. Test recovery procedures regularly
4. Document rollback procedures

### Updating and Upgrades

**Version Control**
- Use Git for configuration management
- Tag stable releases
- Maintain change logs

**Rolling Updates**
```bash
# Example rolling update
./scripts/stop_services.sh
git pull origin main
pip install -r requirements.txt
./scripts/start_services.sh
```

## Performance Benchmarks

### Expected Performance Metrics

**File Processing**
- Small files (< 1MB): < 5 seconds
- Medium files (1-10MB): < 30 seconds  
- Large files (10-100MB): < 5 minutes

**API Response Times**
- Simple queries: < 100ms
- Complex queries: < 1 second
- Large dataset queries: < 10 seconds

**Dashboard Load Times**
- Simple dashboards: < 2 seconds
- Complex dashboards: < 10 seconds

### Optimization Targets

**Resource Usage**
- CPU usage: < 80% average
- Memory usage: < 4GB per service
- Disk I/O: < 100MB/s sustained

**Availability**
- Service uptime: > 99.5%
- Data processing success rate: > 99%
- Dashboard response time: < 3 seconds 95th percentile

## Troubleshooting Checklist

### Quick Diagnostic Steps

1. **Check Service Status**
   ```bash
   ./scripts/start_services.sh status
   ```

2. **Verify Network Connectivity**
   ```bash
   curl http://localhost:5000/health
   curl http://localhost:5001/health
   ```

3. **Check Logs**
   ```bash
   tail -f logs/*.log
   ```

4. **Test Data Processing**
   ```bash
   python scripts/dymola_export.py test_file.mat
   ```

5. **Validate Configuration**
   ```bash
   python -c "import json; print(json.load(open('config/automation_config.json')))"
   ```

### Emergency Procedures

**Service Recovery**
```bash
# Emergency restart
./scripts/stop_services.sh force
./scripts/start_services.sh
```

**Data Corruption Recovery**
```bash
# Restore from backup
tar -xzf backup_YYYYMMDD.tar.gz
./scripts/start_services.sh
```

---

## Getting Help

### Support Resources

- **Documentation**: Check this guide and inline code comments
- **Logs**: Review service logs in `logs/` directory
- **Configuration**: Verify settings in `config/` directory
- **Community**: Grafana Community Forums, OpenTelemetry Slack

### Reporting Issues

When reporting issues, include:
1. Service status output
2. Relevant log files
3. Configuration files (redacted)
4. Steps to reproduce
5. Expected vs actual behavior