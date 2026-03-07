# Makefile for OCR Metadata Extraction - Production

.PHONY: help setup deploy rollback backup restore logs clean health test

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "$(BLUE)OCR Metadata Extraction - Production Management$(NC)"
	@echo ""
	@echo "$(GREEN)Available commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(BLUE)%-15s$(NC) %s\n", $$1, $$2}'

# ==================== Setup ====================

setup: ## Initial production setup
	@echo "$(GREEN)Running initial production setup...$(NC)"
	./scripts/setup-production.sh

init: setup ## Alias for setup

# ==================== Deployment ====================

deploy: ## Deploy to production
	@echo "$(GREEN)Deploying to production...$(NC)"
	./scripts/deploy-production.sh

deploy-version: ## Deploy specific version (make deploy-version VERSION=v1.2.0)
	@echo "$(GREEN)Deploying version $(VERSION)...$(NC)"
	./scripts/deploy-production.sh $(VERSION)

rollback: ## Rollback to previous deployment
	@echo "$(YELLOW)Rolling back deployment...$(NC)"
	./scripts/rollback.sh

# ==================== Services ====================

start: ## Start all services
	@echo "$(GREEN)Starting services...$(NC)"
	docker-compose -f docker-compose.prod.yml up -d

stop: ## Stop all services
	@echo "$(YELLOW)Stopping services...$(NC)"
	docker-compose -f docker-compose.prod.yml stop

restart: ## Restart all services
	@echo "$(YELLOW)Restarting services...$(NC)"
	docker-compose -f docker-compose.prod.yml restart

down: ## Stop and remove all containers
	@echo "$(YELLOW)Stopping and removing containers...$(NC)"
	docker-compose -f docker-compose.prod.yml down

ps: ## Show running containers
	@docker-compose -f docker-compose.prod.yml ps

# ==================== Monitoring ====================

logs: ## Show logs from all services
	docker-compose -f docker-compose.prod.yml logs -f

logs-backend: ## Show backend logs
	docker-compose -f docker-compose.prod.yml logs -f backend

logs-frontend: ## Show frontend logs
	docker-compose -f docker-compose.prod.yml logs -f frontend

logs-enrichment: ## Show enrichment worker logs
	docker-compose -f docker-compose.prod.yml logs -f enrichment-worker

logs-error: ## Show only error logs
	docker-compose -f docker-compose.prod.yml logs | grep -i error

health: ## Check health of all services
	@echo "$(GREEN)Checking service health...$(NC)"
	@./health-check.sh || echo "$(YELLOW)health-check.sh not found, checking containers...$(NC)" && docker ps --filter "name=gvpocr" --format "table {{.Names}}\t{{.Status}}"

status: ## Show service status
	@echo "$(BLUE)Service Status:$(NC)"
	@docker ps --filter "name=gvpocr" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

stats: ## Show resource usage statistics
	docker stats --no-stream --filter "name=gvpocr"

# ==================== Database ====================

backup: ## Backup MongoDB database
	@echo "$(GREEN)Backing up database...$(NC)"
	./scripts/backup-db.sh

restore: ## Restore database from latest backup
	@echo "$(YELLOW)Restoring database from latest backup...$(NC)"
	./scripts/rollback.sh

list-backups: ## List available database backups
	@echo "$(BLUE)Available backups:$(NC)"
	@ls -lh backups/ | grep mongodb_backup

db-shell: ## Open MongoDB shell
	docker exec -it gvpocr-mongodb-prod mongosh -u $$(grep MONGO_ROOT_USERNAME .env.production | cut -d= -f2) -p $$(grep MONGO_ROOT_PASSWORD .env.production | cut -d= -f2) gvpocr

# ==================== Maintenance ====================

clean: ## Clean up old containers, images, and logs
	@echo "$(YELLOW)Cleaning up...$(NC)"
	docker-compose -f docker-compose.prod.yml down --remove-orphans
	docker image prune -f
	docker volume prune -f
	find logs/ -name "*.log" -mtime +30 -delete
	find backups/ -name "mongodb_backup_*.gz" -mtime +30 -delete
	@echo "$(GREEN)Cleanup complete$(NC)"

update: ## Update all Docker images
	@echo "$(GREEN)Updating Docker images...$(NC)"
	docker-compose -f docker-compose.prod.yml pull

rebuild: ## Rebuild all Docker images
	@echo "$(GREEN)Rebuilding Docker images...$(NC)"
	docker-compose -f docker-compose.prod.yml build --no-cache

# ==================== Scaling ====================

scale-workers: ## Scale enrichment workers (make scale-workers N=3)
	@echo "$(GREEN)Scaling enrichment workers to $(N)...$(NC)"
	docker-compose -f docker-compose.prod.yml up -d --scale enrichment-worker=$(N)

# ==================== Testing ====================

test: ## Run E2E tests
	@echo "$(GREEN)Running E2E tests...$(NC)"
	./run-e2e-test.sh

test-quick: ## Run quick health check test
	@echo "$(GREEN)Running quick health check...$(NC)"
	@curl -s http://localhost:5000/health || echo "Backend not responding"
	@curl -s http://localhost:3000 || echo "Frontend not responding"
	@curl -s http://localhost:5001/health || echo "Review API not responding"
	@curl -s http://localhost:5002/health || echo "Cost API not responding"

# ==================== Utilities ====================

shell-backend: ## Open shell in backend container
	docker exec -it gvpocr-backend-prod /bin/bash

shell-worker: ## Open shell in enrichment worker container
	docker exec -it gvpocr-enrichment-worker-prod /bin/bash

env-check: ## Check .env.production for placeholder values
	@echo "$(BLUE)Checking .env.production for placeholders...$(NC)"
	@if grep -q "CHANGE_ME" .env.production; then \
		echo "$(YELLOW)WARNING: .env.production contains CHANGE_ME placeholders$(NC)"; \
		grep "CHANGE_ME" .env.production; \
	else \
		echo "$(GREEN)No placeholders found$(NC)"; \
	fi

disk-usage: ## Check disk usage
	@echo "$(BLUE)Disk Usage:$(NC)"
	@df -h /
	@echo ""
	@echo "$(BLUE)Docker Volume Usage:$(NC)"
	@docker system df -v

grafana: ## Open Grafana in browser
	@echo "$(GREEN)Opening Grafana...$(NC)"
	@xdg-open http://localhost:3001 2>/dev/null || open http://localhost:3001 2>/dev/null || echo "Grafana: http://localhost:3001"

prometheus: ## Open Prometheus in browser
	@echo "$(GREEN)Opening Prometheus...$(NC)"
	@xdg-open http://localhost:9090 2>/dev/null || open http://localhost:9090 2>/dev/null || echo "Prometheus: http://localhost:9090"

nsq: ## Open NSQ Admin in browser
	@echo "$(GREEN)Opening NSQ Admin...$(NC)"
	@xdg-open http://localhost:4171 2>/dev/null || open http://localhost:4171 2>/dev/null || echo "NSQ Admin: http://localhost:4171"

# ==================== Information ====================

version: ## Show deployed version
	@echo "$(BLUE)Version Information:$(NC)"
	@grep "VERSION=" .env.production || echo "Version not set"
	@git describe --tags 2>/dev/null || echo "No git tags"

info: ## Show production information
	@echo "$(BLUE)Production Information:$(NC)"
	@echo "Environment: $$(grep ENVIRONMENT .env.production | cut -d= -f2)"
	@echo "MongoDB: $$(docker inspect -f '{{.State.Status}}' gvpocr-mongodb-prod 2>/dev/null || echo 'Not running')"
	@echo "Backend: $$(docker inspect -f '{{.State.Status}}' gvpocr-backend-prod 2>/dev/null || echo 'Not running')"
	@echo "Frontend: $$(docker inspect -f '{{.State.Status}}' gvpocr-frontend-prod 2>/dev/null || echo 'Not running')"
	@echo "Enrichment Worker: $$(docker inspect -f '{{.State.Status}}' gvpocr-enrichment-worker-prod 2>/dev/null || echo 'Not running')"
	@echo ""
	@echo "$(BLUE)Latest Backup:$(NC)"
	@ls -t backups/mongodb_backup_*.gz 2>/dev/null | head -1 || echo "No backups found"
	@echo ""
	@echo "$(BLUE)Disk Usage:$(NC)"
	@df -h / | tail -1 | awk '{print $$5 " used"}'

docs: ## Show production documentation
	@echo "$(BLUE)Production Documentation:$(NC)"
	@echo "  - PRODUCTION_README.md - Main production guide"
	@echo "  - DEPLOYMENT_GUIDE.md - Detailed deployment steps"
	@echo "  - PRODUCTION_DEPLOYMENT_CHECKLIST.md - Deployment checklist"
	@echo "  - ROLLBACK_PROCEDURES.md - Rollback procedures"
	@echo ""
	@echo "View with: less PRODUCTION_README.md"
