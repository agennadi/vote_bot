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

        # If there's a message (from inline query trigger), reply to it for context
        reply_to_message_id = update.message.message_id if update.message else None

        message = await context.bot.send_poll(
            chat_id=update.effective_chat.id,
            question=poll.question,
            options=poll.options,
            is_anonymous=poll.anonimity,
            allows_multiple_answers=True,
            protect_content=poll.forwarding,
            reply_to_message_id=reply_to_message_id
        )

        # Update poll with Telegram ID
        poll.id = message.poll.id

        # Extract user info
        chat_id = update.effective_chat.id
        user_id = update.message.from_user.id

        # Save some info about the poll the bot_data for later use in record_poll_answer
        payload = {
            message.poll.id: {
                "poll_object": poll,  # Store the actual Poll object!
                "question": poll.question,
                "options": poll.options,
                "message_id": message.message_id,
                "chat_id": chat_id,
                "answer_num": 0,
                "votes": {},
                "anonimity": poll.anonimity,
                "forwarding": poll.forwarding,
                "limit": poll.limit
            }
        }
        context.bot_data.update(payload)
        logger.info("Poll with id %s was created", message.poll.id)
        logger.info("Information about the poll: %s", message.poll)

        # Database logic
        self.poll_repository.create_poll(poll, user_id, chat_id)

        logger.info("Poll %s created and sent successfully", poll.id)

    async def handle_anonymous_poll_update(self, poll, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle Poll update for anonymous polls.
        Extracts vote counts and persists to database.
        """
        poll_id = poll.id

        # Extract vote counts from Poll object
        vote_counts = {}
        for i, option in enumerate(poll.options):
            vote_counts[i] = option.voter_count

        logger.info("Poll %s update - vote counts: %s, total voters: %s",
                    poll_id, vote_counts, poll.total_voter_count)

        # Check if this is our poll
        if poll_id not in context.bot_data:
            # Try to load from database
            db_poll = self.poll_repository.get_poll_by_id(poll_id)
            if not db_poll:
                logger.warning("Received update for unknown poll: %s", poll_id)
                return

        # Update database if anonymous poll
        if poll_id in context.bot_data:
            poll_data = context.bot_data[poll_id]
            # Get our original Poll object!
            our_poll = poll_data.get("poll_object")

            if poll_data.get("anonimity"):  # If poll is anonymous
                self.poll_repository.update_anonymous_poll_counts(
                    poll_id, vote_counts, poll.total_voter_count)
                logger.info(
                    "Updated vote counts for anonymous poll %s in database", poll_id)

            # Update our poll object with current voter count
            if our_poll:
                our_poll.answer_num = poll.total_voter_count
                # Update bot_data to keep it in sync
                poll_data["answer_num"] = poll.total_voter_count

            # Check if we need to close the poll based on vote limit
            if not poll.is_closed and our_poll:
                if our_poll.limit and our_poll.answer_num >= our_poll.limit:
                    logger.info(
                        "Poll %s reached limit of %s voters, closing...", poll_id, our_poll.limit)
                    await self.close_poll(our_poll, poll_data, context)

    async def record_poll_answer(self, poll: Poll, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Tracks users' poll responses and closes poll if the limit is reached."""
        import sys

        answer = update.poll_answer
        poll_id = answer.poll_id
        user_id = answer.user.id
        selected_options = answer.option_ids

        logger.info("Recording vote for poll %s from user %s",
                    poll_id, user_id)

        # If poll not provided, try to load it
        if not poll:
            # Try from user_data first (conversation handler)
            poll = context.user_data.get("poll")

            # Try from bot_data (inline queries)
            if not poll and poll_id in context.bot_data:
                poll_data = context.bot_data[poll_id]

                # First try to get the stored poll object
                poll = poll_data.get("poll_object")
                if poll:
                    logger.info("Retrieved stored poll object from bot_data")
                else:
                    # Fallback: reconstruct from data (for backward compatibility)
                    votes_dict = {}
                    if "votes" in poll_data:
                        for uid_str, opts in poll_data["votes"].items():
                            votes_dict[int(uid_str)] = opts

                    poll = Poll(
                        id=poll_id,
                        question=poll_data["question"],
                        options=poll_data["options"],
                        answer_num=poll_data.get("answer_num", 0),
                        votes=votes_dict,
                        anonimity=poll_data.get("anonimity", False),
                        forwarding=poll_data.get("forwarding", True),
                        limit=poll_data.get("limit", sys.maxsize)
                    )
                    logger.info("Reconstructed poll from bot_data")

            # Try from database (bot restart)
            if not poll:
                poll = self.poll_repository.get_poll_by_id(poll_id)
                if poll:
                    logger.info("Loaded poll from database")
                    # Repopulate bot_data
                    context.bot_data[poll_id] = {
                        "poll_object": poll,  # Store the actual Poll object!
                        "question": poll.question,
                        "options": poll.options,
                        "answer_num": poll.answer_num,
                        "votes": {str(k): v for k, v in poll.votes.items()},
                        "anonimity": poll.anonimity,
                        "forwarding": poll.forwarding,
                        "limit": poll.limit,
                        "message_id": None,
                        "chat_id": None
                    }
                else:
                    logger.error("Poll %s not found", poll_id)
                    return

        # Update bot_data if available
        if poll_id in context.bot_data:
            poll_data = context.bot_data[poll_id]
            poll_data["answer_num"] += 1
            poll_data["votes"][str(user_id)] = selected_options

        # Update poll instance
        poll.votes[user_id] = selected_options
        poll.answer_num += 1

        # Check if poll should close after the limit of answers has been reached
        if poll_id in context.bot_data:
            poll_data = context.bot_data[poll_id]
            if poll.limit and poll_data["answer_num"] >= poll.limit:
                await self.close_poll(poll, poll_data, context)

        # Save to database
        self.poll_repository.record_poll_answer(
            poll, user_id, selected_options, poll.closed)

    async def retract_vote(self, poll: Poll, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Removes the votes when user clicks 'retract vote'"""

        answer = update.poll_answer
        poll_id = answer.poll_id
        user_id = answer.user.id  # User who voted
        self.poll_repository.remove_vote(poll_id, user_id)

    async def list_polls_by_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> list[Poll]:
        pass

    async def delete_poll(self, poll: Poll) -> None:
        """Deletes a poll"""
        self.poll_repository.delete_poll(poll.id)

    async def close_poll(self, poll: Poll, poll_data: dict, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Closes a poll when limit is reached"""

        stopped_poll = await context.bot.stop_poll(poll_data["chat_id"], poll_data["message_id"])

        # For anonymous polls, persist final counts
        if poll_data.get("anonimity"):
            final_vote_counts = {}
            for i, option in enumerate(stopped_poll.options):
                final_vote_counts[i] = option.voter_count

            self.poll_repository.update_anonymous_poll_counts(
                poll.id, final_vote_counts, stopped_poll.total_voter_count)
            logger.info("Persisted final counts for anonymous poll %s: %s voters",
                        poll.id, stopped_poll.total_voter_count)

        # Update closed status in database
        logger.info("Closing poll with id: %s", str(poll.id))
        logger.info("Poll id type: %s", str(type(poll.id)))
        logger.info("Poll id repr: %s", repr(poll.id))
        self.poll_repository.close_poll(poll.id)
        poll.closed = True

        await context.bot.send_message(
            poll_data["chat_id"],
            f"The poll '{poll_data['question']}' has closed after reaching the limit of {poll.limit} voters."
        )
