import logging
from telegram.ext import ContextTypes
from telegram import Update


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Listens to poll answer updates"""
    poll_answer = update.poll_answer    
    logger.info("Poll answer received: %s", poll_answer)
    selected_option_ids = poll_answer.option_ids  # This will be [] if user retracted vote

    poll = context.user_data.get("poll")
    poll_service = context.bot_data['poll_service']

    if not selected_option_ids:
        await poll_service.retract_vote(poll, update, context)
    else:
        await poll_service.record_poll_answer(poll, update, context)
    