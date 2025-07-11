import aiosqlite
import os
import random
import bcrypt
from datetime import datetime
from typing import Optional, Dict, List

DATABASE_PATH = "swipingforjobs.db"
RESUME_UPLOAD_DIR = "uploaded_resumes"

# Ensure upload directory exists
os.makedirs(RESUME_UPLOAD_DIR, exist_ok=True)

class DatabaseManager:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
    
    async def init_database(self):
        """Initialize database with required tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # Create users table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    login_code TEXT UNIQUE NOT NULL,
                    linkedin_url TEXT,
                    github_url TEXT,
                    portfolio_url TEXT,
                    phone_number TEXT,
                    location TEXT,
                    bio TEXT,
                    skills TEXT NOT NULL,
                    preferences TEXT NOT NULL,  -- JSON string
                    work_mode TEXT DEFAULT 'remote',  -- remote, hybrid, onsite
                    experience_level TEXT DEFAULT 'entry',  -- entry, junior, mid, senior
                    salary_min INTEGER,
                    salary_max INTEGER,
                    currency TEXT DEFAULT 'USD',
                    resume_filename TEXT,
                    resume_path TEXT,
                    linkedin_data TEXT,  -- JSON string of LinkedIn profile data
                    github_data TEXT,    -- JSON string of GitHub profile data
                    resume_processed_data TEXT,  -- JSON string of processed resume data
                    profile_completed BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create job_applications table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS job_applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    user_email TEXT NOT NULL,
                    job_title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    job_source TEXT NOT NULL,
                    job_url TEXT,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Create sessions table for login management
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_token TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Create indexes
            await db.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_users_login_code ON users (login_code)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_applications_user_id ON job_applications (user_id)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions (session_token)')
            
            await db.commit()
    
    def generate_login_code(self) -> str:
        """Generate a unique 4-digit login code"""
        return f"{random.randint(1000, 9999)}"
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    async def create_user(self, name: str, email: str, linkedin_url: str, github_url: str, 
                         skills: str, preferences: List[str], resume_filename: str = "", 
                         resume_path: str = "", linkedin_data: str = "", github_data: str = "",
                         resume_processed_data: str = "", **kwargs) -> Dict:
        """Create a new user with auto-generated login code"""
        async with aiosqlite.connect(self.db_path) as db:
            # Generate unique login code
            login_code = self.generate_login_code()
            
            # Check if login code already exists (very unlikely but safety first)
            while True:
                cursor = await db.execute('SELECT id FROM users WHERE login_code = ?', (login_code,))
                if not await cursor.fetchone():
                    break
                login_code = self.generate_login_code()
            
            # Hash the login code as password
            password_hash = self.hash_password(login_code)
            
            # Convert preferences list to JSON string
            preferences_json = ','.join(preferences)
            
            try:
                cursor = await db.execute('''
                    INSERT INTO users (name, email, password_hash, login_code, linkedin_url, 
                                     github_url, skills, preferences, resume_filename, resume_path,
                                     linkedin_data, github_data, resume_processed_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (name, email, password_hash, login_code, linkedin_url, github_url, 
                      skills, preferences_json, resume_filename, resume_path,
                      linkedin_data, github_data, resume_processed_data))
                
                user_id = cursor.lastrowid
                await db.commit()
                
                return {
                    "user_id": user_id,
                    "login_code": login_code,
                    "message": "User created successfully"
                }
                
            except aiosqlite.IntegrityError:
                raise ValueError("Email already exists")
    
    async def authenticate_user(self, name: str, login_code: str) -> Optional[Dict]:
        """Authenticate user with name and login code"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT id, name, email, password_hash, linkedin_url, github_url, portfolio_url,
                       phone_number, location, bio, skills, preferences, work_mode, 
                       experience_level, salary_min, salary_max, currency, resume_filename, 
                       resume_path, linkedin_data, github_data, resume_processed_data, 
                       profile_completed
                FROM users 
                WHERE LOWER(name) = LOWER(?) AND login_code = ?
            ''', (name, login_code))
            
            user = await cursor.fetchone()
            if not user:
                return None
            
            # Convert to dictionary
            user_data = {
                "id": user[0],
                "name": user[1],
                "email": user[2],
                "linkedin_url": user[4] or "",
                "github_url": user[5] or "",
                "portfolio_url": user[6] or "",
                "phone_number": user[7] or "",
                "location": user[8] or "",
                "bio": user[9] or "",
                "skills": user[10],
                "preferences": user[11].split(',') if user[11] else [],
                "work_mode": user[12] or "remote",
                "experience_level": user[13] or "entry",
                "salary_min": user[14],
                "salary_max": user[15],
                "currency": user[16] or "USD",
                "resume_filename": user[17] or "",
                "resume_path": user[18] or "",
                "linkedin_data": user[19] or "",
                "github_data": user[20] or "",
                "resume_processed_data": user[21] or "",
                "profile_completed": bool(user[22])
            }
            
            return user_data
    
    async def update_user(self, user_id: int, **kwargs) -> bool:
        """Update user information"""
        async with aiosqlite.connect(self.db_path) as db:
            # Build dynamic update query
            set_clauses = []
            values = []
            
            for key, value in kwargs.items():
                if key == 'preferences' and isinstance(value, list):
                    value = ','.join(value)
                set_clauses.append(f"{key} = ?")
                values.append(value)
            
            if not set_clauses:
                return False
            
            values.append(user_id)
            query = f"UPDATE users SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
            
            await db.execute(query, values)
            await db.commit()
            return True
    
    async def record_job_application(self, user_id: int, user_email: str, job_title: str, 
                                   company: str, job_source: str, job_url: str = "") -> bool:
        """Record a job application"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO job_applications (user_id, user_email, job_title, company, job_source, job_url)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, user_email, job_title, company, job_source, job_url))
            
            await db.commit()
            return True
    
    async def get_user_applications(self, user_id: int) -> List[Dict]:
        """Get all applications for a user"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT job_title, company, job_source, job_url, applied_at
                FROM job_applications
                WHERE user_id = ?
                ORDER BY applied_at DESC
            ''', (user_id,))
            
            applications = await cursor.fetchall()
            return [
                {
                    "job_title": app[0],
                    "company": app[1],
                    "job_source": app[2],
                    "job_url": app[3] or "",
                    "applied_at": app[4]
                }
                for app in applications
            ]
    
    async def get_user_profile(self, user_id: int) -> Optional[Dict]:
        """Get complete user profile by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT id, name, email, linkedin_url, github_url, portfolio_url,
                       phone_number, location, bio, skills, preferences, work_mode, 
                       experience_level, salary_min, salary_max, currency, resume_filename, 
                       resume_path, linkedin_data, github_data, resume_processed_data, 
                       profile_completed, created_at, updated_at
                FROM users 
                WHERE id = ?
            ''', (user_id,))
            
            user = await cursor.fetchone()
            if not user:
                return None
            
            # Convert to dictionary
            return {
                "id": user[0],
                "name": user[1],
                "email": user[2],
                "linkedin_url": user[3] or "",
                "github_url": user[4] or "",
                "portfolio_url": user[5] or "",
                "phone_number": user[6] or "",
                "location": user[7] or "",
                "bio": user[8] or "",
                "skills": user[9],
                "preferences": user[10].split(',') if user[10] else [],
                "work_mode": user[11] or "remote",
                "experience_level": user[12] or "entry",
                "salary_min": user[13],
                "salary_max": user[14],
                "currency": user[15] or "USD",
                "resume_filename": user[16] or "",
                "resume_path": user[17] or "",
                "linkedin_data": user[18] or "",
                "github_data": user[19] or "",
                "resume_processed_data": user[20] or "",
                "profile_completed": bool(user[21]),
                "created_at": user[22],
                "updated_at": user[23]
            }

# Global database manager instance
db_manager = DatabaseManager()
