#!/usr/bin/env python
"""Initialize database tables using a fresh SQLAlchemy setup - avoids caching issues"""

import os
import sys

# Configure database URL directly
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    user = os.getenv("POSTGRES_USER", "intent_user")
    password = os.getenv("POSTGRES_PASSWORD", "intent_secure_password_change_in_prod")
    db = os.getenv("POSTGRES_DB", "intent_engine")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{db}"
else:
    # Extract user from URL if possible for GRANT command
    import re
    match = re.search(r'://([^:]+):', DATABASE_URL)
    user = match.group(1) if match else os.getenv("POSTGRES_USER", "intent_user")

from sqlalchemy import text
from sqlalchemy.pool import NullPool
from sqlalchemy import create_engine, inspect

print("1. Wiping database schema...")
engine = create_engine(DATABASE_URL, poolclass=NullPool, isolation_level="AUTOCOMMIT")
with engine.connect() as conn:
    conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
    conn.commit()
conn.close()
engine.dispose()


print("   Recreating schema...")
engine = create_engine(DATABASE_URL, poolclass=NullPool, isolation_level="AUTOCOMMIT")
with engine.connect() as conn:
    conn.execute(text("CREATE SCHEMA public"))
    conn.execute(text(f"GRANT ALL ON SCHEMA public TO {user}"))
    conn.execute(text(f"GRANT ALL ON ALL TABLES IN SCHEMA public TO {user}"))
    conn.execute(text(f"GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO {user}"))
    conn.commit()
conn.close()
engine.dispose()
print("   Schema wiped successfully.")

print("2. Creating tables using ORM models...")

# Import ORM models from database.py - this uses Base.metadata
from app.database import Base, engine as orm_engine

# Create all tables from ORM models
Base.metadata.create_all(orm_engine)

# Verify
inspector = inspect(orm_engine)
tables_created = sorted(inspector.get_table_names())
print(f"   Tables created: {', '.join(tables_created)}")

# Verify key tables exist
if "creative_assets" in tables_created and "audit_trails" in tables_created and "user_consents" in tables_created:
    print("✅ Database initialized successfully!")
else:
    print(
        f"   ⚠️  WARNING: missing tables! creative_assets: {'creative_assets' in tables_created}, audit_trails: {'audit_trails' in tables_created}, user_consents: {'user_consents' in tables_created}"
    )
    sys.exit(1)
