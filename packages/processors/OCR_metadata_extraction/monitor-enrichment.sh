#!/bin/bash

# Enrichment Pipeline Monitoring Script
# Real-time monitoring of enrichment pipeline progress and metrics

MONGO_USER="${MONGO_USER:-enrichment_user}"
MONGO_PASSWORD="${MONGO_PASSWORD:-changeMe123}"
MONGO_HOST="${MONGO_HOST:-localhost}"
MONGO_PORT="${MONGO_PORT:-27017}"
MONGO_DB="${MONGO_DB:-gvpocr}"

UPDATE_INTERVAL="${UPDATE_INTERVAL:-5}"
REFRESH_COUNT="${REFRESH_COUNT:-0}"

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Clear screen and move cursor to top
clear_and_home() {
    clear
    printf '\e[H'
}

# Get MongoDB query result
mongo_query() {
    local query=$1
    mongosh \
        --username "$MONGO_USER" \
        --password "$MONGO_PASSWORD" \
        --host "$MONGO_HOST:$MONGO_PORT" \
        --authenticationDatabase admin \
        --quiet \
        --eval "$query" 2>/dev/null || echo "0"
}

# Format timestamp
format_time() {
    date "+%Y-%m-%d %H:%M:%S"
}

echo "================================"
echo "Enrichment Pipeline Monitor"
echo "================================"
echo ""
echo "Monitoring enrichment.gvpocr at $MONGO_HOST:$MONGO_PORT"
echo "Update interval: ${UPDATE_INTERVAL}s"
echo ""
echo "Press Ctrl+C to exit"
echo ""

# Main monitoring loop
while true; do
    clear_and_home

    echo "Enrichment Pipeline Monitor - $(format_time)"
    echo "=========================================="
    echo ""

    # Enrichment Jobs Status
    echo -e "${BLUE}ENRICHMENT JOBS${NC}"
    echo "---"

    TOTAL_JOBS=$(mongo_query "db = db.getSiblingDB('$MONGO_DB'); db.enrichment_jobs.countDocuments({})")
    PROCESSING=$(mongo_query "db = db.getSiblingDB('$MONGO_DB'); db.enrichment_jobs.countDocuments({status: 'processing'})")
    COMPLETED=$(mongo_query "db = db.getSiblingDB('$MONGO_DB'); db.enrichment_jobs.countDocuments({status: 'completed'})")
    ERRORS=$(mongo_query "db = db.getSiblingDB('$MONGO_DB'); db.enrichment_jobs.countDocuments({status: 'error'})")

    echo "Total Jobs: $TOTAL_JOBS"
    echo -e "  ${GREEN}✓ Completed${NC}: $COMPLETED"
    echo -e "  ${YELLOW}⏳ Processing${NC}: $PROCESSING"
    echo -e "  ${RED}✗ Errors${NC}: $ERRORS"
    echo ""

    # Document Processing Status
    echo -e "${BLUE}DOCUMENTS PROCESSED${NC}"
    echo "---"

    TOTAL_DOCS=$(mongo_query "db = db.getSiblingDB('$MONGO_DB'); db.enriched_documents.countDocuments({})")
    APPROVED=$(mongo_query "db = db.getSiblingDB('$MONGO_DB'); db.enriched_documents.countDocuments({review_status: 'approved'})")
    PENDING_REVIEW=$(mongo_query "db = db.getSiblingDB('$MONGO_DB'); db.enriched_documents.countDocuments({review_status: 'pending'})")
    NOT_REQUIRED=$(mongo_query "db = db.getSiblingDB('$MONGO_DB'); db.enriched_documents.countDocuments({review_status: 'not_required'})")

    echo "Total Documents: $TOTAL_DOCS"
    echo -e "  ${GREEN}✓ Approved${NC}: $APPROVED"
    echo -e "  ${YELLOW}⏳ Review Pending${NC}: $PENDING_REVIEW"
    echo -e "  ${GREEN}✓ No Review Required${NC}: $NOT_REQUIRED"
    echo ""

    # Review Queue
    echo -e "${BLUE}REVIEW QUEUE${NC}"
    echo "---"

    PENDING_TASKS=$(mongo_query "db = db.getSiblingDB('$MONGO_DB'); db.review_queue.countDocuments({status: 'pending'})")
    IN_PROGRESS=$(mongo_query "db = db.getSiblingDB('$MONGO_DB'); db.review_queue.countDocuments({status: 'in_progress'})")
    APPROVED_REVIEWS=$(mongo_query "db = db.getSiblingDB('$MONGO_DB'); db.review_queue.countDocuments({status: 'approved'})")

    echo "Queue Size: $PENDING_TASKS"
    echo -e "  ${YELLOW}⏳ Pending${NC}: $PENDING_TASKS"
    echo -e "  ${YELLOW}👤 In Progress${NC}: $IN_PROGRESS"
    echo -e "  ${GREEN}✓ Approved${NC}: $APPROVED_REVIEWS"
    echo ""

    # Completeness Statistics
    echo -e "${BLUE}COMPLETENESS METRICS${NC}"
    echo "---"

    AVG_COMPLETENESS=$(mongo_query "
        db = db.getSiblingDB('$MONGO_DB');
        docs = db.enriched_documents.find({}, {quality_metrics: 1}).toArray();
        if (docs.length > 0) {
            var sum = docs.reduce((acc, doc) => acc + (doc.quality_metrics?.completeness_score || 0), 0);
            print((sum / docs.length).toFixed(2));
        } else {
            print('0.00');
        }
    ")

    HIGH_COMPLETE=$(mongo_query "db = db.getSiblingDB('$MONGO_DB'); db.enriched_documents.countDocuments({'quality_metrics.completeness_score': {\$gte: 0.95}})")
    LOW_COMPLETE=$(mongo_query "db = db.getSiblingDB('$MONGO_DB'); db.enriched_documents.countDocuments({'quality_metrics.completeness_score': {\$lt: 0.95}})")

    echo "Average Completeness: ${AVG_COMPLETENESS}"
    echo -e "  ${GREEN}≥95%${NC}: $HIGH_COMPLETE"
    echo -e "  ${YELLOW}<95%${NC}: $LOW_COMPLETE"
    echo ""

    # Cost Summary
    echo -e "${BLUE}COST TRACKING${NC}"
    echo "---"

    TOTAL_COST=$(mongo_query "
        db = db.getSiblingDB('$MONGO_DB');
        records = db.cost_records.find({}).toArray();
        var sum = records.reduce((acc, r) => acc + (r.cost_usd || 0), 0);
        print(sum.toFixed(2));
    ")

    CLAUDE_CALLS=$(mongo_query "db = db.getSiblingDB('$MONGO_DB'); db.cost_records.countDocuments({model: /^claude/})")
    OLLAMA_CALLS=$(mongo_query "db = db.getSiblingDB('$MONGO_DB'); db.cost_records.countDocuments({model: 'ollama'})")

    echo "Total Cost: \$$TOTAL_COST"
    echo "  Claude API Calls: $CLAUDE_CALLS"
    echo "  Ollama Calls (Free): $OLLAMA_CALLS"
    echo ""

    # NSQ Queue Status
    echo -e "${BLUE}MESSAGE QUEUE STATUS${NC}"
    echo "---"

    if curl -s http://localhost:4161/api/stats > /dev/null 2>&1; then
        QUEUE_STATS=$(curl -s http://localhost:4161/api/stats | jq '.topics[] | select(.name=="enrichment") | {depth: .depth, in_flight: .channels[0].in_flight, deferred: .channels[0].deferred}' 2>/dev/null)
        if [ -z "$QUEUE_STATS" ] || [ "$QUEUE_STATS" = "" ]; then
            echo "  Queue: (no active messages)"
        else
            echo "  Queue Statistics:"
            echo "$QUEUE_STATS" | jq '.'
        fi
    else
        echo "  NSQ API not accessible"
    fi
    echo ""

    # Agent Status
    echo -e "${BLUE}AGENT HEALTH${NC}"
    echo "---"

    if curl -s http://localhost:3000/health > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ MCP Server${NC}"
    else
        echo -e "  ${RED}✗ MCP Server${NC}"
    fi

    for agent in metadata-agent entity-agent structure-agent content-agent context-agent; do
        if docker ps -q -f "name=$agent" > /dev/null 2>&1; then
            STATUS=$(docker inspect --format='{{.State.Status}}' "enrichment_$agent" 2>/dev/null || echo "unknown")
            if [ "$STATUS" = "running" ]; then
                echo -e "  ${GREEN}✓${NC} $agent"
            else
                echo -e "  ${YELLOW}⚠${NC}  $agent ($STATUS)"
            fi
        fi
    done
    echo ""

    # Last Updated
    echo -e "${BLUE}LAST UPDATED${NC}: $(format_time)"
    echo "Refresh #$REFRESH_COUNT (Updating every ${UPDATE_INTERVAL}s...)"

    # Increment refresh counter
    ((REFRESH_COUNT++))

    # Wait before refresh
    sleep "$UPDATE_INTERVAL"
done
