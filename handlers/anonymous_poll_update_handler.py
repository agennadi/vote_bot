import logging
from telegram.ext import ContextTypes
from telegram import Update

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def handle_anonymous_poll_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for Poll updates (for anonymous polls).
    Delegates all logic to PollService.
    """
    poll = update.poll
    logger.info("Poll update received for poll %s (voters: %s)",
                poll.id, poll.total_voter_count)

    poll_service = context.bot_data.get('poll_service')
    if not poll_service:
        logger.error("Poll service not found in bot_data")
        return

    # Let the service handle everything
    await poll_service.handle_anonymous_poll_update(poll, context)


