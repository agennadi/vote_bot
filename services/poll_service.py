import logging
from telegram import Update
from telegram.ext import ContextTypes
from database.poll_repository import PollRepository
from models.poll import Poll

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

class PollService:
    def __init__(self, poll_repository: PollRepository):
        self.poll_repository = poll_repository
    

    async def send_poll(self, poll: Poll, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Sends a new poll"""     

        message = await context.bot.send_poll(
            chat_id=update.effective_chat.id,
            question=poll.question,
            options=poll.options,
            is_anonymous=poll.anonimity,
            allows_multiple_answers=True,
            protect_content=poll.forwarding
        )

        # Update poll with Telegram ID
        poll.id = message.poll.id

        # Extract user info
        chat_id = update.effective_chat.id
        user_id = update.message.from_user.id

        # Save some info about the poll the bot_data for later use in record_poll_answer
        payload = {
            message.poll.id: {
                "question": poll.question,
                "options": poll.options,
                "message_id": message.message_id,
                "chat_id": chat_id,
                "answer_num": 0,
                "votes": {}
            }
        }
        context.bot_data.update(payload)
        logger.info("Poll with id %s was created", message.poll.id)
        logger.info("Information about the poll: %s", message.poll)

        # Database logic
        self.poll_repository.create_poll(poll, user_id, chat_id)
        
        logger.info("Poll %s created and sent successfully", poll.id)        


    async def record_poll_answer(self, poll: Poll, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Tracks users' poll responses and closes poll if the limit is reached."""

        answer = update.poll_answer
        logger.info("Poll answer received: %s", answer)        
        poll_id = answer.poll_id
        if poll_id not in context.bot_data:
            return  # Poll not found (probably bot restarted)

        poll_data = context.bot_data[poll_id]
        user_id = answer.user.id  # User who voted    
        selected_options = answer.option_ids

        logger.info("Answer: %s", answer)
        logger.info("Selected options: %s", selected_options)
         
        # Update bot_data
        poll_data["answer_num"] += 1
        poll_data["votes"][str(user_id)] = selected_options

        # Update poll instance        
        poll.votes[user_id] = selected_options
        poll.answer_num += 1

        logger.info("Context bot data: %s", context.bot_data[poll_id])

        # Check if poll should close after the limit of answers has been reached
        if poll_data["answer_num"] >= poll.limit:
            await poll._close_poll(poll, poll_data, context)            
            poll.closed = True

        # Save to database
        self.poll_repository.record_poll_answer(poll, user_id, selected_options, poll.closed)


    async def retract_vote(self, poll: Poll, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Removes the votes when user clicks 'retract vote'"""
        
        answer = update.poll_answer
        poll_id = answer.poll_id      
        user_id = answer.user.id  # User who voted    
        self.poll_repository.remove_vote(poll_id, user_id)


    async def _close_poll(self, poll: Poll, poll_data: dict, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Closes a poll when limit is reached"""
        
        await context.bot.stop_poll(poll_data["chat_id"], poll_data["message_id"])
        await context.bot.send_message(
            poll_data["chat_id"],
            f"The poll '{poll_data['question']}' has closed after reaching the limit of {poll.limit} votes."
        )
        poll.closed = True            