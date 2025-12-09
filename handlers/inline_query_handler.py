#!/usr/bin/env python3
import logging
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from telegram.error import BadRequest
import os
from utils.translations import translator

logger = logging.getLogger(__name__)


async def handle_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline queries - triggered when user types @botname in any chat"""
    query = update.inline_query.query.strip()
    user = update.inline_query.from_user
    
    logger.info(f"Inline query received: '{query}' from user {user.id}")
    
    # Show poll creation form
    await show_poll_form(update, context, query)


async def show_poll_form(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
    """Show inline results with web app form option"""
    user = update.inline_query.from_user
    logger.info(f"Showing poll form for query: '{query}'")
    
    results = [
        InlineQueryResultArticle(
            id="webapp_create_poll",
            title="📝 Create Poll with Form",
            description="Fill out a form to create your poll",
            input_message_content=InputTextMessageContent("📝 Check your private chat with the bot to fill out the poll form. The poll will appear in this group!"),
            thumbnail_url="https://img.icons8.com/fluency/48/000000/create-new.png"
        )
    ]
    
    logger.info(f"Sending {len(results)} results to inline query")
    await update.inline_query.answer(results, cache_time=1)


async def handle_chosen_inline_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle when user selects an inline result"""
    result = update.chosen_inline_result
    
    logger.info("Handling chosen inline result")
    logger.info(f"Chosen inline result: {result.result_id}")
    logger.info(f"Chosen result details: from_user={result.from_user.id if result.from_user else None}, query={result.query}, inline_message_id={result.inline_message_id}")
    
    if result.result_id == "webapp_create_poll":
        logger.info("Web App form result selected - trigger message will be handled by handle_poll_creation_message")


async def handle_poll_creation_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detect and handle Web App form trigger messages."""
    
    message_text = update.message.text
    logger.info(f"handle_poll_creation_message called with text: '{message_text}' from chat {update.effective_chat.id}")
    
    if not message_text:
        logger.debug("No message text, returning")
        return
    
    # Handle Web App form trigger
    if "Check your private chat with the bot" in message_text:
        logger.info(f"Web App form trigger detected in message: '{message_text}'")
        
        # Use KeyboardButton with WebApp (tg.sendData works!)
        webapp_url = os.getenv("WEBAPP_URL", "")
        logger.info(f"Web App URL from env: {webapp_url}")
        
        # Check if URL is configured
        if not webapp_url:
            logger.warning("WEBAPP_URL not configured")
            user = update.effective_user
            error_msg = translator.translate("error_occurred", user)
            await update.message.reply_text(
                f"{error_msg}\n\n⚠️ WEBAPP_URL not configured. Set it to your ngrok URL."
            )
            try:
                await update.message.delete()
            except:
                pass
            return
        
        chat_id = update.effective_chat.id
        is_group = update.effective_chat.type in ["group", "supergroup"]
        
        if is_group:
            # Send button to private chat with group chat_id in URL
            from urllib.parse import urlencode
            webapp_url_with_chat = f"{webapp_url}?{urlencode({'chat_id': chat_id})}"
            webapp_button = KeyboardButton(
                text=translator.translate("webapp_button_title", update.effective_user),
                web_app=WebAppInfo(url=webapp_url_with_chat)
            )
            keyboard = ReplyKeyboardMarkup([[webapp_button]], resize_keyboard=True, one_time_keyboard=False)
            
            try:
                await context.bot.send_message(
                    chat_id=update.effective_user.id,
                    text=translator.translate("webapp_click_button_instructions", update.effective_user),
                    reply_markup=keyboard
                )
                logger.info(f"Sent Web App button to private chat for group {chat_id}")
                
                # Delete the trigger message
                try:
                    await update.message.delete()
                    logger.debug("Successfully deleted trigger message")
                except BadRequest as e:
                    logger.debug(f"Cannot delete trigger message (may not have permission): {e}")
                except Exception as e:
                    logger.debug(f"Error deleting trigger message: {e}")
            except Exception as e:
                logger.error(f"Could not send to private chat: {e}", exc_info=True)
        else:
            # Private chat - send button directly
            webapp_button = KeyboardButton(
                text=translator.translate("webapp_button_title", update.effective_user),
                web_app=WebAppInfo(url=webapp_url)
            )
            keyboard = ReplyKeyboardMarkup([[webapp_button]], resize_keyboard=True, one_time_keyboard=False)
            
            try:
                await update.message.reply_text(
                    translator.translate("webapp_click_button_instructions", update.effective_user),
                    reply_markup=keyboard
                )
                logger.info(f"Sent Web App button in private chat")
                
                # Delete the trigger message
                try:
                    await update.message.delete()
                    logger.debug("Successfully deleted trigger message")
                except BadRequest as e:
                    logger.debug(f"Cannot delete trigger message: {e}")
                except Exception as e:
                    logger.debug(f"Error deleting trigger message: {e}")
            except Exception as e:
                logger.error(f"Could not send Web App button: {e}", exc_info=True)
        
        return
    