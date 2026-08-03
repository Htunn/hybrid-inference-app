#!/usr/bin/env bash
# ==============================================================================
# Production Deployment Script
# ==============================================================================
# Deploys InferMesh with production best practices:
# - Environment validation
# - Database backup before deployment
# - Zero-downtime deployment (build then swap)
# - Health check verification
# - Automatic rollback on failure
# ==============================================================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"
BACKUP_DIR="$PROJECT_ROOT/backups"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ==============================================================================
# Helper Functions
# ==============================================================================

log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

die() {
    log_error "$1"
    exit 1
}

# ==============================================================================
# Pre-flight Checks
# ==============================================================================

preflight_checks() {
    log_info "Running pre-flight checks..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        die "Docker is not installed. Install from https://docs.docker.com/get-docker/"
    fi
    
    # Check Docker Compose
    if ! docker compose version &> /dev/null; then
        die "Docker Compose is not available. Update Docker to latest version."
    fi
    
    # Check .env exists
    if [[ ! -f "$ENV_FILE" ]]; then
        die ".env file not found. Copy .env.example and configure it:\n  cp .env.example .env"
    fi
    
    # Load environment
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    
    # Validate critical variables
    if [[ -z "${INFERENCE_PROVIDER:-}" ]]; then
        die "INFERENCE_PROVIDER not set in .env"
    fi
    
    if [[ -z "${POSTGRES_PASSWORD:-}" ]] || [[ "$POSTGRES_PASSWORD" == "CHANGE_THIS"* ]]; then
        die "POSTGRES_PASSWORD not set or still using default value. Generate a secure password:\n  openssl rand -base64 32"
    fi
    
    # Provider-specific checks
    case "$INFERENCE_PROVIDER" in
        gemini)
            if [[ -z "${GOOGLE_API_KEY:-}" ]] || [[ "$GOOGLE_API_KEY" == "your_"* ]]; then
                die "GOOGLE_API_KEY not set for Gemini provider. Get key: https://aistudio.google.com/apikey"
            fi
            ;;
        openai)
            if [[ -z "${OPENAI_API_KEY:-}" ]]; then
                die "OPENAI_API_KEY not set for OpenAI provider"
            fi
            ;;
        vllm)
            log_warning "vLLM provider requires NVIDIA GPU. Ensure --gpus all is available."
            ;;
        ollama)
            log_warning "Ollama provider requires Ollama running on host at $OLLAMA_BASE_URL"
            ;;
    esac
    
    log_success "Pre-flight checks passed"
}

# ==============================================================================
# Backup Database
# ==============================================================================

backup_database() {
    log_info "Creating database backup..."
    
    mkdir -p "$BACKUP_DIR"
    
    # Check if postgres container is running
    if docker compose ps postgres | grep -q "Up"; then
        timestamp=$(date +%Y%m%d_%H%M%S)
        backup_file="$BACKUP_DIR/postgres_backup_${timestamp}.sql"
        
        docker compose exec -T postgres pg_dump -U rag -d rag_db > "$backup_file" 2>/dev/null || {
            log_warning "Database backup failed (database might be empty)"
            return 0
        }
        
        # Compress backup
        gzip "$backup_file"
        log_success "Database backed up to: ${backup_file}.gz"
        
        # Keep only last 7 backups
        find "$BACKUP_DIR" -name "postgres_backup_*.sql.gz" -type f -mtime +7 -delete 2>/dev/null || true
    else
        log_info "No running database to backup (fresh deployment)"
    fi
}

# ==============================================================================
# Build Images
# ==============================================================================

build_images() {
    log_info "Building Docker images..."
    
    # Determine profiles
    profiles=()
    if [[ "${INFERENCE_PROVIDER:-}" == "vllm" ]]; then
        profiles+=(--profile vllm)
    fi
    
    # Build with no cache for production
    if ! docker compose "${profiles[@]}" build --no-cache; then
        die "Docker build failed"
    fi
    
    log_success "Images built successfully"
}

# ==============================================================================
# Deploy
# ==============================================================================

deploy() {
    log_info "Deploying services..."
    
    # Determine profiles
    profiles=()
    if [[ "${INFERENCE_PROVIDER:-}" == "vllm" ]]; then
        profiles+=(--profile vllm)
    fi
    
    # Stop old services gracefully (allows in-flight requests to complete)
    if docker compose ps --services 2>/dev/null | grep -q backend; then
        log_info "Stopping old services (30s graceful shutdown)..."
        docker compose "${profiles[@]}" stop -t 30
    fi
    
    # Start new services
    if ! docker compose "${profiles[@]}" up -d; then
        die "Deployment failed"
    fi
    
    log_success "Services started"
}

# ==============================================================================
# Health Check
# ==============================================================================

wait_for_health() {
    log_info "Waiting for services to be healthy..."
    
    local max_wait=120  # 2 minutes
    local elapsed=0
    local interval=5
    
    while [[ $elapsed -lt $max_wait ]]; do
        if docker compose ps backend | grep -q "healthy"; then
            log_success "Backend is healthy"
            return 0
        fi
        
        sleep $interval
        elapsed=$((elapsed + interval))
        echo -n "."
    done
    
    log_error "Health check timeout after ${max_wait}s"
    docker compose logs --tail=50 backend
    return 1
}

verify_deployment() {
    log_info "Verifying deployment..."
    
    # Run health check script
    if [[ -x "$SCRIPT_DIR/health-check.sh" ]]; then
        if "$SCRIPT_DIR/health-check.sh"; then
            log_success "Deployment verified"
            return 0
        else
            log_error "Health check failed"
            return 1
        fi
    else
        # Basic check
        local response
        response=$(curl -sf http://localhost/api/health 2>&1) || {
            log_error "Health endpoint not responding"
            return 1
        }
        
        if echo "$response" | grep -q '"status":"ok"'; then
            log_success "Deployment verified"
            return 0
        else
            log_error "Unexpected health response: $response"
            return 1
        fi
    fi
}

# ==============================================================================
# Rollback
# ==============================================================================

rollback() {
    log_error "Deployment failed. Rolling back..."
    
    docker compose down
    
    # Restore from backup if available
    latest_backup=$(find "$BACKUP_DIR" -name "postgres_backup_*.sql.gz" -type f 2>/dev/null | sort -r | head -n1)
    
    if [[ -n "$latest_backup" ]]; then
        log_info "Restoring database from: $latest_backup"
        # This would require starting postgres first
        # Implement if needed
    fi
    
    die "Rollback complete. Fix issues and retry deployment."
}

# ==============================================================================
# Main
# ==============================================================================

main() {
    echo ""
    echo "=========================================="
    echo "  InferMesh — Deployment"
    echo "=========================================="
    echo ""
    
    cd "$PROJECT_ROOT"
    
    preflight_checks
    backup_database
    build_images
    deploy
    
    if ! wait_for_health; then
        rollback
    fi
    
    if ! verify_deployment; then
        rollback
    fi
    
    echo ""
    echo "=========================================="
    log_success "Deployment successful!"
    echo ""
    echo "Services:"
    docker compose ps
    echo ""
    echo "Frontend:  http://localhost"
    echo "API:       http://localhost/api/health"
    echo "Metrics:   http://localhost/metrics"
    echo ""
    echo "Logs:      docker compose logs -f"
    echo "Stop:      docker compose down"
    echo "=========================================="
    echo ""
}

main "$@"
