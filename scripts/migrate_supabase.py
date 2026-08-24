import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()

DIRECT_URL = os.getenv("DIRECT_URL")

if not DIRECT_URL:
    print("Error: DIRECT_URL environment variable is not defined in .env.")
    sys.exit(1)

# Tabular Category base tables (hardcoded fallbacks if not run yet)
BASE_DDL = [
    """
    CREATE TABLE IF NOT EXISTS data_sources (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      category_name TEXT UNIQUE NOT NULL,
      source_type TEXT NOT NULL,
      source_url TEXT NOT NULL,
      fetch_method TEXT,
      column_schema JSONB,
      row_count INTEGER DEFAULT 0,
      sync_status TEXT DEFAULT 'never_synced',
      last_synced_at TIMESTAMPTZ,
      last_error TEXT,
      created_at TIMESTAMPTZ DEFAULT now(),
      updated_at TIMESTAMPTZ DEFAULT now()
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS data_rows (
      id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
      source_id UUID REFERENCES data_sources(id) ON DELETE CASCADE,
      sheet_name TEXT,
      row_index INTEGER,
      row_data JSONB NOT NULL,
      created_at TIMESTAMPTZ DEFAULT now()
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_data_rows_source ON data_rows(source_id);",
    "CREATE INDEX IF NOT EXISTS idx_data_rows_gin ON data_rows USING gin(row_data);"
]

def run_migration():
    print("Connecting to database using direct connection url...")
    try:
        # Connect directly to bypass pgBouncer and execute index/DDL/policies
        engine = create_engine(DIRECT_URL)
        with engine.connect() as conn:
            # 1. Run baseline DDL
            with conn.begin():
                print("Running baseline tabular schemas...")
                for stmt in BASE_DDL:
                    conn.execute(text(stmt))

            # 2. Run folder-based migrations in alphabetical order
            migrations_dir = Path(__file__).resolve().parent.parent / "supabase" / "migrations"
            if migrations_dir.exists():
                sql_files = sorted(migrations_dir.glob("*.sql"))
                print(f"Found {len(sql_files)} SQL migration file(s) in {migrations_dir}.")
                for sql_file in sql_files:
                    print(f"Executing migration: {sql_file.name}...")
                    with open(sql_file, "r", encoding="utf-8") as f:
                        sql_content = f.read()
                    
                    # Execute migration block in a transaction
                    with conn.begin():
                        conn.execute(text(sql_content))
            else:
                print("No migrations folder found. Skipping folder-based migrations.")
                
        print("All migrations completed successfully!")
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
