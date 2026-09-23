import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager

# On Render: DB_PATH=/data/skincare_fashion.db  (persistent disk mounted at /data)
# Locally:   falls back to ./data/skincare_fashion.db
_default_db_dir = Path(__file__).parent.parent / "data"
_default_db_dir.mkdir(exist_ok=True)

DB_PATH = Path(
    os.getenv("DB_PATH", str(_default_db_dir / "skincare_fashion.db"))
)
# Ensure parent directory exists (important when Render mounts a fresh disk)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def get_connection():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")    # Allows concurrent reads alongside writes
    conn.execute("PRAGMA synchronous = NORMAL")   # Safe + fast writes
    conn.execute("PRAGMA busy_timeout = 10000")   # Wait up to 10 s on lock contention
    conn.execute("PRAGMA cache_size = -32768")    # 32 MB in-memory page cache
    return conn

@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            gender TEXT DEFAULT 'unspecified',
            age INTEGER DEFAULT 25,
            budget_skincare REAL DEFAULT 2000.0,
            budget_fashion REAL DEFAULT 3500.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 2. Scans table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            image_path TEXT,
            overall_score INTEGER DEFAULT 75,
            skin_type TEXT DEFAULT 'Combination',
            undertone TEXT DEFAULT 'Neutral',
            age_estimate INTEGER DEFAULT 25,
            face_shape TEXT DEFAULT 'Oval',
            raw_telemetry TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """)

        # 3. Skin Issues table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS skin_issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER NOT NULL,
            issue_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            score INTEGER DEFAULT 50,
            zone TEXT DEFAULT 'Full Face',
            description TEXT,
            precautions TEXT,
            FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE
        )
        """)

        # 4. Product Recommendations table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            brand TEXT NOT NULL,
            price_inr REAL NOT NULL,
            platform TEXT NOT NULL,
            product_url TEXT,
            image_url TEXT,
            rating REAL DEFAULT 4.5,
            reason TEXT,
            target_issue TEXT,
            FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE
        )
        """)

        # 5. Outfits & Styling table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS outfits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER,
            user_id INTEGER,
            occasion TEXT NOT NULL,
            style_name TEXT NOT NULL,
            total_cost_inr REAL NOT NULL,
            palette_json TEXT,
            items_json TEXT NOT NULL,
            styling_tips TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE SET NULL
        )
        """)

        # 6. Purchases & Click tracker
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_name TEXT NOT NULL,
            platform TEXT NOT NULL,
            price_inr REAL NOT NULL,
            product_url TEXT,
            category TEXT,
            status TEXT DEFAULT 'clicked',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """)

        # 7. Face Embeddings table (for FaceNet face-based login & stored face images)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS face_embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            embedding_json TEXT NOT NULL,
            face_image_base64 TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """)
        
        # Schema migration check: ensure face_image_base64 exists if table was previously created
        cursor.execute("PRAGMA table_info(face_embeddings)")
        cols = [col[1] for col in cursor.fetchall()]
        if "face_image_base64" not in cols:
            cursor.execute("ALTER TABLE face_embeddings ADD COLUMN face_image_base64 TEXT")

        # Indexes for fast lookup
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scans_user_id ON scans(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_skin_issues_scan_id ON skin_issues(scan_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_recommendations_scan_id ON recommendations(scan_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_outfits_user_id ON outfits(user_id)")

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DB_PATH)
