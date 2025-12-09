import logging
import os
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from models.poll import Poll
from services.poll_service import PollService
from utils.translations import translator

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def handle_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline queries for poll creation with a single form."""

    query = update.inline_query.query
    logger.info(
        f"Inline query received: '{query}' from user {update.effective_user.id}")

    # Always show the form interface - users can type their poll data or use examples
    await show_poll_form(update, context, query)


async def show_poll_form(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str = ""):
    """Show the poll creation form as inline query results."""

    logger.info(f"Showing poll form for query: '{query}'")
    results = []

    # Get Web App URL from environment or use default
    webapp_url = os.getenv("WEBAPP_URL", "https://your-domain.com/webapp/index.html")
    
    # Always show Web App form option first (most user-friendly)
    webapp_button = InlineKeyboardButton(
        text="📝 Create Poll with Form",
        web_app=WebAppInfo(url=webapp_url)
    )
    
    results.append(
        InlineQueryResultArticle(
            id="webapp_create_poll",
            title="📝 Create Poll with Form",
            description="Fill out a user-friendly form to create your poll",
            input_message_content=InputTextMessageContent(
                message_text="Creating poll..."
            ),
            reply_markup=InlineKeyboardMarkup([[webapp_button]])
        )
    )

    # If user has typed something, try to parse it and show preview
    if query.strip():
        poll_data = parse_poll_query(query)
        if poll_data:
            # Create trigger message that will auto-create the poll
            # Format: hidden command marker + human-readable text
            poll_command = f"CREATEPOLL:{query}"

            results.append(
                InlineQueryResultArticle(
                    id=f"create_poll_{update.inline_query.id}",
                    title="🗳️ Create Poll",
                    description=f"{poll_data['question'][:60]}",
                    input_message_content=InputTextMessageContent(
                        message_text=poll_command
                    )
                )
            )

    # Always show examples
    results.extend([
        InlineQueryResultArticle(
            id="poll_example_1",
            title="🍕 Food Preference Poll",
            description="What's your favorite food?|Pizza|Burger|Sushi",
            input_message_content=InputTextMessageContent(
                message_text="CREATEPOLL:What's your favorite food?|Pizza|Burger|Sushi|false|true"
            )
        ),
        InlineQueryResultArticle(
            id="poll_example_2",
            title="🎬 Movie Night Poll",
            description="Which movie should we watch?|Action|Comedy|Horror",
            input_message_content=InputTextMessageContent(
                message_text="CREATEPOLL:Which movie should we watch?|Action|Comedy|Horror|true|false|50"
            )
        ),
        InlineQueryResultArticle(
            id="poll_example_3",
            title="🎨 Color Preference Poll",
            description="What's your favorite color?|Red|Blue|Green|Yellow",
            input_message_content=InputTextMessageContent(
                message_text="CREATEPOLL:What's your favorite color?|Red|Blue|Green|Yellow|false|true|100"
            )
        ),
        InlineQueryResultArticle(
            id="poll_help",
            title="📝 How to Create Polls",
            description="Format: question|option1|option2|anonimity|forwarding|limit",
            input_message_content=InputTextMessageContent(
                message_text="""📝 **How to Create Polls**

Use this format: `question|option1|option2|option3|anonimity|forwarding|limit`

**Parameters:**
• **question**: Your poll question
• **option1, option2, etc.**: Poll options (minimum 2)
• **anonimity**: true/false (default: false)
• **forwarding**: true/false (default: true) 
• **limit**: max voters (optional, default: unlimited)

**Examples:**
• `What's your favorite food?|Pizza|Burger|Sushi|false|true`
• `Which movie should we watch?|Action|Comedy|Horror|true|false|50`
• `What's your favorite color?|Red|Blue|Green|Yellow|false|true|100`

Just type your poll data after @yourbot and select the result!""",
                parse_mode='Markdown'
            )
        )
    ])

    logger.info(f"Sending {len(results)} results to inline query")
    await update.inline_query.answer(results, cache_time=1)


def parse_poll_query(query: str) -> dict:
    """Parse the inline query to extract poll parameters."""

    parts = [part.strip() for part in query.split('|')]

    if len(parts) < 3:  # Need at least question + 2 options
        return None

    try:
        poll_data = {
            'question': parts[0],
            # All middle parts are options
            'options': parts[1:-3] if len(parts) > 5 else parts[1:],
            'anonimity': False,
            'forwarding': True,
            'limit': None
        }

        # Parse optional parameters from the end
        if len(parts) >= 5:
            # Check if last part is a number (limit)
            try:
                poll_data['limit'] = int(parts[-1])
                remaining_parts = parts[:-1]
            except ValueError:
                remaining_parts = parts

            # Parse anonimity and forwarding
            if len(remaining_parts) >= 4:
                poll_data['anonimity'] = remaining_parts[-2].lower() == 'true'
                poll_data['forwarding'] = remaining_parts[-1].lower() == 'true'
                poll_data['options'] = remaining_parts[1:-2]

        # Validate minimum options
        if len(poll_data['options']) < 2:
            return None

        return poll_data

    except Exception as e:
        logger.error(f"Error parsing poll query: {e}")
        return None


async def handle_chosen_inline_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle when user selects an inline query result."""
    chosen_result = update.chosen_inline_result
    logger.info(f"Chosen inline result: {chosen_result.result_id}")


async def handle_poll_creation_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detect and handle CREATEPOLL: messages to automatically create polls."""

    message_text = update.message.text

    if not message_text or not message_text.startswith("CREATEPOLL:"):
        return

    # Extract the poll query
    poll_query = message_text.replace("CREATEPOLL:", "").strip()
    logger.info(f"Poll creation triggered via inline query: {poll_query}")

    # Parse the poll data
    poll_data = parse_poll_query(poll_query)

    if not poll_data:
        user = update.effective_user
        message = translator.translate("invalid_poll_format", user)
        await update.message.reply_text(
            message,
            parse_mode='Markdown'
        )
        return

    try:
        # Create Poll object first
        poll = Poll(
            question=poll_data['question'],
            options=poll_data['options'],
            anonimity=poll_data['anonimity'],
            forwarding=poll_data['forwarding'],
            limit=poll_data['limit'] if poll_data['limit'] else None
        )

        # Get poll service and send the poll
        poll_service = context.bot_data.get('poll_service')
        if poll_service:
            await poll_service.send_poll(poll, update, context)
            logger.info(
                f"Poll created successfully from inline query in chat {update.effective_chat.id}")

            # Try to delete the CREATEPOLL message
            # Note: This usually fails for inline query results since they're sent by the user
            try:
                await update.message.delete()
                logger.debug("Successfully deleted CREATEPOLL trigger message")
            except BadRequest as e:
                # Expected: inline query messages are sent by users, not the bot
                logger.debug(
                    f"Cannot modify inline query result message (expected): {e}")
        else:
            logger.error("Poll service not found in bot_data")
            user = update.effective_user
            message = translator.translate("poll_creation_failed", user)
            await update.message.reply_text(message)

    except Exception as e:
        logger.error(f"Error creating poll from message: {e}", exc_info=True)
        try:
            user = update.effective_user
            message = translator.translate("poll_creation_failed", user)
            await update.message.reply_text(message)
        except:
            pass  # Avoid cascading errors
