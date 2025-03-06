import logging
import sys
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import sqlite3

from telegram import (
    KeyboardButton,
    Poll,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PollAnswerHandler,
    PollHandler,
    filters,
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

load_dotenv()

polls_db = os.getenv("POLLS_DB")


class Poll:
    def __init__(self, anonimity: bool = False, forwarding: bool = True, limit: int = sys.maxsize, question: str = '', options: list[str] = None):
        self.id = ''
        self.anonimity = anonimity
        self.forwarding = forwarding
        self.limit = limit
        self.question = question
        self.options = options if options is not None else []  
        self.expiration_date = datetime.now() + timedelta(weeks=1)
        self.answer_num = 0
        self.votes = dict()
        self.closed = False


    async def send_poll(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Sends a new poll"""     

        message = await context.bot.send_poll(
            chat_id=update.effective_chat.id,
            question=self.question,
            options=self.options,
            is_anonymous=self.anonimity,
            allows_multiple_answers=True,
            protect_content=self.forwarding
        )

        self.id = message.poll.id

        # Save some info about the poll the bot_data for later use in receive_poll_answer
        payload = {
            message.poll.id: {
                "question": self.question,
                "options": self.options,
                "message_id": message.message_id,
                "chat_id": update.effective_chat.id,
                "answer_num": 0,
                "votes": {}
            }
        }
        context.bot_data.update(payload)
        logger.info("Poll with id %s was created", message.poll.id)
        logger.info("Information about the poll: %s", message.poll)

        with sqlite3.connect(polls_db) as conn:
            cursor = conn.cursor()
            
            try:
                # Insert poll
                cursor.execute("""
                INSERT INTO polls (poll_id, anonimity, forwarding, "limit", question, expiration_date, answer_num, closed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (self.id, self.anonimity, self.forwarding, self.limit, self.question, self.expiration_date, self.answer_num, self.closed))
                
                # Insert poll options
                for option in self.options:
                    cursor.execute("INSERT INTO poll_options (poll_id, option_text) VALUES (?, ?)", (self.id, option))
                conn.commit()    
                logger.info("Inserted the poll %s and its options into the db", self.id)
            except sqlite3.IntegrityError as e:
                logger.error("Database integrity error while inserting poll: %s", e)
                conn.rollback()
            except sqlite3.DatabaseError as e:
                logger.error("Database error while inserting poll: %s", e)
                conn.rollback()
            except Exception as e:
                logger.error("Unexpected error while inserting poll: %s", e)
                conn.rollback()                        


    async def receive_poll_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Tracks users' poll responses and closes poll if the limit is reached."""

        answer = update.poll_answer
        logger.info("Poll answer received: %s", answer)        
        poll_id = answer.poll_id
        if poll_id not in context.bot_data:
            return  # Poll not found (probably bot restarted)

        poll_data = context.bot_data[poll_id]
        user_id = answer.user.id  # User who voted    
        selected_options = answer.option_ids
        logger.info("Answer: %s", answer)
        logger.info("Selected options: %s", selected_options)
        poll_data["answer_num"] += 1
        poll_data["votes"][str(user_id)] = selected_options

        self.votes[user_id] = selected_options
        self.answer_num += 1

        logger.info("Context bot data: %s", context.bot_data[poll_id])
        # Close poll after the participants' limit has been reached 
        if poll_data["answer_num"] >= self.limit:
            await context.bot.stop_poll(poll_data["chat_id"], poll_data["message_id"])
            await context.bot.send_message(
                poll_data["chat_id"],
                f"The poll '{poll_data['question']}' has closed after reaching the limit of {self.limit} votes."
            )
            self.closed = True
            
        with sqlite3.connect(polls_db) as conn:
            cursor = conn.cursor()

            try:    
                for selected_option in selected_options:
                    selected_option = self.options[selected_option]
                    logger.info("poll_id: %s, selected_option: %s, user.id: %s", self.id, selected_option, user_id)
                    
                    # Find the option ID
                    cursor.execute("SELECT id FROM poll_options WHERE poll_id = ? AND option_text = ?", (self.id, selected_option))
                    option_id = cursor.fetchone()
                    logger.info("option_id: %s", option_id[0])

                    # Update votes
                    cursor.execute("""INSERT INTO votes (poll_id, user_id, option_id)
                    VALUES (?, ?, ?);""",(self.id, user_id, option_id[0]))    


                # Update poll
                cursor.execute("""
                    UPDATE polls
                    SET answer_num = answer_num + 1, 
                        closed = ?
                    WHERE poll_id = ?;
                """, (self.closed, self.id))

                conn.commit()              
                logger.info("Updated the database row for poll %s", self.id)  
            except sqlite3.IntegrityError as e:
                logger.error("Database integrity error while updating poll: %s", e)
                conn.rollback()
            except sqlite3.DatabaseError as e:
                logger.error("Database error while updating poll: %s", e)
                conn.rollback()
            except Exception as e:
                logger.error("Unexpected error while updating poll: %s", e)
                conn.rollback()                


    async def publish_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Inline button to choose where to publish the poll"""
        keyboard = [
            [InlineKeyboardButton("Publish poll", switch_inline_query="Choose chat for poll")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text("Where do you want to publish this poll?", reply_markup=reply_markup)      


    async def preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Displays a preview of the poll"""
        pass


    async def get_poll_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Displays the poll results."""
        pass


    def __repr__(self):
        return f"Poll({self.id}, {self.anonimity}, {self.forwarding}, {self.limit}, {self.question}, {self.options})"


