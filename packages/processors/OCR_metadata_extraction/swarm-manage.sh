#!/bin/bash

# Docker Swarm OCR Worker Management Script
# This script manages OCR workers running on Docker Swarm

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

STACK_FILE="${1:-docker-stack.yml}"
STACK_NAME="gvpocr"

# Helper functions
log_info() {
    echo -e "${GREEN}✓${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_header() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
}

# Command: Deploy workers
deploy_workers() {
    log_header "Deploying OCR Workers Stack"
    
    if [ ! -f "$STACK_FILE" ]; then
        log_error "Stack file not found: $STACK_FILE"
        exit 1
    fi
    
    echo "Deploying stack: $STACK_NAME"
    docker stack deploy -c "$STACK_FILE" "$STACK_NAME"
    
    log_info "Stack deployed successfully"
    sleep 3
    show_status
}

# Command: Remove workers
remove_workers() {
    log_header "Removing OCR Workers Stack"
    
    read -p "Are you sure you want to remove all workers? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        log_warning "Cancelled"
        return
    fi
    
    docker stack rm "$STACK_NAME"
    log_info "Stack removed successfully"
}

# Command: Show status
show_status() {
    log_header "Docker Swarm Status"
    
    echo -e "\n${BLUE}Swarm Info:${NC}"
    docker info | grep Swarm
    
    echo -e "\n${BLUE}Nodes:${NC}"
    docker node ls --format "table {{.ID}}\t{{.Hostname}}\t{{.Status}}\t{{.ManagerStatus}}\t{{.Availability}}"
    
    echo -e "\n${BLUE}Services:${NC}"
    docker service ls --filter "label=service=ocr-worker"
    
    echo -e "\n${BLUE}Tasks (Running Workers):${NC}"
    docker service ps "$STACK_NAME"_ocr-worker --format "table {{.ID}}\t{{.Name}}\t{{.Node}}\t{{.Status}}\t{{.DesiredState}}" 2>/dev/null || echo "No tasks found"
}

# Command: Scale workers
scale_workers() {
    local replicas=$1
    
    if [ -z "$replicas" ]; then
        log_error "Usage: ./swarm-manage.sh scale <number>"
        exit 1
    fi
    
    log_header "Scaling OCR Workers"
    
    echo "Scaling to $replicas replicas..."
    docker service scale "${STACK_NAME}_ocr-worker=$replicas"
    
    log_info "Scaled to $replicas workers"
    sleep 3
    show_status
}

# Command: View logs
view_logs() {
    local worker_id=$1
    
    log_header "Worker Logs"
    
    if [ -z "$worker_id" ]; then
        echo "Available workers:"
        docker service ps "$STACK_NAME"_ocr-worker --format "table {{.ID}}\t{{.Name}}\t{{.Node}}\t{{.Status}}"
        echo ""
        read -p "Enter task ID or name: " worker_id
    fi
    
    docker logs "$worker_id" -f
}

# Command: View service stats
view_stats() {
    log_header "Worker Resource Usage"
    
    docker stats --format "table {{.Container}}\t{{.MemUsage}}\t{{.CPUPerc}}\t{{.NetIO}}\t{{.BlockIO}}" \
        $(docker ps --filter "label=com.docker.swarm.service.name=${STACK_NAME}_ocr-worker" -q)
}

# Command: Restart service
restart_service() {
    log_header "Restarting OCR Worker Service"
    
    docker service update --force "${STACK_NAME}_ocr-worker"
    
    log_info "Service restarted"
    sleep 3
    show_status
}

# Command: Update service
update_service() {
    local key=$1
    local value=$2
    
    if [ -z "$key" ] || [ -z "$value" ]; then
        log_error "Usage: ./swarm-manage.sh update <KEY> <VALUE>"
        echo "Example: ./swarm-manage.sh update --image registry.docgenai.com:5010/gvpocr-worker-updated:latest"
        exit 1
    fi
    
    log_header "Updating OCR Worker Service"
    
    docker service update "$key" "$value" "${STACK_NAME}_ocr-worker"
    
    log_info "Service updated"
    sleep 3
    show_status
}

# Command: Health check
health_check() {
    log_header "Health Check"
    
    echo "Checking worker health..."
    
    local unhealthy=0
    local total=0
    
    while IFS= read -r task; do
        total=$((total + 1))
        status=$(echo "$task" | awk '{print $4}')
        
        if [[ "$status" != "Running" ]]; then
            unhealthy=$((unhealthy + 1))
            echo "$(echo "$task" | awk '{print $2}'): $status"
        fi
    done < <(docker service ps "$STACK_NAME"_ocr-worker --format "{{.ID}}\t{{.Name}}\t{{.Node}}\t{{.Status}}")
    
    echo ""
    echo "Workers: $((total - unhealthy))/$total healthy"
    
    if [ $unhealthy -eq 0 ]; then
        log_info "All workers are healthy"
    else
        log_error "$unhealthy worker(s) unhealthy"
    fi
}

# Command: Add worker node
add_worker_node() {
    log_header "Add Worker Node to Swarm"
    
    echo "Getting worker join token..."
    docker swarm join-token worker
    
    echo ""
    echo "Run the command on the worker machine to join the swarm"
}

# Command: Remove worker node
remove_worker_node() {
    local node_id=$1
    
    if [ -z "$node_id" ]; then
        log_error "Usage: ./swarm-manage.sh remove-node <node_id>"
        echo "Get node IDs with: docker node ls"
        exit 1
    fi
    
    log_header "Removing Worker Node"
    
    docker node rm "$node_id"
    log_info "Node removed"
}

# Command: Drain node (for maintenance)
drain_node() {
    local node_id=$1
    
    if [ -z "$node_id" ]; then
        log_error "Usage: ./swarm-manage.sh drain <node_id>"
        exit 1
    fi
    
    log_header "Draining Node (Pausing worker tasks)"
    
    docker node update --availability drain "$node_id"
    log_info "Node drained - tasks will be moved to other nodes"
}

# Command: Restore node (from drain)
restore_node() {
    local node_id=$1
    
    if [ -z "$node_id" ]; then
        log_error "Usage: ./swarm-manage.sh restore <node_id>"
        exit 1
    fi
    
    log_header "Restoring Node"
    
    docker node update --availability active "$node_id"
    log_info "Node restored"
}

# Command: Show help
show_help() {
    cat << EOF
${BLUE}Docker Swarm OCR Worker Management${NC}

${BLUE}Usage:${NC}
  ./swarm-manage.sh <command> [arguments]

${BLUE}Commands:${NC}
  deploy              Deploy the OCR workers stack
  remove              Remove all workers (requires confirmation)
  status              Show current swarm and worker status
  scale <num>         Scale workers to <num> replicas
  logs [task_id]      View worker logs (follow mode)
  stats               Show resource usage of workers
  restart             Restart the worker service
  update <key> <val>  Update service configuration
  health              Check health of all workers
  
  add-node            Show command to add a worker node to swarm
  remove-node <id>    Remove a node from swarm
  drain <id>          Drain node (pause tasks for maintenance)
  restore <id>        Restore drained node
  
  help                Show this help message

${BLUE}Examples:${NC}
  # Deploy 3 workers
  ./swarm-manage.sh deploy
  
  # Scale to 5 workers
  ./swarm-manage.sh scale 5
  
  # View logs of first worker
  ./swarm-manage.sh logs
  
  # Update image
  ./swarm-manage.sh update --image registry.docgenai.com:5010/gvpocr-worker-updated:v2
  
  # Check health
  ./swarm-manage.sh health

${BLUE}Node Management:${NC}
  # List all nodes
  docker node ls
  
  # View node details
  docker node inspect <node_id>
  
  # Update node labels
  docker node update --label-add type=worker <node_id>

EOF
}

# Main script logic
case "$1" in
    deploy)
        deploy_workers
        ;;
    remove)
        remove_workers
        ;;
    status)
        show_status
        ;;
    scale)
        scale_workers "$2"
        ;;
    logs)
        view_logs "$2"
        ;;
    stats)
        view_stats
        ;;
    restart)
        restart_service
        ;;
    update)
        update_service "$2" "$3"
        ;;
    health)
        health_check
        ;;
    add-node)
        add_worker_node
        ;;
    remove-node)
        remove_worker_node "$2"
        ;;
    drain)
        drain_node "$2"
        ;;
    restore)
        restore_node "$2"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        echo "Run './swarm-manage.sh help' for usage"
        exit 1
        ;;
esac
