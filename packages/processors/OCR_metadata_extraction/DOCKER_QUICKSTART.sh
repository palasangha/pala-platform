#!/bin/bash

# LangChain Docker Quick Start Script
# Start Ollama + Open WebUI with one command

PROJECT_DIR="/mnt/sda1/mango1_home/gvpocr"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     LangChain Docker Quick Start                           ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not installed"
    exit 1
fi

echo "✅ Docker version: $(docker --version)"
echo ""

# Check if compose file exists
if [ ! -f "$PROJECT_DIR/docker-compose.langchain.yml" ]; then
    echo "❌ docker-compose.langchain.yml not found"
    exit 1
fi

# Get command from argument
CMD=${1:-start}

case $CMD in
    start)
        echo "🚀 Starting LangChain Docker stack..."
        cd "$PROJECT_DIR"
        docker-compose -f docker-compose.langchain.yml up -d
        
        echo ""
        echo "⏳ Waiting for services to start..."
        sleep 5
        
        echo ""
        echo "✅ Services started!"
        echo ""
        echo "📋 Next steps:"
        echo "   1. Pull models: ./DOCKER_QUICKSTART.sh models"
        echo "   2. Open WebUI: http://localhost:8080"
        echo "   3. Check status: ./DOCKER_QUICKSTART.sh status"
        echo ""
        ;;
        
    models)
        echo "🔍 Pulling Ollama models..."
        docker exec -it langchain-ollama ollama pull mistral
        docker exec -it langchain-ollama ollama pull nomic-embed-text
        echo ""
        echo "✅ Models installed"
        echo "   Open WebUI: http://localhost:8080"
        ;;
        
    status)
        echo "📊 Service Status:"
        docker-compose -f docker-compose.langchain.yml ps
        echo ""
        echo "🌐 URLs:"
        echo "   Open WebUI: http://localhost:8080"
        echo "   Ollama API: http://localhost:11434"
        ;;
        
    logs)
        echo "📋 Showing logs (Ctrl+C to exit)..."
        docker-compose -f docker-compose.langchain.yml logs -f
        ;;
        
    stop)
        echo "🛑 Stopping services..."
        docker-compose -f docker-compose.langchain.yml down
        echo "✅ Services stopped"
        ;;
        
    clean)
        echo "🧹 Removing all containers and volumes..."
        docker-compose -f docker-compose.langchain.yml down -v
        echo "✅ Cleaned up"
        ;;
        
    test)
        echo "🧪 Testing services..."
        echo ""
        echo "1. Testing Ollama API..."
        curl -s http://localhost:11434/api/tags | jq . || echo "   ❌ Ollama not responding"
        echo ""
        echo "2. Testing Open WebUI..."
        curl -s http://localhost:8080 > /dev/null && echo "   ✅ Open WebUI is running" || echo "   ❌ Open WebUI not responding"
        ;;
        
    *)
        echo "Usage: ./DOCKER_QUICKSTART.sh [command]"
        echo ""
        echo "Commands:"
        echo "  start   - Start all services (default)"
        echo "  models  - Pull Ollama models"
        echo "  status  - Show service status"
        echo "  logs    - Show service logs"
        echo "  stop    - Stop all services"
        echo "  clean   - Remove containers and volumes"
        echo "  test    - Test all services"
        echo ""
        echo "Examples:"
        echo "  ./DOCKER_QUICKSTART.sh start"
        echo "  ./DOCKER_QUICKSTART.sh models"
        echo "  ./DOCKER_QUICKSTART.sh logs"
        ;;
esac
