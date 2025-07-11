#!/usr/bin/env python3
"""
Database setup script for SwipingForJobs
This script demonstrates how to set up a proper SQLite database for production use.
"""

import sqlite3
import os
from datetime import datetime

DATABASE_PATH = "swipingforjobs.db"

def create_database():
    """Create SQLite database with proper tables"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            linkedin_url TEXT,
            github_url TEXT,
            skills TEXT NOT NULL,
            preferences TEXT NOT NULL,  -- JSON string of preferences array
            resume_filename TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create job_applications table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS job_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            job_title TEXT NOT NULL,
            company TEXT NOT NULL,
            job_source TEXT NOT NULL,
            job_url TEXT,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_email) REFERENCES users (email)
        )
    ''')
    
    # Create jobs_cache table for caching API results
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            job_data TEXT NOT NULL,  -- JSON string of job data
            cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL
        )
    ''')
    
    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_applications_user_email ON job_applications (user_email)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_cache_source ON jobs_cache (source)')
    
    conn.commit()
    conn.close()
    
    print(f"✅ Database created successfully at {DATABASE_PATH}")

def add_sample_data():
    """Add some sample data for testing"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Sample user
    cursor.execute('''
        INSERT OR REPLACE INTO users 
        (name, email, linkedin_url, github_url, skills, preferences, resume_filename)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        "John Doe",
        "john.doe@example.com",
        "https://linkedin.com/in/johndoe",
        "https://github.com/johndoe",
        "React, Node.js, Python, Docker",
        '["frontend", "backend", "fullstack"]',
        "john_doe_resume.pdf"
    ))
    
    conn.commit()
    conn.close()
    
    print("✅ Sample data added successfully")

def show_database_info():
    """Display database information"""
    if not os.path.exists(DATABASE_PATH):
        print("❌ Database does not exist. Run create_database() first.")
        return
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Get table info
    tables = ['users', 'job_applications', 'jobs_cache']
    
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"📊 {table}: {count} records")
    
    conn.close()

if __name__ == "__main__":
    print("🚀 SwipingForJobs Database Setup")
    print("=" * 40)
    
    create_database()
    add_sample_data()
    show_database_info()
    
    print("\n💡 To use this database in production:")
    print("1. Replace in-memory storage in main.py with SQLite queries")
    print("2. Add proper database connection pooling")
    print("3. Implement data migration scripts")
    print("4. Add database backup strategies")
    print("\n📚 For now, the app uses in-memory storage for simplicity")
