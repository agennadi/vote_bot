from telegram.ext import CommandHandler
from telegram import Update
from telegram.ext import ContextTypes
from utils.translations import translator

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    help_text = translator.translate("help_text", user)
    await update.message.reply_text(help_text)

help_handler = CommandHandler("help", help_command)