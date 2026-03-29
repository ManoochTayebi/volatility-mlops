#!/bin/bash

# PINN Volatility App Starter Script
# This script ensures a clean start of the application

echo "🧹 Cleaning up any existing processes..."

# Kill any processes on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Wait a moment
sleep 1

echo "🚀 Starting PINN Volatility Application..."
echo "📂 Frontend will be served from: $(pwd)/frontend"
echo "🌐 Access the app at: http://127.0.0.1:8000"
echo ""
echo "💡 TIP: If you see old content, try:"
echo "   - Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows/Linux)"
echo "   - Or open in incognito/private mode"
echo ""

# Start the Python application
python backend/app.py