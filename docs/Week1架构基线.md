# Week 1 架构基线

## 概述

Week 1 完成了 NewsAgent 项目的基础设施搭建，建立了从"想法"到"可运行系统底盘"的完整工程骨架。

## 完成的模块

### 1. 项目结构与依赖管理

**文件**: [`pyproject.toml`](pyproject.toml)

- 使用现代 Python 项目配置
- 依赖分组: runtime, dev, test
- 配置代码检查工具: ruff, mypy
- 配置测试工具: pytest, pytest-asyncio

**目录结构**:
```
newsagent/
├── app/
│   ├── api/           # FastAPI 路由与入口
│   ├── bootstrap/     # 启动配置
│   ├── common/        # 通用工具
│   ├── contracts/     # 协议与 DTO
│   ├── storage/       # 存储层
│   └── tests/         # 测试
├── alembic/           # 数据库迁移
├── tests/             # 项目级测试
└── pyproject.toml
```

### 2. 配置系统

**文件**: [`app/bootstrap/settings.py`](app/bootstrap/settings.py)

- 使用 pydantic-settings 管理配置
- 按模块拆分: AppSettings, DatabaseSettings, RedisSettings, LLMSettings
- 支持环境变量前缀 (env_prefix)
- 提供 get_settings() 缓存函数

**环境变量模板**: [`.env.example`](.env.example)

### 3. 日志系统

**文件**: [`app/bootstrap/logging.py`](app/bootstrap/logging.py)

- 统一日志格式 (带颜色输出)
- 支持 debug 模式
- 提供 get_logger(name) 工厂函数
- LogContext 用于结构化日志上下文

### 4. 数据库层

**文件**:
- [`app/storage/db/base.py`](app/storage/db/base.py) - SQLAlchemy Base
- [`app/storage/db/models_base.py`](app/storage/db/models_base.py) - 通用 ORM mixin
- [`app/storage/db/session.py`](app/storage/db/session.py) - 异步 session 管理

**特性**:
- 异步引擎 (asyncpg)
- 连接池配置
- ping_database() 连通性检查

### 5. 数据库迁移

**文件**:
- [`alembic.ini`](alembic.ini) - Alembic 配置
- [`alembic/env.py`](alembic/env.py) - 异步迁移环境

**特性**:
- 支持异步迁移
- 从 app settings 读取数据库 URL
- 文件名带时间戳

### 6. 全局枚举与异常

**文件**:
- [`app/common/enums.py`](app/common/enums.py) - Environment, BoardType, SourceType, ContentType
- [`app/common/exceptions.py`](app/common/exceptions.py) - AppError, ConfigError, ValidationError, InfrastructureError

### 7. Contracts 层

**DTOs**:
- [`app/contracts/dto/source.py`](app/contracts/dto/source.py) - SourceCreate, SourceUpdate, SourceRead
- [`app/contracts/dto/raw_item.py`](app/contracts/dto/raw_item.py) - RawItemDTO
- [`app/contracts/dto/normalized_item.py`](app/contracts/dto/normalized_item.py) - NormalizedItemDTO

**Protocols**:
- [`app/contracts/protocols/repositories.py`](app/contracts/protocols/repositories.py) - SourceRepositoryProtocol, RawItemRepositoryProtocol, NormalizedItemRepositoryProtocol

### 8. 应用生命周期

**文件**: [`app/bootstrap/lifecycle.py`](app/bootstrap/lifecycle.py)

- FastAPI lifespan 管理
- 启动时初始化日志
- 启动时检查数据库连通性

### 9. FastAPI 入口

**文件**: [`app/api/app.py`](app/api/app.py)

- /health 健康检查端点
- 返回应用配置信息
- 集成 settings 依赖注入

### 10. 测试基础

**文件**:
- [`tests/unit/test_settings.py`](tests/unit/test_settings.py) - 配置单元测试
- [`tests/integration/test_health.py`](tests/integration/test_health.py) - 健康检查集成测试

## 验收标准

- [x] 项目目录清晰
- [x] `uvicorn app.api.app:app --reload` 能启动
- [x] /health 返回成功
- [x] .env.example 完成
- [x] 配置可以从 env 读取
- [x] 日志系统正常工作
- [x] 数据库连接层建立
- [x] Alembic 可运行
- [x] DTO 与 Protocol 定义完成
- [x] 基础测试可运行

## 下一步 (Week 2)

Week 2 将在此基础上:
1. 实现 Source ORM 模型与 Repository
2. 实现 RawItem / NormalizedItem ORM 模型
3. 实现 Unit of Work 模式
4. 设计 Agent Runtime 顶层结构
