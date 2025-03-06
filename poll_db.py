import sqlite3
import logging

_DB_FILE = "polls.db"
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def setup_database():
    with sqlite3.connect(_DB_FILE) as conn:
        cursor = conn.cursor()
        
        try:
            # Table to store poll metadata
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS polls (
                poll_id TEXT PRIMARY KEY,
                anonimity BOOLEAN NOT NULL,
                forwarding BOOLEAN NOT NULL,
                "limit" INTEGER NOT NULL,
                question TEXT NOT NULL,
                expiration_date DATETIME,
                answer_num INTEGER, 
                closed BOOLEAN DEFAULT FALSE
            )
            """)

            # Table for poll options
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS poll_options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                poll_id TEXT NOT NULL,
                option_text TEXT NOT NULL,
                FOREIGN KEY (poll_id) REFERENCES polls (poll_id) ON DELETE CASCADE
            )
            """)

            # Table for votes
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                poll_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                option_id INTEGER NOT NULL,
                FOREIGN KEY (poll_id) REFERENCES polls (poll_id) ON DELETE CASCADE,
                FOREIGN KEY (option_id) REFERENCES poll_options (id) ON DELETE CASCADE
            )
            """)
            
            conn.commit()
        except sqlite3.DatabaseError as e:
            logger.error("Database initialization error: %s", e)            

# Run this once when setting up
setup_database()