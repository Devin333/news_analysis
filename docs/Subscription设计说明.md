# Subscription 设计说明

## 概述

Subscription（订阅）模块让用户能够持续追踪感兴趣的内容，当有新的匹配内容出现时自动通知。

## 核心概念

### 订阅类型 (SubscriptionType)

| 类型 | 说明 | 匹配方式 |
|------|------|----------|
| query | 关键词订阅 | 标题/摘要包含关键词 |
| tag | 标签订阅 | 内容包含指定标签 |
| entity | 实体订阅 | 内容关联指定实体 |
| topic | 主题订阅 | 追踪特定主题更新 |
| board | 板块订阅 | 追踪特定板块内容 |

### 匹配模式 (MatchMode)

- `any`: 任一条件匹配即可
- `all`: 所有条件都需匹配
- `exact`: 精确匹配

### 通知频率 (NotifyFrequency)

- `immediate`: 立即通知
- `daily`: 每日汇总
- `weekly`: 每周汇总

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    Subscription API                          │
│  POST /subscriptions  GET /subscriptions  DELETE /...       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  SubscriptionService                         │
│  - create_subscription()                                     │
│  - list_subscriptions()                                      │
│  - match_topic_against_subscriptions()                       │
│  - record_subscription_hit()                                 │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│SubscriptionRepo │ │SubscriptionMatcher│ │  EventRepo     │
│                 │ │                   │ │                 │
│ - create()      │ │ - match_topic()   │ │ - create()     │
│ - list_active() │ │ - match_query()   │ │ - list_by_sub()│
│ - update_status │ │ - match_tags()    │ │ - mark_as_read │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

## 数据模型

### Subscription 表

```sql
CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    subscription_type VARCHAR(20) NOT NULL,
    user_key VARCHAR(100) NOT NULL,
    query TEXT,
    tags_json JSONB,
    board_type VARCHAR(50),
    entity_id INTEGER,
    topic_id INTEGER,
    name VARCHAR(200),
    status VARCHAR(20) DEFAULT 'active',
    notify_email BOOLEAN DEFAULT TRUE,
    notify_frequency VARCHAR(20) DEFAULT 'daily',
    min_score FLOAT DEFAULT 0.5,
    match_mode VARCHAR(20) DEFAULT 'any',
    metadata_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    last_matched_at TIMESTAMP WITH TIME ZONE
);
```

### SubscriptionEvent 表

```sql
CREATE TABLE subscription_events (
    id SERIAL PRIMARY KEY,
    subscription_id INTEGER REFERENCES subscriptions(id),
    target_type VARCHAR(50) NOT NULL,
    target_id INTEGER NOT NULL,
    match_score FLOAT,
    match_reason TEXT,
    matched_fields_json JSONB,
    matched_tags_json JSONB,
    notification_status VARCHAR(20) DEFAULT 'pending',
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP WITH TIME ZONE,
    notified_at TIMESTAMP WITH TIME ZONE,
    metadata_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE
);
```

## 匹配策略

### SubscriptionMatcher

匹配器支持多种匹配方式：

1. **关键词匹配**
   - 标题匹配（权重 0.6）
   - 摘要匹配（权重 0.4）
   - 分词匹配（部分匹配）

2. **标签匹配**
   - 支持 require_all_tags 模式
   - 计算匹配比例作为分数

3. **板块匹配**
   - 精确匹配板块类型

4. **语义匹配**（可选）
   - 使用 embedding 相似度

### 匹配策略配置

```python
class MatchPolicyConfig:
    min_score: float = 0.3
    partial_match: bool = True
    case_sensitive: bool = False
    require_all_tags: bool = False
    semantic_enabled: bool = False
    semantic_threshold: float = 0.7
```

## 定时任务

### SubscriptionMatchJob

定期扫描新内容并匹配订阅：

```python
class SubscriptionMatchJob:
    async def run(
        self,
        lookback_hours: int = 1,
        scan_topics: bool = True,
        scan_reports: bool = True,
        scan_trends: bool = True,
    ) -> dict:
        # 1. 获取最近的 topics
        # 2. 获取最近的 reports
        # 3. 获取趋势 topics
        # 4. 对每个内容匹配所有活跃订阅
        # 5. 记录匹配事件
```

## API 接口

### 创建订阅

```http
POST /subscriptions
Content-Type: application/json

{
    "subscription_type": "query",
    "user_key": "user@example.com",
    "query": "AI agent",
    "notify_frequency": "daily",
    "min_score": 0.5
}
```

### 列出订阅

```http
GET /subscriptions?user_key=user@example.com&status=active
```

### 获取匹配事件

```http
GET /subscriptions/{id}/matches?unread_only=true
```

### 手动触发匹配

```http
POST /subscriptions/match/topic/{topic_id}
```

## 使用示例

### 创建关键词订阅

```python
from app.subscription.service import SubscriptionService
from app.contracts.dto.subscription import SubscriptionCreateDTO, SubscriptionType

service = SubscriptionService(...)

subscription = await service.create_subscription(
    SubscriptionCreateDTO(
        subscription_type=SubscriptionType.QUERY,
        user_key="user@example.com",
        query="LLM agent framework",
        notify_frequency=NotifyFrequency.DAILY,
        min_score=0.5,
    )
)
```

### 匹配新主题

```python
result = await service.match_topic_against_subscriptions(
    topic_id=123,
    topic_title="New LLM Agent Framework Released",
    topic_summary="A new framework for building AI agents...",
    topic_tags=["llm", "agent", "framework"],
    board_type="tech",
)

print(f"Matched {result.total_matches} subscriptions")
```

## 扩展点

1. **语义匹配**: 接入 embedding 服务实现语义相似度匹配
2. **实体匹配**: 接入实体识别服务匹配实体订阅
3. **通知服务**: 接入邮件/推送服务发送通知
4. **订阅推荐**: 基于用户行为推荐订阅
