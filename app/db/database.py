"""
Database connection and session management.
Lightweight async PostgreSQL with connection pooling.
"""
from databases import Database
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# Database URL from environment
DATABASE_URL = settings.DATABASE_URL

# Create async engine with connection pool
engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,  # Log SQL queries in dev
    pool_pre_ping=True,   # Auto-reconnect on stale connections
    pool_size=10,         # Max connections
    max_overflow=20,      # Extra connections under load
    pool_recycle=3600,    # Recycle connections after 1 hour
)

# Async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


async def get_db() -> AsyncSession:
    """Dependency for FastAPI routes to get DB session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables (run on startup)."""
    async with engine.begin() as conn:
        # Import all models to register them with Base.metadata
        from app.db import models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections (run on shutdown)."""
    await engine.dispose()
