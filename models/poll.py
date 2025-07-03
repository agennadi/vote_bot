import logging
from dataclasses import dataclass, field

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

@dataclass
class Poll:
    id: str=''
    anonimity: bool=False
    forwarding: bool=True
    limit: int=sys.maxsize
    question: str=''
    options: list[str]=field(default_factory=list)
    expiration_date: datetime=(default_factory=lambda: datetime.now() + timedelta(weeks=1)) 
    answer_num: int=0
    votes: dict=field(default_factory=dict)
    closed: bool=False

    def to_dict(self):
        return {
            "id": self.id,
            "anonimity": self.anonimity,
            "forwarding": self.forwarding,
            "limit": self.limit,
            "question": self.question,
            "options": self.options,
            "expiration_date": self.expiration_date,
            "answer_num": self.answer_num,
            "votes": self.votes,
            "closed": self.closed,
        }    

