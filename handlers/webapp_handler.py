import logging
import json
from telegram import Update
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


async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle data submitted from Web App form."""
    
    if not update.message or not update.message.web_app_data:
        return
    
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
        
        # Try to delete the Web App trigger message
        try:
            await update.message.delete()
            logger.debug("Successfully deleted Web App trigger message")
        except BadRequest as e:
            # Expected: may not be able to delete in some cases
            logger.debug(f"Cannot delete Web App message (expected): {e}")
        
        # Send success message
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


# Handler for Web App data messages
webapp_handler = MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data)


