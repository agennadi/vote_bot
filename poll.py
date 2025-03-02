import logging

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


class Poll:
    def __init__(self, anonimity: bool, forwarding: bool, limit: int, question: str, options: list[str]):
        self.anonimity = anonimity
        self.forwarding = forwarding
        self.limit = limit
        self.question = question
        self.options = options 


    async def send_poll(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Sends a predefined poll"""

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


    async def receive_poll_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Tracks users' poll responses and closes poll if the limit is reached."""

        answer = update.poll_answer
        poll_id = answer.poll_id
        if poll_id not in context.bot_data:
            return  # Poll not found (probably bot restarted)
        selected_options = answer.option_ids
        answered_poll["answers"] += 1

        # Close poll after participants' limit has been reached 
        if answered_poll["answers"] == self.limit:
            await context.bot.stop_poll(answered_poll["chat_id"], answered_poll["message_id"])


