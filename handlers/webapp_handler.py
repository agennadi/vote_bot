import logging
import json
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, MessageHandler, filters
from telegram.error import BadRequest
from models.poll import Poll
from utils.translations import translator

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


# Track processed updates to prevent duplicate processing
_processed_updates = set()

async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle data submitted from Web App form."""
    
    # Prevent duplicate processing
    if update.update_id in _processed_updates:
        logger.debug(f"Update {update.update_id} already processed, skipping")
        return
    
    logger.info("=" * 50)
    logger.info("=== handle_webapp_data CALLED ===")
    logger.info("=" * 50)
    logger.info(f"Update ID: {update.update_id}")
    logger.info(f"Update type: {update.update_type}")
    logger.info(f"Has message: {update.message is not None}")
    if update.message:
        logger.info(f"Message chat_id: {update.effective_chat.id}")
        logger.info(f"Message message_id: {update.message.message_id}")
        logger.info(f"Message text: {update.message.text}")
        logger.info(f"Message from_user: {update.message.from_user.id if update.message.from_user else None}")
        logger.info(f"Has web_app_data: {update.message.web_app_data is not None}")
        if update.message.web_app_data:
            logger.info(f"*** WEB APP DATA FOUND IN HANDLER ***")
            logger.info(f"Web App data string: {update.message.web_app_data.data}")
        else:
            logger.warning("Message exists but web_app_data is None")
    else:
        logger.warning("No message in update")
    
    if not update.message or not update.message.web_app_data:
        logger.warning("No message or web_app_data found, returning early")
        return
    
    # Mark as processed
    _processed_updates.add(update.update_id)
    # Clean up old entries (keep only last 1000)
    if len(_processed_updates) > 1000:
        _processed_updates.clear()
    
    try:
        # Parse JSON data from Web App
        data_str = update.message.web_app_data.data
        poll_data = json.loads(data_str)
        
        logger.info(f"Web App data received: {poll_data}")
        
        # Validate required fields
        if not poll_data.get('question') or not poll_data.get('options'):
            raise ValueError("Missing required fields")
        
        options = poll_data['options']
        if len(options) < 2:
            raise ValueError("At least 2 options are required")
        
        # Create Poll object
        poll = Poll(
            question=poll_data['question'],
            options=options,
            anonimity=poll_data.get('anonymous', False),
            forwarding=poll_data.get('forwarding', True),
            limit=poll_data.get('limit') if poll_data.get('limit') else None
        )
        
        # Validate limit if provided
        if poll.limit is not None and poll.limit < 1:
            user = update.effective_user
            message = translator.translate("invalid_limit_min", user)
            await update.message.reply_text(message)
            return
        
        # Get poll service and send the poll
        poll_service = context.bot_data.get('poll_service')
        if not poll_service:
            logger.error("Poll service not found in bot_data")
            user = update.effective_user
            message = translator.translate("poll_creation_failed", user)
            await update.message.reply_text(message)
            return
        
        # Send the poll
        await poll_service.send_poll(poll, update, context)
        logger.info(
            f"Poll created successfully from Web App in chat {update.effective_chat.id}")
        
        # Remove the keyboard (since we used ReplyKeyboardMarkup)
        try:
            await update.message.reply_text(
                translator.translate("poll_created_success", update.effective_user),
                reply_markup=ReplyKeyboardRemove()
            )
        except Exception as e:
            logger.debug(f"Could not remove keyboard: {e}")
            # Fallback: send success message without removing keyboard
            user = update.effective_user
            message = translator.translate("poll_created_success", user)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message
            )
        
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing Web App JSON data: {e}")
        user = update.effective_user
        message = translator.translate("poll_creation_failed", user)
        await update.message.reply_text(message)
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        user = update.effective_user
        message = translator.translate("invalid_poll_format", user)
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error creating poll from Web App: {e}", exc_info=True)
        try:
            user = update.effective_user
            message = translator.translate("poll_creation_failed", user)
            await update.message.reply_text(message)
        except:
            pass  # Avoid cascading errors


# Custom filter to catch Web App data messages
# Web App data can come as StatusUpdate or as regular messages with web_app_data attribute
class WebAppDataFilter(filters.MessageFilter):
    def filter(self, message):
        if message is None:
            return False
        return hasattr(message, 'web_app_data') and message.web_app_data is not None

# Handler for Web App data messages - use multiple filters to catch all cases
# Try StatusUpdate filter first, then custom filter, and also catch all messages to check
webapp_handler_status = MessageHandler(
    filters.StatusUpdate.WEB_APP_DATA,
    handle_webapp_data
)

webapp_handler_custom = MessageHandler(
    WebAppDataFilter(),
    handle_webapp_data
)

# Also add a catch-all handler that checks for web_app_data in any message
# This is a safety net to catch Web App data that might not match the other filters
async def catch_webapp_data_anywhere(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Catch Web App data from any message, regardless of filter."""
    if update.message:
        # Check if this message has web_app_data
        if hasattr(update.message, 'web_app_data') and update.message.web_app_data is not None:
            logger.info("*** CAUGHT WEB APP DATA IN CATCH-ALL HANDLER ***")
            logger.info(f"  Update ID: {update.update_id}")
            logger.info(f"  Chat ID: {update.effective_chat.id}")
            logger.info(f"  Web App data: {update.message.web_app_data.data[:200]}...")
            await handle_webapp_data(update, context)
            # Don't return anything - let python-telegram-bot handle the update consumption
    # If no web_app_data, don't do anything - let other handlers process it

webapp_handler_catchall = MessageHandler(filters.ALL, catch_webapp_data_anywhere)


