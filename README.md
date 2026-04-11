# NewsAgent

AI 驱动的新闻聚合与话题分析系统。

## 项目定位

NewsAgent 是一个智能新闻聚合平台，能够：
- 从多种来源（RSS、网页、GitHub、arXiv 等）采集内容
- 自动解析、清洗、标准化内容
- 基于 AI 进行话题聚合与分析
- 提供结构化的信息流

## 当前阶段

**Week 1: 项目骨架与基础设施** ✅ 已完成

已完成：
- [x] 项目目录结构
- [x] 依赖管理 (pyproject.toml)
- [x] 环境变量模板
- [x] 最小 FastAPI 入口
- [x] 配置系统 (pydantic-settings)
- [x] 日志系统 (统一格式)
- [x] 数据库连接 (异步 SQLAlchemy)
- [x] Alembic 迁移环境
- [x] Contracts 层 (DTO + Protocol)
- [x] 基础测试

## 快速开始

### 环境要求

- Python 3.11+
- PostgreSQL 15+
- Redis (可选)

### 安装

```bash
# 克隆项目
git clone <repo-url>
cd newsagent

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 安装依赖
pip install -e ".[dev,test]"

# 复制环境变量
cp .env.example .env
# 编辑 .env 填入实际配置
```

### 启动服务

```bash
uvicorn app.api.app:app --reload
```

### 验证

访问 http://localhost:8000/health 应返回：
```json
{
  "status": "healthy",
  "app_name": "NewsAgent",
  "environment": "development",
  "debug": false
}
```

### 运行测试

```bash
pytest
```

## 项目结构

```
newsagent/
├── app/
│   ├── api/               # FastAPI 路由与入口
│   │   ├── app.py         # 应用入口
│   │   └── dependencies.py # 依赖注入
│   ├── bootstrap/         # 启动配置
│   │   ├── settings.py    # 配置管理
│   │   ├── logging.py     # 日志系统
│   │   └── lifecycle.py   # 生命周期管理
│   ├── common/            # 通用工具
│   │   ├── enums.py       # 全局枚举
│   │   └── exceptions.py  # 异常定义
│   ├── contracts/         # 协议与 DTO
│   │   ├── dto/           # 数据传输对象
│   │   └── protocols/     # 接口协议
│   ├── storage/           # 存储层
│   │   └── db/            # 数据库相关
│   └── tests/             # 应用测试
├── alembic/               # 数据库迁移
├── tests/                 # 项目级测试
│   ├── unit/              # 单元测试
│   └── integration/       # 集成测试
├── docs/                  # 文档
├── pyproject.toml         # 项目配置与依赖
├── alembic.ini            # Alembic 配置
├── .env.example           # 环境变量模板
└── README.md
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

## License

MIT
