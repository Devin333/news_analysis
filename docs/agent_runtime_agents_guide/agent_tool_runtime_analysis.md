# Agent Tool Runtime 代码详解与改进建议

## 1. 文档目标

这份文档面向**初学者**，从 **Agent 研究者** 的视角，系统分析你这组 `tool runtime` 代码的实现细节，并结合当前 GitHub 上一些常见 Agent 项目的设计思路，指出哪些地方可以继续改进。

重点不只是“这段代码在做什么”，而是：

- 为什么要这样设计
- 这种设计在 Agent Runtime 里处于什么位置
- 它和主流项目相比差在哪里
- 作为初学者，应该先学会哪些核心思想

---

## 2. 先看整体：这组代码在 Agent 系统中处于什么位置

你的代码主要对应 Agent Runtime 里的 **Tool Layer（工具层）**。

一个典型的 Agent 执行链路通常是：

```text
用户任务
  -> LLM 推理
  -> 决定是否调用工具
  -> Tool Registry 找到工具
  -> Tool Executor 执行工具
  -> ToolResult 返回结果
  -> 转成 observation 写回上下文
  -> LLM 继续下一轮决策
```

你的这组文件大致对应：

- `base.py`：工具抽象基类
- `registry.py`：工具注册中心
- `executor.py`：工具执行器
- `history_tools.py`：Historian Agent 的业务工具
- `analysis_tools.py`：Analyst Agent 的业务工具
- `__init__.py`：统一导出入口

从架构上看，这是一个非常经典的自研 Agent Runtime 设计。

---

## 3. 文件级总览

## 3.1 `__init__.py`

这个文件的作用是把工具模块统一暴露出去，形成包级别的公共出口。

```python
from app.agent_runtime.tools.base import (
    BaseTool,
    SyncTool,
    ToolArgsSchema,
    ToolDefinition,
    ToolResult,
)
```

### 它的价值

这类 `__init__.py` 的意义不在于逻辑，而在于**对外 API 整理**。  
外部模块只需要：

```python
from app.agent_runtime.tools import ToolExecutor, ToolRegistry
```

而不需要关心这些类型分别定义在哪个文件里。

### 优点

- 对外接口整洁
- 降低导入路径复杂度
- 方便未来重构内部文件结构

### 研究者视角

这相当于在做“runtime API surface”的整理。  
成熟项目一般都会做这一层，因为框架最终不是给自己看，而是给“使用者”看。

---

## 3.2 `base.py`

这是整个工具系统最核心的抽象层。  
它定义了：

- `ToolArgsSchema`
- `ToolResult`
- `ToolDefinition`
- `BaseTool`
- `SyncTool`

---

### 3.2.1 `ToolArgsSchema`

```python
class ToolArgsSchema(BaseModel):
    pass
```

这是一个空的 Pydantic 基类。

### 设计意图

它说明你已经意识到：  
**工具参数不应该只是裸 `dict`，而应该有 schema。**

这是非常正确的方向。

### 当前问题

虽然你定义了 `ToolArgsSchema`，但后面的具体工具并没有真正统一继承它，而是直接各自写自己的 `BaseModel`：

```python
class GetTopicMetricsInput(BaseModel):
    ...
```

这说明你已经有了正确抽象，但还没有完全落地。

### 改进建议

可以让 `BaseTool` 明确声明：

```python
args_schema: type[ToolArgsSchema] | None = None
```

然后让每个工具显式绑定自己的输入模型。这样：

- 参数校验可以统一
- JSON Schema 可以自动生成
- 给 LLM 的 tool definition 可以自动导出

---

### 3.2.2 `ToolResult`

```python
@dataclass
class ToolResult:
    success: bool
    output: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

这是你设计得很好的一个点。

### 为什么重要

在 Agent Runtime 里，工具结果如果不标准化，后面会非常乱。  
有的返回字符串，有的返回 dict，有的抛异常，有的返回 None，最后 observation 很难统一处理。

`ToolResult` 统一了以下语义：

- 是否成功
- 成功时输出什么
- 失败时错误是什么
- 额外元信息是什么

### `ok()` / `fail()` 的作用

```python
ToolResult.ok(output, ...)
ToolResult.fail(error, ...)
```

这能让业务层更统一地构造返回值。

### 研究者视角

这是“动作结果标准化”的第一步。  
以后你可以继续扩展：

- `retryable`
- `error_code`
- `safe_for_llm`
- `raw_output`
- `artifact_uri`

### 这里的关键问题

你的很多具体工具写的是：

```python
ToolResult(success=True, data={...})
```

但 `ToolResult` 定义里没有 `data` 字段，只有 `output`。  
这说明**抽象层和实现层接口已经不一致了**。

这是当前代码里最重要的问题之一。

---

### 3.2.3 `ToolDefinition`

```python
@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    required_params: list[str] = field(default_factory=list)
    examples: list[dict[str, Any]] = field(default_factory=list)
```

它负责描述“工具给 LLM 看起来是什么样的”。

### 它解决的问题

LLM 不关心 Python 类，只关心：

- 工具名
- 工具描述
- 参数 schema

`to_openai_format()` 就是在把内部工具定义转换成 OpenAI function calling 风格。

```python
{
  "type": "function",
  "function": {
    "name": self.name,
    "description": self.description,
    "parameters": {...}
  }
}
```

### 研究者视角

这一步很关键，因为它意味着你的工具系统已经不是“给人手调”的，而是朝“给模型调用”方向设计了。

### 当前不足

虽然你定义了 `ToolDefinition`，但你没有真正把参数 schema 自动接上。  
现在 `BaseTool.parameters()` 默认返回 `{}`，`required_params()` 默认返回 `[]`。

也就是说：

- 这个抽象层是对的
- 但 schema 自动化还没落地

---

### 3.2.4 `BaseTool`

这是你的核心抽象。

```python
class BaseTool(ABC):
```

它要求所有工具具备：

- `name`
- `description`
- `execute`

### 这是正确的思想

因为从 Agent Runtime 的角度看，一个工具最本质的三个属性就是：

1. 我是谁
2. 我能做什么
3. 我怎么执行

### `validate_args()`

```python
def validate_args(self, **kwargs: Any) -> tuple[bool, str | None]:
```

当前实现只是检查 required 参数是否存在。

### 优点

- 至少做了最基础校验
- 让 tool 执行前有个统一入口

### 不足

这个校验太弱了：

- 只检查字段存在
- 不检查类型
- 不检查取值范围
- 不检查嵌套结构

而你其实已经在具体工具里用 Pydantic 了，所以这里更合理的做法是：  
**统一在基类层完成 schema 校验，而不是每个工具自己手动 `InputModel(**input_data)`。**

---

### 3.2.5 `safe_execute()`

这是 `BaseTool` 最有价值的函数之一。

```python
async def safe_execute(self, **kwargs: Any) -> ToolResult:
```

它统一处理：

1. 参数校验
2. 调用实际执行逻辑
3. 捕获异常
4. 永远返回 `ToolResult`

### 为什么这很重要

在 Agent Runtime 里，工具层不能随便把异常抛到最上层，否则会直接中断 Agent Loop。

所以 `safe_execute()` 的价值就是：

> 工具调用是“不可信动作”，必须统一兜底。

### 研究者视角

这是 Runtime 的“容错边界”。  
很多成熟框架都会有类似包装层。

---

### 3.2.6 `SyncTool`

```python
class SyncTool(BaseTool):
    @abstractmethod
    def execute_sync(self, **kwargs: Any) -> ToolResult:
        pass
```

它的作用是让同步工具也能接到异步 runtime 里。

### 为什么有用

因为很多业务工具本质上是同步函数，但你的 Agent Runtime 很可能整体是 async 的。  
如果没有这一层，你就要在每个同步工具里单独适配。

### 当前不足

现在只是简单包装：

```python
async def execute(self, **kwargs: Any) -> ToolResult:
    return self.execute_sync(**kwargs)
```

严格来说，这并没有把同步阻塞问题彻底解决。  
如果同步工具执行时间长，依然可能阻塞事件循环。

### 后续更合理的做法

如果某些同步工具可能比较重，可以考虑：

- `asyncio.to_thread()`
- 线程池执行
- 进程池执行

---

## 3.3 `registry.py`

这个文件定义了 `ToolRegistry`，也就是“工具注册中心”。

Agent Runtime 里，注册中心的意义是：

> 把“工具名字”映射到“工具实例”。

---

### 3.3.1 内部结构

```python
self._tools: dict[str, BaseTool] = {}
```

最核心的数据结构非常直接：  
用字典维护 `tool_name -> tool_instance`。

### 这是合理的

因为工具调用阶段最常见的操作就是：

- 根据名字查工具
- 判断工具是否存在
- 列出所有工具定义给 LLM

字典正好适合这个需求。

---

### 3.3.2 `register()`

```python
def register(self, tool: BaseTool) -> None:
```

### 它做了什么

- 检查工具名是否重复
- 注册到 `_tools`
- 写日志

### 这是很重要的保护

```python
if tool.name in self._tools:
    raise ValueError(...)
```

如果没有这个检查，两个同名工具会互相覆盖，LLM 调用行为会变得不可预测。

### 研究者视角

注册中心本质上是“能力目录”。  
目录最重要的一点就是：**名字唯一。**

---

### 3.3.3 `get()` / `get_required()`

这两个接口的区别也很清楚：

- `get()`：取不到返回 `None`
- `get_required()`：取不到直接报错

这种双接口设计是不错的。

### 为什么好

因为不同调用方对错误处理的预期不一样：

- Executor 想自己兜底，就用 `get()`
- 某些初始化流程要求强约束，就用 `get_required()`

---

### 3.3.4 `list_definitions()` / `to_openai_tools()`

这两个接口非常关键。

```python
def list_definitions(self) -> list[ToolDefinition]:
def to_openai_tools(self) -> list[dict[str, Any]]:
```

### 意义

它们把 registry 从“内部管理器”变成了“对模型暴露能力”的中间层。

也就是说 registry 不只是存工具，还负责向 LLM 提供“你现在可以调用哪些工具”。

### 研究者视角

这是从“代码组织”走向“runtime capability exposure”的关键一步。

---

### 3.3.5 全局单例 `get_global_registry()`

```python
_global_registry: ToolRegistry | None = None
```

### 优点

- 使用方便
- 小项目里很省事
- 不需要层层传递 registry

### 缺点

在真正复杂的 Agent 系统里，全局单例容易引发：

- 隐式依赖
- 测试污染
- 多 agent / 多 tenant 之间互相干扰
- 生命周期难管理

### 结论

对于初学者学习来说，这种设计完全可以接受。  
但如果以后你要做：

- 多 agent runtime
- 插件化 tool pack
- 多租户
- 独立测试环境

建议尽量减少对全局 registry 的依赖。

---

## 3.4 `executor.py`

这个文件是整个工具 runtime 的“调度与执行核心”。

它定义了：

- `ExecutionContext`
- `ExecutionResult`
- `ToolExecutor`

---

### 3.4.1 `ExecutionContext`

```python
@dataclass
class ExecutionContext:
    call_id: str
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

### 它的作用

这是一次工具调用的上下文封装。

比直接传：

```python
execute(tool_name, args)
```

更强，因为它能携带额外信息：

- 调用 ID
- 超时限制
- 额外元数据

### 为什么这是 Agent Runtime 的重要设计

因为一个真正成熟的 tool call 并不只是“调一下函数”，它还可能带有：

- tracing 信息
- request_id
- user_id
- step_id
- retry 次数
- budget 信息

`ExecutionContext` 已经是往这个方向迈出了一步。

---

### 3.4.2 `ExecutionResult`

```python
@dataclass
class ExecutionResult:
    call_id: str
    tool_name: str
    result: ToolResult
    duration_ms: float = 0.0
    executed_at: float = 0.0
```

### 它为什么有价值

`ToolResult` 只关心“工具业务结果”。  
但 runtime 还关心“执行元信息”：

- 这次调用是谁
- 花了多久
- 什么时候执行的

所以 `ExecutionResult` 是“业务结果 + 执行元信息”的组合包装。

### 研究者视角

这很像 LangGraph / OpenTelemetry 里常见的“span result”思路：  
动作本身和动作的执行记录应该分开。

---

### 3.4.3 `to_observation()`

这个函数非常值得你重点学。

```python
def to_observation(self) -> str:
```

### 为什么关键

Agent 不会直接理解 Python 对象。  
下一轮 LLM 需要的是 observation，也就是“可以放回上下文的可读信息”。

所以这个函数的本质是：

> 把工具执行结果，转换成模型下一轮可消费的观察。

### 当前实现逻辑

- 成功时：
  - 字符串直接返回
  - dict 转成 JSON 字符串
  - 其他类型转 `str()`
- 失败时：
  - 返回 `"Error: ..."`

### 这是非常经典的 runtime 思路

你之前学过“为什么 tool result 不是直接返回用户，而是先写回 messages”，这个函数就是那个思想的具体落点之一。

### 但这里也有潜在问题

当前 observation 仍然比较原始：

- dict 直接 JSON dump，信息可能过于冗长
- 没有做摘要
- 没有按工具类型做格式化
- 没有做敏感信息过滤

### 更好的方向

不同工具最好有不同的 observation serializer，例如：

- search tool：返回摘要 + top k 结果
- db tool：返回结构化表格摘要
- memory tool：返回精炼要点
- analysis tool：返回关键结论而不是全量数据

---

### 3.4.4 `ToolExecutor.execute()`

这是核心执行入口。

```python
async def execute(self, tool_name, arguments=None, *, call_id=None, timeout=None)
```

### 它做了什么

1. 生成 call_id
2. 记录开始时间
3. 从 registry 查找工具
4. 工具不存在则返回失败结果
5. 调用 `tool.safe_execute(**arguments)`
6. 记录耗时
7. 返回 `ExecutionResult`

### 这个结构本身是正确的

它把：

- 工具查找
- 工具执行
- 异常处理
- 元信息采集

全部集中在一个 runtime 层里，而不是散落在业务代码中。

### 研究者视角

这是把“工具”从普通函数提升为“runtime-managed action”的关键步骤。

---

### 3.4.5 最大问题：`timeout` 参数没真正生效

你在接口里已经写了：

```python
timeout: float | None = None
```

但实际执行时并没有用 `asyncio.wait_for` 或其他方式去约束执行时长。

也就是说，这个 timeout 目前只是“接口有了，能力没实现”。

### 为什么这是问题

在 Agent 系统里，tool 是最不稳定的部分之一：

- 可能查数据库很慢
- 可能请求网络超时
- 可能第三方 API 卡住
- 可能出现死循环

如果 timeout 不生效，agent loop 很容易被某个工具拖死。

---

### 3.4.6 `execute_many()`

目前是串行执行：

```python
for tool_name, arguments in calls:
    result = await self.execute(tool_name, arguments)
```

### 优点

- 简单
- 顺序稳定
- 调试方便

### 局限

如果多个工具没有依赖关系，串行会浪费时间。  
以后可以考虑增加：

- 并行执行
- 并发数限制
- 失败策略控制

不过对初学者来说，先保持串行是合理的。

---

## 3.5 `history_tools.py`

这是 Historian Agent 的具体业务工具集合。

### 它体现了一个很重要的思想

> BaseTool / Registry / Executor 是“运行时框架层”
> `history_tools.py` / `analysis_tools.py` 是“业务能力层”

这个分层是对的。

---

### 3.5.1 输入模型定义

比如：

```python
class RetrieveTopicTimelineInput(BaseModel):
    topic_id: int
    limit: int = 50
```

### 好处

- 参数清晰
- 类型明确
- 默认值明确
- 后续可自动生成 schema

### 初学者需要理解的一点

这一步不是“为了写得好看”，而是为了避免模型乱传参数。

在 Agent 系统里，LLM 不是一个完全可靠的调用方。  
它会：

- 漏字段
- 字段名写错
- 类型传错
- 传一些奇怪的嵌套数据

所以工具参数 schema 是非常必要的。

---

### 3.5.2 具体工具实现模式

以 `RetrieveTopicTimelineTool` 为例，它的流程是：

1. 用 Pydantic 解析输入
2. 获取 retrieval service
3. 调 service 取 timeline
4. 把返回对象序列化成 dict
5. 包成 `ToolResult`

这是比较标准的业务 tool 模式。

---

### 3.5.3 当前最大问题：依赖注入没有真正完成

每个工具里都有这种逻辑：

```python
retrieval_service = self._get_retrieval_service()
if retrieval_service is None:
    return ToolResult(success=False, error="Retrieval service not available")
```

然后：

```python
def _get_retrieval_service(self):
    return getattr(self, "_retrieval_service", None)
```

### 这说明什么

说明你知道工具不应该自己 new service，而应该由外部注入。  
这个方向是对的。

### 但为什么说“没真正完成”

因为你现在并没有正式的注入机制，只是在工具实例上“偷偷挂一个属性”。

这会导致：

- 工具依赖不透明
- 测试不方便
- IDE 也看不出这个依赖
- 初始化流程容易漏掉

### 更好的做法

显式构造：

```python
class RetrieveTopicTimelineTool(BaseTool):
    def __init__(self, retrieval_service: MemoryRetrievalService):
        self.retrieval_service = retrieval_service
```

这样依赖是可见的、明确的、可测试的。

---

### 3.5.4 另一个明显问题：`ToolResult(data=...)` 接口错位

在这些业务工具里，你大量写了：

```python
ToolResult(success=True, data={...})
```

而基类 `ToolResult` 是：

```python
ToolResult(success, output=None, error=None, metadata=...)
```

这会直接造成接口错位。

### 这类 bug 说明什么

从工程视角，它说明当前 tool runtime 还处于“骨架已经成型，但统一性还没收口”的阶段。

这是非常常见的开发阶段问题。

---

### 3.5.5 序列化层思路是对的

你把领域对象转成了可序列化 dict：

```python
{
  "event_time": e.event_time.isoformat(),
  "event_type": e.event_type,
  ...
}
```

这是必须做的。  
因为 tool result 最终要么给 LLM，要么写日志，要么做持久化，都不适合直接塞 ORM / dataclass / domain object。

---

## 3.6 `analysis_tools.py`

这个文件和 `history_tools.py` 很像，只是面向 Analyst Agent。

提供的工具包括：

- 获取 topic metrics
- 获取 recent items
- 获取 tags
- 获取 historian output
- 获取 related entity activity
- 获取 recent judgements

### 架构上是合理的

这说明你已经开始按“agent 职责”而不是按“数据库表”去组织工具了。

这是一个很好的 Agent 研究思路。  
因为工具最好和 Agent 的任务语义对齐，而不是和底层实现对齐。

例如：

- Historian Agent 关注历史演化
- Analyst Agent 关注指标与价值判断

这会比直接设计成：

- `query_topic_table`
- `query_item_table`
- `query_tag_table`

更符合 agent 的思考方式。

---

# 4. 当前代码的核心问题总结

这里我从研究者和工程实践两个角度，把最重要的问题收一下。

---

## 4.1 问题一：抽象层与实现层接口不一致

最典型的是：

- `ToolResult` 定义的是 `output`
- 具体工具返回的是 `data`

这属于基础接口错位。

### 为什么严重

因为 runtime 的统一抽象一旦错位，后续所有层都会出问题：

- executor 取不到结果
- observation 生成错误
- 业务层和框架层对不上

### 优先级：最高

这个应该第一时间修。

---

## 4.2 问题二：schema 已经有了，但没有统一接入 runtime

现在的状态是：

- 具体工具自己手动定义 Pydantic 输入模型
- 基类层没有真正统一利用这些模型

### 问题所在

这会导致：

- schema 定义重复
- 参数校验逻辑分散
- tool definition 难以自动导出
- 模型调用接口不稳定

### 理想状态

工具应该显式声明 `args_schema`，基类统一完成：

- 参数解析
- 参数校验
- JSON Schema 生成

---

## 4.3 问题三：依赖注入方式太弱

`getattr(self, "_retrieval_service", None)` 只是一个过渡方案，不适合作为正式机制。

### 更好的方向

- 构造函数注入
- context 注入
- runtime service container 注入

---

## 4.4 问题四：timeout 只是接口声明，没有真正实现

在 executor 里 timeout 没有生效。

### 这会带来什么后果

- 某个工具卡住会拖死整个 agent loop
- runtime 缺少治理能力
- 难以做生产级稳定性保障

---

## 4.5 问题五：observation 生成过于粗糙

现在 `to_observation()` 只是做简单 JSON dump。

### 问题

这可能导致：

- token 浪费
- LLM 上下文过长
- 重点不突出
- 模型被原始细节淹没

### 更合理的方向

给不同工具定义专门的 observation serializer。

---

## 4.6 问题六：缺少更强的可观测性

虽然你记录了日志和 duration，但还缺：

- step_id / trace_id
- retry_count
- tool category
- input size / output size
- structured tracing

### 为什么这在 Agent 系统中特别重要

因为 agent bug 往往不是“某函数报错”，而是：

- 第 3 步为什么选了这个工具
- 参数为什么传成这样
- 结果为什么让模型误判
- 哪一步 token 爆了

所以工具层的 tracing 很重要。

---

# 5. 和 GitHub 上常见 Agent 项目相比，可以怎么理解

你问的是“跟现在 GitHub 上一些项目相比，这段代码还能怎么改”。  
这里我不去做表面上的“谁更火”，而是从设计思想上做对比。

---

## 5.1 和 LangChain / LangGraph 风格对比

LangChain / LangGraph 的典型特点是：

- 工具 schema 与模型调用接口集成得更深
- graph/step 状态管理更强
- tracing 能力更完整
- tool 调用和 message state 结合得更紧

### 你这套代码的优势

- 更容易看懂
- 控制权在自己手里
- 适合学习 runtime 本质
- 不会一上来就陷入框架黑箱

### 不足

- schema 自动化还弱
- 状态管理还没接起来
- tracing 和 timeout 不够
- observation 层不够精细

### 对初学者结论

你现在这种代码比直接上 LangGraph 更适合学习。  
因为你能看清 runtime 的骨架。

---

## 5.2 和 PydanticAI 风格对比

PydanticAI 非常强调：

- 类型安全
- schema 自动推导
- 输入输出校验
- agent 与工具的类型约束

### 你这套代码和它的差距

最核心的差距就是：

> 你已经意识到 schema 很重要，但还没把 schema 变成 runtime 的一等公民。

也就是：

- 你在“用 Pydantic”
- 它在“以 Pydantic 为核心组织 agent”

### 你最值得借鉴它的地方

把工具参数模型正式挂到 tool class 上，形成：

- 自动校验
- 自动 schema 导出
- 更强类型一致性

---

## 5.3 和 OpenAI Agents SDK / function calling 风格对比

OpenAI 官方思路通常更关注：

- 工具定义标准化
- function calling 协议对齐
- tool use 和 message loop 的整合

你的 `ToolDefinition.to_openai_format()` 已经在往这个方向走了。

### 说明什么

说明你现在这套 runtime 不是“封闭内部系统”，而是已经有潜力接到标准 function calling 模式上。

### 还差什么

- parameters 自动生成
- 更严格的 schema
- 结果序列化统一
- tool call / tool result 消息格式标准化

---

## 5.4 和 AutoGen / CrewAI 这类高层多智能体框架对比

这些框架更关注：

- agent 协作
- 角色分工
- 任务编排
- 多轮对话 orchestration

而你的代码更底层，关注的是：

- 单个 tool runtime 怎么搭

### 这是好事

因为如果 tool runtime 这层没打稳，多 agent 只是“搭积木搭在沙子上”。

初学者非常适合先学你现在这层，而不是一上来就追求多 agent 编排。

---

# 6. 初学者最值得先改的版本

下面我给你一个“学习优先级最高”的改进顺序。

---

## 第一步：先统一 `ToolResult`

把所有业务工具里的：

```python
ToolResult(success=True, data={...})
```

统一改成：

```python
ToolResult(success=True, output={...})
```

或者直接：

```python
return ToolResult.ok({...})
```

### 这是第一优先级

因为这是基础接口一致性问题。

---

## 第二步：把 `args_schema` 正式接到 `BaseTool`

例如：

```python
class BaseTool(ABC):
    args_schema: type[ToolArgsSchema] | None = None
```

然后在具体工具里：

```python
class RetrieveTopicTimelineTool(BaseTool):
    args_schema = RetrieveTopicTimelineInput
```

接着在 `safe_execute()` 里统一做：

- schema 解析
- 参数校验
- 错误转换

这样工具实现会更干净。

---

## 第三步：统一生成 tool definition schema

让 `get_definition()` 可以基于 `args_schema.model_json_schema()` 自动导出 `parameters`。

这样你就不需要手写：

- `parameters`
- `required_params`

也能自然接到 OpenAI function calling。

---

## 第四步：改正式依赖注入

不要再用：

```python
getattr(self, "_retrieval_service", None)
```

改成构造函数注入：

```python
class GetTopicMetricsTool(BaseTool):
    def __init__(self, retrieval_service):
        self.retrieval_service = retrieval_service
```

然后在注册时传入依赖。

---

## 第五步：给 executor 真正加上 timeout

例如用：

```python
await asyncio.wait_for(tool.safe_execute(...), timeout=timeout_value)
```

这样 runtime 的治理能力才是真实存在的。

---

## 第六步：把 `to_observation()` 做成可扩展机制

而不是所有工具一律 JSON dump。  
可以考虑：

- 每个工具自定义 `format_observation(output)`
- 或者 executor 根据 tool_name 分派 serializer

这是后面让 agent 真正变聪明的关键点之一。

---

# 7. 一个更合理的演进方向

如果我站在 Agent 研究者角度，给你这套代码一个演进路线，我会建议这样走：

## 阶段 1：工具层统一化
目标：

- 统一 ToolResult
- 统一 args schema
- 统一 tool definition 导出
- 统一依赖注入

## 阶段 2：执行治理增强
目标：

- timeout
- retry
- circuit breaker
- structured logging
- tracing

## 阶段 3：observation 层精细化
目标：

- 不同工具返回不同风格 observation
- 压缩 token
- 提高 LLM 下一轮决策质量

## 阶段 4：和 Agent Loop 深度耦合
目标：

- tool call message 标准化
- observation 写回消息历史
- step state 跟踪
- reasoning + action + observation 闭环

---

# 8. 你现在这套代码最大的优点是什么

虽然我上面提了很多问题，但你这套代码有一个很大的优点：

> 它已经是“runtime 思维”了，而不是“把几个函数凑一起”。

这点很重要。

很多初学者写工具层的时候，会直接这样做：

```python
if tool_name == "xxx":
    ...
elif tool_name == "yyy":
    ...
```

这种代码能跑，但没有 runtime 结构。

而你已经有：

- 抽象基类
- 注册中心
- 执行器
- 结果包装
- observation 转换
- agent-specific tool pack

这说明你已经在用框架设计的思路看问题了。

---

# 9. 对初学者来说，应该重点学什么

如果你是为了“学习 tool 工具实现”，那最值得盯紧的不是所有细节，而是这 5 个核心思想：

## 9.1 工具不是普通函数，而是受控动作接口
工具的意义不是“帮忙执行一段代码”，而是给模型提供一个**受约束的外部能力**。

## 9.2 schema 很重要
工具输入一定要强约束，因为 LLM 不是完全可靠的调用方。

## 9.3 结果必须标准化
不然 runtime 根本没法统一处理。

## 9.4 执行层必须兜底
工具可能失败、超时、返回脏数据，所以 executor/safe_execute 这层必不可少。

## 9.5 observation 才是 Agent 闭环的关键
工具结果的真正价值，不是“返回给用户”，而是“形成下一轮推理的观察”。

---

# 10. 最后的结论

你的这套代码已经具备了一个自研 Agent Tool Runtime 的核心雏形，尤其适合学习，因为：

- 架构分层是清楚的
- 抽象思路是对的
- 和主流 Agent Runtime 的核心思想一致
- 问题也很典型，正好适合拿来练手改进

如果用一句话概括现在的状态：

> 这不是“不会设计”，而是“设计方向对了，但统一性、类型约束、依赖注入和执行治理还没完全收口”。

所以你接下来最值得做的，不是再继续堆工具数量，而是先把这 4 件事打稳：

1. 统一 `ToolResult`
2. 正式接入 `args_schema`
3. 改好依赖注入
4. 补齐 timeout / observation 策略

这样你这套工具层，就会从“能跑的骨架”进化成“真正像一个 runtime 的工具系统”。

---

# 11. 建议你下一步继续学习的内容

建议按照这个顺序往下学：

1. `ToolResult / ExecutionResult / observation` 三者分层关系
2. `args_schema` 如何自动生成 OpenAI function schema
3. dependency injection 在 Agent Runtime 里的作用
4. timeout / retry / tracing 怎么进入 executor
5. tool result 为什么不能直接裸写回用户，而要先进入 observation

---

# 12. 可直接落地的下一版重构目标

你下一版可以先只做这一小步：

- 修掉 `ToolResult(data=...)`
- 给 `BaseTool` 增加 `args_schema`
- 在 `safe_execute()` 中统一做 Pydantic 校验
- 在 `get_definition()` 中自动导出 schema

如果这一步完成，你的工具系统会马上整洁很多。

