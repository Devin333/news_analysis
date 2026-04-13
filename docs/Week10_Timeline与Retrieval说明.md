# Week 10 Timeline Engine 与 Retrieval Layer 说明

## 概述

Week 10 建立了 Timeline Engine 和 Retrieval Layer，让记忆系统不只是"存档"，而是"可检索、可组织、可形成时间线"。

## 核心组件

### 1. Timeline 数据结构

#### ORM 模型 (`app/storage/db/models/topic_timeline_event.py`)
```
topic_timeline_events 表:
- id, topic_id, event_time
- event_type (first_seen, release_published, paper_published, etc.)
- title, description
- source_item_id, source_type
- importance_score (0-1)
- is_milestone
- metadata_json
```

#### Timeline Repository (`app/memory/repositories/timeline_repository.py`)
- `create_event()` - 创建单个事件
- `bulk_create_events()` - 批量创建事件
- `list_by_topic()` - 按 topic 列出事件
- `list_by_time_range()` - 按时间范围查询
- `list_milestones()` - 获取里程碑事件
- `delete_by_topic()` - 删除 topic 的所有事件

### 2. Timeline Event 抽取器

#### Event Types (`app/memory/timeline/event_types.py`)
定义了所有事件类型：
- `FIRST_SEEN` - 首次出现
- `RELEASE_PUBLISHED` - 版本发布
- `PAPER_PUBLISHED` - 论文发表
- `REPO_CREATED` - 仓库创建
- `COMMUNITY_DISCUSSION_SPIKE` - 社区讨论激增
- `ITEM_COUNT_MILESTONE` - 内容数量里程碑
- `STATUS_CHANGED` - 状态变更
- 等等...

#### Extractors (`app/memory/timeline/extractors.py`)
```python
extractor = TimelineExtractor()

# 从 item 抽取事件
event = extractor.extract_from_normalized_item(item, topic_id)

# 从 snapshot 抽取事件
event = extractor.extract_from_topic_snapshot(snapshot)

# 创建首次出现事件
event = extractor.extract_first_seen_event(first_seen_at, title)

# 创建里程碑事件
event = extractor.extract_milestone_event(event_time, "item_count", 100, title)
```

### 3. Timeline Builder (`app/memory/timeline/builder.py`)

组织和构建时间线：
- 聚合来自 item / snapshot / judgement 的事件
- 排序
- 去重（相同类型、相近时间的事件）
- 标记里程碑

```python
builder = TimelineBuilder()

# 从 items 构建
timeline = builder.build_from_items(items, topic)

# 组合多个来源
timeline = builder.build_combined(items, snapshots, topic)

# 合并多个时间线
timeline = builder.merge_timelines(timeline1, timeline2)
```

### 4. Timeline Service (`app/memory/timeline/service.py`)

```python
service = TimelineService(timeline_repo, topic_repo, item_repo)

# 构建时间线（不持久化）
timeline = await service.build_topic_timeline(topic_id)

# 刷新并持久化时间线
timeline = await service.refresh_topic_timeline(topic_id)

# 获取已持久化的时间线
timeline = await service.get_topic_timeline(topic_id)

# 获取里程碑
milestones = await service.get_topic_milestones(topic_id)
```

### 5. Memory Retrieval Service (`app/memory/retrieval/service.py`)

统一的历史检索入口：
```python
service = MemoryRetrievalService(
    topic_memory_repo,
    entity_memory_repo,
    judgement_repo,
    timeline_repo,
)

# 获取完整历史上下文
context = await service.retrieve_topic_history(topic_id)

# 获取时间线
timeline = await service.retrieve_topic_timeline(topic_id)

# 获取快照
snapshots = await service.retrieve_topic_snapshots(topic_id)

# 获取完整检索结果
result = await service.retrieve_full_context(topic_id)
```

### 6. Semantic Retriever (`app/memory/retrieval/semantic_retriever.py`)

基于 embedding 的语义检索：
```python
retriever = SemanticRetriever(indexer, vector_store)

# 按文本查找相似 topics
similar = await retriever.retrieve_similar_topics_by_text(query)

# 查找相似判断
judgements = await retriever.retrieve_similar_judgements(query)

# 查找相关历史
histories = await retriever.retrieve_related_history_by_query(query)
```

### 7. Hybrid Retriever (`app/memory/retrieval/hybrid_retriever.py`)

混合检索策略，组合结构化查询和语义搜索：
```python
retriever = HybridRetriever(structured_retriever, semantic_retriever)

# 使用策略检索
result = await retriever.retrieve(topic_id, policy="historian")

# 为 Historian 优化的检索
result = await retriever.retrieve_for_historian(topic_id, query)

# 为 Analyst 优化的检索
result = await retriever.retrieve_for_analyst(topic_id)

# 快速检索
result = await retriever.retrieve_quick(topic_id)

# 完整检索
result = await retriever.retrieve_full(topic_id, query)
```

### 8. Retrieval Policies (`app/memory/retrieval/policies.py`)

定义不同检索模式：
- `topic_context` - 通用 topic 上下文
- `entity_context` - 实体聚焦检索
- `historian` - Historian Agent 专用
- `analyst` - Analyst Agent 专用
- `quick` - 快速检索（最小数据）
- `full` - 完整检索（所有数据）

### 9. Vector Store (`app/vector_store/service.py`)

向量存储服务（当前为内存实现）：
```python
store = get_vector_store()

# 存储向量
await store.upsert(namespace, id, vector, metadata)

# 搜索相似向量
results = await store.search(namespace, query_vector, limit=10)
```

### 10. Embedding Indexing (`app/embeddings/indexing.py`)

为记忆对象构建 embedding：
```python
indexer = MemoryIndexer(embedding_provider)

# 索引 item
embedding = await indexer.index_normalized_item(item)

# 索引 topic summary
embedding = await indexer.index_topic_summary(topic_id, title, summary)

# 索引 judgement
embedding = await indexer.index_judgement(judgement)
```

## API 端点

Week 10 新增的 API：

- `GET /memory/topics/{id}/timeline` - 获取 topic 时间线
- `GET /memory/topics/{id}/milestones` - 获取里程碑事件
- `POST /memory/topics/{id}/timeline/refresh` - 刷新时间线
- `GET /memory/topics/{id}/history-context` - 获取完整历史上下文

## 数据库迁移

Week 10 新增的迁移文件：
- `e5f6g7h8i9j0_create_topic_timeline_events_table.py`

## 脚本

- `app/scripts/rebuild_timelines.py` - 批量重建时间线

```bash
# 重建所有 topic 的时间线
python -m app.scripts.rebuild_timelines --limit 100

# 重建单个 topic 的时间线
python -m app.scripts.rebuild_timelines --topic-id 123
```

## 架构原则

1. **Timeline 是一等对象**
   - 有独立的数据模型和 repository
   - 支持增量更新和完整重建

2. **Retrieval 分层**
   - 结构化检索：精确查询
   - 语义检索：相似性搜索
   - 混合检索：组合两者

3. **策略可配置**
   - 不同 Agent 使用不同检索策略
   - 策略定义了检索范围和限制

4. **向量存储抽象**
   - 当前使用内存存储
   - 可扩展到 pgvector 或其他向量数据库

## 后续扩展 (Week 11+)

- Historian Agent：使用 Timeline 和 Retrieval 进行历史考证
- Analyst Agent：使用 Retrieval 进行价值判断
- 更复杂的事件抽取逻辑
- pgvector 集成

## 使用示例

```python
from app.storage.uow import UnitOfWork
from app.memory.repositories.timeline_repository import TimelineRepository
from app.memory.timeline.service import TimelineService
from app.memory.retrieval.service import MemoryRetrievalService

async with UnitOfWork() as uow:
    # 创建 Timeline Service
    timeline_repo = TimelineRepository(uow.session)
    timeline_service = TimelineService(
        timeline_repo=timeline_repo,
        topic_repo=uow.topics,
        item_repo=uow.normalized_items,
    )
    
    # 刷新时间线
    events = await timeline_service.refresh_topic_timeline(topic_id)
    
    # 创建 Retrieval Service
    retrieval_service = MemoryRetrievalService(
        topic_memory_repo=uow.topic_memories,
        entity_memory_repo=uow.entity_memories,
        judgement_repo=uow.judgements,
        timeline_repo=timeline_repo,
    )
    
    # 获取完整历史上下文
    context = await retrieval_service.retrieve_topic_history(topic_id)
```
