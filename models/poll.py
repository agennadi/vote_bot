import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import sys

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


@dataclass
class Poll:
    id: str = ''
    anonimity: bool = False
    forwarding: bool = True
    limit: int = sys.maxsize
    question: str = ''
    options: list[str] = field(default_factory=list)
    expiration_date: datetime = field(
        default_factory=lambda: datetime.now() + timedelta(weeks=1))
    voters_num: int = 0
    votes: dict = field(default_factory=dict)
    closed: bool = False

    def get_vote_counts(self) -> dict:
        """
        Get vote count for each option.
        Returns dict: {option_index: vote_count}
        Works for both anonymous and non-anonymous polls.
        """
        vote_counts = {i: 0 for i in range(len(self.options))}

        for user_id, selected_option_ids in self.votes.items():
            for option_id in selected_option_ids:
                if option_id in vote_counts:
                    vote_counts[option_id] += 1

        return vote_counts

    def get_results_summary(self) -> str:
        """Get a formatted summary of poll results."""
        vote_counts = self.get_vote_counts()
        total_votes = sum(vote_counts.values())

        summary = f"📊 Poll Results: {self.question}\n\n"

        for i, option in enumerate(self.options):
            count = vote_counts.get(i, 0)
            percentage = (count / total_votes * 100) if total_votes > 0 else 0
            summary += f"{option}: {count} votes ({percentage:.1f}%)\n"

        summary += f"\n👥 Total voters: {len(self.votes)}"
        summary += f"\n📝 Total votes: {total_votes}"

        return summary

    def to_dict(self):
        return {
            "id": self.id,
            "anonimity": self.anonimity,
            "forwarding": self.forwarding,
            "limit": self.limit,
            "question": self.question,
            "options": self.options,
            "expiration_date": self.expiration_date,
            "voters_num": self.voters_num,
            "votes": self.votes,
            "closed": self.closed,
        }
