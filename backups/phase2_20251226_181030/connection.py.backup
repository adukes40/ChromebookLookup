"""
Database connection and session management for PostgreSQL
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
import os
from typing import Generator

from .models import Base


class Database:
    """Database connection manager"""
    
    def __init__(self, database_url: str = None):
        """
        Initialize database connection
        
        Args:
            database_url: PostgreSQL connection string
                         Format: postgresql://user:password@host:port/database
        """
        if database_url is None:
            # Build from environment variables
            db_user = os.getenv('DB_USER', 'chromebook_user')
            db_pass = os.getenv('DB_PASSWORD', 'j3ymMbqRknz4twazvaVX8zVJN')
            db_host = os.getenv('DB_HOST', 'localhost')
            db_port = os.getenv('DB_PORT', '5432')
            db_name = os.getenv('DB_NAME', 'chromebook_dashboard')
            
            database_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        
        # Create engine with connection pooling
        self.engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=10,  # Max 10 connections
            max_overflow=20,  # Allow 20 additional connections under load
            pool_pre_ping=True,  # Verify connections before using
            pool_recycle=3600,  # Recycle connections after 1 hour
            echo=False  # Set to True for SQL debugging
        )
        
        # Create session factory
        self.SessionLocal = scoped_session(
            sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
        )
    
    def create_tables(self):
        """Create all tables in the database"""
        Base.metadata.create_all(bind=self.engine)
        print("✓ Database tables created successfully")
    
    def drop_tables(self):
        """Drop all tables (use with caution!)"""
        Base.metadata.drop_all(bind=self.engine)
        print("✗ All database tables dropped")
    
    @contextmanager
    def get_session(self) -> Generator:
        """
        Context manager for database sessions
        
        Usage:
            with db.get_session() as session:
                session.query(Chromebook).all()
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_db_session(self):
        """
        Dependency for FastAPI endpoints
        
        Usage:
            @app.get("/devices")
            def get_devices(db: Session = Depends(db.get_db_session)):
                return db.query(Chromebook).all()
        """
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()
    
    def close(self):
        """Close database connection pool"""
        self.SessionLocal.remove()
        self.engine.dispose()
        print("✓ Database connection closed")


# Global database instance
db = Database()


# Convenience function for getting sessions
def get_db():
    """FastAPI dependency for database sessions"""
    return db.get_db_session()
