import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, PollAnswerHandler, PollHandler, CallbackContext, InlineQueryHandler, ChosenInlineResultHandler, CommandHandler, MessageHandler, filters
import os
from dotenv import load_dotenv
from handlers.error_handler import error_handler
from handlers.help_handler import help_handler
from handlers.unknown_handler import unknown_handler
from handlers.cancel_handler import cancel_handler
from handlers.conversation_handler import conv_handler
from handlers.poll_answer_handler import handle_poll_answer
from handlers.poll_update_handler import handle_poll_update
from handlers.inline_query_handler import handle_inline_query, handle_chosen_inline_result, handle_poll_creation_message
from database.poll_repository import PollRepository
from services.poll_service import PollService


load_dotenv()

telegram_token = os.getenv("TELEGRAM_TOKEN")
polls_db = os.getenv("POLLS_DB")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def start_command_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command in group chats - show inline query instructions."""
    logger.info(f"Group chat detected - showing inline query instructions")
    await update.message.reply_text(
        "🗳️ **Welcome to the Poll Bot!**\n\n"
        "To create polls in this group, use the inline form:\n"
        "1. Type `@yourbot` in this chat\n"
        "2. Choose from examples or create your own\n"
        "3. Click to create the poll instantly!\n\n"
        "**Format:** `question|option1|option2|option3|anonimity|forwarding|limit`\n\n"
        "**Example:** `What's your favorite color?|Red|Blue|Green|false|true|100`",
        parse_mode='Markdown'
    )


if __name__ == '__main__':
    application = ApplicationBuilder().token(telegram_token).build()

    poll_repository = PollRepository(polls_db)
    poll_service = PollService(poll_repository)

    application.bot_data["poll_service"] = poll_service

    inline_query_handler = InlineQueryHandler(handle_inline_query)
    chosen_inline_result_handler = ChosenInlineResultHandler(
        handle_chosen_inline_result)

    application.add_error_handler(error_handler)
    application.add_handler(conv_handler)  # Handles /start in private chats
    application.add_handler(CommandHandler(
        # Handles /start in groups
        "start", start_command_group, filters=filters.ChatType.GROUPS))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(
        r'^CREATEPOLL:'), handle_poll_creation_message))  # Auto-create polls from inline
    application.add_handler(inline_query_handler)
    application.add_handler(chosen_inline_result_handler)
    application.add_handler(cancel_handler)
    application.add_handler(help_handler)
    application.add_handler(PollAnswerHandler(
        handle_poll_answer))  # For non-anonymous polls
    # For anonymous polls (and all polls)
    application.add_handler(PollHandler(handle_poll_update))
    application.add_handler(unknown_handler)
    # application.add_handler(CommandHandler("poll_results", poll.get_poll_results))'''

    application.run_polling(allowed_updates=Update.ALL_TYPES)
