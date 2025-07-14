#!/usr/bin/env python3
"""
SwipingForJobs Launch Script (Python version)
This script starts both frontend and backend services with better cross-platform support
"""

import os
import sys
import subprocess
import time
import signal
import socket
from pathlib import Path
import shutil

class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def print_status(message):
    print(f"{Colors.BLUE}[INFO]{Colors.NC} {message}")

def print_success(message):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {message}")

def print_warning(message):
    print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {message}")

def print_error(message):
    print(f"{Colors.RED}[ERROR]{Colors.NC} {message}")

def command_exists(command):
    """Check if a command exists in the system"""
    return shutil.which(command) is not None

def port_in_use(port):
    """Check if a port is in use"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    return result == 0

def kill_port(port):
    """Kill processes using a specific port"""
    if port_in_use(port):
        print_warning(f"Port {port} is in use. Attempting to free it...")
        try:
            if os.name == 'nt':  # Windows
                subprocess.run(['taskkill', '/F', '/IM', 'python.exe'], 
                             capture_output=True, check=False)
                subprocess.run(['taskkill', '/F', '/IM', 'node.exe'], 
                             capture_output=True, check=False)
            else:  # Unix-like systems
                subprocess.run([f'lsof -ti :{port} | xargs kill -9 2>/dev/null || true'], 
                             shell=True, capture_output=True, check=False)
        except Exception as e:
            print_warning(f"Could not kill processes on port {port}: {e}")
        time.sleep(2)

def create_env_file():
    """Create a sample .env file if it doesn't exist"""
    env_content = """# Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Database Configuration
DATABASE_URL=sqlite:///./swipingforjobs.db

# Server Configuration
HOST=0.0.0.0
PORT=8000

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print_warning("Created sample .env file. Please edit it with your actual API keys.")

def main():
    print_status("Starting SwipingForJobs Application...")
    
    # Check if we're in the right directory
    if not (Path('main.py').exists() and Path('frontend').exists()):
        print_error("Please run this script from the SwipingForJobs root directory")
        sys.exit(1)
    
    # Check required commands
    print_status("Checking dependencies...")
    
    if not command_exists('python3') and not command_exists('python'):
        print_error("Python 3 is required but not installed")
        sys.exit(1)
    
    python_cmd = 'python3' if command_exists('python3') else 'python'
    
    if not command_exists('node'):
        print_error("Node.js is required but not installed")
        sys.exit(1)
    
    if not command_exists('npm'):
        print_error("npm is required but not installed")
        sys.exit(1)
    
    # Check for uv
    use_uv = command_exists('uv')
    if not use_uv:
        print_warning("uv is not installed. Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh")
        print_warning("Falling back to pip...")
    
    # Clean up any existing processes on our ports
    kill_port(8000)
    kill_port(3000)
    
    # Set up backend environment
    print_status("Setting up backend environment...")
    
    # Check if .env file exists
    if not Path('.env').exists():
        print_warning(".env file not found. Creating a sample .env file...")
        create_env_file()
    
    # Install Python dependencies
    try:
        if use_uv:
            print_status("Installing Python dependencies with uv...")
            subprocess.run(['uv', 'sync'], check=True)
        else:
            print_status("Installing Python dependencies with pip...")
            if Path('requirements.txt').exists():
                subprocess.run([python_cmd, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
            else:
                print_warning("requirements.txt not found. Installing from pyproject.toml...")
                subprocess.run([python_cmd, '-m', 'pip', 'install', '-e', '.'], check=True)
    except subprocess.CalledProcessError:
        print_error("Failed to install Python dependencies")
        sys.exit(1)
    
    # Install additional PDF processing libraries
    print_status("Installing PDF processing libraries...")
    try:
        if use_uv:
            subprocess.run(['uv', 'add', 'PyPDF2', 'pdfplumber'], check=True)
        else:
            subprocess.run([python_cmd, '-m', 'pip', 'install', 'PyPDF2', 'pdfplumber'], check=True)
    except subprocess.CalledProcessError:
        print_warning("Could not install PDF processing libraries")
    
    # Set up frontend environment
    print_status("Setting up frontend environment...")
    
    frontend_dir = Path('frontend')
    if not (frontend_dir / 'node_modules').exists():
        print_status("Installing frontend dependencies...")
        try:
            subprocess.run(['npm', 'install'], cwd=frontend_dir, check=True)
        except subprocess.CalledProcessError:
            print_error("Failed to install frontend dependencies")
            sys.exit(1)
    else:
        print_status("Frontend dependencies already installed")
    
    # Start backend server
    print_status("Starting backend server on port 8000...")
    
    backend_cmd = ['uv', 'run', 'uvicorn', 'main:app', '--host', '0.0.0.0', '--port', '8000', '--reload'] if use_uv else \
                  [python_cmd, '-m', 'uvicorn', 'main:app', '--host', '0.0.0.0', '--port', '8000', '--reload']
    
    try:
        backend_process = subprocess.Popen(backend_cmd)
    except Exception as e:
        print_error(f"Failed to start backend server: {e}")
        sys.exit(1)
    
    # Wait for backend to start
    print_status("Waiting for backend to start...")
    for _ in range(30):  # Wait up to 30 seconds
        if port_in_use(8000):
            break
        time.sleep(1)
    else:
        print_error("Backend failed to start on port 8000")
        backend_process.terminate()
        sys.exit(1)
    
    print_success("Backend server started successfully on http://localhost:8000")
    
    # Start frontend server
    print_status("Starting frontend server on port 3000...")
    
    try:
        frontend_process = subprocess.Popen(['npm', 'run', 'dev'], cwd=frontend_dir)
    except Exception as e:
        print_error(f"Failed to start frontend server: {e}")
        backend_process.terminate()
        sys.exit(1)
    
    # Wait for frontend to start
    print_status("Waiting for frontend to start...")
    for _ in range(30):  # Wait up to 30 seconds
        if port_in_use(3000):
            break
        time.sleep(1)
    else:
        print_error("Frontend failed to start on port 3000")
        backend_process.terminate()
        frontend_process.terminate()
        sys.exit(1)
    
    print_success("Frontend server started successfully on http://localhost:3000")
    
    # Print status
    print("")
    print_success("🚀 SwipingForJobs Application is running!")
    print("")
    print_status("Frontend: http://localhost:3000")
    print_status("Backend:  http://localhost:8000")
    print_status("API Docs: http://localhost:8000/docs")
    print("")
    print_status("Press Ctrl+C to stop both servers")
    print("")
    
    # Set up signal handlers for cleanup
    def cleanup_handler(signum, frame):
        print_status("Cleaning up processes...")
        backend_process.terminate()
        frontend_process.terminate()
        
        # Wait a bit for graceful shutdown
        time.sleep(2)
        
        # Force kill if still running
        try:
            backend_process.kill()
            frontend_process.kill()
        except:
            pass
        
        print_success("Cleanup complete")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, cleanup_handler)
    signal.signal(signal.SIGTERM, cleanup_handler)
    
    # Wait for both processes
    try:
        backend_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        cleanup_handler(None, None)

if __name__ == "__main__":
    main()
