#!/bin/bash

# SwipingForJobs Launch Script
# This script starts both frontend and backend services

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is in use
port_in_use() {
    lsof -i :$1 >/dev/null 2>&1
}

# Function to kill processes on specific ports
kill_port() {
    if port_in_use $1; then
        print_warning "Port $1 is in use. Killing existing processes..."
        lsof -ti :$1 | xargs kill -9 2>/dev/null || true
        sleep 2
    fi
}

# Function to cleanup on exit
cleanup() {
    print_status "Cleaning up processes..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    # Kill any remaining processes on our ports
    kill_port 8000
    kill_port 3000
    print_success "Cleanup complete"
}

# Set up trap to cleanup on exit
trap cleanup EXIT INT TERM

print_status "Starting SwipingForJobs Application..."

# Check if we're in the right directory
if [ ! -f "main.py" ] || [ ! -d "frontend" ]; then
    print_error "Please run this script from the SwipingForJobs root directory"
    exit 1
fi

# Check required commands
print_status "Checking dependencies..."

if ! command_exists python3; then
    print_error "Python 3 is required but not installed"
    exit 1
fi

if ! command_exists node; then
    print_error "Node.js is required but not installed"
    exit 1
fi

if ! command_exists npm; then
    print_error "npm is required but not installed"
    exit 1
fi

# Check for uv (Python package manager)
if ! command_exists uv; then
    print_warning "uv is not installed. Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    print_warning "Falling back to pip..."
    USE_UV=false
else
    USE_UV=true
fi

# Clean up any existing processes on our ports
kill_port 8000
kill_port 3000

# Set up backend environment
print_status "Setting up backend environment..."

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Creating a sample .env file..."
    cat > .env << EOF
# Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Database Configuration
DATABASE_URL=sqlite:///./swipingforjobs.db

# Server Configuration
HOST=0.0.0.0
PORT=8000

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001
EOF
    print_warning "Please edit .env file with your actual API keys before running the application"
fi

# Install Python dependencies
if [ "$USE_UV" = true ]; then
    print_status "Installing Python dependencies with uv..."
    uv sync
else
    print_status "Installing Python dependencies with pip..."
    python3 -m pip install -r requirements.txt 2>/dev/null || {
        print_warning "requirements.txt not found. Installing from pyproject.toml..."
        python3 -m pip install -e .
    }
fi

# Install additional PDF processing libraries if not present
print_status "Installing PDF processing libraries..."
if [ "$USE_UV" = true ]; then
    uv add PyPDF2 pdfplumber
else
    python3 -m pip install PyPDF2 pdfplumber
fi

# Set up frontend environment
print_status "Setting up frontend environment..."
cd frontend

# Install frontend dependencies
if [ ! -d "node_modules" ]; then
    print_status "Installing frontend dependencies..."
    npm install
else
    print_status "Frontend dependencies already installed"
fi

cd ..

# Start backend server
print_status "Starting backend server on port 8000..."
if [ "$USE_UV" = true ]; then
    uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
else
    python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
fi
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Check if backend started successfully
if ! port_in_use 8000; then
    print_error "Backend failed to start on port 8000"
    exit 1
fi

print_success "Backend server started successfully on http://localhost:8000"

# Start frontend server
print_status "Starting frontend server on port 3000..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# Wait a moment for frontend to start
sleep 3

# Check if frontend started successfully
if ! port_in_use 3000; then
    print_error "Frontend failed to start on port 3000"
    exit 1
fi

print_success "Frontend server started successfully on http://localhost:3000"

# Print status
echo ""
print_success "🚀 SwipingForJobs Application is running!"
echo ""
print_status "Frontend: http://localhost:3000"
print_status "Backend:  http://localhost:8000"
print_status "API Docs: http://localhost:8000/docs"
echo ""
print_status "Press Ctrl+C to stop both servers"
echo ""

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
