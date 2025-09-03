#!/bin/bash

# Stop Services Script for Dymola-Grafana Integration
# This script stops all running services

set -e

# Configuration
LOGS_DIR="$(pwd)/logs"

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

# Stop service by PID file
stop_service() {
    local service_name="$1"
    local pid_file="$2"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        
        if ps -p "$pid" > /dev/null 2>&1; then
            log "Stopping $service_name (PID: $pid)..."
            
            # Try graceful shutdown first
            kill "$pid" 2>/dev/null || true
            
            # Wait for graceful shutdown
            local count=0
            while ps -p "$pid" > /dev/null 2>&1 && [ $count -lt 10 ]; do
                sleep 1
                ((count++))
            done
            
            # Force kill if still running
            if ps -p "$pid" > /dev/null 2>&1; then
                warning "Graceful shutdown failed, force killing $service_name..."
                kill -9 "$pid" 2>/dev/null || true
                sleep 1
            fi
            
            if ! ps -p "$pid" > /dev/null 2>&1; then
                success "$service_name stopped"
                rm -f "$pid_file"
            else
                error "Failed to stop $service_name"
            fi
        else
            warning "$service_name was not running"
            rm -f "$pid_file"
        fi
    else
        warning "No PID file found for $service_name"
    fi
}

# Stop all services
stop_all_services() {
    log "Stopping all Dymola-Grafana Integration services..."
    
    # Stop services in reverse order
    stop_service "Automation Pipeline" "$LOGS_DIR/automation.pid"
    stop_service "OpenTelemetry Alloy" "$LOGS_DIR/alloy.pid"
    stop_service "Data Server" "$LOGS_DIR/data_server.pid"
    stop_service "CSV Metrics Exporter" "$LOGS_DIR/csv_exporter.pid"
    
    # Additional cleanup - kill any remaining processes
    cleanup_remaining_processes
    
    success "All services stopped"
}

# Cleanup any remaining processes
cleanup_remaining_processes() {
    log "Cleaning up remaining processes..."
    
    # Kill any remaining Python processes related to our services
    pkill -f "data_server.py" 2>/dev/null || true
    pkill -f "csv_metrics_exporter.py" 2>/dev/null || true
    pkill -f "automation_pipeline.py" 2>/dev/null || true
    
    # Kill any remaining Alloy processes
    pkill -f "alloy.*alloy-config.alloy" 2>/dev/null || true
    
    # Wait a moment for processes to terminate
    sleep 2
}

# Show current status
show_status() {
    echo ""
    log "Service Status:"
    echo "=================================="
    
    local any_running=false
    
    # Check each service
    for service in "data_server:Data Server" "csv_exporter:CSV Metrics Exporter" "alloy:OpenTelemetry Alloy" "automation:Automation Pipeline"; do
        IFS=':' read -r pid_name display_name <<< "$service"
        local pid_file="$LOGS_DIR/${pid_name}.pid"
        
        if [ -f "$pid_file" ]; then
            local pid=$(cat "$pid_file")
            if ps -p "$pid" > /dev/null 2>&1; then
                echo -e "${GREEN}✓${NC} $display_name (PID: $pid) - Running"
                any_running=true
            else
                echo -e "${RED}✗${NC} $display_name - Stopped"
            fi
        else
            echo -e "${RED}✗${NC} $display_name - Stopped"
        fi
    done
    
    echo "=================================="
    
    if [ "$any_running" = true ]; then
        warning "Some services are still running"
        return 1
    else
        success "All services are stopped"
        return 0
    fi
}

# Force stop function
force_stop() {
    log "Force stopping all services..."
    
    # Kill all related processes
    pkill -9 -f "data_server.py" 2>/dev/null || true
    pkill -9 -f "csv_metrics_exporter.py" 2>/dev/null || true
    pkill -9 -f "automation_pipeline.py" 2>/dev/null || true
    pkill -9 -f "alloy.*alloy-config.alloy" 2>/dev/null || true
    
    # Remove all PID files
    rm -f "$LOGS_DIR"/*.pid
    
    success "Force stop completed"
}

# Clean up function
cleanup() {
    log "Cleaning up temporary files..."
    
    # Remove PID files
    rm -f "$LOGS_DIR"/*.pid
    
    # Optionally clean up log files (uncomment if desired)
    # rm -f "$LOGS_DIR"/*.log
    
    success "Cleanup completed"
}

# Main function
main() {
    case "${1:-stop}" in
        stop)
            stop_all_services
            show_status
            ;;
        status)
            show_status
            ;;
        force)
            force_stop
            show_status
            ;;
        cleanup)
            stop_all_services
            cleanup
            ;;
        *)
            echo "Usage: $0 {stop|status|force|cleanup}"
            echo ""
            echo "Commands:"
            echo "  stop    - Gracefully stop all services (default)"
            echo "  status  - Show current status of services"
            echo "  force   - Force kill all services"
            echo "  cleanup - Stop services and clean up files"
            exit 1
            ;;
    esac
}

# Create logs directory if it doesn't exist
mkdir -p "$LOGS_DIR"

# Run main function
main "$@"