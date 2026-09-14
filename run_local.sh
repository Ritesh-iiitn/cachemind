#!/usr/bin/env bash
# ==============================================================================
# CacheMind - Run Locally Without Docker
# Starts: 1) FastAPI API Gateway, 2) Ingestion Worker, 3) Vite React Frontend
# ==============================================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "=================================================="
echo "⚡ Starting CacheMind Platform Locally (No Docker)"
echo "=================================================="

# 1. Activate Python virtual environment
if [ -d "ai_doc_assistant/venv" ]; then
    VENV_PATH="ai_doc_assistant/venv"
elif [ -d ".venv" ]; then
    VENV_PATH=".venv"
else
    echo "❌ Virtual environment not found. Please create one with: python3 -m venv ai_doc_assistant/venv"
    exit 1
fi

echo "🐍 Using Python environment: $VENV_PATH"
source "$VENV_PATH/bin/activate"

# Export PYTHONPATH so backend.app is discoverable
export PYTHONPATH="$PROJECT_ROOT/ai_doc_assistant"

# 2. Start Background Ingestion Worker
echo "⚙️  Starting Ingestion Worker..."
python -m backend.app.workers.worker &
WORKER_PID=$!

# 3. Start FastAPI API Gateway Server
echo "🚀 Starting FastAPI Gateway on http://localhost:8000..."
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

# 4. Start Frontend Vite Server
echo "🎨 Starting React Frontend on http://localhost:5173..."
npm --prefix ai_doc_assistant/frontend run dev &
FRONTEND_PID=$!

# Trap Ctrl+C to stop all background processes gracefully
cleanup() {
    echo ""
    echo "🛑 Shutting down CacheMind services..."
    kill "$FRONTEND_PID" 2>/dev/null || true
    kill "$API_PID" 2>/dev/null || true
    kill "$WORKER_PID" 2>/dev/null || true
    wait "$FRONTEND_PID" 2>/dev/null || true
    wait "$API_PID" 2>/dev/null || true
    wait "$WORKER_PID" 2>/dev/null || true
    echo "✓ All services stopped."
}
trap cleanup SIGINT SIGTERM EXIT

echo ""
echo "=================================================="
echo "✅ All CacheMind services are running!"
echo "   • Frontend UI:    http://localhost:5173"
echo "   • API Docs:       http://localhost:8000/docs"
echo "   • Health Check:   http://localhost:8000/health"
echo "=================================================="
echo "Press Ctrl+C to stop all services."
echo ""

# Keep script running
wait
