#!/usr/bin/env bash
# ==============================================================================
# Health Check Script — Verifies all services are running correctly
# ==============================================================================
# Usage:
#   ./scripts/health-check.sh              # Check default http://localhost
#   ./scripts/health-check.sh localhost:8080  # Check custom host:port
# ==============================================================================

set -euo pipefail

BASE_URL="${1:-http://localhost}"
TIMEOUT=5
MAX_RETRIES=3

echo "🔍 InferMesh — Health Check"
echo "=========================================="
echo "Target: $BASE_URL"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ==============================================================================
# Helper Functions
# ==============================================================================

check_endpoint() {
    local endpoint="$1"
    local expected_status="${2:-200}"
    local description="$3"
    
    echo -n "├─ $description... "
    
    for i in $(seq 1 "$MAX_RETRIES"); do
        if response=$(curl -s -w "\n%{http_code}" --max-time "$TIMEOUT" "${BASE_URL}${endpoint}" 2>&1); then
            # Extract status code (last line) and body (all but last line)
            # macOS-compatible: use sed instead of head -n-1
            status_code=$(echo "$response" | tail -n1)
            body=$(echo "$response" | sed '$d')
            
            if [[ "$status_code" == "$expected_status" ]]; then
                echo -e "${GREEN}✓${NC} (HTTP $status_code)"
                return 0
            fi
        fi
        
        if [[ $i -lt $MAX_RETRIES ]]; then
            sleep 2
        fi
    done
    
    echo -e "${RED}✗${NC} (Failed after $MAX_RETRIES attempts)"
    echo "   Response: $body"
    return 1
}

check_json_field() {
    local endpoint="$1"
    local jq_query="$2"
    local expected="$3"
    local description="$4"
    
    echo -n "├─ $description... "
    
    if ! command -v jq &> /dev/null; then
        echo -e "${YELLOW}⚠${NC} (jq not installed, skipping)"
        return 0
    fi
    
    response=$(curl -s --max-time "$TIMEOUT" "${BASE_URL}${endpoint}" 2>&1 || echo "{}")
    actual=$(echo "$response" | jq -r "$jq_query" 2>/dev/null || echo "null")
    
    if [[ "$actual" == "$expected" ]]; then
        echo -e "${GREEN}✓${NC} ($expected)"
        return 0
    else
        echo -e "${RED}✗${NC} (expected: $expected, got: $actual)"
        return 1
    fi
}

# ==============================================================================
# Core Health Checks
# ==============================================================================

echo "📡 Core Services"
echo "────────────────"

# Frontend static files
check_endpoint "/" "200" "Frontend (SPA shell)"

# Backend health endpoint
check_endpoint "/api/health" "200" "Backend health endpoint"

# Metrics endpoint (Prometheus)
check_endpoint "/metrics" "200" "Metrics endpoint"

echo ""
echo "🔧 API Validation"
echo "─────────────────"

# Check health response structure
check_json_field "/api/health" ".status" "ok" "Health status = ok"

# Check inference provider is set
if command -v jq &> /dev/null; then
    echo -n "├─ Inference provider configured... "
    provider=$(curl -s --max-time "$TIMEOUT" "${BASE_URL}/api/health" | jq -r '.provider' 2>/dev/null || echo "unknown")
    if [[ "$provider" != "null" && "$provider" != "unknown" ]]; then
        echo -e "${GREEN}✓${NC} ($provider)"
    else
        echo -e "${YELLOW}⚠${NC} (provider not detected)"
    fi
fi

echo ""
echo "🧪 Functional Tests"
echo "───────────────────"

# Test chat endpoint (streaming SSE)
echo -n "├─ Chat endpoint (streaming)... "
chat_response=$(curl -s --max-time 10 -X POST "${BASE_URL}/api/chat" \
    -H "Content-Type: application/json" \
    -d '{"messages":[{"role":"user","content":"Hi"}]}' 2>&1 || echo "")

if [[ "$chat_response" == *"data:"* ]]; then
    echo -e "${GREEN}✓${NC} (SSE stream received)"
else
    echo -e "${RED}✗${NC} (No SSE response)"
    echo "   Response: ${chat_response:0:100}..."
fi

echo ""
echo "🐳 Docker Services"
echo "──────────────────"

# Check if running in Docker
if command -v docker &> /dev/null && docker compose ps &> /dev/null 2>&1; then
    echo -n "├─ Docker Compose services... "
    
    # Count running services
    running=$(docker compose ps --services --filter "status=running" 2>/dev/null | wc -l)
    total=$(docker compose ps --services 2>/dev/null | wc -l)
    
    if [[ $running -eq $total && $total -gt 0 ]]; then
        echo -e "${GREEN}✓${NC} ($running/$total running)"
    else
        echo -e "${YELLOW}⚠${NC} ($running/$total running)"
    fi
    
    # Check postgres specifically
    if docker compose ps postgres 2>&1 | grep -q "Up"; then
        echo -e "├─ PostgreSQL (RAG database)... ${GREEN}✓${NC}"
    else
        echo -e "├─ PostgreSQL (RAG database)... ${YELLOW}⚠${NC} (not running)"
    fi
else
    echo -e "├─ Docker check... ${YELLOW}⚠${NC} (docker or compose not available)"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✓${NC} Health check complete"
echo ""
