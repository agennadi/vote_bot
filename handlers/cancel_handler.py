from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler
import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the conversation."""
    logger.info("User canceled the poll creation")
    
    if "poll" in context.user_data:
        del context.user_data["poll"]
        await update.message.reply_text("Poll creation canceled.")
    else:
        await update.message.reply_text("There is nothing to cancel yet. Use /start to create a new poll.")
    return ConversationHandler.END


cancel_handler = CommandHandler("cancel", cancel)  