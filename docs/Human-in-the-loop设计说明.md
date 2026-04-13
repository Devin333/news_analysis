# Human-in-the-loop 设计说明

## 概述

Human-in-the-loop (HITL) 模块提供人工干预能力，让编辑/运营人员能够：
- 审核和修正 AI 生成的内容
- 覆写系统决策
- 请求重新运行 Agent
- 手动合并/拆分主题

## 核心概念

### 操作类型 (EditorActionType)

| 类型 | 说明 | 目标 |
|------|------|------|
| approve | 批准内容 | copy, report |
| reject | 拒绝内容 | copy, report |
| revise_copy | 修改文案 | copy |
| reassign_board | 重新分配板块 | topic |
| split_topic | 拆分主题 | topic |
| merge_topic | 合并主题 | topic |
| rerun_agent | 重跑 Agent | topic, copy |
| pin | 置顶内容 | topic, report |
| unpin | 取消置顶 | topic, report |
| feature | 推荐内容 | topic |
| archive | 归档内容 | topic, report |
| restore | 恢复内容 | topic, report |

### 目标类型 (TargetType)

- `topic`: 主题
- `copy`: 文案
- `report`: 报告
- `item`: 原始条目
- `insight`: 洞察

### Agent 类型 (AgentType)

- `historian`: 历史学家 Agent
- `analyst`: 分析师 Agent
- `writer`: 写手 Agent
- `reviewer`: 审稿人 Agent

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                      Admin API                               │
│  POST /admin/copies/{id}/approve                            │
│  POST /admin/topics/{id}/rerun-historian                    │
│  POST /admin/topics/{id}/merge                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      HITLService                             │
│  - approve_copy()                                            │
│  - reject_copy()                                             │
│  - revise_copy()                                             │
│  - override_topic_board()                                    │
│  - request_rerun_agent()                                     │
│  - merge_topics_manual()                                     │
│  - split_topic_manual()                                      │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│EditorActionRepo │ │   TopicRepo     │ │   CopyRepo      │
│                 │ │                 │ │                 │
│ - create()      │ │ - update_board()│ │ - update_status │
│ - list_by_target│ │ - merge_into()  │ │ - update_content│
│ - update_status │ │ - split_items() │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

## 数据模型

### EditorAction 表

```sql
CREATE TABLE editor_actions (
    id SERIAL PRIMARY KEY,
    target_type VARCHAR(50) NOT NULL,
    target_id INTEGER NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    action_payload_json JSONB,
    editor_key VARCHAR(100) NOT NULL,
    reason TEXT,
    notes TEXT,
    status VARCHAR(20) DEFAULT 'completed',
    error_message TEXT,
    parent_action_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_editor_actions_target ON editor_actions(target_type, target_id);
CREATE INDEX idx_editor_actions_editor ON editor_actions(editor_key);
CREATE INDEX idx_editor_actions_type ON editor_actions(action_type);
```

## 操作流程

### 批准/拒绝流程

```
编辑查看待审内容
       │
       ▼
┌──────────────┐
│ 审核内容质量  │
└──────────────┘
       │
   ┌───┴───┐
   ▼       ▼
批准     拒绝
 │        │
 ▼        ▼
更新状态  记录原因
 │        │
 ▼        ▼
记录操作  可选：建议修改
```

### Agent 重跑流程

```
编辑发现问题
       │
       ▼
┌──────────────┐
│ 请求重跑Agent │
└──────────────┘
       │
       ▼
记录 pending 状态
       │
       ▼
调度器获取待处理
       │
       ▼
执行 Agent 重跑
       │
       ▼
更新为 completed
```

### 主题合并流程

```
编辑发现重复主题
       │
       ▼
┌──────────────┐
│ 选择目标主题  │
└──────────────┘
       │
       ▼
选择源主题列表
       │
       ▼
执行合并操作
       │
       ▼
移动所有 items
       │
       ▼
标记源主题为已合并
```

## API 接口

### 批准文案

```http
POST /admin/copies/{copy_id}/approve
Content-Type: application/json

{
    "editor_key": "editor@example.com",
    "reason": "Content quality verified",
    "notes": "Minor grammar issues fixed"
}
```

### 拒绝文案

```http
POST /admin/copies/{copy_id}/reject
Content-Type: application/json

{
    "editor_key": "editor@example.com",
    "reason": "Factual errors detected",
    "suggest_revision": true
}
```

### 重跑 Historian

```http
POST /admin/topics/{topic_id}/rerun-historian
Content-Type: application/json

{
    "editor_key": "editor@example.com",
    "reason": "Missing historical context"
}
```

### 合并主题

```http
POST /admin/topics/{target_id}/merge
Content-Type: application/json

{
    "editor_key": "editor@example.com",
    "source_topic_ids": [456, 789],
    "reason": "Duplicate topics about same event"
}
```

### 查看操作历史

```http
GET /admin/actions/target/topic/123
```

### 获取待处理重跑

```http
GET /admin/pending-reruns?agent_type=historian
```

## 使用示例

### 批准文案

```python
from app.editorial.hitl_service import HITLService

service = HITLService(action_repo=action_repo, copy_repo=copy_repo)

result = await service.approve_copy(
    copy_id=123,
    editor_key="editor@example.com",
    reason="Content verified",
)

if result.success:
    print(f"Approved, action ID: {result.action_id}")
```

### 请求 Agent 重跑

```python
from app.contracts.dto.editorial import RerunAgentDTO, AgentType, TargetType

result = await service.request_rerun_agent(
    RerunAgentDTO(
        target_type=TargetType.TOPIC,
        target_id=123,
        agent_type=AgentType.HISTORIAN,
        editor_key="editor@example.com",
        reason="Need more historical context",
    )
)
```

### 合并主题

```python
from app.contracts.dto.editorial import MergeTopicsDTO

result = await service.merge_topics_manual(
    MergeTopicsDTO(
        source_topic_ids=[456, 789],
        target_topic_id=123,
        editor_key="editor@example.com",
        reason="Duplicate topics",
    )
)
```

## 命令行工具

### 重跑 Agent

```bash
# 重跑单个 Agent
python scripts/admin_rerun_topic.py --topic-id 123 --agent historian

# 重跑所有 Agent
python scripts/admin_rerun_topic.py --topic-id 123 --all

# 强制重跑
python scripts/admin_rerun_topic.py --topic-id 123 --agent analyst --force
```

### 合并主题

```bash
# 合并主题
python scripts/admin_merge_topics.py --target 123 --sources 456 789

# 带原因
python scripts/admin_merge_topics.py --target 123 --sources 456 789 --reason "Duplicates"

# 预览模式
python scripts/admin_merge_topics.py --target 123 --sources 456 789 --dry-run
```

## 审计与追溯

所有编辑操作都会被记录，支持：

1. **操作追溯**: 查看某个内容的所有操作历史
2. **编辑统计**: 统计编辑的操作量
3. **操作回滚**: 通过 parent_action_id 关联回滚操作
4. **错误追踪**: 记录失败操作的错误信息

## 与其他模块集成

### 与 Review 模块

- HITL 的 approve/reject 会更新 copy 的 review_status
- 可以覆写 Reviewer Agent 的自动审核结果

### 与 Agent Runtime

- pending 状态的 rerun 请求会被调度器获取
- Agent 执行完成后更新操作状态

### 与 Topic Service

- merge/split 操作会调用 TopicRepository 的相应方法
- 操作完成后触发相关 Agent 重新处理

## 最佳实践

1. **记录原因**: 所有操作都应该记录原因，便于追溯
2. **批量操作**: 对于大量相似操作，使用脚本批量处理
3. **定期审计**: 定期检查操作日志，发现异常模式
4. **权限控制**: 生产环境应该添加编辑权限验证
