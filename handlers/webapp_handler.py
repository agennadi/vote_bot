import logging
import json
from telegram import Update, ReplyKeyboardRemove, Message, Chat, User
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
    
    logger.info("Handling Web App data")
    
    try:
        # Parse the JSON data from the Web App
        poll_data = json.loads(update.message.web_app_data.data)
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
        
        # Check if target chat_id is provided (for group chats)
        target_chat_id = poll_data.get("chat_id")
        if target_chat_id:
            # Send poll directly to target chat using target_chat_id parameter
            await poll_service.send_poll(poll, update, context, target_chat_id=target_chat_id)
            logger.info(f"Poll created in target chat {target_chat_id} from Web App")
        else:
            # No target chat_id - send to current chat
            await poll_service.send_poll(poll, update, context)
            logger.info(f"Poll created successfully from Web App in chat {update.effective_chat.id}")
        
        # Remove the keyboard (since we used ReplyKeyboardMarkup)
        try:
            await update.message.reply_text(
                translator.translate("poll_created_success", update.effective_user),
                reply_markup=ReplyKeyboardRemove()
            )
        except Exception as e:
            logger.debug(f"Could not remove keyboard: {e}")
        
        # Delete the Web App data message to keep chat clean
        try:
            await update.message.delete()
        except:
            pass
            
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON from Web App: {e}")
        user = update.effective_user
        message = translator.translate("error_occurred", user)
        await update.message.reply_text(message)
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        user = update.effective_user
        message = translator.translate("error_occurred", user)
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error creating poll from Web App: {e}", exc_info=True)
        user = update.effective_user
        message = translator.translate("error_occurred", user)
        await update.message.reply_text(message)


# Handle Web App data
webapp_handler_status = MessageHandler(
    filters.StatusUpdate.WEB_APP_DATA,
    handle_webapp_data
)
