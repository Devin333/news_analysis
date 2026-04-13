# Week 9 复杂记忆系统基础说明

## 概述

Week 9 建立了 NewsAgent 的复杂记忆系统基础层，将"记忆"从概念变成基础设施。

## 核心组件

### 1. Memory DTO 层 (`app/contracts/dto/memory.py`)

定义了所有记忆相关的数据传输对象：

- `WorkingMemoryDTO` - 当前 Agent 会话的工作记忆
- `SessionMemoryDTO` - 跨 Agent 运行的会话级记忆
- `TopicMemoryDTO` - Topic 长期记忆
- `TopicSnapshotDTO` - Topic 时间点快照
- `EntityMemoryDTO` - Entity 长期记忆
- `JudgementMemoryDTO` - 系统判断记录
- `TimelinePointDTO` / `TimelineEventDTO` - 时间线事件
- `MemoryRetrievalResultDTO` - 记忆检索结果
- `TopicHistoryContextDTO` - Topic 完整历史上下文

### 2. Memory Protocol 层 (`app/contracts/protocols/memory.py`)

定义了记忆层的统一协议：

- `TopicMemoryRepositoryProtocol` - Topic 记忆仓库协议
- `EntityMemoryRepositoryProtocol` - Entity 记忆仓库协议
- `JudgementMemoryRepositoryProtocol` - 判断记忆仓库协议
- `TimelineRepositoryProtocol` - 时间线仓库协议
- `MemoryRetrievalProtocol` - 统一检索协议

### 3. ORM 模型

#### Topic Memory (`app/storage/db/models/topic_memory.py`)
```
topic_memories 表:
- id, topic_id (唯一)
- first_seen_at, last_seen_at
- historical_status (new/evolving/recurring/milestone)
- current_stage (emerging/active/stable/declining)
- history_summary
- key_milestones_json
- latest_historian_output_json
- historian_confidence
```

#### Topic Snapshot (`app/storage/db/models/topic_snapshot.py`)
```
topic_snapshots 表:
- id, topic_id, snapshot_at
- summary, why_it_matters, system_judgement
- heat_score, trend_score
- item_count, source_count
- representative_item_id
- timeline_json
```

#### Entity (`app/storage/db/models/entity.py`)
```
entities 表:
- id, entity_type, name, normalized_name
- aliases_json, description
- first_seen_at, last_seen_at
- activity_score
```

#### Entity Memory (`app/storage/db/models/entity_memory.py`)
```
entity_memories 表:
- id, entity_id (唯一)
- summary
- related_topic_ids_json
- milestones_json, recent_signals_json
- last_refreshed_at
```

#### Topic-Entity 关系 (`app/storage/db/models/topic_entity.py`)
```
topic_entities 表:
- topic_id, entity_id (联合主键)
- relevance_score
- created_at
```

#### Judgement Log (`app/storage/db/models/judgement_log.py`)
```
judgement_logs 表:
- id, target_type, target_id
- agent_name, judgement_type
- judgement, confidence
- evidence_json
- later_outcome (用于验证)
```

### 4. Repository 层 (`app/memory/repositories/`)

- `TopicMemoryRepository` - Topic 记忆 CRUD
- `EntityMemoryRepository` - Entity 记忆 CRUD
- `JudgementRepository` - 判断记录 CRUD

### 5. MemoryService (`app/memory/service.py`)

统一的记忆服务入口，Agent 只能通过此服务访问记忆：

```python
# Topic Memory
await service.get_topic_memory(topic_id)
await service.create_or_update_topic_memory(topic_id, data)
await service.create_topic_snapshot(topic_id, snapshot)
await service.get_topic_snapshots(topic_id)
await service.get_latest_topic_snapshot(topic_id)

# Entity Memory
await service.get_entity_memory(entity_id)
await service.refresh_entity_memory(entity_id, data)
await service.get_entity_related_topics(entity_id)

# Judgement Memory
await service.create_judgement_log(data)
await service.get_judgements_for_target(target_type, target_id)
await service.get_recent_judgements_by_type(judgement_type)

# Retrieval
await service.retrieve_topic_context(topic_id)
await service.get_topic_historical_context(topic_id)
```

### 6. Snapshot Builder (`app/memory/topic_memory/snapshot_builder.py`)

从当前 Topic 状态构建快照：

```python
builder = TopicSnapshotBuilder(topic_repo, item_repo)
snapshot = await builder.build_snapshot(topic_id)
```

### 7. API 调试接口 (`app/api/routers/memory.py`)

- `GET /memory/topics/{id}/memory` - 获取 Topic 记忆
- `GET /memory/topics/{id}/snapshots` - 获取 Topic 快照列表
- `GET /memory/topics/{id}/context` - 获取 Topic 历史上下文
- `GET /memory/entities/{id}/memory` - 获取 Entity 记忆
- `GET /memory/entities/{id}/related-topics` - 获取 Entity 相关 Topics
- `GET /memory/judgements/{target_type}/{target_id}` - 获取判断记录
- `GET /memory/debug/stats` - 获取记忆系统统计

## 数据库迁移

Week 9 新增的迁移文件：

1. `b2c3d4e5f6g7_create_topic_memory_tables.py`
   - topic_memories 表
   - topic_snapshots 表

2. `c3d4e5f6g7h8_create_entity_memory_tables.py`
   - entities 表
   - entity_memories 表
   - topic_entities 表

3. `d4e5f6g7h8i9_create_judgement_log_table.py`
   - judgement_logs 表

## 架构原则

1. **Agent 不直接访问 Repository**
   - 所有记忆访问必须通过 MemoryService

2. **记忆分层清晰**
   - Topic Memory: 长期演化记忆
   - Entity Memory: 实体历史记忆
   - Judgement Memory: 系统判断历史

3. **Snapshot 追踪演化**
   - 每次重要更新可创建快照
   - 支持历史回溯和对比

4. **为后续 Agent 打基础**
   - Historian Agent 可读取历史上下文
   - Analyst Agent 可读取判断历史

## 后续扩展 (Week 10+)

- Timeline Engine: 时间线抽取和构建
- Retrieval Layer: 混合检索策略
- Historian Agent: 历史考证
- Analyst Agent: 价值判断

## 使用示例

```python
from app.storage.uow import UnitOfWork
from app.memory.service import MemoryService

async with UnitOfWork() as uow:
    # 创建 MemoryService
    memory_service = MemoryService.from_uow(uow)
    
    # 获取 Topic 历史上下文
    context = await memory_service.retrieve_topic_context(topic_id)
    
    # 创建判断记录
    from app.contracts.dto.memory import JudgementCreateDTO
    judgement = JudgementCreateDTO(
        target_type="topic",
        target_id=topic_id,
        agent_name="analyst",
        judgement_type="importance",
        judgement="High importance due to...",
        confidence=0.85,
        evidence=["evidence1", "evidence2"],
    )
    await memory_service.create_judgement_log(judgement)
```
