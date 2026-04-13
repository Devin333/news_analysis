# Ranking 设计说明

## 概述

Ranking 模块负责对 Topic 进行排序，决定"什么更值得先看"。系统支持多种排序策略，可根据不同场景（新闻、技术、首页、趋势）应用不同的排序逻辑。

## 架构

```
app/ranking/
├── __init__.py
├── service.py           # RankingService 主服务
├── features.py          # 特征计算函数
├── feature_provider.py  # 特征提取器
├── tracing.py           # 排序日志追踪
└── strategies/
    ├── __init__.py
    ├── base.py              # 基础策略类
    ├── news_ranking.py      # 新闻排序策略
    ├── tech_ranking.py      # 技术排序策略
    ├── homepage_ranking.py  # 首页排序策略
    ├── trend_ranking.py     # 趋势排序策略
    └── report_selection.py  # 报告选题策略
```

## 核心组件

### 1. RankingService

主服务类，协调特征提取和策略应用：

```python
service = RankingService(
    feature_provider=feature_provider,
    strategies={"news_feed": NewsRankingStrategy()}
)

# 对单个 topic 打分
score = await service.score_topic(topic_id, context)

# 对多个 topic 排序
ranked = await service.rank_topics(topic_ids, context)
```

### 2. RankingFeatureDTO

排序特征数据结构：

| 特征 | 说明 | 范围 |
|------|------|------|
| recency_score | 时效性分数 | 0-1 |
| stale_penalty | 过期惩罚 | 0-1 |
| source_authority_score | 来源权威性 | 0-1 |
| source_diversity_score | 来源多样性 | 0-1 |
| topic_heat_score | 话题热度 | 0-1 |
| trend_signal_score | 趋势信号 | 0-1 |
| analyst_importance_score | 分析师重要性评估 | 0-1 |
| historian_novelty_score | 历史学家新颖性评估 | 0-1 |
| review_pass_bonus | 审核通过加分 | 0-1 |
| homepage_candidate_score | 首页候选分数 | 0-1 |

### 3. RankingContextDTO

排序上下文：

```python
context = RankingContextDTO(
    context_name="news_feed",
    board_type="ai",
    time_window_hours=24,
    max_results=50,
    include_unreviewed=False,
)
```

## 排序策略

### News Ranking

新闻排序，强调时效性和来源可信度：

| 特征 | 权重 |
|------|------|
| recency | 30% |
| source_authority | 15% |
| trusted_source | 15% |
| topic_heat | 10% |
| source_diversity | 10% |
| review_bonus | 10% |
| analyst_importance | 5% |
| trend_signal | 5% |

### Tech Ranking

技术排序，强调新颖性和趋势：

| 特征 | 权重 |
|------|------|
| historian_novelty | 20% |
| analyst_importance | 15% |
| trend_signal | 15% |
| trend | 10% |
| source_diversity | 10% |
| recency | 10% |
| topic_size | 10% |
| review_bonus | 5% |
| source_authority | 5% |

### Homepage Ranking

首页排序，强调整体重要性和板块平衡：

| 特征 | 权重 |
|------|------|
| homepage_candidate | 25% |
| review_bonus | 20% |
| analyst_importance | 15% |
| trend_signal | 10% |
| recency | 10% |
| source_diversity | 10% |
| topic_heat | 10% |

特点：
- 必须通过审核
- 板块平衡（每个板块最多 5 条）
- 去重/去相似

### Trend Ranking

趋势排序，强调趋势信号和热度：

| 特征 | 权重 |
|------|------|
| trend_signal | 30% |
| trend | 20% |
| topic_heat | 15% |
| source_diversity | 10% |
| analyst_importance | 10% |
| recency | 10% |
| topic_size | 5% |

特点：
- 根据趋势阶段（emerging/growing/peak）额外加分
- 支持新兴趋势和热门趋势两种子策略

## 特征计算

### 时效性分数 (recency_score)

```python
# 指数衰减，半衰期 = time_window_hours
score = e^(-decay_rate * age_hours)
```

### 来源多样性分数 (source_diversity_score)

```python
# 对数缩放
score = log(source_count + 1) / log(max_sources + 1)
```

### 分析师重要性分数 (analyst_importance_score)

```python
score = confidence * 0.4 + normalized_momentum * 0.3 + content_presence * 0.3
```

### 首页候选分数 (homepage_candidate_score)

```python
# 必须满足：source_count >= 2, item_count >= 2, review_passed
score = recency * 0.3 + trend * 0.3 + diversity * 0.2 + size * 0.2
```

## API 接口

### Feed API

```
GET /feed/news          # 新闻 Feed
GET /feed/tech          # 技术 Feed
GET /feed/homepage      # 首页 Feed
GET /feed/board/{type}  # 板块 Feed
```

### Ranking Debug API

```
GET /ranking/topic/{id}              # 查看 topic 排序详情
GET /ranking/context/{name}          # 查看上下文排序结果
GET /ranking/topic/{id}/history      # 查看排序历史
GET /ranking/compare?topic_ids=1,2,3 # 比较多个 topic
GET /ranking/strategies              # 查看所有策略
GET /ranking/debug/features/{id}     # 查看原始特征
GET /ranking/logs/recent             # 查看最近排序日志
```

## 可解释性

每次排序都会记录：

1. **特征值**：所有计算出的特征
2. **组件分数**：每个特征的加权分数
3. **最终分数**：总分
4. **Top Factors**：影响最大的因素
5. **解释文本**：人类可读的解释

示例：
```json
{
  "topic_id": 123,
  "final_score": 0.75,
  "component_scores": {
    "recency": 0.27,
    "source_authority": 0.12,
    "trend_signal": 0.15
  },
  "top_factors": ["recency", "trend_signal", "source_authority"],
  "explanation": "Top factors: recency(+0.27), trend_signal(+0.15), source_authority(+0.12)"
}
```

## 扩展策略

实现新策略只需继承 `BaseRankingStrategy`：

```python
class CustomRankingStrategy(BaseRankingStrategy):
    def __init__(self):
        super().__init__("custom_ranking")
    
    def get_weights(self, context: RankingContextDTO) -> dict[str, float]:
        return {
            "recency": 0.3,
            "trend_signal": 0.3,
            # ...
        }
```

然后注册到 RankingService：

```python
service.register_strategy("custom_feed", CustomRankingStrategy())
```

## 性能优化

1. **特征缓存**：`CachedFeatureProvider` 支持 TTL 缓存
2. **批量处理**：`get_features_batch` 批量获取特征
3. **惰性计算**：只计算策略需要的特征

## 监控

- 排序日志存储在 `ranking_logs` 表
- 支持按 topic、context、时间查询
- 可追踪排序变化趋势
