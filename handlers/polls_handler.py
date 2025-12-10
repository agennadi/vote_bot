import logging
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.translations import translator

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def polls_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all polls created by the user with close/delete buttons"""
    
    poll_service = context.bot_data.get('poll_service')
    if not poll_service:
        await update.message.reply_text(
            translator.translate("error_service_unavailable", update.effective_user)
        )
        return
    
    user_id = update.effective_user.id
    user = update.effective_user
    
    # Get all user's polls
    polls = await poll_service.list_polls_by_user(user_id)
    
    if not polls:
        await update.message.reply_text(
            translator.translate("no_polls_created", user)
        )
        return
    
    # Send header message
    await update.message.reply_text(
        translator.translate("your_polls_header", user, count=len(polls))
    )
    
    # Send each poll with its buttons
    for poll in polls:
        # Create preview
        status = "🔴" if poll.closed else "🟢"
        limit_text = str(poll.limit) if poll.limit != sys.maxsize else "∞"
        
        # Truncate options if too many
        options_preview = ", ".join(poll.options[:3])
        if len(poll.options) > 3:
            options_preview += "..."
        
        preview = (
            f"{status} **{poll.question}**\n\n"
            f"📊 {translator.translate('poll_options', user)}: {options_preview}\n"
            f"👥 {translator.translate('poll_voters', user)}: {poll.voters_num}/{limit_text}\n"
            f"🔒 {translator.translate('anonymous' if poll.anonimity else 'public', user)} | "
            f"{translator.translate('protected' if not poll.forwarding else 'forwardable', user)}"
        )
        
        # Create buttons
        buttons = []
        if not poll.closed:
            buttons.append(InlineKeyboardButton(
                translator.translate("close_poll_button", user),
                callback_data=f"close_poll:{poll.id}"
            ))
        buttons.append(InlineKeyboardButton(
            translator.translate("delete_poll_button", user),
            callback_data=f"delete_poll:{poll.id}"
        ))
        
        keyboard = InlineKeyboardMarkup([buttons])
        
        await update.message.reply_text(
            preview,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )


async def handle_poll_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle close/delete button callbacks"""
    query = update.callback_query
    await query.answer()
    
    action, poll_id = query.data.split(":", 1)
    poll_service = context.bot_data.get('poll_service')
    user = update.effective_user
    
    if not poll_service:
        await query.edit_message_text(
            translator.translate("error_service_unavailable", user)
        )
        return
    
    if action == "close_poll":
        # Get poll from database
        poll = poll_service.poll_repository.get_poll_by_id(poll_id)
        
        if not poll:
            await query.edit_message_text(
                translator.translate("poll_not_found", user)
            )
            return
        
        if poll.closed:
            await query.edit_message_text(
                translator.translate("poll_already_closed", user)
            )
            return
        
        # Check if we have message_id and chat_id
        if not poll.message_id or not poll.chat_id:
            await query.edit_message_text(
                translator.translate("cannot_close_poll_no_message_id", user)
            )
            return
        
        # Try to get poll_data from bot_data, or create minimal version
        poll_data = context.bot_data.get(poll_id)
        if not poll_data:
            poll_data = {
                "poll_object": poll,
                "question": poll.question,
                "message_id": poll.message_id,
                "chat_id": poll.chat_id,
                "anonimity": poll.anonimity,
                "limit": poll.limit,
                "user": user
            }
        
        try:
            await poll_service.close_poll(poll, poll_data, context)
            await query.edit_message_text(
                translator.translate("poll_closed_success", user, question=poll.question)
            )
        except Exception as e:
            logger.error(f"Error closing poll {poll_id}: {e}")
            await query.edit_message_text(
                translator.translate("error_closing_poll", user)
            )
    
    elif action == "delete_poll":
        # Show confirmation dialog
        confirm_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    translator.translate("confirm_delete", user),
                    callback_data=f"confirm_delete:{poll_id}"
                ),
                InlineKeyboardButton(
                    translator.translate("cancel", user),
                    callback_data="cancel_delete"
                )
            ]
        ])
        await query.edit_message_text(
            translator.translate("confirm_delete_poll", user),
            reply_markup=confirm_keyboard
        )


async def handle_delete_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle delete confirmation"""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    
    if query.data == "cancel_delete":
        await query.edit_message_text(
            translator.translate("deletion_cancelled", user)
        )
        return
    
    _, poll_id = query.data.split(":", 1)
    poll_service = context.bot_data.get('poll_service')
    
    if not poll_service:
        await query.edit_message_text(
            translator.translate("error_service_unavailable", user)
        )
        return
    
    # Get poll for showing question
    poll = poll_service.poll_repository.get_poll_by_id(poll_id)
    
    if poll:
        try:
            await poll_service.delete_poll(poll)
            
            # Remove from bot_data if exists
            if poll_id in context.bot_data:
                del context.bot_data[poll_id]
            
            await query.edit_message_text(
                translator.translate("poll_deleted_success", user, question=poll.question)
            )
        except Exception as e:
            logger.error(f"Error deleting poll {poll_id}: {e}")
            await query.edit_message_text(
                translator.translate("error_deleting_poll", user)
            )
    else:
        await query.edit_message_text(
            translator.translate("poll_not_found", user)
        )
