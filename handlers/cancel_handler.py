from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler
from utils.translations import translator
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
    
    user = update.effective_user
    if "poll" in context.user_data:
        del context.user_data["poll"]
        message = translator.translate("poll_cancelled", user)
        await update.message.reply_text(message)
    else:
        message = translator.translate("nothing_to_cancel", user)
        await update.message.reply_text(message)
    return ConversationHandler.END


cancel_handler = CommandHandler("cancel", cancel)  