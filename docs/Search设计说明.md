# Search 设计说明

## 概述

Search 模块提供统一的搜索能力，支持关键词搜索、语义搜索和混合搜索。系统可用于用户搜索、Agent 内部检索、Topic 查找、Entity 查找和历史案例搜索。

## 架构

```
app/search/
├── __init__.py
├── service.py              # SearchService 主服务
├── keyword_search.py       # 关键词搜索
├── semantic_search.py      # 语义搜索
├── hybrid_search.py        # 混合搜索
├── query_builder.py        # SQL 查询构建器
├── result_formatter.py     # 结果格式化
├── semantic_result_merger.py # 结果合并
├── ranking.py              # 搜索结果排序
├── explain.py              # 搜索解释
└── policies.py             # 搜索策略
```

## 核心组件

### 1. SearchService

主服务类，协调各种搜索方式：

```python
service = SearchService(
    keyword_search=keyword_search,
    semantic_search=semantic_search,
    ranker=ranker,
)

# 执行搜索
response = await service.search(query)

# 搜索特定类型
topics = await service.search_topics(query)
entities = await service.search_entities(query)
history = await service.search_history(query)
```

### 2. SearchQueryDTO

搜索查询参数：

```python
query = SearchQueryDTO(
    query="AI agent framework",
    board_filter=["ai", "engineering"],
    content_type_filter=[SearchContentType.TOPIC],
    tags=["python", "llm"],
    date_from=datetime(2024, 1, 1),
    date_to=datetime.now(),
    top_k=20,
    semantic_enabled=True,
    mode=SearchMode.HYBRID,
)
```

### 3. SearchResultItemDTO

搜索结果项：

| 字段 | 说明 |
|------|------|
| id | 结果 ID |
| content_type | 内容类型 (topic/item/entity/history) |
| score | 相关性分数 |
| title | 标题 |
| summary | 摘要 |
| matched_by | 匹配方式 (keyword/semantic/hybrid) |
| keyword_score | 关键词分数 |
| semantic_score | 语义分数 |
| highlights | 高亮片段 |

## 搜索模式

### 1. Keyword Search（关键词搜索）

基于 PostgreSQL 全文搜索：

```python
# 支持的搜索方式
- 标题搜索
- 摘要搜索
- 标签过滤
- 板块/内容类型/日期过滤
```

特点：
- 精确匹配
- 支持复杂过滤
- 快速响应

### 2. Semantic Search（语义搜索）

基于向量嵌入的相似度搜索：

```python
# 支持的功能
- 查询嵌入
- 相似 Topic/Item/Entity 搜索
- 最小分数过滤
```

特点：
- 语义理解
- 找到标题不完全匹配但语义相关的内容
- 支持相似内容推荐

### 3. Hybrid Search（混合搜索）

结合关键词和语义搜索：

```python
# 合并策略
- weighted: 加权组合
- rrf: Reciprocal Rank Fusion
- interleaved: 交替合并
```

特点：
- 综合两种搜索的优势
- 混合匹配加分
- 可配置权重

## 搜索策略

系统提供预配置的搜索策略：

| 策略 | 关键词权重 | 语义权重 | 适用场景 |
|------|-----------|---------|---------|
| user_search | 50% | 50% | 用户搜索 |
| topic_lookup | 70% | 30% | Topic 查找 |
| entity_lookup | 100% | 0% | Entity 查找 |
| historical_case_lookup | 30% | 70% | 历史案例 |
| agent_retrieval | 40% | 60% | Agent 检索 |
| similar_content | 0% | 100% | 相似内容 |

使用策略：

```python
from app.search.policies import SearchPolicies, SearchPolicyMode

# 获取预定义策略
policy = SearchPolicies.get_policy(SearchPolicyMode.USER_SEARCH)

# 自定义策略
policy = SearchPolicies.customize(
    SearchPolicyMode.USER_SEARCH,
    max_results=50,
    min_score=0.3,
)
```

## 结果合并

### Weighted Merge

```python
combined_score = keyword_score * keyword_weight + semantic_score * semantic_weight
```

### RRF (Reciprocal Rank Fusion)

```python
rrf_score = sum(1 / (k + rank)) for each result list
# k 默认为 60
```

### Interleaved

交替从关键词和语义结果中选取，保持多样性。

## 搜索排序

搜索结果可应用额外排序因素：

```python
ranker = SearchRanker(
    recency_weight=0.1,      # 时效性加分
    board_match_weight=0.1,  # 板块匹配加分
    review_weight=0.1,       # 审核通过加分
)
```

## 搜索解释

每个搜索结果可生成解释：

```python
explainer = SearchExplainer()
explanation = explainer.explain_result(result, query)

# 返回
{
    "keyword_matches": [...],
    "semantic_similarity": 0.85,
    "score_components": {...},
    "explanation_text": "Matched by both keyword and semantic search..."
}
```

## API 接口

### 通用搜索

```
GET /search?q=query&board=ai&mode=hybrid
```

### 特定类型搜索

```
GET /search/topics?q=query
GET /search/entities?q=query
GET /search/history?q=query
```

### 相似内容

```
GET /search/similar/{content_type}/{item_id}
```

### 搜索建议

```
GET /search/suggest?q=prefix
```

### 可用过滤器

```
GET /search/filters
```

## 性能优化

1. **查询构建器**：高效构建 SQL 查询
2. **结果缓存**：可缓存热门查询结果
3. **批量嵌入**：批量处理查询嵌入
4. **分页**：支持高效分页

## 扩展

### 添加新的搜索策略

```python
policy = SearchPolicyConfig(
    mode=SearchPolicyMode.CUSTOM,
    keyword_enabled=True,
    semantic_enabled=True,
    keyword_weight=0.6,
    semantic_weight=0.4,
    merge_strategy="rrf",
)
```

### 自定义结果格式化

```python
formatter = SearchResultFormatter()
result = formatter.format_topic_result(
    row,
    score=0.9,
    matched_by="hybrid",
    highlights={"title": ["<mark>AI</mark> agent"]},
)
```

## 监控

- 搜索延迟
- 查询分布
- 零结果查询
- 点击率
