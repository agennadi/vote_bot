import logging
from telegram.ext import CommandHandler, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
from models.poll import Poll
from states import ANONIMITY, FORWARDING, LIMIT, QUESTION, OPTIONS
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils.translations import translator

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 1: Ask for poll type (public or anonymous)."""

    reply_keyboard = [[InlineKeyboardButton("Public", callback_data="Public"), InlineKeyboardButton(
        "Anonymous", callback_data="Anonymous")]]
    context.user_data["poll"] = Poll()
    logger.info(repr(context.user_data["poll"]))

    # Get user's language and translate the message
    user = update.effective_user
    message = translator.translate("start_private", user)

    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(reply_keyboard),
    )

    return ANONIMITY


async def poll_type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 2: Store poll anonimity and ask about forwarding."""
    query = update.callback_query
    await query.answer()
    poll = context.user_data["poll"]
    poll.anonimity = True if query.data == "Anonymous" else False
    logger.info("Poll anonimity: %s", poll.anonimity)

    user = update.effective_user
    reply_keyboard = [[InlineKeyboardButton(
        "Yes", callback_data="Yes"), InlineKeyboardButton("No", callback_data="No")]]
    message = translator.translate("poll_forwarding_prompt", user)
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(reply_keyboard)
    )
    return FORWARDING


async def forwarding_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 3: Store the forwarding setting and ask about vote limits."""
    query = update.callback_query
    await query.answer()
    poll = context.user_data["poll"]
    poll.forwarding = False if query.data == "Yes" else True
    logger.info("Disable poll forwarding: %s", poll.forwarding)

    user = update.effective_user
    message = translator.translate("poll_limit_prompt", user)
    await query.edit_message_text(message)
    return LIMIT


async def set_limit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 4: Store the vote limits."""

    try:
        limit_value = int(update.message.text)

        # Validate that limit is at least 1
        if limit_value < 1:
            user = update.effective_user
            message = translator.translate("invalid_limit_min", user)
            await update.message.reply_text(message)
            return LIMIT  # Stay in LIMIT state to ask again

        poll = context.user_data["poll"]
        poll.limit = limit_value
        logger.info("Poll limit: %s", poll.limit)

        return await ask_for_question(update, context)
    except ValueError:
        # If conversion to int fails, show invalid number message
        user = update.effective_user
        message = translator.translate("invalid_number", user)
        await update.message.reply_text(message)
        return LIMIT  # Stay in LIMIT state to ask again


async def skip_limit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 4: Skip setting the vote limits."""

    logger.info("User didn't set a vote limit")

    return await ask_for_question(update, context)


async def ask_for_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask for a poll question."""

    user = update.effective_user
    message = translator.translate("poll_question_prompt", user)
    await update.message.reply_text(message)

    return QUESTION


async def set_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 5: Store the poll question and ask for an option."""

    poll = context.user_data["poll"]
    poll.question = update.message.text
    logger.info("Poll question is %s", poll.question)

    user = update.effective_user
    message = translator.translate("poll_option_prompt", user)
    await update.message.reply_text(message)

    return OPTIONS


async def set_option(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 6: Store the poll option and ask for another one."""

    poll = context.user_data["poll"]
    poll_option = update.message.text
    poll.options.append(poll_option)
    logger.info("Poll option is '%s'", poll_option)
    logger.info("All poll options: %s", poll.options)

    user = update.effective_user
    if len(poll.options) < 2:
        message = translator.translate("poll_min_options_required", user)
        await update.message.reply_text(message)
    else:
        message = translator.translate("poll_options_continue", user)
        await update.message.reply_text(message)

    return OPTIONS  # Stay in this step until the user is done


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> input:
    """Final Step: Confirm poll creation and end conversation."""

    poll = context.user_data["poll"]
    poll_service = context.bot_data['poll_service']
    user = update.effective_user

    try:
        await poll_service.send_poll(poll, update, context)
        logger.info("Poll sent successfully")
        message = translator.translate("poll_created_success", user)
        await update.message.reply_text(message)
    except BadRequest as e:
        logger.error("Failed to send poll: %s", e)
        message = translator.translate("poll_creation_failed", user)
        await update.message.reply_text(message)
    return ConversationHandler.END


async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Notifies the user when the bot doesn't recognize their input."""
    user = update.effective_user
    message = translator.translate("error_occurred", user)
    await update.message.reply_text(message)


conv_handler = ConversationHandler(
    entry_points=[CommandHandler(
        "start", start, filters=filters.ChatType.PRIVATE)],
    states={
        ANONIMITY: [CallbackQueryHandler(poll_type_selected)],
        FORWARDING: [CallbackQueryHandler(forwarding_selected)],
        LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_limit), CommandHandler("skip", skip_limit)],
        QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_question)],
        OPTIONS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, set_option),
            CommandHandler("done", end),
        ],
    },
    fallbacks=[MessageHandler(
        filters.TEXT & ~filters.COMMAND, fallback), CommandHandler("start", start, filters=filters.ChatType.PRIVATE)],
)
