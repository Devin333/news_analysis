# Evaluation 体系说明

## 概述

Evaluation 模块提供系统质量的自动化评估能力，让系统从"感觉还行"升级到"可量化、可追踪"。

## 指标体系

### 分类指标 (Classification)

| 指标 | 说明 | 阈值 |
|------|------|------|
| board_classification_accuracy | 板块分类准确率 | ≥ 0.85 |
| content_type_classification_accuracy | 内容类型分类准确率 | ≥ 0.80 |

### 聚类指标 (Clustering)

| 指标 | 说明 | 阈值 |
|------|------|------|
| topic_merge_precision | 主题合并精确率 | ≥ 0.70 |
| topic_merge_recall | 主题合并召回率 | ≥ 0.60 |
| topic_merge_f1 | 主题合并 F1 分数 | - |

### Agent 质量指标

| 指标 | 说明 | 阈值 |
|------|------|------|
| historian_consistency | 历史学家输出一致性 | ≥ 0.75 |
| analyst_value_quality | 分析师价值质量 | ≥ 0.70 |
| writer_faithfulness | 写手忠实度 | ≥ 0.80 |
| reviewer_catch_rate | 审稿人问题捕获率 | ≥ 0.85 |

### 趋势检测指标

| 指标 | 说明 | 阈值 |
|------|------|------|
| trend_detection_precision | 趋势检测精确率 | ≥ 0.60 |
| trend_detection_recall | 趋势检测召回率 | - |

### 系统指标

| 指标 | 说明 | 阈值 |
|------|------|------|
| pipeline_success_rate | 流水线成功率 | ≥ 0.95 |
| average_latency | 平均延迟 | - |

## 数据集结构

### 样本格式

```json
{
  "id": "sample_001",
  "input": {
    "title": "...",
    "summary": "...",
    "source": "..."
  },
  "expected": {
    "board_type": "tech"
  },
  "metadata": {},
  "tags": ["ai", "llm"]
}
```

### 数据集文件

```
app/evaluation/fixtures/
├── board_classification_v1.0.json
├── topic_merge_v1.0.json
├── historian_quality_v1.0.json
└── writer_quality_v1.0.json
```

## 使用方式

### 命令行

```bash
# 运行单个评估
python scripts/run_eval.py --type board_classification

# 运行所有评估
python scripts/run_eval.py --all

# 限制样本数
python scripts/run_eval.py --type topic_merge --limit 10

# 输出到文件
python scripts/run_eval.py --all --output results.json
```

### 代码调用

```python
from app.evaluation.runner import EvaluationRunner
from app.evaluation.schemas import EvaluationConfigDTO, EvaluationType

runner = EvaluationRunner()

# 运行评估
config = EvaluationConfigDTO(
    evaluation_type=EvaluationType.BOARD_CLASSIFICATION,
    sample_limit=100,
)
run = runner.run(config)

# 查看结果
print(f"Passed: {run.summary.get('passed')}")
for metric in run.metrics:
    print(f"  {metric.name}: {metric.value:.4f}")
```

## 扩展评估

### 添加新指标

```python
# app/evaluation/metrics.py

def my_custom_metric(
    predictions: list[str],
    labels: list[str],
) -> MetricResult:
    # 计算指标
    value = ...
    
    return MetricResult(
        name="my_custom_metric",
        category=MetricCategory.AGENT,
        value=value,
        sample_size=len(predictions),
    )
```

### 添加新数据集

1. 创建 JSON 文件：`app/evaluation/fixtures/my_eval_v1.0.json`
2. 在 `EvaluationType` 添加新类型
3. 在 `EvaluationRunner` 添加评估器

## 最佳实践

1. **定期运行**: 每次发布前运行完整评估
2. **持续扩充数据集**: 将发现的问题案例加入数据集
3. **设置合理阈值**: 根据业务需求调整阈值
4. **追踪趋势**: 保存历史评估结果，观察指标变化
