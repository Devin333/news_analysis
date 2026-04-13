# NewsAgent

AI 驱动的新闻聚合与话题分析系统。

## 项目定位

NewsAgent 是一个完整的 AI 科技情报平台，具备：
- 多源内容采集（RSS、网页、GitHub、arXiv）
- 自动解析、清洗、标准化
- AI 话题聚合与分析
- 多 Agent 编辑部（Historian, Analyst, Writer, Reviewer）
- 智能排序与搜索
- 订阅与人工干预
- 自动化评估与成本控制

## 快速开始

### 1. 环境要求

- Python 3.11+
- PostgreSQL 15+
- Redis (可选，用于缓存)

### 2. 安装依赖

```bash
# 克隆项目
git clone <repo-url>
cd NewsAgent

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 安装依赖
pip install -e ".[dev,test]"
```

### 3. 配置环境变量

```bash
# 复制示例配置
cp .env.example .env

# 编辑 .env 文件
```

必须配置的变量：

```env
# 数据库连接
DB_URL=postgresql+asyncpg://postgres:password@localhost:5432/newsagent

# LLM API（选择一个）
LLM_PROVIDER=openai
LLM_API_KEY=sk-your-api-key-here

# 或使用其他兼容 API
LLM_BASE_URL=https://api.openai.com/v1
```

### 4. 初始化数据库

```bash
# 创建数据库（PostgreSQL）
createdb newsagent

# 运行迁移
alembic upgrade head
```

### 5. 启动服务

```bash
# 开发模式启动
uvicorn app.api.app:app --reload --host 0.0.0.0 --port 8000
```

### 6. 验证

访问 http://localhost:8000/health

```json
{
  "status": "healthy",
  "app_name": "NewsAgent",
  "environment": "development"
}
```

访问 http://localhost:8000/docs 查看 API 文档。

## 核心功能

### API 端点

| 端点 | 说明 |
|------|------|
| `GET /health` | 健康检查 |
| `GET /sources` | 数据源列表 |
| `GET /feed` | Feed 流 |
| `GET /trends` | 趋势列表 |
| `GET /search` | 搜索 |
| `GET /subscriptions` | 订阅管理 |
| `GET /admin/*` | 运营后台 |

### 脚本工具

```bash
# Topic 增强
python scripts/run_topic_enrichment.py --topic-id 100

# 运行 Historian
python scripts/run_historian_for_topic.py --topic-id 100

# 运行 Writer
python scripts/run_writer_for_topic.py --topic-id 100

# 生成日报
python scripts/generate_daily_report.py

# 生成周报
python scripts/generate_weekly_report.py

# 运行评估
python scripts/run_eval.py --all

# 调试排序
python scripts/debug_ranking.py --topic-id 100

# 调试搜索
python scripts/debug_search.py --query "AI agent"

# 管理员操作
python scripts/admin_rerun_topic.py --topic-id 100 --agent historian
python scripts/admin_merge_topics.py --target 100 --sources 101 102
```

## 项目结构

```
NewsAgent/
├── app/
│   ├── api/                 # FastAPI 路由
│   │   └── routers/         # 各模块路由
│   ├── agents/              # Agent 实现
│   ├── agent_runtime/       # Agent 运行时
│   ├── contracts/           # 协议与 DTO
│   ├── editorial/           # 编辑服务
│   ├── embeddings/          # 向量嵌入
│   ├── evaluation/          # 评估模块
│   ├── memory/              # 记忆系统
│   ├── monitoring/          # 监控与成本
│   ├── ranking/             # 排序模块
│   ├── search/              # 搜索模块
│   ├── subscription/        # 订阅模块
│   ├── storage/             # 存储层
│   └── ...
├── alembic/                 # 数据库迁移
├── scripts/                 # 脚本工具
├── tests/                   # 测试
├── docs/                    # 文档
└── ...
```

## 配置说明

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| APP_ENV | 运行环境 | development |
| APP_NAME | 应用名称 | NewsAgent |
| APP_DEBUG | 调试模式 | false |
| DB_URL | 数据库连接 | postgresql+asyncpg://... |
| REDIS_URL | Redis 连接 | redis://localhost:6379/0 |
| LLM_PROVIDER | LLM 提供商 | openai |
| LLM_API_KEY | LLM API Key | - |
| LLM_BASE_URL | LLM API 地址 | https://api.openai.com/v1 |
| EMBEDDING_PROVIDER | Embedding 提供商 | openai |

## 开发

```bash
# 运行测试
pytest

# 代码检查
ruff check .

# 类型检查
mypy app

# 数据库迁移
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## 文档

- [Week 1 架构基线](docs/Week1架构基线.md)
- [Week 9-12 复杂记忆与历史分析里程碑](docs/Week9-12复杂记忆与历史分析里程碑.md)
- [Week 13-16 多Agent编辑部与前端显化里程碑](docs/Week13-16多Agent编辑部与前端显化里程碑.md)
- [Week 17-20 排序搜索订阅人工干预评估成本控制里程碑](docs/Week17-20排序搜索订阅人工干预评估成本控制里程碑.md)
- [Ranking 设计说明](docs/Ranking设计说明.md)
- [Search 设计说明](docs/Search设计说明.md)
- [Subscription 设计说明](docs/Subscription设计说明.md)
- [Human-in-the-loop 设计说明](docs/Human-in-the-loop设计说明.md)
- [Evaluation 体系说明](docs/Evaluation体系说明.md)
- [成本优化策略说明](docs/成本优化策略说明.md)

## 系统能力

### 产品能力
- ✅ 首页/Feed 排序
- ✅ 趋势排序
- ✅ 搜索（关键词+语义）
- ✅ 订阅追踪
- ✅ 周报/日报生成
- ✅ 人工审核与修正

### 运维能力
- ✅ Ranking Explain
- ✅ Agent Run Trace
- ✅ Review Logs
- ✅ Evaluation Runs
- ✅ Cost Logs

### 优化能力
- ✅ 评估体系
- ✅ 成本控制策略
- ✅ Human-in-the-loop 纠偏
- ✅ 订阅驱动长期观察

## License

MIT
