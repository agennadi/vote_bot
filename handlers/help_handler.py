from telegram.ext import CommandHandler
from telegram import Update
from telegram.ext import ContextTypes

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = ("This bot creates customizable polls. You can set poll visibility, duration, and vote limits.\n\n" \
                "- Use /start to create a poll here, then forward it to chats.\n\n" \
                "- If you want to disable poll forwarding, add the bot to the group of people who are allowed to vote and create the poll inside the group.\n\n" \
                "- Send /polls to manage your existing polls.")

    await update.message.reply_text(help_text)

help_handler = CommandHandler("help", help_command)