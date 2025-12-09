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
from handlers.webapp_handler import webapp_handler_status, webapp_handler_custom, webapp_handler_catchall
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
    
    # Temporary debug handler to see all updates (remove after debugging)
    async def debug_all_updates(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message:
            logger.info(f"DEBUG UPDATE: update_id={update.update_id}, chat_id={update.effective_chat.id}, "
                       f"text='{update.message.text}', "
                       f"has_web_app_data={update.message.web_app_data is not None}")
            if update.message.web_app_data:
                logger.info(f"  *** WEB APP DATA DETECTED ***: {update.message.web_app_data.data[:200]}...")
            # Don't block other handlers
            return
    
    # Test handler to catch ALL status updates to see if Web App data comes through
    async def test_all_status_updates(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message:
            logger.info(f"TEST STATUS UPDATE: update_id={update.update_id}, chat_id={update.effective_chat.id}")
            logger.info(f"  message.text={update.message.text}")
            logger.info(f"  message.web_app_data={update.message.web_app_data}")
            logger.info(f"  message type attributes: {dir(update.message)}")
            # Check all possible attributes
            if hasattr(update.message, 'web_app_data'):
                logger.info(f"  web_app_data attribute exists: {update.message.web_app_data}")
                if update.message.web_app_data:
                    logger.info(f"  *** WEB APP DATA IN STATUS UPDATE HANDLER ***: {update.message.web_app_data.data[:200]}...")
                    # Call our handler!
                    from handlers.webapp_handler import handle_webapp_data_wrapper
                    await handle_webapp_data_wrapper(update, context)
            if hasattr(update.message, 'via_bot'):
                logger.info(f"  via_bot: {update.message.via_bot}")

    application.add_handler(MessageHandler(filters.StatusUpdate.ALL, test_all_status_updates), group=0)  # Test all status updates
    
    # IMPORTANT: Web App handlers must be registered BEFORE other MessageHandlers
    # to ensure they catch Web App data messages first
    # Register in group 0 to ensure highest priority
    application.add_handler(webapp_handler_catchall, group=0)  # Catch-all for Web App data - MUST be first
    application.add_handler(webapp_handler_status, group=0)  # Handle Web App via StatusUpdate filter
    application.add_handler(webapp_handler_custom, group=0)  # Handle Web App via custom filter
    
    # Add logging wrapper for handle_poll_creation_message - register BEFORE conv_handler
    # Handler for WEBAPPFORM: messages - must be before ConversationHandler
    async def logged_handle_poll_creation_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"REGEX HANDLER CALLED: text='{update.message.text if update.message else None}'")
        if update.message and update.message.text:
            logger.info(f"REGEX HANDLER CHECK: text='{update.message.text}', matches WEBAPPFORM: {update.message.text.startswith('WEBAPPFORM:')}")
            import re
            pattern = r'^(CREATEPOLL:|WEBAPPFORM:)'
            if re.match(pattern, update.message.text):
                logger.info("REGEX PATTERN MATCHED!")
            else:
                logger.info("REGEX PATTERN DID NOT MATCH")
        await handle_poll_creation_message(update, context)
    
    # Handler for WEBAPPFORM: and CREATEPOLL: - MUST be before ConversationHandler
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(
        r'^(CREATEPOLL:|WEBAPPFORM:)'), logged_handle_poll_creation_message), group=1)  # Auto-create polls from inline or Web App form trigger - BEFORE conv_handler
    
    application.add_handler(conv_handler)  # Handles /start in private chats
    application.add_handler(CommandHandler(
        # Handles /start in groups
        "start", start_command_group, filters=filters.ChatType.GROUPS))
    
    # Debug handler to see all messages
    async def debug_all_updates(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message:
            logger.info(f"DEBUG UPDATE: update_id={update.update_id}, chat_id={update.effective_chat.id}, "
                       f"text='{update.message.text}', "
                       f"has_web_app_data={update.message.web_app_data is not None}")
            if update.message.web_app_data:
                logger.info(f"  *** WEB APP DATA DETECTED ***: {update.message.web_app_data.data[:200]}...")
        # Don't block - let other handlers process
        return
    application.add_handler(inline_query_handler)
    application.add_handler(chosen_inline_result_handler)
    application.add_handler(cancel_handler)
    application.add_handler(help_handler)
    application.add_handler(PollAnswerHandler(
        handle_non_anonymous_poll_answer))  # For non-anonymous polls
    # For anonymous polls (and all polls)
    application.add_handler(PollHandler(handle_anonymous_poll_update))
    application.add_handler(unknown_handler)
    
    # Debug handler at the end to catch everything - including Web App data
    async def debug_all_messages_comprehensive(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message:
            logger.info(f"=== COMPREHENSIVE DEBUG ===")
            logger.info(f"  update_id={update.update_id}")
            logger.info(f"  chat_id={update.effective_chat.id}")
            logger.info(f"  message_id={update.message.message_id}")
            logger.info(f"  text={update.message.text}")
            logger.info(f"  web_app_data={update.message.web_app_data}")
            if update.message.web_app_data:
                logger.info(f"  *** WEB APP DATA FOUND ***: {update.message.web_app_data.data}")
            logger.info(f"  message type: {type(update.message)}")
            logger.info(f"========================")
    
    application.add_handler(MessageHandler(filters.ALL, debug_all_messages_comprehensive))  # Debug all messages
    
    # application.add_handler(CommandHandler("poll_results", poll.get_poll_results))'''

    application.run_polling(allowed_updates=Update.ALL_TYPES)
