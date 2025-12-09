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
from handlers.non_anonymous_poll_answer_handler import handle_non_anonymous_poll_answer
from handlers.anonymous_poll_update_handler import handle_anonymous_poll_update
from handlers.inline_query_handler import handle_inline_query, handle_chosen_inline_result, handle_poll_creation_message
from handlers.webapp_handler import webapp_handler_status
from database.poll_repository import PollRepository
from services.poll_service import PollService
from utils.translations import translator

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

    # Get user's language and translate the message
    user = update.effective_user
    bot_username = context.bot.username
    message = translator.translate(
        "start_group", user, bot_username=bot_username)

    await update.message.reply_text(
        message,
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
    

    application.add_handler(webapp_handler_status, group=0)  # Handle Web App via StatusUpdate filter  # Handle Web App via custom filter
    
    # Handler for WEBAPPFORM: messages - must be before ConversationHandler

    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(
        r'^(CREATEPOLL:|WEBAPPFORM:)'), handle_poll_creation_message), group=1)  # Auto-create polls from inline or Web App form trigger - BEFORE conv_handler
    
    application.add_handler(conv_handler)  # Handles /start in private chats
    application.add_handler(CommandHandler(
        # Handles /start in groups
        "start", start_command_group, filters=filters.ChatType.GROUPS))
    
    application.add_handler(inline_query_handler)
    application.add_handler(chosen_inline_result_handler)
    application.add_handler(cancel_handler)
    application.add_handler(help_handler)
    application.add_handler(PollAnswerHandler(
        handle_non_anonymous_poll_answer))  # For non-anonymous polls
    # For anonymous polls (and all polls)
    application.add_handler(PollHandler(handle_anonymous_poll_update))
    application.add_handler(unknown_handler)
    
    # application.add_handler(CommandHandler("poll_results", poll.get_poll_results))'''

    application.run_polling(allowed_updates=Update.ALL_TYPES)
