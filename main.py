import logging
from telegram import Update
from telegram.ext import filters, ApplicationBuilder, ContextTypes, PollAnswerHandler, PollHandler, CallbackContext, InlineQueryHandler
import os
from dotenv import load_dotenv
from handlers.error_handler import error_handler
from handlers.help_handler import help_handler
from handlers.unknown_handler import unknown_handler
from handlers.cancel_handler import cancel_handler
from handlers.conversation_handler import conv_handler
from handlers.poll_answer_handler import handle_poll_answer
from database.poll_repository import PollRepository
from services.poll_service import PollService


load_dotenv()

telegram_token = os.getenv("TELEGRAM_TOKEN")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def handle_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass


if __name__ == '__main__':
    application = ApplicationBuilder().token(telegram_token).build()

    poll_repository = PollRepository("polls.db")
    poll_service = PollService(poll_repository)

    application.bot_data["poll_service"] = poll_service


    inline_query_handler = InlineQueryHandler(handle_inline_query)

    application.add_error_handler(error_handler)
    application.add_handler(conv_handler)
    application.add_handler(inline_query_handler)
    application.add_handler(cancel_handler)
    application.add_handler(help_handler)
    application.add_handler(PollAnswerHandler(handle_poll_answer))
    application.add_handler(unknown_handler)
    # application.add_handler(CommandHandler("poll_results", poll.get_poll_results))'''

    application.run_polling(allowed_updates=Update.ALL_TYPES)
