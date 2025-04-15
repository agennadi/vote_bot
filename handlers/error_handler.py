from telegram.error import TelegramError, BadRequest, TimedOut, NetworkError
from telegram import Update
from telegram.ext import BaseHandler, ContextTypes
import logging

logger = logging.getLogger(__name__)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception while handling an update:", exc_info=context.error)
    try:
        if isinstance(update, Update) and update.effective_chat:
            chat_id = update.effective_chat.id
            if isinstance(context.error, BadRequest):
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="Bad request. Please check your input and try again.",
                )
            elif isinstance(context.error, TimedOut):
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="Request timed out. Please try again.",
                )
            elif isinstance(context.error, NetworkError):
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="Network error. The bot might be temporarily offline.",
                )                
            elif isinstance(context.error, TelegramError):
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="A Telegram error occurred. Please try again later.",
                )
            else:
                # Generic fallback for unknown errors
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="An unexpected error occurred. Please try again later.",
                )            
    except Exception as send_error:
        logger.error("Failed to send error message", exc_info=send_error)   