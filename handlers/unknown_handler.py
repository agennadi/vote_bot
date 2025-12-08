from telegram.ext import MessageHandler
from telegram import Update
from telegram.ext import ContextTypes, filters
from utils.translations import translator

async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = translator.translate("unknown_command", user)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)

unknown_handler = MessageHandler(filters.COMMAND, unknown_message)