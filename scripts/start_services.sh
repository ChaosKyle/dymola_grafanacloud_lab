#!/bin/bash

# Start Services Script for Dymola-Grafana Integration
# This script starts all required services in the correct order

set -e

# Configuration
DATA_DIR="$(pwd)/data"
CONFIG_DIR="$(pwd)/config"
LOGS_DIR="$(pwd)/logs"
SCRIPTS_DIR="$(pwd)/scripts"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] SUCCESS:${NC} $1"
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Create necessary directories
create_directories() {
    log "Creating necessary directories..."
    
    mkdir -p "$DATA_DIR"/{raw,processed,metadata,archive}
    mkdir -p "$LOGS_DIR"
    mkdir -p "$CONFIG_DIR"
    
    success "Directories created"
}

# Check dependencies
check_dependencies() {
    log "Checking dependencies..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        error "Python 3 is required but not installed"
        exit 1
    fi
    
    # Check required Python packages
    python3 -c "import pandas, numpy, scipy, flask, watchdog" 2>/dev/null || {
        error "Missing Python dependencies. Run: pip install -r requirements.txt"
        exit 1
    }
    
    # Check Alloy (if configured)
    if command -v alloy &> /dev/null; then
        success "OpenTelemetry Alloy found"
    else
        warning "OpenTelemetry Alloy not found. Install from https://grafana.com/docs/alloy/"
    fi
    
    success "Dependencies checked"
}

# Load environment variables
load_environment() {
    log "Loading environment configuration..."
    
    if [ -f "$CONFIG_DIR/.env" ]; then
        set -a
        source "$CONFIG_DIR/.env"
        set +a
        success "Environment loaded from .env file"
    else
        warning "No .env file found. Using example configuration."
        if [ -f "$CONFIG_DIR/.env.example" ]; then
            cp "$CONFIG_DIR/.env.example" "$CONFIG_DIR/.env"
            warning "Please edit $CONFIG_DIR/.env with your Grafana Cloud credentials"
        fi
    fi
}

# Start CSV Metrics Exporter
start_csv_metrics_exporter() {
    log "Starting CSV Metrics Exporter..."
    
    cd "$SCRIPTS_DIR"
    nohup python3 csv_metrics_exporter.py \
        --port 5001 \
        --data-dir "$DATA_DIR/processed" \
        > "$LOGS_DIR/csv_metrics_exporter.log" 2>&1 &
    
    CSV_EXPORTER_PID=$!
    echo $CSV_EXPORTER_PID > "$LOGS_DIR/csv_exporter.pid"
    
    # Wait for service to start
    sleep 3
    
    if ps -p $CSV_EXPORTER_PID > /dev/null; then
        success "CSV Metrics Exporter started (PID: $CSV_EXPORTER_PID)"
    else
        error "Failed to start CSV Metrics Exporter"
        cat "$LOGS_DIR/csv_metrics_exporter.log"
        exit 1
    fi
}

# Start Data Server
start_data_server() {
    log "Starting Data Server..."
    
    cd "$SCRIPTS_DIR"
    nohup python3 data_server.py \
        --port 5000 \
        --host 0.0.0.0 \
        --data-dir "$DATA_DIR" \
        > "$LOGS_DIR/data_server.log" 2>&1 &
    
    DATA_SERVER_PID=$!
    echo $DATA_SERVER_PID > "$LOGS_DIR/data_server.pid"
    
    # Wait for service to start
    sleep 3
    
    if ps -p $DATA_SERVER_PID > /dev/null; then
        success "Data Server started (PID: $DATA_SERVER_PID)"
    else
        error "Failed to start Data Server"
        cat "$LOGS_DIR/data_server.log"
        exit 1
    fi
}

# Start OpenTelemetry Alloy
start_alloy() {
    if command -v alloy &> /dev/null; then
        log "Starting OpenTelemetry Alloy..."
        
        nohup alloy run "$CONFIG_DIR/alloy-config.alloy" \
            > "$LOGS_DIR/alloy.log" 2>&1 &
        
        ALLOY_PID=$!
        echo $ALLOY_PID > "$LOGS_DIR/alloy.pid"
        
        # Wait for service to start
        sleep 5
        
        if ps -p $ALLOY_PID > /dev/null; then
            success "OpenTelemetry Alloy started (PID: $ALLOY_PID)"
        else
            error "Failed to start OpenTelemetry Alloy"
            cat "$LOGS_DIR/alloy.log"
            exit 1
        fi
    else
        warning "OpenTelemetry Alloy not found, skipping..."
    fi
}

# Start Automation Pipeline
start_automation_pipeline() {
    log "Starting Automation Pipeline..."
    
    cd "$SCRIPTS_DIR"
    nohup python3 automation_pipeline.py \
        --config "$CONFIG_DIR/automation_config.json" \
        --daemon \
        > "$LOGS_DIR/automation_pipeline.log" 2>&1 &
    
    AUTOMATION_PID=$!
    echo $AUTOMATION_PID > "$LOGS_DIR/automation.pid"
    
    # Wait for service to start
    sleep 3
    
    if ps -p $AUTOMATION_PID > /dev/null; then
        success "Automation Pipeline started (PID: $AUTOMATION_PID)"
    else
        error "Failed to start Automation Pipeline"
        cat "$LOGS_DIR/automation_pipeline.log"
        exit 1
    fi
}

# Health check function
health_check() {
    log "Performing health checks..."
    
    # Check Data Server
    if curl -s http://localhost:5000/health > /dev/null; then
        success "Data Server is healthy"
    else
        error "Data Server health check failed"
    fi
    
    # Check CSV Metrics Exporter
    if curl -s http://localhost:5001/health > /dev/null; then
        success "CSV Metrics Exporter is healthy"
    else
        error "CSV Metrics Exporter health check failed"
    fi
    
    # Check Alloy (if running)
    if [ -f "$LOGS_DIR/alloy.pid" ]; then
        ALLOY_PID=$(cat "$LOGS_DIR/alloy.pid")
        if ps -p $ALLOY_PID > /dev/null; then
            if curl -s http://localhost:12345 > /dev/null; then
                success "OpenTelemetry Alloy is healthy"
            else
                warning "OpenTelemetry Alloy may not be fully started"
            fi
        else
            error "OpenTelemetry Alloy process not found"
        fi
    fi
}

# Display service status
show_status() {
    echo ""
    log "Service Status:"
    echo "=================================="
    
    # Data Server
    if [ -f "$LOGS_DIR/data_server.pid" ]; then
        PID=$(cat "$LOGS_DIR/data_server.pid")
        if ps -p $PID > /dev/null; then
            echo -e "${GREEN}✓${NC} Data Server (PID: $PID) - http://localhost:5000"
        else
            echo -e "${RED}✗${NC} Data Server (not running)"
        fi
    fi
    
    # CSV Metrics Exporter
    if [ -f "$LOGS_DIR/csv_exporter.pid" ]; then
        PID=$(cat "$LOGS_DIR/csv_exporter.pid")
        if ps -p $PID > /dev/null; then
            echo -e "${GREEN}✓${NC} CSV Metrics Exporter (PID: $PID) - http://localhost:5001"
        else
            echo -e "${RED}✗${NC} CSV Metrics Exporter (not running)"
        fi
    fi
    
    # OpenTelemetry Alloy
    if [ -f "$LOGS_DIR/alloy.pid" ]; then
        PID=$(cat "$LOGS_DIR/alloy.pid")
        if ps -p $PID > /dev/null; then
            echo -e "${GREEN}✓${NC} OpenTelemetry Alloy (PID: $PID) - http://localhost:12345"
        else
            echo -e "${RED}✗${NC} OpenTelemetry Alloy (not running)"
        fi
    else
        echo -e "${YELLOW}?${NC} OpenTelemetry Alloy (not configured)"
    fi
    
    # Automation Pipeline
    if [ -f "$LOGS_DIR/automation.pid" ]; then
        PID=$(cat "$LOGS_DIR/automation.pid")
        if ps -p $PID > /dev/null; then
            echo -e "${GREEN}✓${NC} Automation Pipeline (PID: $PID)"
        else
            echo -e "${RED}✗${NC} Automation Pipeline (not running)"
        fi
    fi
    
    echo "=================================="
    echo ""
}

# Main execution
main() {
    log "Starting Dymola-Grafana Integration Services..."
    
    create_directories
    check_dependencies
    load_environment
    
    # Start services in order
    start_csv_metrics_exporter
    start_data_server
    start_alloy
    start_automation_pipeline
    
    # Wait a moment for all services to stabilize
    sleep 5
    
    # Perform health checks
    health_check
    
    # Show status
    show_status
    
    success "All services started successfully!"
    
    echo ""
    log "Next steps:"
    echo "1. Configure Grafana Cloud credentials in $CONFIG_DIR/.env"
    echo "2. Import dashboards from dashboards/ directory"
    echo "3. Add Infinity datasource pointing to http://localhost:5000"
    echo "4. Place .mat files in $DATA_DIR/raw/ for automatic processing"
    echo ""
    log "View logs in $LOGS_DIR/"
    log "Stop services with: ./scripts/stop_services.sh"
}

# Handle command line arguments
case "${1:-start}" in
    start)
        main
        ;;
    status)
        show_status
        ;;
    health)
        health_check
        ;;
    *)
        echo "Usage: $0 {start|status|health}"
        exit 1
        ;;
esac