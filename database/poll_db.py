import sqlite3
import logging
import os
from dotenv import load_dotenv

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


load_dotenv()

polls_db = os.getenv("POLLS_DB")


def migrate_answer_num_to_voters_num():
    """Migrate answer_num column to voters_num in existing databases."""
    with sqlite3.connect(polls_db) as conn:
        cursor = conn.cursor()
        try:
            # Check if answer_num column exists
            cursor.execute("PRAGMA table_info(polls)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'answer_num' in columns and 'voters_num' not in columns:
                logger.info("Migrating answer_num to voters_num...")
                
                # SQLite doesn't support ALTER TABLE RENAME COLUMN in older versions
                # So we need to recreate the table
                cursor.execute("""
                    CREATE TABLE polls_new (
                        poll_id TEXT PRIMARY KEY,
                        user_id INTEGER,
                        chat_id INTEGER,
                        anonimity BOOLEAN NOT NULL,
                        forwarding BOOLEAN NOT NULL,
                        "limit" INTEGER,
                        question TEXT NOT NULL,
                        expiration_date DATETIME,
                        voters_num INTEGER, 
                        closed BOOLEAN DEFAULT FALSE
                    )
                """)
                
                # Copy data from old table to new table
                cursor.execute("""
                    INSERT INTO polls_new 
                    SELECT poll_id, user_id, chat_id, anonimity, forwarding, "limit", 
                           question, expiration_date, answer_num, closed
                    FROM polls
                """)
                
                # Drop old table
                cursor.execute("DROP TABLE polls")
                
                # Rename new table
                cursor.execute("ALTER TABLE polls_new RENAME TO polls")
                
                conn.commit()
                logger.info("Migration completed: answer_num -> voters_num")
            elif 'voters_num' in columns:
                logger.info("Database already uses voters_num column")
        except sqlite3.DatabaseError as e:
            logger.error("Migration error: %s", e)
            conn.rollback()


def setup_database():
    with sqlite3.connect(polls_db) as conn:
        cursor = conn.cursor()

        try:
            # Table to store poll metadata
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS polls (
                poll_id TEXT PRIMARY KEY,
                user_id INTEGER,
                chat_id INTEGER,
                anonimity BOOLEAN NOT NULL,
                forwarding BOOLEAN NOT NULL,
                "limit" INTEGER,
                question TEXT NOT NULL,
                expiration_date DATETIME,
                voters_num INTEGER, 
                closed BOOLEAN DEFAULT FALSE
            )
            """)

            # Table for poll options
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS poll_options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                poll_id TEXT NOT NULL,
                option_text TEXT NOT NULL,
                vote_count INTEGER DEFAULT 0,
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
            
            # Run migration if needed
            migrate_answer_num_to_voters_num()
        except sqlite3.DatabaseError as e:
            logger.error("Database initialization error: %s", e)


# Run this once when setting up
setup_database()
