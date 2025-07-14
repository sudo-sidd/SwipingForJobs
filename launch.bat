@echo off
REM SwipingForJobs Launch Script for Windows
REM This script starts both frontend and backend services

echo [INFO] Starting SwipingForJobs Application...

REM Check if we're in the right directory
if not exist "main.py" (
    echo [ERROR] main.py not found. Please run this script from the SwipingForJobs root directory
    pause
    exit /b 1
)

if not exist "frontend" (
    echo [ERROR] frontend directory not found. Please run this script from the SwipingForJobs root directory
    pause
    exit /b 1
)

REM Check required commands
echo [INFO] Checking dependencies...

where python >nul 2>&1
if %errorlevel% neq 0 (
    where python3 >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Python 3 is required but not installed
        pause
        exit /b 1
    )
    set PYTHON_CMD=python3
) else (
    set PYTHON_CMD=python
)

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is required but not installed
    pause
    exit /b 1
)

where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] npm is required but not installed
    pause
    exit /b 1
)

REM Check for uv
where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] uv is not installed. Falling back to pip...
    set USE_UV=false
) else (
    set USE_UV=true
)

REM Kill any existing processes on our ports
echo [INFO] Cleaning up existing processes...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM node.exe >nul 2>&1

REM Set up backend environment
echo [INFO] Setting up backend environment...

REM Check if .env file exists
if not exist ".env" (
    echo [WARNING] .env file not found. Creating a sample .env file...
    (
        echo # Gemini API Configuration
        echo GEMINI_API_KEY=your_gemini_api_key_here
        echo.
        echo # Database Configuration
        echo DATABASE_URL=sqlite:///./swipingforjobs.db
        echo.
        echo # Server Configuration
        echo HOST=0.0.0.0
        echo PORT=8000
        echo.
        echo # CORS Configuration
        echo CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001
    ) > .env
    echo [WARNING] Please edit .env file with your actual API keys before running the application
)

REM Install Python dependencies
if "%USE_UV%"=="true" (
    echo [INFO] Installing Python dependencies with uv...
    uv sync
) else (
    echo [INFO] Installing Python dependencies with pip...
    if exist "requirements.txt" (
        %PYTHON_CMD% -m pip install -r requirements.txt
    ) else (
        echo [WARNING] requirements.txt not found. Installing from pyproject.toml...
        %PYTHON_CMD% -m pip install -e .
    )
)

REM Install additional PDF processing libraries
echo [INFO] Installing PDF processing libraries...
if "%USE_UV%"=="true" (
    uv add PyPDF2 pdfplumber
) else (
    %PYTHON_CMD% -m pip install PyPDF2 pdfplumber
)

REM Set up frontend environment
echo [INFO] Setting up frontend environment...
cd frontend

if not exist "node_modules" (
    echo [INFO] Installing frontend dependencies...
    npm install
) else (
    echo [INFO] Frontend dependencies already installed
)

cd ..

REM Start backend server
echo [INFO] Starting backend server on port 8000...
if "%USE_UV%"=="true" (
    start "Backend Server" uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
) else (
    start "Backend Server" %PYTHON_CMD% -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
)

REM Wait for backend to start
echo [INFO] Waiting for backend to start...
timeout /t 5 /nobreak >nul

REM Start frontend server
echo [INFO] Starting frontend server on port 3000...
cd frontend
start "Frontend Server" npm run dev
cd ..

REM Wait for frontend to start
echo [INFO] Waiting for frontend to start...
timeout /t 5 /nobreak >nul

echo.
echo [SUCCESS] SwipingForJobs Application is running!
echo.
echo [INFO] Frontend: http://localhost:3000
echo [INFO] Backend:  http://localhost:8000
echo [INFO] API Docs: http://localhost:8000/docs
echo.
echo [INFO] Press any key to stop both servers...
pause >nul

REM Cleanup
echo [INFO] Cleaning up processes...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM node.exe >nul 2>&1
echo [SUCCESS] Cleanup complete
