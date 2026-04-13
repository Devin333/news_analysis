# Week 13-16 多 Agent 编辑部与前端显化里程碑

## 概述

Week 13-16 完成了 NewsAgent 系统的"编辑部"能力建设，包括：
- WriterAgent：内容写作
- ReviewerAgent：内容审稿
- TrendHunterAgent：趋势识别
- ReportEditorAgent：报告生成

## 核心能力

### 1. WriterAgent (Week 13)

WriterAgent 负责将分析结果转化为可展示的内容产物。

**输出类型：**
- `FeedCardCopyDTO`：Feed 卡片文案
- `TopicIntroCopyDTO`：Topic 页面导语
- `TrendCardCopyDTO`：趋势卡片文案
- `ReportSectionCopyDTO`：报告段落

**关键原则：**
- Writer 只负责表达，不负责判断
- 基于 Historian/Analyst 的结论写作
- 不允许编造或偏离原始结论

### 2. ReviewerAgent (Week 14)

ReviewerAgent 负责审稿，避免自动生成内容失控。

**审查维度：**
- factual_drift：事实偏离
- unsupported_statement：无依据陈述
- historical_mismatch：历史不匹配
- vague_summary：模糊摘要
- low_information_density：信息密度低
- repetitive_wording：重复用词

**输出状态：**
- approve：通过
- revise：需修改
- reject：拒绝

### 3. TrendHunterAgent (Week 15)

TrendHunterAgent 负责识别趋势。

**趋势阶段：**
- emerging：新兴
- rising：上升
- peak：峰值
- stable：稳定
- declining：下降
- dormant：休眠

**信号类型：**
- growth：增长
- diversity：来源多样性
- recency：近期活跃度
- release：发布信号
- discussion：讨论信号
- github：GitHub 活动
- repeated：重复出现
- burst：突发

### 4. ReportEditorAgent (Week 15-16)

ReportEditorAgent 负责生成日报/周报。

**报告类型：**
- daily：日报
- weekly：周报

**报告结构：**
- 标题
- 执行摘要
- 分节内容
- 编辑部结论
- 后续关注点

## 工作流

### Writer → Reviewer 工作流

```
1. Writer 生成内容
2. Reviewer 审查内容
3. 通过则标记 published
4. 需修改则标记 needs_revision
5. 拒绝则标记 rejected
```

### Trend → Report 工作流

```
1. TrendHunter 扫描 topics
2. 识别 emerging/rising trends
3. ReportEditor 组织报告
4. 生成日报/周报
```

## 数据模型

### TopicCopy 表
存储 Writer 生成的内容。

### ReviewLog 表
存储审稿结果。

### TrendSignal 表
存储趋势信号。

### Report 表
存储生成的报告。

### ReportTopicLink 表
报告与 Topic 的关联。

## API 端点

### Trends API
- `GET /trends` - 列出趋势
- `GET /trends/emerging` - 新兴趋势
- `GET /trends/{topic_id}` - Topic 趋势分析

### Reports API
- `GET /reports` - 列出报告
- `GET /reports/daily/{date}` - 日报
- `GET /reports/weekly/{week_key}` - 周报
- `POST /reports/daily/generate` - 生成日报
- `POST /reports/weekly/generate` - 生成周报

### Admin API
- `GET /admin/agent-runs` - Agent 运行日志
- `GET /admin/reviews` - 审稿日志
- `GET /admin/copies` - 内容列表
- `GET /admin/topics/{id}/debug` - Topic 调试信息

## 前端视图契约

### FeedItemView
Feed 卡片展示字段。

### TopicDetailView
Topic 详情页展示字段。

### TrendCardView
趋势卡片展示字段。

### ReportDetailView
报告详情展示字段。

## 脚本

- `scripts/run_writer_for_topic.py` - 运行 Writer
- `scripts/run_review_for_topic.py` - 运行 Review
- `scripts/generate_daily_report.py` - 生成日报
- `scripts/generate_weekly_report.py` - 生成周报

## 下一步

Week 17+ 可以进入：
- Ranking 排序优化
- Search 搜索能力
- Subscription 订阅系统
- Human-in-the-loop 人工干预
- Evaluation benchmark 评估基准
- Cost optimization 成本优化
