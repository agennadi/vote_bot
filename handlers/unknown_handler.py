from telegram.ext import MessageHandler
from telegram import Update
from telegram.ext import ContextTypes, filters

async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")

unknown_handler = MessageHandler(filters.COMMAND, unknown_message)