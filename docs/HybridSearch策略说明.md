# Hybrid Search 策略说明

## 概述

Hybrid Search 结合关键词搜索和语义搜索的优势，提供更全面的搜索结果。本文档说明混合搜索的策略配置和使用方法。

## 为什么需要混合搜索

| 搜索类型 | 优势 | 劣势 |
|---------|------|------|
| 关键词搜索 | 精确匹配、快速、可解释 | 无法理解语义、同义词问题 |
| 语义搜索 | 理解语义、找到相关内容 | 可能遗漏精确匹配、较慢 |
| 混合搜索 | 综合两者优势 | 需要权衡配置 |

## 合并策略

### 1. Weighted Merge（加权合并）

最常用的合并方式，按权重组合分数：

```python
combined_score = keyword_score * keyword_weight + semantic_score * semantic_weight
```

适用场景：
- 通用搜索
- 需要平衡精确和语义匹配

配置示例：
```python
policy = SearchPolicyConfig(
    keyword_weight=0.5,
    semantic_weight=0.5,
    merge_strategy="weighted",
)
```

### 2. RRF（Reciprocal Rank Fusion）

基于排名的合并，不依赖原始分数：

```python
rrf_score = sum(1 / (k + rank)) for each result list
```

优势：
- 不受分数尺度影响
- 对异构结果更公平

适用场景：
- 关键词和语义分数尺度差异大
- 需要更稳定的合并结果

配置示例：
```python
policy = SearchPolicyConfig(
    merge_strategy="rrf",
)
```

### 3. Interleaved（交替合并）

交替从两个结果列表中选取：

```
结果: K1, S1, K2, S2, K3, S3, ...
```

优势：
- 保证两种搜索结果都有展示
- 简单直观

适用场景：
- 探索性搜索
- 需要多样性

## 搜索策略配置

### SearchPolicyConfig 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| mode | SearchPolicyMode | - | 策略模式 |
| keyword_enabled | bool | True | 启用关键词搜索 |
| semantic_enabled | bool | True | 启用语义搜索 |
| keyword_weight | float | 0.5 | 关键词权重 |
| semantic_weight | float | 0.5 | 语义权重 |
| min_score | float | 0.0 | 最小分数阈值 |
| boost_hybrid | bool | True | 混合匹配加分 |
| hybrid_boost_factor | float | 1.2 | 混合加分系数 |
| merge_strategy | str | "weighted" | 合并策略 |
| max_results | int | 20 | 最大结果数 |
| include_explanation | bool | False | 包含解释 |

### 预定义策略

#### 1. user_search（用户搜索）

```python
SearchPolicyConfig(
    mode=SearchPolicyMode.USER_SEARCH,
    keyword_weight=0.5,
    semantic_weight=0.5,
    min_score=0.1,
    boost_hybrid=True,
    merge_strategy="weighted",
)
```

特点：平衡、通用、适合大多数用户查询

#### 2. topic_lookup（Topic 查找）

```python
SearchPolicyConfig(
    mode=SearchPolicyMode.TOPIC_LOOKUP,
    keyword_weight=0.7,
    semantic_weight=0.3,
    min_score=0.2,
)
```

特点：偏向精确匹配，适合查找特定 Topic

#### 3. entity_lookup（Entity 查找）

```python
SearchPolicyConfig(
    mode=SearchPolicyMode.ENTITY_LOOKUP,
    keyword_enabled=True,
    semantic_enabled=False,
    keyword_weight=1.0,
)
```

特点：纯关键词搜索，适合实体名称查找

#### 4. historical_case_lookup（历史案例查找）

```python
SearchPolicyConfig(
    mode=SearchPolicyMode.HISTORICAL_CASE_LOOKUP,
    keyword_weight=0.3,
    semantic_weight=0.7,
    min_score=0.4,
    merge_strategy="rrf",
    include_explanation=True,
)
```

特点：偏向语义相似，适合找相关历史案例

#### 5. agent_retrieval（Agent 检索）

```python
SearchPolicyConfig(
    mode=SearchPolicyMode.AGENT_RETRIEVAL,
    keyword_weight=0.4,
    semantic_weight=0.6,
    max_results=30,
    merge_strategy="rrf",
)
```

特点：高召回率，适合 Agent 收集上下文

#### 6. similar_content（相似内容）

```python
SearchPolicyConfig(
    mode=SearchPolicyMode.SIMILAR_CONTENT,
    keyword_enabled=False,
    semantic_enabled=True,
    semantic_weight=1.0,
    min_score=0.5,
)
```

特点：纯语义搜索，适合推荐相似内容

## 使用示例

### 基本使用

```python
from app.search.hybrid_search import HybridSearch
from app.search.policies import SearchPolicies

# 创建混合搜索
hybrid = HybridSearch(
    keyword_search=keyword_search,
    semantic_search=semantic_search,
)

# 使用默认策略
response = await hybrid.search(query)

# 使用特定策略
policy = SearchPolicies.topic_lookup()
response = await hybrid.search(query, policy=policy)
```

### 自定义策略

```python
from app.search.policies import SearchPolicies, SearchPolicyMode

# 基于现有策略自定义
policy = SearchPolicies.customize(
    SearchPolicyMode.USER_SEARCH,
    keyword_weight=0.6,
    semantic_weight=0.4,
    max_results=50,
)

response = await hybrid.search(query, policy=policy)
```

### 按模式搜索

```python
response = await hybrid.search_with_policy(
    "AI agent framework",
    SearchPolicyMode.AGENT_RETRIEVAL,
    board_filter=["ai"],
)
```

## 混合匹配加分

当一个结果同时被关键词和语义搜索命中时，可以获得额外加分：

```python
if matched_by_both:
    score *= hybrid_boost_factor  # 默认 1.2
```

这鼓励同时满足精确匹配和语义相关的结果排在前面。

## 调优建议

### 1. 根据查询类型选择策略

| 查询类型 | 推荐策略 |
|---------|---------|
| 精确名称查询 | entity_lookup |
| 概念性查询 | user_search |
| 相似内容推荐 | similar_content |
| Agent 上下文收集 | agent_retrieval |

### 2. 调整权重

- 如果用户反馈"找不到精确匹配"，提高 keyword_weight
- 如果用户反馈"结果不相关"，提高 semantic_weight
- 如果结果太少，降低 min_score

### 3. 选择合并策略

- 分数尺度一致时用 weighted
- 分数尺度不一致时用 rrf
- 需要多样性时用 interleaved

## 监控指标

- 各策略的使用频率
- 混合匹配比例
- 搜索延迟分布
- 用户点击率
