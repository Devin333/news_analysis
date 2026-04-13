# Historian + Analyst 工作流说明

## 概述

Historian 和 Analyst 是 NewsAgent 系统中两个核心的分析 Agent，它们协同工作为 Topic 提供历史考证和价值判断能力。

## 工作流架构

```
┌─────────────────────────────────────────────────────────────┐
│                  Topic Enrichment Pipeline                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   Timeline   │───▶│  Historian   │───▶│   Analyst    │   │
│  │   Refresh    │    │    Agent     │    │    Agent     │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│         │                   │                   │            │
│         ▼                   ▼                   ▼            │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   Timeline   │    │    Topic     │    │    Topic     │   │
│  │  Repository  │    │   Memory     │    │   Insight    │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## HistorianAgent

### 职责

Historian 负责"历史考证"，回答以下问题：
- 这个 topic 是什么时候首次出现的？
- 它的历史演变过程是怎样的？
- 这次有什么新的变化？
- 有没有类似的历史 topic？

### 输入

```python
HistorianInput(
    topic_id=100,
    topic_summary="GPT-5 发布",
    representative_items=[...],      # 代表性内容
    tags=["ai", "openai"],           # 标签
    board_type="tech",               # 板块类型
    timeline=[...],                  # 时间线事件
    snapshots=[...],                 # 历史快照
    related_topics=[...],            # 相关 topic
    entity_memories=[...],           # 实体记忆
)
```

### 输出

```python
HistorianOutput(
    first_seen_at=datetime(...),     # 首次出现时间
    history_summary="...",           # 历史摘要
    timeline_points=[...],           # 关键时间点
    historical_status="new",         # 历史状态
    current_stage="emerging",        # 当前阶段
    what_is_new_this_time="...",     # 本次新变化
    similar_past_topics=[...],       # 类似历史 topic
    important_background="...",      # 重要背景
    historical_confidence=0.85,      # 置信度
)
```

### 历史状态类型

| 状态 | 说明 |
|------|------|
| new | 全新 topic，首次出现 |
| evolving | 持续演化中的 topic |
| recurring | 周期性出现的 topic |
| milestone | 重大里程碑事件 |

### 当前阶段类型

| 阶段 | 说明 |
|------|------|
| emerging | 刚刚出现 |
| growing | 快速增长 |
| peak | 达到峰值 |
| declining | 热度下降 |
| stable | 稳定状态 |

## AnalystAgent

### 职责

Analyst 负责"价值判断"，回答以下问题：
- 这个 topic 为什么重要？
- 对谁重要？
- 当前是什么趋势阶段？
- 后续应该追踪什么？

### 输入

```python
AnalystInput(
    topic_id=100,
    topic_summary="GPT-5 发布",
    representative_items=[...],
    tags=["ai", "openai"],
    board_type="tech",
    historian_output={...},          # Historian 输出
    metrics={                        # 指标数据
        "item_count": 15,
        "source_count": 5,
        "heat_score": 0.85,
        "trend_score": 0.9,
    },
)
```

### 输出

```python
AnalystOutput(
    why_it_matters="...",            # 为什么重要
    system_judgement="high_priority", # 系统判断
    likely_audience=[...],           # 可能受众
    follow_up_points=[...],          # 后续追踪点
    trend_stage="emerging",          # 趋势阶段
    confidence=0.88,                 # 置信度
    evidence_summary="...",          # 证据摘要
)
```

### 系统判断类型

| 判断 | 说明 |
|------|------|
| high_priority | 高优先级，需要重点关注 |
| medium_priority | 中等优先级 |
| low_priority | 低优先级 |
| worth_tracking | 值得持续追踪 |
| noise | 噪音，可忽略 |

## 工作流执行

### 完整流程

```python
async def enrich_topic(topic_id: int):
    # Step 1: 刷新时间线
    await timeline_service.refresh_topic_timeline(topic_id)
    
    # Step 2: 运行 Historian
    historian_output = await historian_service.run_for_topic(topic_id)
    
    # Step 3: 保存 topic memory
    await topic_memory_service.update_from_historian(
        topic_id, historian_output
    )
    
    # Step 4: 运行 Analyst（使用 Historian 输出）
    analyst_output = await analyst_service.run_for_topic(
        topic_id, historian_output=historian_output
    )
    
    # Step 5: 保存 insight
    await insight_service.update_from_analyst(
        topic_id, analyst_output
    )
```

### 使用 Workflow 类

```python
from app.agent_runtime.workflow import HistorianThenAnalystWorkflow

workflow = HistorianThenAnalystWorkflow(
    historian_service=historian_service,
    analyst_service=analyst_service,
)

result = await workflow.execute(topic_id=100)

if result.success:
    historian_output = result.metadata["historian_output"]
    analyst_output = result.metadata["analyst_output"]
```

### 部分执行

```python
# 只运行 Historian
result = await workflow.execute(topic_id=100, skip_analyst=True)

# 只运行 Analyst
result = await workflow.execute(topic_id=100, skip_historian=True)
```

## 工具链

### Historian Tools

| 工具 | 用途 |
|------|------|
| retrieve_topic_timeline | 获取 topic 时间线 |
| retrieve_topic_snapshots | 获取历史快照 |
| retrieve_related_topics | 获取相关 topic |
| retrieve_entity_memories | 获取实体记忆 |
| retrieve_historical_judgements | 获取历史判断 |

### Analyst Tools

| 工具 | 用途 |
|------|------|
| get_topic_metrics | 获取 topic 指标 |
| get_recent_topic_items | 获取最近内容 |
| get_topic_tags | 获取标签 |
| get_historian_output | 获取 Historian 输出 |
| get_related_entity_activity | 获取实体活动 |
| get_recent_judgements_for_topic | 获取最近判断 |

## 结果持久化

### Topic Memory 更新

Historian 输出会更新 topic_memory 表：
- history_summary
- historical_status
- current_stage
- key_milestones
- latest_historian_output_json

### Topic Insight 创建

Analyst 输出会创建 topic_insight 记录：
- why_it_matters
- system_judgement
- likely_audience
- follow_up_points
- trend_stage
- confidence

## 前端展示

Topic Detail 页面可展示：

```json
{
  "topic_id": 100,
  "summary": "GPT-5 发布",
  
  // 来自 Historian
  "history_summary": "OpenAI 自 2018 年开始...",
  "first_seen_at": "2024-01-15T10:00:00Z",
  "what_is_new_this_time": "首次发布 GPT-5...",
  "historical_status": "milestone",
  "timeline_points": [...],
  
  // 来自 Analyst
  "why_it_matters": "代表 AI 能力的重大突破...",
  "system_judgement": "high_priority",
  "likely_audience": ["AI 研究者", "开发者", "企业决策者"],
  "follow_up_points": ["关注采用率", "竞品反应", "监管动态"]
}
```

## 调试脚本

### 运行单个 Topic

```bash
python -m scripts.run_topic_enrichment --topic-id 100
```

### 只运行 Historian

```bash
python -m scripts.run_topic_enrichment --topic-id 100 --historian-only
```

### 只运行 Analyst

```bash
python -m scripts.run_topic_enrichment --topic-id 100 --analyst-only
```

### 不保存结果

```bash
python -m scripts.run_topic_enrichment --topic-id 100 --no-save
```

## 注意事项

1. **Historian 不是 Writer**：Historian 负责考证，不负责写文案
2. **Analyst 不替代 Ranking**：Analyst 做判断，不做最终排序
3. **顺序依赖**：Analyst 依赖 Historian 输出，需要先运行 Historian
4. **工具隔离**：Agent 通过工具访问数据，不直接操作数据库
5. **结果可追溯**：所有判断都会记录到 judgement_log
