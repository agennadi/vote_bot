#!/usr/bin/env python3
import logging
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from urllib.parse import urlencode
import os
from utils.translations import translator

logger = logging.getLogger(__name__)


async def form_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /form command - sends Web App button directly
    Same functionality as inline query "Create Poll with Form"
    """
    
    # Get WEBAPP_URL from environment
    webapp_url = os.getenv("WEBAPP_URL", "")
    
    # Check if URL is configured
    if not webapp_url:
        logger.warning("WEBAPP_URL not configured for /form command")
        user = update.effective_user
        error_msg = translator.translate("error_occurred", user)
        await update.message.reply_text(
            f"{error_msg}\n\n⚠️ WEBAPP_URL not configured. Please set it up first."
        )
        return
    
    chat_id = update.effective_chat.id
    is_group = update.effective_chat.type in ["group", "supergroup"]
    
    if is_group:
        # For group chats: send button to private chat with group chat_id in URL
        webapp_url_with_chat = f"{webapp_url}?{urlencode({'chat_id': chat_id})}"
        webapp_button = KeyboardButton(
            text="📝 Open Poll Creation Form",
            web_app=WebAppInfo(url=webapp_url_with_chat)
        )
        keyboard = ReplyKeyboardMarkup([[webapp_button]], resize_keyboard=True, one_time_keyboard=False)
        
        try:
            # Send to user's private chat
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text="👇 **CLICK THE BUTTON BELOW** 👇\n\n📝 Open the form to create your poll.\n\n⚠️ Don't type anything - just tap the button!",
                reply_markup=keyboard
            )
            logger.info(f"Sent Web App button to private chat for group {chat_id} via /form")
            
            # Confirm in the group
            await update.message.reply_text(
                "✅ Check your private chat with me to open the poll creation form!"
            )
            
        except BadRequest as e:
            # User hasn't started the bot yet
            logger.warning(f"Could not send to private chat: {e}")
            await update.message.reply_text(
                "⚠️ Please start a private chat with me first!\n\n"
                "Then use /form again."
            )
        except Exception as e:
            logger.error(f"Could not send to private chat: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Failed to send form. Please try the inline method."
            )
    else:
        # Private chat - send button directly
        webapp_button = KeyboardButton(
            text="📝 Open Poll Creation Form",
            web_app=WebAppInfo(url=webapp_url)
        )
        keyboard = ReplyKeyboardMarkup([[webapp_button]], resize_keyboard=True, one_time_keyboard=False)
        
        try:
            await update.message.reply_text(
                "👇 **CLICK THE BUTTON BELOW** 👇\n\n📝 Open the form to create your poll.\n\n⚠️ Don't type anything - just tap the button!",
                reply_markup=keyboard
            )
            logger.info(f"Sent Web App button in private chat via /form")
        except Exception as e:
            logger.error(f"Could not send Web App button: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Failed to send form. Please try again."
            )
