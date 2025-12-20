import uuid
from datetime import datetime


class Memory:
    def __init__(
        self,
        category: str,
        interpreted_meaning: str,
        source_datetime: datetime,
        interpreted_datetime: datetime | None = None,
        datetime_confidence: float = 1.0,
        confidence: float = 1.0,
        importance: float = 0.5
    ):
        self.memory_id = str(uuid.uuid4())

        self.category = category
        self.interpreted_meaning = interpreted_meaning

        self.source_datetime = source_datetime
        self.interpreted_datetime = interpreted_datetime

        self.datetime_confidence = datetime_confidence
        self.confidence = confidence
        self.importance = importance

        self.state = "active"
