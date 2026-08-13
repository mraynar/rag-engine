import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()

DIRECT_URL = os.getenv("DIRECT_URL")

if not DIRECT_URL:
    print("Error: DIRECT_URL environment variable is not defined in .env.")
    sys.exit(1)

DDL_STATEMENTS = [
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
    print(f"Connecting to database using direct connection url...")
    try:
        # Connect directly to bypass pgBouncer and execute index/DDL commands
        engine = create_engine(DIRECT_URL)
        with engine.connect() as conn:
            with conn.begin():
                for stmt in DDL_STATEMENTS:
                    print(f"Executing: {stmt.strip().splitlines()[0]}...")
                    conn.execute(text(stmt))
        print("Migration completed successfully!")
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_migration()
