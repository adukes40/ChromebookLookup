#!/usr/bin/env python3
"""
Database initialization script
Run this once to set up PostgreSQL database and tables
"""
import os
import sys
from sqlalchemy import create_engine, text

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import Base
from database.connection import db


def init_database():
    """Initialize database and create all tables"""
    
    print("=" * 60)
    print("Chromebook Dashboard - Database Initialization")
    print("=" * 60)
    print()
    
    # Database connection info
    db_user = os.getenv('DB_USER', 'chromebook_user')
    db_name = os.getenv('DB_NAME', 'chromebook_dashboard')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    
    print(f"Database: {db_name}")
    print(f"Host: {db_host}:{db_port}")
    print(f"User: {db_user}")
    print()
    
    # Test connection
    print("Testing database connection...")
    try:
        with db.get_session() as session:
            result = session.execute(text('SELECT version()'))
            version = result.fetchone()[0]
            print(f"✓ Connected to PostgreSQL")
            print(f"  Version: {version.split(',')[0]}")
            print()
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        print()
        print("Please ensure:")
        print("1. PostgreSQL is running")
        print("2. Database exists: sudo -u postgres createdb chromebook_dashboard")
        print("3. User exists with permissions")
        print()
        sys.exit(1)
    
    # Create tables
    print("Creating database tables...")
    try:
        db.create_tables()
        print()
        
        # List created tables
        with db.get_session() as session:
            result = session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]
            
            print("Created tables:")
            for table in tables:
                print(f"  • {table}")
            print()
    except Exception as e:
        print(f"✗ Table creation failed: {e}")
        sys.exit(1)
    
    # Create indexes
    print("Creating indexes for fast queries...")
    try:
        with db.get_session() as session:
            # Additional indexes for performance
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_chromebooks_user_lower 
                ON chromebooks (LOWER(annotated_user))
            """))
            
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_chromebooks_status_orgunit 
                ON chromebooks (status, org_unit_path)
            """))
            
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_users_email_lower 
                ON users (LOWER(email))
            """))
            
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_sync_logs_type_status 
                ON sync_logs (sync_type, status, completed_at DESC)
            """))
            
            session.commit()
            print("✓ Indexes created")
            print()
    except Exception as e:
        print(f"⚠ Index creation warning: {e}")
        print()
    
    print("=" * 60)
    print("✓ Database initialization complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Update .env with database credentials")
    print("2. Run initial sync: python3 sync_script.py")
    print("3. Start the API: uvicorn main:app --reload")
    print()


if __name__ == "__main__":
    init_database()
