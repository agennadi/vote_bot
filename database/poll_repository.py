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
                    cursor.execute(
                        "INSERT INTO poll_options (poll_id, option_text) VALUES (?, ?)", (poll.id, option))
                conn.commit()
                logger.info(
                    "Inserted the poll %s and its options into the db", poll.id)
            except sqlite3.IntegrityError as e:
                logger.error(
                    "Database integrity error while inserting poll: %s", e)
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
                    logger.info("poll_id: %s, selected_option: %s, user.id: %s",
                                poll.id, selected_option, user_id)
                    # Find the option ID
                    cursor.execute(
                        "SELECT id FROM poll_options WHERE poll_id = ? AND option_text = ?", (poll.id, selected_option))
                    option_id = cursor.fetchone()
                    logger.info("option_id: %s", option_id[0])
                    # Update votes
                    cursor.execute("""INSERT INTO votes (poll_id, user_id, option_id)
                    VALUES (?, ?, ?);""", (poll.id, user_id, option_id[0]))
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
                logger.error(
                    "Database integrity error while updating poll: %s", e)
                conn.rollback()
            except sqlite3.DatabaseError as e:
                logger.error("Database error while updating poll: %s", e)
                conn.rollback()
            except Exception as e:
                logger.error("Unexpected error while updating poll: %s", e)
                conn.rollback()

    def update_anonymous_poll_counts(self, poll_id: str, vote_counts: dict[int, int], total_voter_count: int = None):
        """
        Update vote counts for anonymous polls.
        vote_counts: {option_index: vote_count}
        total_voter_count: unique voters (from Telegram's poll.total_voter_count)
        """
        with sqlite3.connect(self.db) as conn:
            try:
                cursor = conn.cursor()

                # Get all option IDs for this poll in order
                cursor.execute("""
                    SELECT id, option_text 
                    FROM poll_options 
                    WHERE poll_id = ?
                    ORDER BY id
                """, (poll_id,))
                options = cursor.fetchall()

                # Update vote_count for each option
                for i, (option_id, option_text) in enumerate(options):
                    if i in vote_counts:
                        cursor.execute("""
                            UPDATE poll_options 
                            SET vote_count = ? 
                            WHERE id = ?
                        """, (vote_counts[i], option_id))

                # Update total voter count in polls table
                if total_voter_count is not None:
                    cursor.execute("""
                        UPDATE polls 
                        SET answer_num = ? 
                        WHERE poll_id = ?
                    """, (total_voter_count, poll_id))

                conn.commit()
                logger.info(
                    "Updated vote counts for anonymous poll %s (voters: %s)", poll_id, total_voter_count)
            except Exception as e:
                logger.error("Error updating anonymous poll counts: %s", e)
                conn.rollback()

    def remove_vote(self, poll_id: str, user_id: int):
        with sqlite3.connect(self.db) as conn:
            try:
                cursor = conn.cursor()
                # Count how many votes the user had
                cursor.execute(
                    "SELECT COUNT(*) FROM votes WHERE poll_id = ? AND user_id = ?", (poll_id, user_id))
                num_votes = cursor.fetchone()[0]
                # Delete all votes for this user and poll
                cursor.execute(
                    "DELETE FROM votes WHERE poll_id = ? AND user_id = ?", (poll_id, user_id))
                # Decrement the answer_num by the number of votes removed
                cursor.execute(
                    "UPDATE polls SET answer_num = answer_num - ? WHERE poll_id = ?", (num_votes, poll_id))
                conn.commit()
            except sqlite3.IntegrityError as e:
                logger.error(
                    "Database integrity error while updating poll: %s", e)
                conn.rollback()
            except sqlite3.DatabaseError as e:
                logger.error("Database error while updating poll: %s", e)
                conn.rollback()
            except Exception as e:
                logger.error("Unexpected error while updating poll: %s", e)
                conn.rollback()

    def get_poll_by_id(self, poll_id: str) -> Poll:
        """Fetch a single poll from the database by its ID."""
        with sqlite3.connect(self.db) as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM polls WHERE poll_id = ?", (poll_id,))
                row = cursor.fetchone()

                if not row:
                    logger.warning(
                        "Poll with id %s not found in database", poll_id)
                    return None

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
                cursor.execute(
                    "SELECT option_text FROM poll_options WHERE poll_id = ?", (poll.id,))
                options = [opt_row[0] for opt_row in cursor.fetchall()]
                poll.options = options

                # Fetch votes
                cursor.execute(
                    "SELECT user_id, option_id FROM votes WHERE poll_id = ?", (poll.id,))
                votes = {}
                for vote_row in cursor.fetchall():
                    voter_id, option_id = vote_row
                    if voter_id not in votes:
                        votes[voter_id] = []
                    votes[voter_id].append(option_id)
                poll.votes = votes

                return poll
            except Exception as e:
                logger.error(
                    "Couldn't retrieve poll %s from database: %s", poll_id, e)
                return None

    def get_polls_by_user(self, user_id: str) -> list[Poll]:
        with sqlite3.connect(self.db) as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM polls WHERE user_id = ?", (user_id))
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
                    cursor.execute(
                        "SELECT option_text FROM poll_options WHERE poll_id = ?", (poll.id,))
                    options = [opt_row[0] for opt_row in cursor.fetchall()]
                    poll.options = options

                    # Fetch votes
                    cursor.execute(
                        "SELECT user_id, option_id FROM votes WHERE poll_id = ?", (poll.id,))
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
            # Try with explicit tuple creation
            cursor.execute(
                "UPDATE polls SET closed = 1 WHERE poll_id = ?", (poll_id,))
            conn.commit()

    def delete_poll(self, poll_id: str) -> None:
        """Deletes a poll and all related data (cascade delete)"""
        # TODO: add cascade delete for poll_options and votes
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            try:
                cursor.execute(
                    "DELETE FROM polls WHERE poll_id = ?", (poll_id,))
                conn.commit()
                logger.info("Poll %s deleted from database", poll_id)

            except sqlite3.DatabaseError as e:
                logger.error("Database error while deleting poll: %s", e)
                conn.rollback()
                raise

    def get_poll_results(self, poll_id: str) -> dict:
        """Get vote counts per option for a poll."""
        with sqlite3.connect(self.db) as conn:
            try:
                cursor = conn.cursor()

                # Check if this is an anonymous poll
                cursor.execute(
                    "SELECT anonimity FROM polls WHERE poll_id = ?", (poll_id,))
                poll_row = cursor.fetchone()
                if not poll_row:
                    return {}

                is_anonymous = bool(poll_row[0])

                # Get all options for this poll
                cursor.execute("""
                    SELECT id, option_text, vote_count
                    FROM poll_options 
                    WHERE poll_id = ?
                    ORDER BY id
                """, (poll_id,))
                options = cursor.fetchall()

                # Initialize results
                results = {}
                for option_id, option_text, stored_vote_count in options:
                    if is_anonymous:
                        # For anonymous polls, use the vote_count column
                        results[option_text] = stored_vote_count or 0
                    else:
                        # For non-anonymous polls, count individual votes
                        cursor.execute("""
                            SELECT COUNT(*) 
                            FROM votes 
                            WHERE poll_id = ? AND option_id = ?
                        """, (poll_id, option_id))
                        vote_count = cursor.fetchone()[0]
                        results[option_text] = vote_count

                return results
            except Exception as e:
                logger.error(
                    "Error getting poll results for %s: %s", poll_id, e)
                return {}

    def get_poll_statistics(self, poll_id: str) -> dict:
        """Get detailed statistics for a poll."""
        with sqlite3.connect(self.db) as conn:
            try:
                cursor = conn.cursor()

                # Get poll info
                cursor.execute("""
                    SELECT question, answer_num, closed, anonimity
                    FROM polls 
                    WHERE poll_id = ?
                """, (poll_id,))
                poll_info = cursor.fetchone()

                if not poll_info:
                    return {}

                question, answer_num, closed, is_anonymous = poll_info

                # Get unique voter count
                cursor.execute("""
                    SELECT COUNT(DISTINCT user_id) 
                    FROM votes 
                    WHERE poll_id = ?
                """, (poll_id,))
                unique_voters = cursor.fetchone()[0]

                # Get total vote count
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM votes 
                    WHERE poll_id = ?
                """, (poll_id,))
                total_votes = cursor.fetchone()[0]

                # Get vote counts per option
                vote_results = self.get_poll_results(poll_id)

                return {
                    "question": question,
                    "is_anonymous": bool(is_anonymous),
                    "is_closed": bool(closed),
                    "unique_voters": unique_voters,
                    "total_votes": total_votes,
                    "vote_counts": vote_results
                }
            except Exception as e:
                logger.error(
                    "Error getting poll statistics for %s: %s", poll_id, e)
                return {}
