"""ORM model registry for Alembic autogenerate."""

from app.source_management.models import Source
from app.storage.db.models.entity import Entity
from app.storage.db.models.entity_memory import EntityMemory
from app.storage.db.models.item_tag import ItemTag
from app.storage.db.models.judgement_log import JudgementLog
from app.storage.db.models.normalized_item import NormalizedItem
from app.storage.db.models.raw_item import RawItem
from app.storage.db.models.tag import Tag
from app.storage.db.models.topic import Topic
from app.storage.db.models.topic_entity import TopicEntity
from app.storage.db.models.topic_item import TopicItem
from app.storage.db.models.topic_memory import TopicMemory
from app.storage.db.models.topic_snapshot import TopicSnapshot
from app.storage.db.models.topic_tag import TopicTag
from app.storage.db.models.topic_timeline_event import TopicTimelineEvent

__all__ = [
    "Source",
    "RawItem",
    "NormalizedItem",
    "Topic",
    "TopicItem",
    "Tag",
    "ItemTag",
    "TopicTag",
    "TopicMemory",
    "TopicSnapshot",
    "Entity",
    "EntityMemory",
    "TopicEntity",
    "JudgementLog",
    "TopicTimelineEvent",
]
