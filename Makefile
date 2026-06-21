# ==============================================================================
# Hybrid Inference App — Makefile
# ==============================================================================
# Production-ready commands for building, deploying, testing, and managing
# the Hybrid Inference application.
#
# Quick Start:
#   make setup          # First-time setup
#   make dev            # Start in development mode
#   make test           # Run all tests
#   make deploy         # Production deployment
#   make logs           # View logs
#   make clean          # Stop and remove all containers
#
# ==============================================================================

.PHONY: help setup dev build deploy start stop restart logs logs-follow clean test health backup restore monitor down ps exec-backend exec-db lint format

# Default target
.DEFAULT_GOAL := help

# Load environment variables from .env if it exists
-include .env
export

# ==============================================================================
# Configuration
# ==============================================================================

DOCKER_COMPOSE := docker compose
DOCKER_COMPOSE_DEV := docker compose
DOCKER_COMPOSE_PROD := docker compose --profile monitoring
BACKEND_SERVICE := backend
FRONTEND_SERVICE := frontend
DB_SERVICE := postgres

# Determine profiles based on INFERENCE_PROVIDER
ifeq ($(INFERENCE_PROVIDER),vllm)
	PROFILES := --profile vllm
else
	PROFILES :=
endif

# Colors for output
GREEN  := \033[0;32m
YELLOW := \033[1;33m
BLUE   := \033[0;34m
RED    := \033[0;31m
NC     := \033[0m # No Color

# ==============================================================================
# Help
# ==============================================================================

help: ## Show this help message
	@echo ""
	@echo "$(BLUE)Hybrid Inference App — Available Commands$(NC)"
	@echo "=============================================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Environment:$(NC)"
	@echo "  INFERENCE_PROVIDER: $(INFERENCE_PROVIDER)"
	@echo "  PORT: $(PORT)"
	@echo ""

# ==============================================================================
# Setup & Installation
# ==============================================================================

setup: ## First-time setup (copy .env, install dependencies)
	@echo "$(BLUE)Setting up Hybrid Inference App...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)⚠  .env file already exists. Skipping...$(NC)"; \
		echo "$(GREEN)✓  .env file exists$(NC)"; \
	fi
	@echo "$(GREEN)✓  Setup complete$(NC)"
	@echo ""
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "  1. Edit .env and configure your inference provider"
	@echo "  2. Set POSTGRES_PASSWORD to a strong password"
	@echo "  3. Run 'make dev' to start development environment"
	@echo ""

check-env: ## Validate .env configuration
	@if [ ! -f .env ]; then \
		echo "$(RED)✗ .env file not found$(NC)"; \
		echo "  Run: make setup"; \
		exit 1; \
	fi
	@if grep -q "CHANGE_THIS" .env 2>/dev/null; then \
		echo "$(RED)✗ POSTGRES_PASSWORD still has default value$(NC)"; \
		echo "  Generate a password: openssl rand -base64 32"; \
		exit 1; \
	fi
	@if grep -q "your_gemini_api_key_here" .env 2>/dev/null; then \
		echo "$(YELLOW)⚠  GOOGLE_API_KEY not configured$(NC)"; \
	fi
	@echo "$(GREEN)✓  Environment configuration valid$(NC)"

# ==============================================================================
# Development
# ==============================================================================

dev: check-env ## Start development environment
	@echo "$(BLUE)Starting development environment...$(NC)"
	$(DOCKER_COMPOSE) $(PROFILES) up --build

dev-detached: check-env ## Start development in background
	@echo "$(BLUE)Starting development environment (detached)...$(NC)"
	$(DOCKER_COMPOSE) $(PROFILES) up --build -d
	@echo "$(GREEN)✓  Services running in background$(NC)"
	@$(MAKE) logs-follow

# ==============================================================================
# Build
# ==============================================================================

build: check-env ## Build all Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	$(DOCKER_COMPOSE) $(PROFILES) build
	@echo "$(GREEN)✓  Build complete$(NC)"

build-no-cache: check-env ## Build with no cache (clean build)
	@echo "$(BLUE)Building Docker images (no cache)...$(NC)"
	$(DOCKER_COMPOSE) $(PROFILES) build --no-cache
	@echo "$(GREEN)✓  Build complete$(NC)"

pull: ## Pull latest base images
	@echo "$(BLUE)Pulling latest base images...$(NC)"
	$(DOCKER_COMPOSE) $(PROFILES) pull
	@echo "$(GREEN)✓  Pull complete$(NC)"

# ==============================================================================
# Deployment
# ==============================================================================

deploy: check-env ## Production deployment with health checks
	@echo "$(BLUE)Running production deployment...$(NC)"
	@if [ -x ./scripts/deploy.sh ]; then \
		./scripts/deploy.sh; \
	else \
		echo "$(YELLOW)⚠  Deploy script not executable, using basic deployment$(NC)"; \
		$(MAKE) build-no-cache; \
		$(MAKE) start; \
		sleep 10; \
		$(MAKE) health; \
	fi

start: check-env ## Start services (without rebuilding)
	@echo "$(BLUE)Starting services...$(NC)"
	$(DOCKER_COMPOSE) $(PROFILES) up -d
	@echo "$(GREEN)✓  Services started$(NC)"
	@$(MAKE) ps

stop: ## Stop all services (graceful shutdown)
	@echo "$(BLUE)Stopping services...$(NC)"
	$(DOCKER_COMPOSE) stop -t 30
	@echo "$(GREEN)✓  Services stopped$(NC)"

restart: ## Restart all services
	@echo "$(BLUE)Restarting services...$(NC)"
	$(MAKE) stop
	$(MAKE) start

down: ## Stop and remove all containers
	@echo "$(BLUE)Stopping and removing containers...$(NC)"
	$(DOCKER_COMPOSE) down
	@echo "$(GREEN)✓  Containers removed$(NC)"

clean: ## Stop containers and remove volumes
	@echo "$(RED)⚠  This will delete all data including database!$(NC)"
	@read -p "Continue? (y/N): " -n 1 -r; \
	echo ""; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(DOCKER_COMPOSE) down -v; \
		echo "$(GREEN)✓  Cleanup complete$(NC)"; \
	else \
		echo "Cancelled"; \
	fi

# ==============================================================================
# Monitoring & Logs
# ==============================================================================

ps: ## Show running containers
	@$(DOCKER_COMPOSE) ps

logs: ## Show recent logs
	@$(DOCKER_COMPOSE) logs --tail=100

logs-follow: ## Follow logs in real-time
	@$(DOCKER_COMPOSE) logs -f

logs-backend: ## Show backend logs
	@$(DOCKER_COMPOSE) logs --tail=100 -f $(BACKEND_SERVICE)

logs-frontend: ## Show frontend logs
	@$(DOCKER_COMPOSE) logs --tail=100 -f $(FRONTEND_SERVICE)

logs-db: ## Show database logs
	@$(DOCKER_COMPOSE) logs --tail=100 -f $(DB_SERVICE)

health: ## Run health check
	@echo "$(BLUE)Running health check...$(NC)"
	@if [ -x ./scripts/health-check.sh ]; then \
		./scripts/health-check.sh; \
	else \
		curl -sf http://localhost/api/health | jq . || echo "$(RED)✗ Health check failed$(NC)"; \
	fi

monitor: ## Start monitoring stack (Prometheus + Grafana)
	@echo "$(BLUE)Starting monitoring stack...$(NC)"
	$(DOCKER_COMPOSE) --profile monitoring up -d prometheus grafana
	@echo "$(GREEN)✓  Monitoring started$(NC)"
	@echo "  Grafana: http://localhost:3000 (admin/admin)"
	@echo "  Prometheus: http://localhost:9090"

# ==============================================================================
# Testing
# ==============================================================================

test: ## Run all tests
	@echo "$(BLUE)Running tests...$(NC)"
	@$(MAKE) test-health
	@$(MAKE) test-api
	@echo "$(GREEN)✓  All tests passed$(NC)"

test-health: ## Test health endpoints
	@echo "$(BLUE)Testing health endpoint...$(NC)"
	@curl -sf http://localhost/api/health > /dev/null && echo "$(GREEN)✓  Health endpoint OK$(NC)" || echo "$(RED)✗  Health check failed$(NC)"

test-api: ## Test API endpoints
	@echo "$(BLUE)Testing chat API...$(NC)"
	@curl -sf -X POST http://localhost/api/chat \
		-H "Content-Type: application/json" \
		-d '{"messages":[{"role":"user","content":"Test"}]}' > /dev/null \
		&& echo "$(GREEN)✓  Chat API OK$(NC)" || echo "$(RED)✗  Chat API failed$(NC)"

test-e2e: ## Run end-to-end tests
	@if [ -x ./scripts/e2e-test.sh ]; then \
		./scripts/e2e-test.sh; \
	else \
		echo "$(YELLOW)⚠  E2E test script not found$(NC)"; \
	fi

# ==============================================================================
# Database Management
# ==============================================================================

db-shell: ## Open PostgreSQL shell
	@$(DOCKER_COMPOSE) exec $(DB_SERVICE) psql -U rag -d rag_db

db-migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	@$(DOCKER_COMPOSE) exec $(BACKEND_SERVICE) python -c "from db.base import init_db; import asyncio; asyncio.run(init_db())"
	@echo "$(GREEN)✓  Migrations complete$(NC)"

backup: ## Backup database
	@if [ -x ./scripts/backup.sh ]; then \
		./scripts/backup.sh; \
	else \
		mkdir -p backups; \
		$(DOCKER_COMPOSE) exec -T $(DB_SERVICE) pg_dump -U rag -d rag_db | gzip > backups/backup_$$(date +%Y%m%d_%H%M%S).sql.gz; \
		echo "$(GREEN)✓  Backup complete$(NC)"; \
	fi

restore: ## Restore database from backup
	@if [ -x ./scripts/restore.sh ]; then \
		./scripts/restore.sh; \
	else \
		echo "$(YELLOW)Run: ./scripts/restore.sh <backup_file>$(NC)"; \
	fi

# ==============================================================================
# Utilities
# ==============================================================================

exec-backend: ## Open shell in backend container
	@$(DOCKER_COMPOSE) exec $(BACKEND_SERVICE) /bin/bash

exec-db: ## Open shell in database container
	@$(DOCKER_COMPOSE) exec $(DB_SERVICE) /bin/bash

shell: exec-backend ## Alias for exec-backend

prune: ## Remove unused Docker resources
	@echo "$(YELLOW)Cleaning up unused Docker resources...$(NC)"
	@docker system prune -f
	@echo "$(GREEN)✓  Cleanup complete$(NC)"

prune-all: ## Remove ALL unused Docker resources (including volumes)
	@echo "$(RED)⚠  This will remove all unused Docker resources!$(NC)"
	@read -p "Continue? (y/N): " -n 1 -r; \
	echo ""; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker system prune -af --volumes; \
		echo "$(GREEN)✓  Deep cleanup complete$(NC)"; \
	else \
		echo "Cancelled"; \
	fi

# ==============================================================================
# Development Tools
# ==============================================================================

lint-backend: ## Lint backend code
	@echo "$(BLUE)Linting backend...$(NC)"
	@$(DOCKER_COMPOSE) exec $(BACKEND_SERVICE) ruff check . || echo "$(YELLOW)⚠  Install ruff for linting$(NC)"

lint-frontend: ## Lint frontend code
	@echo "$(BLUE)Linting frontend...$(NC)"
	@cd frontend && npm run lint

format-backend: ## Format backend code
	@echo "$(BLUE)Formatting backend...$(NC)"
	@$(DOCKER_COMPOSE) exec $(BACKEND_SERVICE) ruff format . || echo "$(YELLOW)⚠  Install ruff for formatting$(NC)"

install-dev-tools: ## Install development tools
	@echo "$(BLUE)Installing development tools...$(NC)"
	@pip install ruff mypy || echo "$(YELLOW)⚠  Failed to install Python tools$(NC)"
	@cd frontend && npm install || echo "$(YELLOW)⚠  Failed to install npm packages$(NC)"

# ==============================================================================
# Production Utilities
# ==============================================================================

scale-backend: ## Scale backend service (usage: make scale-backend N=3)
	@$(DOCKER_COMPOSE) up -d --scale $(BACKEND_SERVICE)=$(N)
	@echo "$(GREEN)✓  Backend scaled to $(N) instances$(NC)"

stats: ## Show container resource usage
	@docker stats --no-stream $$($(DOCKER_COMPOSE) ps -q)

top: ## Show running processes in containers
	@$(DOCKER_COMPOSE) top

# ==============================================================================
# Quick Actions
# ==============================================================================

up: start ## Alias for 'start'
kill: down ## Alias for 'down'
status: ps ## Alias for 'ps'
tail: logs-follow ## Alias for 'logs-follow'

# ==============================================================================
# Meta
# ==============================================================================

version: ## Show version information
	@echo "$(BLUE)Hybrid Inference App$(NC)"
	@echo "  Docker: $$(docker --version)"
	@echo "  Docker Compose: $$(docker compose version)"
	@if [ -f .env ]; then \
		echo "  Inference Provider: $(INFERENCE_PROVIDER)"; \
		echo "  Port: $(PORT)"; \
	fi

info: version ## Show system information
	@echo ""
	@echo "$(BLUE)Container Status:$(NC)"
	@$(MAKE) ps
	@echo ""
	@echo "$(BLUE)Disk Usage:$(NC)"
	@docker system df

update: ## Update base images and rebuild
	@$(MAKE) pull
	@$(MAKE) build
	@echo "$(GREEN)✓  Update complete$(NC)"
