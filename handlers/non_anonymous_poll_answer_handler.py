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


async def handle_non_anonymous_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for poll answer updates (non-anonymous polls).
    Delegates to existing PollService methods.
    """
    poll_answer = update.poll_answer
    logger.info("Poll answer received for poll %s from user %s",
                poll_answer.poll_id, poll_answer.user.id)

    poll_service = context.bot_data.get('poll_service')
    if not poll_service:
        logger.error("Poll service not found in bot_data")
        return

    # Get poll from user_data (conversation handler creates it there)
    poll = context.user_data.get("poll")

    # Use existing service methods
    if not poll_answer.option_ids:
        # User retracted vote
        await poll_service.retract_vote(poll, update, context)
    else:
        # User voted
        await poll_service.record_poll_answer(poll, update, context)

