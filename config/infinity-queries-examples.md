# Grafana Infinity Plugin Query Examples

This document provides examples of how to configure Infinity plugin queries for Dymola simulation data.

## Basic Time Series Query

**URL**: `http://localhost:5000/simulations/{simulation_id}?variables=temperature,velocity`

**Configuration**:
- Format: `table`
- Parser: `backend`
- Root Selector: `data`

**Columns**:
```json
[
  {"selector": "time", "text": "Time", "type": "number"},
  {"selector": "temperature", "text": "Temperature", "type": "number"},
  {"selector": "velocity", "text": "Velocity", "type": "number"}
]
```

## Variable Selection Query

**URL**: `http://localhost:5000/grafana/variables/{simulation_id}`

**Configuration**:
- Format: `table` 
- Parser: `backend`
- Root Selector: ``

**Use Case**: Populate dashboard variable dropdown with available variables.

## Simulation List Query

**URL**: `http://localhost:5000/simulations`

**Configuration**:
- Format: `table`
- Parser: `backend`  
- Root Selector: ``

**Columns**:
```json
[
  {"selector": "id", "text": "Simulation ID", "type": "string"},
  {"selector": "name", "text": "Name", "type": "string"},
  {"selector": "created", "text": "Created", "type": "string"}
]
```

## Statistics Query

**URL**: `http://localhost:5000/simulations/{simulation_id}/variables/{variable}/stats`

**Configuration**:
- Format: `table`
- Parser: `backend`
- Root Selector: ``

**Columns**:
```json
[
  {"selector": "mean", "text": "Mean", "type": "number"},
  {"selector": "std", "text": "Std Dev", "type": "number"},
  {"selector": "min", "text": "Min", "type": "number"},
  {"selector": "max", "text": "Max", "type": "number"}
]
```

## Filtered Time Range Query

**URL**: `http://localhost:5000/simulations/{simulation_id}?variables=pressure&time_start=10&time_end=100`

**Configuration**:
- Format: `table`
- Parser: `backend` 
- Root Selector: `data`

**Use Case**: Query specific time range for detailed analysis.

## Sampled Data Query

**URL**: `http://localhost:5000/simulations/{simulation_id}?variables=temperature&sample_rate=1000`

**Configuration**:
- Format: `table`
- Parser: `backend`
- Root Selector: `data` 

**Use Case**: Reduce data points for better performance with large datasets.

## Multi-Variable Correlation Query

**URL**: `http://localhost:5000/simulations/{simulation_id}?variables=temperature,pressure,flow_rate`

**Configuration**:
- Format: `table`
- Parser: `backend`
- Root Selector: `data`

**Columns**:
```json
[
  {"selector": "time", "text": "Time", "type": "number"},
  {"selector": "temperature", "text": "Temperature", "type": "number"},
  {"selector": "pressure", "text": "Pressure", "type": "number"}, 
  {"selector": "flow_rate", "text": "Flow Rate", "type": "number"}
]
```

## Grafana Variables Configuration

### Simulation Selection Variable

**Name**: `simulation_id`
**Query**: 
```json
{
  "url": "http://localhost:5000/grafana/search",
  "format": "table",
  "parser": "backend",
  "columns": [{"selector": "", "text": "", "type": "string"}]
}
```

### Variable Selection Variable

**Name**: `variable_name`
**Query**:
```json
{
  "url": "http://localhost:5000/grafana/variables/${simulation_id}",
  "format": "table", 
  "parser": "backend",
  "columns": [{"selector": "", "text": "", "type": "string"}]
}
```

## Advanced Filtering

### Using Filters in Infinity Plugin

You can add filters to refine your data:

```json
{
  "filters": [
    {
      "field": "temperature",
      "operator": ">",
      "value": [25]
    },
    {
      "field": "time", 
      "operator": ">=",
      "value": [10]
    }
  ]
}
```

### URL Parameters for Server-Side Filtering

- `?variables=temp,pressure` - Select specific variables
- `?time_start=10&time_end=100` - Time range filtering
- `?sample_rate=1000` - Reduce data points
- `?limit=50` - Limit result count

## Error Handling

The data server returns appropriate HTTP status codes:

- **200**: Success
- **404**: Simulation or variable not found
- **400**: Invalid parameters
- **500**: Server error

Example error response:
```json
{
  "error": "Simulation not found"
}
```

## Performance Tips

1. **Use sampling**: Add `sample_rate` parameter for large datasets
2. **Select specific variables**: Don't query all variables if not needed
3. **Time range filtering**: Use `time_start` and `time_end` for focused analysis
4. **Cache results**: Enable Grafana query caching for repeated queries
5. **Parallel queries**: Use multiple panels with different variable sets

## Troubleshooting

### Common Issues

1. **Connection refused**: Check if data server is running on correct port
2. **Empty results**: Verify simulation ID and variable names
3. **Timeout**: Increase query timeout in datasource settings
4. **CORS errors**: Ensure Flask-CORS is enabled in data server

### Debug URLs

- Health check: `http://localhost:5000/health`
- API documentation: `http://localhost:5000/`
- Simulation list: `http://localhost:5000/simulations`