import sqlite3
from models.poll import Poll
import logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

class PollRepository:
    def __init__(self, db):
        self.db = db
    
    def create_poll(self, poll: Poll, user_id: int, chat_id: int):
        with sqlite3.connect(self.db) as conn:
            cursor = conn.cursor()
            
            try:
                # Insert poll
                cursor.execute("""
                INSERT INTO polls (poll_id, user_id, chat_id, anonimity, forwarding, "limit", question, expiration_date, answer_num, closed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (poll.id, user_id, chat_id, poll.anonimity, poll.forwarding, poll.limit, poll.question, poll.expiration_date, poll.answer_num, poll.closed))
                
                # Insert poll options
                for option in poll.options:
                    cursor.execute("INSERT INTO poll_options (poll_id, option_text) VALUES (?, ?)", (poll.id, option))
                conn.commit()    
                logger.info("Inserted the poll %s and its options into the db", poll.id)
            except sqlite3.IntegrityError as e:
                logger.error("Database integrity error while inserting poll: %s", e)
                conn.rollback()
            except sqlite3.DatabaseError as e:
                logger.error("Database error while inserting poll: %s", e)
                conn.rollback()
            except Exception as e:
                logger.error("Unexpected error while inserting poll: %s", e)
                conn.rollback()              

                
    def record_poll_answer(self, poll: Poll, user_id: int, selected_options: list[int], is_closed: False):
        with sqlite3.connect(self.db) as conn:
            cursor = conn.cursor()
            try:    
                for selected_option in selected_options:
                    selected_option = poll.options[selected_option]
                    logger.info("poll_id: %s, selected_option: %s, user.id: %s", poll.id, selected_option, user_id)
                    # Find the option ID
                    cursor.execute("SELECT id FROM poll_options WHERE poll_id = ? AND option_text = ?", (poll.id, selected_option))
                    option_id = cursor.fetchone()
                    logger.info("option_id: %s", option_id[0])
                    # Update votes
                    cursor.execute("""INSERT INTO votes (poll_id, user_id, option_id)
                    VALUES (?, ?, ?);""",(poll.id, user_id, option_id[0]))    
                # Update poll
                cursor.execute("""
                    UPDATE polls
                    SET answer_num = answer_num + 1, 
                        closed = ?
                    WHERE poll_id = ?;
                """, (is_closed, poll.id))
                conn.commit()              
                logger.info("Updated the database row for poll %s", poll.id)  
            except sqlite3.IntegrityError as e:
                logger.error("Database integrity error while updating poll: %s", e)
                conn.rollback()
            except sqlite3.DatabaseError as e:
                logger.error("Database error while updating poll: %s", e)
                conn.rollback()
            except Exception as e:
                logger.error("Unexpected error while updating poll: %s", e)
                conn.rollback()                                  

    def remove_vote(self, poll_id: str, user_id: int):
        with sqlite3.connect(self.db) as conn:
            try:
                cursor = conn.cursor()
                # Count how many votes the user had
                cursor.execute("SELECT COUNT(*) FROM votes WHERE poll_id = ? AND user_id = ?", (poll_id, user_id))
                num_votes = cursor.fetchone()[0]
                # Delete all votes for this user and poll
                cursor.execute("DELETE FROM votes WHERE poll_id = ? AND user_id = ?", (poll_id, user_id))
                # Decrement the answer_num by the number of votes removed
                cursor.execute("UPDATE polls SET answer_num = answer_num - ? WHERE poll_id = ?", (num_votes, poll_id))            
                conn.commit()
            except sqlite3.IntegrityError as e:
                logger.error("Database integrity error while updating poll: %s", e)
                conn.rollback()
            except sqlite3.DatabaseError as e:
                logger.error("Database error while updating poll: %s", e)
                conn.rollback()
            except Exception as e:
                logger.error("Unexpected error while updating poll: %s", e)
                conn.rollback()                     


    def get_polls_by_user(self, user_id: str) -> list[Poll]:
        with sqlite3.connect(self.db) as conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM polls WHERE user_id = ?", (user_id))
                rows = cursor.fetchall()
                polls = []
                for row in rows:
                    poll = Poll(
                        id=row[0],
                        anonimity=bool(row[3]),
                        forwarding=bool(row[4]),
                        limit=row[5],
                        question=row[6],
                        expiration_date=row[7],
                        answer_num=row[8],
                        closed=bool(row[9])
                    )
                    # Fetch options
                    cursor.execute("SELECT option_text FROM poll_options WHERE poll_id = ?", (poll.id,))
                    options = [opt_row[0] for opt_row in cursor.fetchall()]
                    poll.options = options
                    
                    # Fetch votes
                    cursor.execute("SELECT user_id, option_id FROM votes WHERE poll_id = ?", (poll.id,))
                    votes = {}
                    for vote_row in cursor.fetchall():
                        voter_id, option_id = vote_row
                        if voter_id not in votes:
                            votes[voter_id] = []
                        votes[voter_id].append(option_id)
                    poll.votes = votes
                    
                    polls.append(poll)
                return polls
            except Exception as e:
                logger.error("Couldn't retrieve polls data: %s", e) 
                return []               

    
    def get_active_polls(self) -> list[Poll]:
        pass

    
    def close_poll(self, poll_id: str) -> None:
        with sqlite3.connect(self.db) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE polls SET closed = 1 WHERE poll_id = ?", (poll_id))
            conn.commit()


    def delete_poll(self, poll_id: str) -> None:
        """Deletes a poll and all related data (cascade delete)"""
        #TODO: add cascade delete for poll_options and votes
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("DELETE FROM polls WHERE poll_id = ?", (poll_id,))
                conn.commit()
                logger.info("Poll %s deleted from database", poll_id)
                
            except sqlite3.DatabaseError as e:
                logger.error("Database error while deleting poll: %s", e)
                conn.rollback()
                raise

    
    def get_poll_results(self, poll_id: str) -> dict:
        pass

    
    def get_poll_statistics(self, poll_id: str) -> dict:
        pass