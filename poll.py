import logging
import sys
from uuid import uuid4

from telegram import (
    KeyboardButton,
    KeyboardButtonPollType,
    Poll,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
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


class Poll:
    def __init__(self, anonimity: bool = False, forwarding: bool = True, limit: int = sys.maxsize, question: str = '', options: list[str] = None):
        self.id = str(uuid4())
        self.anonimity = anonimity
        self.forwarding = forwarding
        self.limit = limit
        self.question = question
        self.options = options if options is not None else []  


    async def send_poll(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Sends a new poll"""

        message = await context.bot.send_poll(
            chat_id=update.effective_chat.id,
            question=self.question,
            options=self.options,
            is_anonymous=self.anonimity,
            allows_multiple_answers=False,
            protect_content=self.forwarding
        )
        # Save some info about the poll the bot_data for later use in receive_poll_answer
        payload = {
            message.poll.id: {
                "question": self.question,
                "message_id": message.message_id,
                "chat_id": update.effective_chat.id,
                "answers": 0,
                "votes": {}
            }
        }
        context.bot_data.update(payload)
        logger.info("Poll with id %s was created", message.poll.id)
        logger.info("Information about the poll: %s", message.poll)


    async def receive_poll_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Tracks users' poll responses and closes poll if the limit is reached."""

        answer = update.poll_answer
        poll_id = answer.poll_id
        if poll_id not in context.bot_data:
            return  # Poll not found (probably bot restarted)

        poll_data = context.bot_data[poll_id]
        user_id = answer.user.id  # User who voted    
        selected_options = answer.option_ids
        poll_data["answers"] += 1
        poll_data["votes"][user_id] = selected_options

        # Close poll after participants' limit has been reached 
        if poll_data["answers"] >= self.limit:
            await context.bot.stop_poll(poll_data["chat_id"], poll_data["message_id"])
            await context.bot.send_message(
                poll_data["chat_id"],
                f"The poll '{poll_data['question']}' has closed after reaching the limit of {self.limit} votes."
            )

    def __repr__(self):
        return f"Poll({self.id}, {self.anonimity}, {self.forwarding}, {self.limit}, {self.question}, {self.options})"


