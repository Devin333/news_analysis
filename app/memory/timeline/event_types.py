"""Timeline event type definitions."""

from enum import StrEnum


class TimelineEventType(StrEnum):
    """Types of timeline events."""

    # Topic lifecycle events
    FIRST_SEEN = "first_seen"
    TOPIC_CREATED = "topic_created"
    TOPIC_MERGED = "topic_merged"
    TOPIC_SUMMARY_CHANGED = "topic_summary_changed"

    # Content events
    RELEASE_PUBLISHED = "release_published"
    PAPER_PUBLISHED = "paper_published"
    REPO_CREATED = "repo_created"
    ARTICLE_PUBLISHED = "article_published"
    NEWS_PUBLISHED = "news_published"

    # Activity events
    COMMUNITY_DISCUSSION_SPIKE = "community_discussion_spike"
    ITEM_COUNT_MILESTONE = "item_count_milestone"
    SOURCE_COUNT_MILESTONE = "source_count_milestone"
    HEAT_SCORE_SPIKE = "heat_score_spike"

    # Analysis events
    HISTORIAN_ANALYSIS = "historian_analysis"
    ANALYST_JUDGEMENT = "analyst_judgement"
    STATUS_CHANGED = "status_changed"
    STAGE_CHANGED = "stage_changed"

    # Snapshot events
    SNAPSHOT_CREATED = "snapshot_created"

    # External events
    EXTERNAL_MILESTONE = "external_milestone"
    CUSTOM = "custom"


# Event type metadata
EVENT_TYPE_INFO = {
    TimelineEventType.FIRST_SEEN: {
        "label": "首次出现",
        "importance_base": 0.9,
        "is_milestone": True,
    },
    TimelineEventType.TOPIC_CREATED: {
        "label": "话题创建",
        "importance_base": 0.8,
        "is_milestone": True,
    },
    TimelineEventType.TOPIC_MERGED: {
        "label": "话题合并",
        "importance_base": 0.6,
        "is_milestone": False,
    },
    TimelineEventType.TOPIC_SUMMARY_CHANGED: {
        "label": "摘要更新",
        "importance_base": 0.4,
        "is_milestone": False,
    },
    TimelineEventType.RELEASE_PUBLISHED: {
        "label": "版本发布",
        "importance_base": 0.85,
        "is_milestone": True,
    },
    TimelineEventType.PAPER_PUBLISHED: {
        "label": "论文发表",
        "importance_base": 0.85,
        "is_milestone": True,
    },
    TimelineEventType.REPO_CREATED: {
        "label": "仓库创建",
        "importance_base": 0.7,
        "is_milestone": True,
    },
    TimelineEventType.ARTICLE_PUBLISHED: {
        "label": "文章发布",
        "importance_base": 0.5,
        "is_milestone": False,
    },
    TimelineEventType.NEWS_PUBLISHED: {
        "label": "新闻发布",
        "importance_base": 0.5,
        "is_milestone": False,
    },
    TimelineEventType.COMMUNITY_DISCUSSION_SPIKE: {
        "label": "社区讨论激增",
        "importance_base": 0.7,
        "is_milestone": False,
    },
    TimelineEventType.ITEM_COUNT_MILESTONE: {
        "label": "内容数量里程碑",
        "importance_base": 0.6,
        "is_milestone": True,
    },
    TimelineEventType.SOURCE_COUNT_MILESTONE: {
        "label": "来源数量里程碑",
        "importance_base": 0.6,
        "is_milestone": True,
    },
    TimelineEventType.HEAT_SCORE_SPIKE: {
        "label": "热度激增",
        "importance_base": 0.65,
        "is_milestone": False,
    },
    TimelineEventType.HISTORIAN_ANALYSIS: {
        "label": "历史分析",
        "importance_base": 0.5,
        "is_milestone": False,
    },
    TimelineEventType.ANALYST_JUDGEMENT: {
        "label": "分析判断",
        "importance_base": 0.55,
        "is_milestone": False,
    },
    TimelineEventType.STATUS_CHANGED: {
        "label": "状态变更",
        "importance_base": 0.6,
        "is_milestone": False,
    },
    TimelineEventType.STAGE_CHANGED: {
        "label": "阶段变更",
        "importance_base": 0.65,
        "is_milestone": True,
    },
    TimelineEventType.SNAPSHOT_CREATED: {
        "label": "快照创建",
        "importance_base": 0.3,
        "is_milestone": False,
    },
    TimelineEventType.EXTERNAL_MILESTONE: {
        "label": "外部里程碑",
        "importance_base": 0.8,
        "is_milestone": True,
    },
    TimelineEventType.CUSTOM: {
        "label": "自定义事件",
        "importance_base": 0.5,
        "is_milestone": False,
    },
}


def get_event_type_info(event_type: TimelineEventType) -> dict:
    """Get metadata for an event type."""
    return EVENT_TYPE_INFO.get(event_type, EVENT_TYPE_INFO[TimelineEventType.CUSTOM])


def get_base_importance(event_type: TimelineEventType) -> float:
    """Get base importance score for an event type."""
    info = get_event_type_info(event_type)
    return info.get("importance_base", 0.5)


def is_milestone_type(event_type: TimelineEventType) -> bool:
    """Check if an event type is typically a milestone."""
    info = get_event_type_info(event_type)
    return info.get("is_milestone", False)
