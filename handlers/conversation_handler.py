import logging
from telegram.ext import CommandHandler, MessageHandler, filters, ConversationHandler
from models.poll import Poll
from states import ANONIMITY, FORWARDING, LIMIT, QUESTION, OPTIONS
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from services.poll_service import PollService
from database.poll_repository import PollRepository

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 1: Ask for poll type (public or anonymous)."""

    reply_keyboard = [["Public", "Anonymous"]]
    context.user_data["poll"] = Poll()
    logger.info(repr(context.user_data["poll"]))

    await update.message.reply_text(
        "Hi, let's create a custom poll! First, select the poll type:",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder="Should the poll be public or anonymous?"),
    )

    return ANONIMITY


async def set_anonimity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 2: Store poll anonimity and ask about forwarding."""

    poll = context.user_data["poll"]
    poll.anonimity = True if update.message.text == 'Anonymous' else False
    logger.info("Poll anonimity: %s", poll.anonimity)

    reply_keyboard = [["Yes", "No"]]
    await update.message.reply_text(
        "Do you allow forwarding the poll to other chats?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder="Do you allow poll forwarding?"),
    )

    return FORWARDING


async def set_forwarding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 3: Store the forwarding setting and ask about vote limits."""

    poll = context.user_data["poll"]
    poll.forwarding = False if update.message.text == 'Yes' else True
    logger.info("Disable poll forwarding: %s", poll.forwarding)

    await update.message.reply_text(
        "Send the max number of voters. If you don't want to set a limit, send /skip",
        reply_markup=ReplyKeyboardRemove(),
    )
    return LIMIT


async def set_limit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 4: Store the vote limits."""

    poll = context.user_data["poll"]
    poll.limit = int(update.message.text)
    logger.info("Poll limit: %s", poll.limit)

    return await ask_for_question(update, context)


async def skip_limit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 4: Skip setting the vote limits."""

    logger.info("User didn't set a vote limit")

    return await ask_for_question(update, context)


async def ask_for_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask for a poll question."""

    await update.message.reply_text("Now, send me the poll question.")

    return QUESTION


async def set_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 5: Store the poll question and ask for an option."""

    poll = context.user_data["poll"]
    poll.question = update.message.text
    logger.info("Poll question is %s", poll.question)

    await update.message.reply_text("Now, send me a poll option.")

    return OPTIONS


async def set_option(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 6: Store the poll option and ask for another one."""

    poll = context.user_data["poll"]
    poll_option = update.message.text
    poll.options.append(poll_option)
    logger.info("Poll option is '%s'", poll_option)
    logger.info("All poll options: %s", poll.options)

    if len(poll.options) < 2:
        await update.message.reply_text("Please enter another option - polls must have at least 2 options.")
    else:
        await update.message.reply_text("Send me another option or type /done if finished.")

    return OPTIONS  # Stay in this step until the user is done


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> input:
    """Final Step: Confirm poll creation and end conversation."""

    poll = context.user_data["poll"]
    poll_service = context.bot_data['poll_service']

    try:
        await poll_service.send_poll(poll, update, context)
        logger.info("Poll sent successfully")
        await update.message.reply_text("You are all set! ✅ Your poll has been created.")
    except BadRequest as e:
        logger.error("Failed to send poll: %s", e)
        await update.message.reply_text("❌ Failed to create the poll. Please check your input and try again.")
    return ConversationHandler.END


async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Notifies the user when the bot doesn't recognize their input."""
    await update.message.reply_text("Sorry, I didn't understand that. Please try again.")


conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        ANONIMITY: [MessageHandler(filters.Regex("^(Public|Anonymous)$"), set_anonimity)],
        FORWARDING: [MessageHandler(filters.Regex("^(Yes|No)$"), set_forwarding)],
        LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_limit), CommandHandler("skip", skip_limit)],
        QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_question)],
        OPTIONS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, set_option),
            CommandHandler("done", end),  # User sends /done to finish
        ],
    },
    fallbacks=[MessageHandler(
        filters.TEXT & ~filters.COMMAND, fallback), CommandHandler("start", start)],
)
