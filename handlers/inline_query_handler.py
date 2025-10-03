import logging
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from models.poll import Poll
from services.poll_service import PollService

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

    # If user has typed something, try to parse it and show preview
    if query.strip():
        poll_data = parse_poll_query(query)
        if poll_data:
            # Show preview of the poll that will be created
            preview_text = f"""
🗳️ **Poll Preview**

**Question:** {poll_data['question']}
**Options:** {', '.join(poll_data['options'])}
**Anonymous:** {'Yes' if poll_data['anonimity'] else 'No'}
**Forwarding:** {'Allowed' if poll_data['forwarding'] else 'Disabled'}
**Vote Limit:** {poll_data['limit'] if poll_data['limit'] else 'Unlimited'}

*Click to create this poll in the chat.*
            """

            results.append(
                InlineQueryResultArticle(
                    id=f"create_poll_{update.inline_query.id}",
                    title="🗳️ Create Poll",
                    description=f"Question: {poll_data['question'][:50]}...",
                    input_message_content=InputTextMessageContent(
                        message_text=preview_text,
                        parse_mode='Markdown'
                    )
                )
            )

            # Store the poll data for when it's actually sent
            context.bot_data[f"pending_poll_{update.inline_query.id}"] = poll_data

    # Always show examples
    results.extend([
        InlineQueryResultArticle(
            id="poll_example_1",
            title="🍕 Food Preference Poll",
            description="What's your favorite food?|Pizza|Burger|Sushi|false|true",
            input_message_content=InputTextMessageContent(
                message_text="What's your favorite food?|Pizza|Burger|Sushi|false|true"
            )
        ),
        InlineQueryResultArticle(
            id="poll_example_2",
            title="🎬 Movie Night Poll",
            description="Which movie should we watch?|Action|Comedy|Horror|true|false|50",
            input_message_content=InputTextMessageContent(
                message_text="Which movie should we watch?|Action|Comedy|Horror|true|false|50"
            )
        ),
        InlineQueryResultArticle(
            id="poll_example_3",
            title="🎨 Color Preference Poll",
            description="What's your favorite color?|Red|Blue|Green|Yellow|false|true|100",
            input_message_content=InputTextMessageContent(
                message_text="What's your favorite color?|Red|Blue|Green|Yellow|false|true|100"
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

    # Check if this is a poll creation result
    if chosen_result.result_id.startswith("create_poll_"):
        query_id = chosen_result.result_id.replace("create_poll_", "")
        poll_data = context.bot_data.get(f"pending_poll_{query_id}")

        if poll_data:
            try:
                # Create Poll object
                poll = Poll(
                    question=poll_data['question'],
                    options=poll_data['options'],
                    anonimity=poll_data['anonimity'],
                    forwarding=poll_data['forwarding'],
                    limit=poll_data['limit'] if poll_data['limit'] else None
                )

                # Get poll service
                poll_service = context.bot_data.get('poll_service')
                if poll_service:
                    # Create a mock update for the poll service
                    mock_update = Update(
                        update_id=update.update_id,
                        message=update.message,
                        effective_chat=update.effective_chat,
                        effective_user=update.effective_user
                    )

                    # Send the actual poll
                    await poll_service.send_poll(poll, mock_update, context)

                    # Clean up
                    del context.bot_data[f"pending_poll_{query_id}"]

            except Exception as e:
                logger.error(f"Error sending poll from inline result: {e}")
                await context.bot.send_message(
                    update.effective_chat.id,
                    "❌ Failed to create the poll. Please try again."
                )

    # Handle example selections - parse the example and create poll
    elif chosen_result.result_id.startswith("poll_example_"):
        try:
            # The example text is in the input_message_content
            example_text = chosen_result.query

            # Parse the example
            poll_data = parse_poll_query(example_text)
            if poll_data:
                # Create Poll object
                poll = Poll(
                    question=poll_data['question'],
                    options=poll_data['options'],
                    anonimity=poll_data['anonimity'],
                    forwarding=poll_data['forwarding'],
                    limit=poll_data['limit'] if poll_data['limit'] else None
                )

                # Get poll service
                poll_service = context.bot_data.get('poll_service')
                if poll_service:
                    # Create a mock update for the poll service
                    mock_update = Update(
                        update_id=update.update_id,
                        message=update.message,
                        effective_chat=update.effective_chat,
                        effective_user=update.effective_user
                    )

                    # Send the actual poll
                    await poll_service.send_poll(poll, mock_update, context)

        except Exception as e:
            logger.error(f"Error creating poll from example: {e}")
            await context.bot.send_message(
                update.effective_chat.id,
                "❌ Failed to create the poll. Please try again."
            )
