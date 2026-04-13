# Week 9-12 复杂记忆与历史分析里程碑

## 概述

Week 9-12 完成了 NewsAgent 系统的复杂记忆层和历史分析能力建设。这是系统从"信息聚合"升级到"研究型 Agent 系统"的关键阶段。

## 核心能力

### 1. 记忆系统 (Week 9)

#### Topic Long-term Memory
- 存储 topic 的长期历史状态
- 追踪 first_seen_at、last_seen_at
- 记录 historical_status（new/evolving/recurring/milestone）
- 保存 history_summary 和 key_milestones

#### Topic Snapshots
- 定期快照 topic 状态
- 记录 heat_score、trend_score
- 保存 item_count、source_count
- 支持历史对比分析

#### Entity Memory
- 存储实体（人物、组织、产品）的长期记忆
- 关联 topic 与 entity 关系
- 追踪实体活动历史

#### Judgement Memory
- 保存系统历史判断
- 记录 agent_name、judgement_type
- 支持后续判断校验和趋势反思

### 2. 历史层 (Week 10)

#### Timeline Repository
- 存储 topic 时间线事件
- 支持按时间范围查询
- 标记里程碑事件

#### Timeline Extractor
- 从 normalized_item 抽取事件
- 从 topic_snapshot 抽取事件
- 支持多种事件类型：
  - first_seen
  - release_published
  - paper_published
  - repo_created
  - topic_summary_changed

#### Timeline Builder
- 聚合多来源事件
- 排序和去重
- 合并相近事件
- 标记 milestone

#### Hybrid Retrieval
- 结构化检索（topic_id、entity、time_range）
- 语义检索（embedding similarity）
- 混合召回策略

### 3. Agent 层 (Week 11-12)

#### HistorianAgent
职责：
- 回溯 topic 历史
- 判断历史状态
- 识别变化点
- 提供历史背景

输出：
- first_seen_at
- history_summary
- timeline_points
- historical_status
- what_is_new_this_time
- similar_past_topics
- important_background

#### AnalystAgent
职责：
- 价值判断
- 受众分析
- 趋势判断
- 后续追踪建议

输出：
- why_it_matters
- system_judgement
- likely_audience
- follow_up_points
- trend_stage
- confidence
- evidence_summary

### 4. 工作流层

#### Topic Enrichment Pipeline
完整流程：
1. refresh_timeline
2. run_historian
3. save_topic_memory
4. run_analyst
5. save_insight
6. refresh_topic_detail

#### Historian → Analyst Workflow
- 串联执行
- Historian 输出作为 Analyst 输入
- 支持部分执行

## 数据模型

### 新增表

| 表名 | 用途 |
|------|------|
| topic_memory | Topic 长期记忆 |
| topic_snapshot | Topic 快照 |
| entity | 实体基础信息 |
| entity_memory | 实体记忆 |
| topic_entity | Topic-Entity 关系 |
| judgement_log | 判断日志 |
| topic_timeline_event | 时间线事件 |
| topic_insight | Topic 洞察 |

### DTO 结构

```
TopicMemoryDTO
├── topic_id
├── first_seen_at
├── last_seen_at
├── historical_status
├── current_stage
├── history_summary
├── key_milestones
└── last_refreshed_at

TopicSnapshotDTO
├── topic_id
├── snapshot_at
├── summary
├── why_it_matters
├── system_judgement
├── heat_score
├── trend_score
├── item_count
└── source_count

TimelinePointDTO
├── event_time
├── event_type
├── title
├── description
├── source_item_id
├── source_type
└── importance_score
```

## API 端点

### Memory API
- `GET /topics/{id}/memory` - 获取 topic 记忆
- `GET /topics/{id}/snapshots` - 获取 topic 快照列表
- `GET /entities/{id}/memory` - 获取 entity 记忆
- `GET /judgements/{target_type}/{target_id}` - 获取判断记录

### Timeline API
- `GET /topics/{id}/timeline` - 获取 topic 时间线
- `GET /topics/{id}/history-context` - 获取历史上下文

### Insight API
- `GET /topics/{id}/insight` - 获取 topic 洞察

## 关键设计原则

### 1. Agent 不直接访问数据库
Agent 必须通过 tools 或 retrieval service 获取上下文。

### 2. Historian 不是 Writer
Historian 负责回溯和对照，不负责写文案。

### 3. Analyst 不替代 Ranking
Analyst 做意义判断，不做最终排序。

### 4. Judgement 先存后用
即使当前未完全使用，也要先持久化判断记录。

### 5. Timeline 允许不完美
第一版重点是可用、可追踪、可扩展。

## 验收标准

- [x] Topic memory 可创建和更新
- [x] Topic snapshot 可写入和查询
- [x] Entity memory 可存历史摘要
- [x] Topic 与 entity 可建立关系
- [x] Judgement 可持久化
- [x] Timeline 可按 topic 和时间查询
- [x] Historian 可输出历史增强结果
- [x] Analyst 可输出价值判断
- [x] Enrichment pipeline 可串联执行
- [x] Topic detail 可展示历史和洞察

## 后续扩展

1. **趋势验证**：对比历史判断与实际结果
2. **实体图谱**：构建更完整的实体关系网络
3. **语义检索增强**：优化 embedding 召回
4. **多 Agent 协作**：引入更多专业 Agent
