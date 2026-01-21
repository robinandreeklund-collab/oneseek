#!/bin/bash

# OneSeek.ai Quick Start Script
# This script helps set up the development environment

set -e

echo "=========================================="
echo "OneSeek.ai MVP - Quick Start Setup"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running from project root
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo -e "${RED}Error: Please run this script from the project root directory${NC}"
    exit 1
fi

echo "Step 1: Backend Setup"
echo "----------------------"

# Backend setup
cd backend

# Check if Python 3.11+ is available
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"
else
    echo -e "${RED}✗ Python 3.11+ is required${NC}"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${YELLOW}Virtual environment already exists${NC}"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✓ Python dependencies installed${NC}"

# Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠ No .env file found${NC}"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo -e "${YELLOW}⚠ Please edit backend/.env with your Vespa credentials${NC}"
else
    echo -e "${GREEN}✓ .env file exists${NC}"
fi

# Run test setup
echo ""
echo "Running backend tests..."
python test_setup.py

cd ..

echo ""
echo "Step 2: Frontend Setup"
echo "----------------------"

# Frontend setup
cd frontend

# Check if Node.js is available
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✓ Node.js $NODE_VERSION found${NC}"
else
    echo -e "${RED}✗ Node.js 18+ is required${NC}"
    exit 1
fi

# Check for package manager
if command -v npm &> /dev/null; then
    PKG_MANAGER="npm"
    echo -e "${GREEN}✓ npm found${NC}"
elif command -v yarn &> /dev/null; then
    PKG_MANAGER="yarn"
    echo -e "${GREEN}✓ yarn found${NC}"
else
    echo -e "${RED}✗ npm or yarn is required${NC}"
    exit 1
fi

# Install dependencies
echo "Installing frontend dependencies..."
if [ "$PKG_MANAGER" = "npm" ]; then
    npm install
else
    yarn install
fi
echo -e "${GREEN}✓ Frontend dependencies installed${NC}"

# Check for .env.local
if [ ! -f ".env.local" ]; then
    echo "Creating .env.local from example..."
    cp .env.local.example .env.local
    echo -e "${GREEN}✓ .env.local created${NC}"
else
    echo -e "${GREEN}✓ .env.local exists${NC}"
fi

cd ..

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo -e "${GREEN}✓ Backend setup complete${NC}"
echo -e "${GREEN}✓ Frontend setup complete${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1. Configure Vespa Cloud (optional but recommended):"
echo "   - Visit https://console.vespa-cloud.com"
echo "   - Create account and tenant"
echo "   - Download certificate and key"
echo "   - Update backend/.env with paths"
echo "   - Run: cd backend && python deploy_vespa.py"
echo ""
echo "2. Start vLLM in a separate terminal:"
echo "   vllm serve Qwen/Qwen2.5-14B-Instruct-AWQ --port 8000"
echo ""
echo "3. Start the backend:"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   uvicorn app:app --reload --port 8001"
echo ""
echo "4. Start the frontend:"
echo "   cd frontend"
echo "   npm run dev  # or yarn dev"
echo ""
echo "5. Open http://localhost:3000 in your browser"
echo ""
echo -e "${YELLOW}Note: Steps 1 (Vespa) is optional for initial testing${NC}"
echo ""
