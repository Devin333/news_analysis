# Agent Runtime 顶层结构说明

## 概述

Agent Runtime 是 NewsAgent 的自研 Agent 框架核心，用于驱动 AI 智能体执行复杂任务。

## 核心组件

### 1. 消息系统 (`app/agent_runtime/messages.py`)

定义 Agent 运行时的消息类型：

```python
BaseMessage          # 基础消息
├── SystemMessage    # 系统提示
├── UserMessage      # 用户输入
├── AssistantMessage # 助手回复
├── ToolMessage      # 工具调用消息
└── ObservationMessage # 观察结果
```

每个消息包含：
- `role` - 消息角色
- `content` - 消息内容
- `created_at` - 创建时间
- `metadata` - 扩展元数据

### 2. 状态管理 (`app/agent_runtime/state.py`)

#### AgentStatus 枚举

```python
IDLE         # 空闲
RUNNING      # 运行中
WAITING_TOOL # 等待工具执行
COMPLETED    # 已完成
FAILED       # 失败
```

#### AgentState 类

管理 Agent 执行状态：

| 属性 | 类型 | 说明 |
|------|------|------|
| step_count | int | 当前步数 |
| max_steps | int | 最大步数限制 |
| messages | list | 消息历史 |
| tool_history | list | 工具调用历史 |
| intermediate_results | dict | 中间结果 |
| status | AgentStatus | 当前状态 |

#### ToolCall / ToolResult

```python
ToolCall:
  - id: str           # 调用 ID
  - name: str         # 工具名称
  - arguments: dict   # 调用参数

ToolResult:
  - call_id: str      # 对应的调用 ID
  - name: str         # 工具名称
  - output: Any       # 执行输出
  - error: str | None # 错误信息
```

### 3. 输出 DTO (`app/contracts/dto/agent_outputs.py`)

#### ToolCallDTO / ToolResultDTO

工具调用的请求和响应数据结构。

#### AgentStepRecordDTO

单步执行记录：
- `step_index` - 步骤索引
- `thought` - 思考过程
- `tool_call` - 工具调用
- `tool_result` - 工具结果
- `observation` - 观察结果

#### AgentFinalOutputDTO

最终输出：
- `status` - 执行状态
- `final_answer` - 最终答案
- `steps` - 步骤记录列表
- `metadata` - 元数据

### 4. 协议定义

#### AgentProtocol (`app/contracts/protocols/agents.py`)

```python
class AgentProtocol(Protocol):
    async def run(self, task: str, **context) -> AgentFinalOutputDTO:
        """执行完整任务"""
        ...

    async def step(self, state: AgentState) -> AgentState:
        """执行单步"""
        ...
```

#### ToolProtocol (`app/contracts/protocols/tools.py`)

```python
class ToolProtocol(Protocol):
    @property
    def name(self) -> str: ...
    
    @property
    def description(self) -> str: ...
    
    async def execute(self, **kwargs) -> Any: ...
    
    def get_schema(self) -> dict: ...
```

## 执行流程

```
1. 初始化 AgentState
2. 循环执行 step() 直到:
   - 达到 max_steps
   - status 变为 COMPLETED/FAILED
3. 每个 step:
   a. LLM 生成思考 + 工具调用
   b. 执行工具
   c. 记录结果
   d. 更新状态
4. 返回 AgentFinalOutputDTO
```

## 扩展点

1. **自定义 Agent**: 实现 `AgentProtocol`
2. **自定义工具**: 实现 `ToolProtocol`
3. **状态持久化**: 扩展 `AgentState` 序列化
4. **执行追踪**: 利用 `AgentStepRecordDTO` 记录

## 后续计划

- Week 3+: 实现具体 Agent（采集、分析、聚合）
- 集成 LLM Provider
- 工具注册中心
- 执行日志持久化
