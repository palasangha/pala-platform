#!/bin/bash

###############################################################################
# Enrichment Services Log Monitoring Script
# Monitors logs from all enrichment services and filters by severity/service
###############################################################################

set -e

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${LOG_DIR:- ${SCRIPT_DIR}/logs}"
SERVICES=("enrichment-coordinator" "enrichment-worker" "review-api" "cost-api")
LOG_LEVEL="${LOG_LEVEL:-INFO}"
FOLLOW="${FOLLOW:-false}"
TAIL_LINES="${TAIL_LINES:-50}"
SERVICE_FILTER="${SERVICE_FILTER:-}"
ERROR_ONLY="${ERROR_ONLY:-false}"

###############################################################################
# Functions
###############################################################################

usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Monitor enrichment services logs

Options:
    -s, --service SERVICE    Filter logs for specific service (coordinator|worker|review-api|cost-api|all)
    -l, --level LEVEL        Log level to display (DEBUG|INFO|WARNING|ERROR|CRITICAL)
    -e, --errors-only        Show only ERROR and CRITICAL logs
    -f, --follow             Follow log files (tail -f)
    -t, --tail LINES         Number of lines to show initially (default: 50)
    -h, --help              Show this help message

Examples:
    # Show last 50 lines of coordinator logs
    $(basename "$0") --service coordinator

    # Follow all error logs
    $(basename "$0") --follow --errors-only

    # Show last 100 lines of INFO level and above
    $(basename "$0") --tail 100 --level INFO

    # Monitor worker logs in real-time
    $(basename "$0") --service worker --follow
EOF
    exit 0
}

print_header() {
    local text="$1"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}${text}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_error() {
    echo -e "${RED}❌ ERROR: $1${NC}" >&2
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        exit 1
    fi
}

get_container_logs() {
    local service="$1"
    local container_name="gvpocr-${service}"

    if ! docker ps -a --format '{{.Names}}' | grep -q "^${container_name}$"; then
        return 1
    fi

    if [ "$FOLLOW" = "true" ]; then
        docker logs -f "$container_name"
    else
        docker logs --tail "$TAIL_LINES" "$container_name"
    fi
}

get_file_logs() {
    local service="$1"
    local log_file="${LOG_DIR}/${service}.log"

    if [ ! -f "$log_file" ]; then
        return 1
    fi

    if [ "$ERROR_ONLY" = "true" ]; then
        grep -i "ERROR\|CRITICAL" "$log_file" | tail -n "$TAIL_LINES"
    elif [ "$FOLLOW" = "true" ]; then
        tail -f "$log_file"
    else
        tail -n "$TAIL_LINES" "$log_file"
    fi
}

monitor_service_logs() {
    local service="$1"

    print_header "Service: ${service} (${LOG_DIR}/${service}.log)"

    # Try to get from file first, then from Docker
    if get_file_logs "$service"; then
        return 0
    elif get_container_logs "$service"; then
        return 0
    else
        print_warning "No logs found for service: $service"
        return 1
    fi
}

show_logs_summary() {
    echo ""
    print_header "Logs Summary"

    for service in "${SERVICES[@]}"; do
        local log_file="${LOG_DIR}/${service}.log"
        local container_name="gvpocr-${service}"

        echo ""
        echo -e "${BLUE}Service: ${service}${NC}"

        # Check file
        if [ -f "$log_file" ]; then
            local file_size=$(du -h "$log_file" | cut -f1)
            local line_count=$(wc -l < "$log_file")
            echo -e "  File: ${GREEN}${log_file}${NC}"
            echo -e "    Size: ${file_size}, Lines: ${line_count}"

            # Error count
            local error_count=$(grep -ci "ERROR\|CRITICAL" "$log_file" || true)
            if [ "$error_count" -gt 0 ]; then
                echo -e "    Errors: ${RED}${error_count}${NC}"
            else
                echo -e "    Errors: ${GREEN}0${NC}"
            fi
        fi

        # Check container
        if docker ps -a --format '{{.Names}}' | grep -q "^${container_name}$"; then
            local container_status=$(docker ps --all --format "table {{.Names}}\t{{.Status}}" | grep "$container_name" | awk '{$1=""; print $0}' | sed 's/^ //')
            echo -e "  Container: ${container_name}"
            echo -e "    Status: ${container_status}"
        fi
    done

    echo ""
    print_header "Recent Errors"
    echo ""

    for service in "${SERVICES[@]}"; do
        local log_file="${LOG_DIR}/${service}.log"
        if [ -f "$log_file" ]; then
            local recent_errors=$(grep -i "ERROR\|CRITICAL" "$log_file" | tail -n 3)
            if [ -n "$recent_errors" ]; then
                echo -e "${YELLOW}${service}:${NC}"
                echo "$recent_errors" | sed 's/^/  /'
                echo ""
            fi
        fi
    done
}

###############################################################################
# Main Script
###############################################################################

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--service)
            SERVICE_FILTER="$2"
            shift 2
            ;;
        -l|--level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        -e|--errors-only)
            ERROR_ONLY="true"
            shift
            ;;
        -f|--follow)
            FOLLOW="true"
            shift
            ;;
        -t|--tail)
            TAIL_LINES="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Main execution
check_docker

echo ""
print_success "Enrichment Services Log Monitor"
echo ""
echo "Configuration:"
echo "  Log Directory: ${LOG_DIR}"
echo "  Log Level: ${LOG_LEVEL}"
echo "  Tail Lines: ${TAIL_LINES}"
echo "  Follow: ${FOLLOW}"
echo "  Errors Only: ${ERROR_ONLY}"
if [ -n "$SERVICE_FILTER" ] && [ "$SERVICE_FILTER" != "all" ]; then
    echo "  Service Filter: ${SERVICE_FILTER}"
fi
echo ""

# Show summary by default
if [ "$FOLLOW" = "false" ] && [ -z "$SERVICE_FILTER" ]; then
    show_logs_summary
else
    # Monitor specific service(s)
    if [ -z "$SERVICE_FILTER" ] || [ "$SERVICE_FILTER" = "all" ]; then
        for service in "${SERVICES[@]}"; do
            monitor_service_logs "$service"
        done
    else
        monitor_service_logs "$SERVICE_FILTER"
    fi
fi
