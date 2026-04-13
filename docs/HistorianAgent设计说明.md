# HistorianAgent 设计说明

## 概述

HistorianAgent 是 NewsAgent 系统中负责历史考证的核心 Agent。它的职责是：

1. 回溯 topic 的历史
2. 判断当前 topic 的历史状态
3. 识别本次报道的新增内容
4. 提供历史背景上下文

## 核心职责

### 输入
- 当前 topic 信息
- 代表性 item
- 历史 timeline
- 历史 snapshots
- 相关 topics
- entity memories

### 输出
- `first_seen_at`: 首次出现时间
- `last_seen_at`: 最近出现时间
- `historical_status`: 历史状态 (new/evolving/recurring/milestone)
- `current_stage`: 当前阶段 (emerging/active/stable/declining)
- `history_summary`: 历史摘要
- `timeline_points`: 关键时间线节点
- `what_is_new_this_time`: 本次新增内容
- `similar_past_topics`: 相似历史 topics
- `important_background`: 重要背景
- `historical_confidence`: 置信度

## 历史状态定义

| 状态 | 说明 |
|------|------|
| `new` | 首次出现的 topic |
| `evolving` | 持续演化中的 topic |
| `recurring` | 旧话题重新出现 |
| `milestone` | 重大更新/里程碑事件 |

## 当前阶段定义

| 阶段 | 说明 |
|------|------|
| `emerging` | 刚开始获得关注 |
| `active` | 活跃讨论中 |
| `stable` | 稳定覆盖 |
| `declining` | 关注度下降 |

## 架构

```
HistorianAgent
├── schemas.py          # 输入输出 Schema
├── input_builder.py    # 输入构建器
├── agent.py            # Agent 实现
├── service.py          # 对外服务
└── validators.py       # 输出校验
```

## 工具集

HistorianAgent 可使用以下工具：

1. `retrieve_topic_timeline` - 获取 topic 时间线
2. `retrieve_topic_snapshots` - 获取历史快照
3. `retrieve_related_topics` - 获取相关 topics
4. `retrieve_entity_memories` - 获取实体记忆
5. `retrieve_historical_judgements` - 获取历史判断

## 使用方式

### 通过 Service 调用

```python
from app.agents.historian.service import HistorianService
from app.storage.uow import UnitOfWork

uow = UnitOfWork()
service = HistorianService(uow=uow)

# 运行分析
output, metadata = await service.run_for_topic(topic_id=123)

if output:
    print(f"Status: {output.historical_status}")
    print(f"Summary: {output.history_summary}")
```

### 通过脚本调用

```bash
# 单个 topic
python -m scripts.run_historian_for_topic --topic-id 123

# 批量处理
python -m scripts.rebuild_historical_context --limit 10
```

## API 端点

- `GET /topics/{id}/enriched` - 获取增强版 topic 详情（含历史上下文）
- `GET /topics/{id}/historian-output` - 获取 historian 输出

## 数据持久化

Historian 输出存储在 `topic_memories` 表：

- `latest_historian_output_json`: 完整输出 JSON
- `historian_confidence`: 置信度
- `historical_status`: 历史状态
- `current_stage`: 当前阶段
- `history_summary`: 历史摘要

## 质量校验

`HistorianValidator` 检查以下问题：

### 错误（阻断）
- `first_seen_at` 在未来
- `first_seen_at` 晚于 `last_seen_at`
- 置信度超出 [0,1] 范围
- 非 new 状态但无历史摘要
- milestone 状态但无新增内容说明

### 警告
- 低置信度 (<0.3)
- 时间线乱序
- 有时间线但无摘要
- new 状态但有多个时间线节点

## 注意事项

1. **Historian 不是 Writer** - 职责是回溯和对照，不是写漂亮文案
2. **不直接访问数据库** - 通过 tools/retrieval service 获取上下文
3. **输出结构化** - 所有输出都是可落库的结构化字段
4. **允许不完美** - 第一版重点是可用、可追踪、可扩展
