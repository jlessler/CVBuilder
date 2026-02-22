#!/usr/bin/env bash
# CVBuilder development startup script
# Run from the cvbuilder/ directory

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Backend ---
BACKEND="$SCRIPT_DIR/backend"
if [ ! -d "$BACKEND/.venv" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv "$BACKEND/.venv"
fi

echo "Installing/updating Python dependencies..."
"$BACKEND/.venv/bin/pip" install -q -r "$BACKEND/requirements.txt"

echo "Starting FastAPI backend on http://localhost:8000 ..."
(cd "$BACKEND" && .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000) &
BACKEND_PID=$!

# --- Frontend ---
FRONTEND="$SCRIPT_DIR/frontend"
if [ ! -d "$FRONTEND/node_modules" ]; then
  echo "Installing Node dependencies..."
  (cd "$FRONTEND" && npm install)
fi

echo "Starting Vite dev server on http://localhost:5173 ..."
(cd "$FRONTEND" && npm run dev) &
FRONTEND_PID=$!

echo ""
echo "CVBuilder is running:"
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
